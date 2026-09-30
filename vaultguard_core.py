"""
VaultGuard Core Encryption & Vault Management Engine
"""

import os
import json
import base64
import hashlib
import string
import secrets
from datetime import datetime
from cryptography.fernet import Fernet

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MASTER_DAT = os.path.join(BASE_DIR, "master.dat")
VAULT_ENC = os.path.join(BASE_DIR, "vault.enc")
ROTATION_DAYS = 120

# ----------------------------------------
# CRYPTOGRAPHY HELPERS
# ----------------------------------------

def hash_password(password: str, salt: bytes) -> bytes:
    """Hash password using PBKDF2-HMAC-SHA256."""
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        100000
    )


def create_encryption_key(password: str, salt: bytes) -> bytes:
    """Derive 32-byte Fernet key from password and salt."""
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        100000,
        dklen=32
    )
    return base64.urlsafe_b64encode(key)


def is_master_password_set() -> bool:
    """Check if master password file exists."""
    return os.path.exists(MASTER_DAT)


def create_master_password(password: str) -> tuple[bool, str]:
    """Create salt and hashed master password, then initialize empty vault."""
    try:
        salt = os.urandom(16)
        hashed = hash_password(password, salt)

        with open(MASTER_DAT, "wb") as f:
            f.write(salt)
            f.write(hashed)

        create_vault(password, salt)
        return True, "Master password created successfully!"
    except Exception as e:
        return False, f"Failed to create master password: {e}"


def verify_master_password(password: str) -> tuple[bool, str, dict | None, bytes | None]:
    """Verify master password and load vault data."""
    if not is_master_password_set():
        return False, "No master password configured.", None, None

    try:
        with open(MASTER_DAT, "rb") as f:
            salt = f.read(16)
            saved_hash = f.read()

        entered_hash = hash_password(password, salt)
        if entered_hash == saved_hash:
            vault = load_vault(password, salt)
            return True, "Login successful!", vault, salt
        else:
            return False, "Incorrect master password.", None, None
    except Exception as e:
        return False, f"Error verifying master password: {e}", None, None


# ----------------------------------------
# VAULT STORAGE MANAGEMENT
# ----------------------------------------

def create_vault(password: str, salt: bytes):
    """Initialize encrypted vault file."""
    key = create_encryption_key(password, salt)
    fernet = Fernet(key)
    encrypted_data = fernet.encrypt(b"{}")
    with open(VAULT_ENC, "wb") as f:
        f.write(encrypted_data)


def load_vault(password: str, salt: bytes) -> dict:
    """Decrypt and parse vault data."""
    key = create_encryption_key(password, salt)
    fernet = Fernet(key)

    if not os.path.exists(VAULT_ENC):
        return {}

    try:
        with open(VAULT_ENC, "rb") as f:
            encrypted_data = f.read()

        decrypted_data = fernet.decrypt(encrypted_data)
        vault_data = json.loads(decrypted_data.decode("utf-8"))

        # Ensure last_changed timestamp exists for all accounts
        today_str = datetime.now().strftime("%Y-%m-%d")
        for service, account in vault_data.items():
            if "last_changed" not in account or not account["last_changed"]:
                account["last_changed"] = today_str

        return vault_data
    except Exception as e:
        print(f"Error loading vault: {e}")
        return {}


def save_vault(vault: dict, password: str, salt: bytes) -> bool:
    """Encrypt and write vault dictionary to disk."""
    try:
        key = create_encryption_key(password, salt)
        fernet = Fernet(key)
        vault_json = json.dumps(vault, indent=2)
        encrypted_data = fernet.encrypt(vault_json.encode("utf-8"))

        with open(VAULT_ENC, "wb") as f:
            f.write(encrypted_data)
        return True
    except Exception as e:
        print(f"Error saving vault: {e}")
        return False


# ----------------------------------------
# ACCOUNT HELPERS
# ----------------------------------------

def get_account_status(last_changed_str: str) -> dict:
    """Calculate age, remaining days, and alert status for an account."""
    try:
        last_changed = datetime.strptime(last_changed_str, "%Y-%m-%d")
    except Exception:
        last_changed = datetime.now()

    today = datetime.now()
    days_passed = (today - last_changed).days
    days_remaining = ROTATION_DAYS - days_passed

    if days_remaining > 30:
        badge_text = f"{days_remaining}d left"
        level = "good"
        color = "#10B981"  # Emerald green
    elif days_remaining > 0:
        badge_text = f"{days_remaining}d remaining"
        level = "warning"
        color = "#F59E0B"  # Amber/Yellow
    elif days_remaining == 0:
        badge_text = "Due Today!"
        level = "due"
        color = "#EF4444"  # Red
    else:
        badge_text = f"{abs(days_remaining)}d overdue"
        level = "overdue"
        color = "#DC2626"  # Dark Red

    return {
        "days_passed": days_passed,
        "days_remaining": days_remaining,
        "badge_text": badge_text,
        "level": level,
        "color": color
    }


def generate_password(length: int = 16, upper: bool = True, lower: bool = True, digits: bool = True, symbols: bool = True) -> str:
    """Generate cryptographically secure random password."""
    charset = ""
    if upper:
        charset += string.ascii_uppercase
    if lower:
        charset += string.ascii_lowercase
    if digits:
        charset += string.digits
    if symbols:
        charset += "!@#$%^&*()_+-=[]{}|;:,.<>?"

    if not charset:
        charset = string.ascii_letters + string.digits

    return "".join(secrets.choice(charset) for _ in range(length))


def evaluate_password_strength(password: str) -> dict:
    """Evaluate password strength and return score, label, and hex color."""
    if not password:
        return {"score": 0, "label": "Empty", "color": "#9CA3AF"}

    score = 0
    length = len(password)

    if length >= 8:
        score += 20
    if length >= 12:
        score += 20
    if length >= 16:
        score += 15

    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_symbol = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)

    types_count = sum([has_upper, has_lower, has_digit, has_symbol])
    score += types_count * 11.25
    score = min(100, int(score))

    if score < 40:
        label = "Weak"
        color = "#EF4444"  # Red
    elif score < 70:
        label = "Medium"
        color = "#F59E0B"  # Amber
    elif score < 90:
        label = "Strong"
        color = "#10B981"  # Emerald
    else:
        label = "Very Strong"
        color = "#3B82F6"  # Blue

    return {"score": score, "label": label, "color": color}


def get_vault_stats(vault: dict) -> dict:
    """Calculate overall vault statistics for the dashboard."""
    total = len(vault)
    overdue = 0
    warning = 0
    weak_count = 0
    total_score = 0

    for service, account in vault.items():
        status = get_account_status(account.get("last_changed", ""))
        if status["level"] in ["due", "overdue"]:
            overdue += 1
        elif status["level"] == "warning":
            warning += 1

        pass_eval = evaluate_password_strength(account.get("password", ""))
        total_score += pass_eval["score"]
        if pass_eval["score"] < 50:
            weak_count += 1

    avg_score = int(total_score / total) if total > 0 else 100

    return {
        "total_accounts": total,
        "overdue_count": overdue,
        "warning_count": warning,
        "weak_passwords": weak_count,
        "security_score": avg_score
    }
