"""
VaultGuard Core Engine - Multi-User Architecture & Encryption Engine
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
USERS_FILE = os.path.join(BASE_DIR, "users.json")
VAULTS_DIR = os.path.join(BASE_DIR, "vaults")
ROTATION_DAYS = 120

# Ensure vaults directory exists
os.makedirs(VAULTS_DIR, exist_ok=True)


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


def load_users_db() -> dict:
    """Load user registry database."""
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_users_db(users: dict):
    """Save user registry database."""
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)


def get_user_vault_path(user_id: str) -> str:
    """Get isolated vault file path for a specific user ID."""
    return os.path.join(VAULTS_DIR, f"{user_id}.enc")


# ----------------------------------------
# MULTI-USER REGISTRATION & LOGIN
# ----------------------------------------

def register_user(email: str, password: str) -> tuple[bool, str, dict | None]:
    """Register a new independent user account and initialize their personal vault."""
    email_clean = email.strip().lower()
    if not email_clean or "@" not in email_clean:
        return False, "Invalid email address format.", None

    if len(password) < 6:
        return False, "Master password must be at least 6 characters.", None

    users = load_users_db()

    if email_clean in users:
        return False, "An account with this email already exists!", None

    # Generate random user ID & 16-byte salt
    user_id = hashlib.sha256(email_clean.encode()).hexdigest()[:16]
    salt_bytes = os.urandom(16)
    salt_b64 = base64.b64encode(salt_bytes).decode("utf-8")

    hashed_bytes = hash_password(password, salt_bytes)
    hash_b64 = base64.b64encode(hashed_bytes).decode("utf-8")

    # Store user credentials metadata
    users[email_clean] = {
        "user_id": user_id,
        "email": email_clean,
        "salt": salt_b64,
        "hash": hash_b64,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    save_users_db(users)

    # Initialize empty vault file for new user
    key = create_encryption_key(password, salt_bytes)
    fernet = Fernet(key)
    encrypted_data = fernet.encrypt(b"{}")
    with open(get_user_vault_path(user_id), "wb") as f:
        f.write(encrypted_data)

    user_info = {
        "user_id": user_id,
        "email": email_clean,
        "salt_bytes": salt_bytes,
        "password": password,
        "vault": {}
    }
    return True, "Account registered successfully!", user_info


def login_user(email: str, password: str) -> tuple[bool, str, dict | None]:
    """Authenticate user against their email and unlock their personal vault."""
    email_clean = email.strip().lower()
    users = load_users_db()

    if email_clean not in users:
        return False, "Account not found. Please check your email or create an account.", None

    user_record = users[email_clean]
    user_id = user_record["user_id"]
    salt_bytes = base64.b64decode(user_record["salt"])
    saved_hash_bytes = base64.b64decode(user_record["hash"])

    entered_hash_bytes = hash_password(password, salt_bytes)

    if entered_hash_bytes == saved_hash_bytes:
        vault = load_user_vault(user_id, password, salt_bytes)
        user_info = {
            "user_id": user_id,
            "email": email_clean,
            "salt_bytes": salt_bytes,
            "password": password,
            "vault": vault
        }
        return True, "Login successful!", user_info
    else:
        return False, "Incorrect master password for this account.", None


# ----------------------------------------
# VAULT STORAGE PER USER
# ----------------------------------------

def load_user_vault(user_id: str, password: str, salt_bytes: bytes) -> dict:
    """Decrypt and parse a specific user's vault file."""
    vault_path = get_user_vault_path(user_id)
    if not os.path.exists(vault_path):
        return {}

    try:
        key = create_encryption_key(password, salt_bytes)
        fernet = Fernet(key)

        with open(vault_path, "rb") as f:
            encrypted_data = f.read()

        decrypted_data = fernet.decrypt(encrypted_data)
        vault_data = json.loads(decrypted_data.decode("utf-8"))

        today_str = datetime.now().strftime("%Y-%m-%d")
        for service, account in vault_data.items():
            if "last_changed" not in account or not account["last_changed"]:
                account["last_changed"] = today_str

        return vault_data
    except Exception as e:
        print(f"Error loading user vault ({user_id}): {e}")
        return {}


def save_user_vault(user_id: str, vault: dict, password: str, salt_bytes: bytes) -> bool:
    """Encrypt and write a specific user's vault file."""
    try:
        vault_path = get_user_vault_path(user_id)
        key = create_encryption_key(password, salt_bytes)
        fernet = Fernet(key)

        vault_json = json.dumps(vault, indent=2)
        encrypted_data = fernet.encrypt(vault_json.encode("utf-8"))

        with open(vault_path, "wb") as f:
            f.write(encrypted_data)
        return True
    except Exception as e:
        print(f"Error saving user vault ({user_id}): {e}")
        return False


# ----------------------------------------
# ACCOUNT STATUS & PASSWORD HELPERS
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
        return {"days_passed": days_passed, "badge_text": f"{days_remaining}d left", "level": "good", "color": "#10B981"}
    elif days_remaining > 0:
        return {"days_passed": days_passed, "badge_text": f"{days_remaining}d remaining", "level": "warning", "color": "#F59E0B"}
    elif days_remaining == 0:
        return {"days_passed": days_passed, "badge_text": "Due Today!", "level": "due", "color": "#EF4444"}
    else:
        return {"days_passed": days_passed, "badge_text": f"{abs(days_remaining)}d overdue", "level": "overdue", "color": "#DC2626"}


def generate_password(length: int = 16, upper: bool = True, lower: bool = True, digits: bool = True, symbols: bool = True) -> str:
    """Generate cryptographically secure random password."""
    charset = ""
    if upper: charset += string.ascii_uppercase
    if lower: charset += string.ascii_lowercase
    if digits: charset += string.digits
    if symbols: charset += "!@#$%^&*()_+-=[]{}|;:,.<>?"
    if not charset: charset = string.ascii_letters + string.digits
    return "".join(secrets.choice(charset) for _ in range(length))


def evaluate_password_strength(password: str) -> dict:
    """Evaluate password strength score."""
    if not password:
        return {"score": 0, "label": "Empty", "color": "#9CA3AF"}

    score = 0
    length = len(password)
    if length >= 8: score += 20
    if length >= 12: score += 20
    if length >= 16: score += 15

    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_symbol = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)

    score += sum([has_upper, has_lower, has_digit, has_symbol]) * 11.25
    score = min(100, int(score))

    if score < 40: return {"score": score, "label": "Weak", "color": "#EF4444"}
    elif score < 70: return {"score": score, "label": "Medium", "color": "#F59E0B"}
    elif score < 90: return {"score": score, "label": "Strong", "color": "#10B981"}
    else: return {"score": score, "label": "Very Strong", "color": "#3B82F6"}


def get_vault_stats(vault: dict) -> dict:
    """Calculate overall vault metrics."""
    total = len(vault)
    overdue = 0
    weak = 0
    total_score = 0

    for service, account in vault.items():
        status = get_account_status(account.get("last_changed", ""))
        if status["level"] in ["due", "overdue"]: overdue += 1
        sev = evaluate_password_strength(account.get("password", ""))
        total_score += sev["score"]
        if sev["score"] < 50: weak += 1

    avg_score = int(total_score / total) if total > 0 else 100

    return {
        "total_accounts": total,
        "overdue_count": overdue,
        "weak_passwords": weak,
        "security_score": avg_score
    }
