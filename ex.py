"""
VaultGuard - Complete Self-Contained Python Password Manager
File: ex.py
"""

import os
import sys
import json
import base64
import hashlib
import string
import secrets
import pyperclip
from datetime import datetime
from cryptography.fernet import Fernet
import customtkinter as ctk
from tkinter import messagebox

# Set global appearance theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MASTER_DAT = os.path.join(BASE_DIR, "master.dat")
VAULT_ENC = os.path.join(BASE_DIR, "vault.enc")
ROTATION_DAYS = 120


# ----------------------------------------
# CRYPTOGRAPHY ENGINE
# ----------------------------------------

def hash_password(password: str, salt: bytes) -> bytes:
    """Hash password using PBKDF2-HMAC-SHA256."""
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)


def create_encryption_key(password: str, salt: bytes) -> bytes:
    """Derive 32-byte Fernet key from password and salt."""
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000, dklen=32)
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


def verify_master_password(password: str):
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


def get_account_status(last_changed_str: str) -> dict:
    """Calculate age and alert status for password rotation."""
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
    """Generate cryptographically secure password."""
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
    """Calculate vault metrics."""
    total = len(vault)
    overdue = 0
    weak = 0
    total_score = 0

    for service, account in vault.items():
        st = get_account_status(account.get("last_changed", ""))
        if st["level"] in ["due", "overdue"]: overdue += 1
        sev = evaluate_password_strength(account.get("password", ""))
        total_score += sev["score"]
        if sev["score"] < 50: weak += 1

    avg_score = int(total_score / total) if total > 0 else 100
    return {"total_accounts": total, "overdue_count": overdue, "weak_passwords": weak, "security_score": avg_score}


# ----------------------------------------
# MODERN CUSTOMTKINTER GUI
# ----------------------------------------

class VaultGuardApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("VaultGuard - NextGen Password Manager")
        self.geometry("1100x720")
        self.minsize(950, 600)
        self.center_window()

        self.vault = {}
        self.master_password = None
        self.salt = None

        self.container = ctk.CTkFrame(self, corner_radius=0)
        self.container.pack(fill="both", expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.show_auth_screen()

    def center_window(self):
        self.update_idletasks()
        w, h = 1100, 720
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def show_auth_screen(self):
        for w in self.container.winfo_children(): w.destroy()

        auth_frame = ctk.CTkFrame(self.container, fg_color=("gray95", "#0F172A"))
        auth_frame.grid(row=0, column=0, sticky="nsew")
        auth_frame.grid_rowconfigure(0, weight=1)
        auth_frame.grid_columnconfigure(0, weight=1)

        card = ctk.CTkFrame(auth_frame, width=420, corner_radius=16, fg_color=("white", "#1E293B"), border_width=1, border_color=("gray85", "#334155"))
        card.grid(row=0, column=0, padx=20, pady=20)

        ctk.CTkLabel(card, text="🔐 VaultGuard", font=ctk.CTkFont(size=32, weight="bold"), text_color=("#1E293B", "#F8FAFC")).pack(pady=(40, 20))

        is_setup = not is_master_password_set()
        ctk.CTkLabel(card, text="Create Master Password" if is_setup else "Unlock Your Vault", font=ctk.CTkFont(size=18, weight="bold"), text_color=("#3B82F6", "#60A5FA")).pack(pady=(5, 2))
        ctk.CTkLabel(card, text="Set a strong master password." if is_setup else "Enter master password to access accounts.", font=ctk.CTkFont(size=12), text_color=("gray60", "#64748B")).pack(pady=(0, 20))

        pass_entry = ctk.CTkEntry(card, width=320, height=44, placeholder_text="Master Password", show="•", font=ctk.CTkFont(size=14), corner_radius=8)
        pass_entry.pack(pady=8)
        pass_entry.focus()

        confirm_entry = None
        if is_setup:
            confirm_entry = ctk.CTkEntry(card, width=320, height=44, placeholder_text="Confirm Master Password", show="•", font=ctk.CTkFont(size=14), corner_radius=8)
            confirm_entry.pack(pady=8)

        error_label = ctk.CTkLabel(card, text="", font=ctk.CTkFont(size=12), text_color="#EF4444")
        error_label.pack(pady=(4, 8))

        def handle_auth(event=None):
            pwd = pass_entry.get().strip()
            if not pwd:
                error_label.configure(text="Master password cannot be empty.")
                return

            if is_setup:
                if pwd != confirm_entry.get().strip():
                    error_label.configure(text="Passwords do not match!")
                    return
                if len(pwd) < 6:
                    error_label.configure(text="Password must be at least 6 characters.")
                    return
                success, msg = create_master_password(pwd)
                if success:
                    ok, _, vault, salt = verify_master_password(pwd)
                    if ok:
                        self.vault, self.master_password, self.salt = vault, pwd, salt
                        self.show_main_dashboard()
                else: error_label.configure(text=msg)
            else:
                ok, msg, vault, salt = verify_master_password(pwd)
                if ok:
                    self.vault, self.master_password, self.salt = vault, pwd, salt
                    self.show_main_dashboard()
                else:
                    error_label.configure(text="Access Denied: Incorrect Master Password")

        pass_entry.bind("<Return>", handle_auth)
        if confirm_entry: confirm_entry.bind("<Return>", handle_auth)

        ctk.CTkButton(card, text="CREATE VAULT" if is_setup else "UNLOCK VAULT", width=320, height=44, font=ctk.CTkFont(size=14, weight="bold"), fg_color="#2563EB", hover_color="#1D4ED8", corner_radius=8, command=handle_auth).pack(pady=(10, 40))

    def show_main_dashboard(self):
        for w in self.container.winfo_children(): w.destroy()

        self.main_frame = ctk.CTkFrame(self.container, fg_color=("gray95", "#0B0F19"))
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        self.main_frame.grid_columnconfigure(1, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)

        self.build_sidebar()

        self.content_area = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.content_area.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.content_area.grid_rowconfigure(1, weight=1)
        self.content_area.grid_columnconfigure(0, weight=1)

        self.search_query = ""
        self.switch_tab("vault")

    def build_sidebar(self):
        sidebar = ctk.CTkFrame(self.main_frame, width=240, corner_radius=0, fg_color=("white", "#111827"), border_width=1, border_color=("gray85", "#1F2937"))
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)

        ctk.CTkLabel(sidebar, text="🔐 VaultGuard", font=ctk.CTkFont(size=22, weight="bold")).pack(padx=20, pady=(25, 2))
        ctk.CTkLabel(sidebar, text="● Vault Unlocked", font=ctk.CTkFont(size=11, weight="bold"), text_color="#10B981").pack(padx=20, pady=(0, 25))

        self.nav_buttons = {}
        for tab_id, label in [("vault", "📦  Accounts Vault"), ("generator", "⚡  Password Generator"), ("audit", "🔔  Security Audit"), ("settings", "⚙️  Settings")]:
            btn = ctk.CTkButton(sidebar, text=label, anchor="w", height=40, font=ctk.CTkFont(size=13, weight="bold"), fg_color="transparent", text_color=("gray30", "#94A3B8"), hover_color=("gray90", "#1E293B"), corner_radius=8, command=lambda t=tab_id: self.switch_tab(t))
            btn.pack(fill="x", padx=15, pady=4)
            self.nav_buttons[tab_id] = btn

        stats_box = ctk.CTkFrame(sidebar, fg_color=("gray90", "#1E293B"), corner_radius=12)
        stats_box.pack(fill="x", padx=15, pady=(40, 15), side="bottom")

        stats = get_vault_stats(self.vault)
        ctk.CTkLabel(stats_box, text="Vault Health", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=12, pady=(10, 2))
        progress = ctk.CTkProgressBar(stats_box, height=8, progress_color="#10B981" if stats["security_score"]>=75 else "#F59E0B")
        progress.set(stats["security_score"] / 100)
        progress.pack(fill="x", padx=12, pady=4)
        ctk.CTkLabel(stats_box, text=f"Score: {stats['security_score']}%  •  {stats['total_accounts']} Items", font=ctk.CTkFont(size=11), text_color=("gray40", "#94A3B8")).pack(anchor="w", padx=12, pady=(0, 10))

        ctk.CTkButton(sidebar, text="🔒 Lock Vault", height=36, fg_color="#DC2626", hover_color="#B91C1C", font=ctk.CTkFont(size=12, weight="bold"), corner_radius=8, command=self.lock_vault).pack(fill="x", padx=15, pady=(0, 20), side="bottom")

    def switch_tab(self, tab_name):
        for t_id, btn in self.nav_buttons.items():
            btn.configure(fg_color=("#3B82F6", "#2563EB") if t_id == tab_name else "transparent", text_color="white" if t_id == tab_name else ("gray30", "#94A3B8"))
        for w in self.content_area.winfo_children(): w.destroy()

        if tab_name == "vault": self.render_vault_view()
        elif tab_name == "generator": self.render_generator_view()
        elif tab_name == "audit": self.render_audit_view()
        elif tab_name == "settings": self.render_settings_view()

    def render_vault_view(self):
        header = ctk.CTkFrame(self.content_area, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        header.grid_columnconfigure(0, weight=1)

        search_entry = ctk.CTkEntry(header, placeholder_text="🔍 Search accounts by service or username...", height=42, font=ctk.CTkFont(size=13), corner_radius=10)
        search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 15))
        search_entry.insert(0, self.search_query)
        search_entry.bind("<KeyRelease>", lambda e: self.on_search(search_entry.get().strip().lower()))

        ctk.CTkButton(header, text="➕  Add Account", height=42, font=ctk.CTkFont(size=13, weight="bold"), fg_color="#10B981", hover_color="#059669", corner_radius=10, command=self.open_add_modal).grid(row=0, column=1)

        self.scroll_frame = ctk.CTkScrollableFrame(self.content_area, fg_color="transparent", corner_radius=0)
        self.scroll_frame.grid(row=1, column=0, sticky="nsew")
        self.scroll_frame.grid_columnconfigure(0, weight=1)

        self.refresh_account_list()

    def on_search(self, q):
        self.search_query = q
        self.refresh_account_list()

    def refresh_account_list(self):
        for w in self.scroll_frame.winfo_children(): w.destroy()

        items = [(s, a) for s, a in self.vault.items() if not self.search_query or self.search_query in s.lower() or self.search_query in a.get("username", "").lower()]
        if not items:
            card = ctk.CTkFrame(self.scroll_frame, fg_color=("white", "#1E293B"), corner_radius=12)
            card.pack(fill="x", pady=20)
            ctk.CTkLabel(card, text="📭 No accounts found in your vault!", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=40)
            return

        for service, acc in items:
            self.build_account_card(service, acc)

    def build_account_card(self, service: str, acc: dict):
        card = ctk.CTkFrame(self.scroll_frame, fg_color=("white", "#1E293B"), corner_radius=12, border_width=1, border_color=("gray85", "#334155"))
        card.pack(fill="x", pady=6, padx=2)
        card.grid_columnconfigure(1, weight=1)

        avatar = ctk.CTkFrame(card, width=44, height=44, corner_radius=10, fg_color=("#DBEAFE", "#1E3A8A"))
        avatar.grid(row=0, column=0, rowspan=2, padx=15, pady=15)
        avatar.grid_propagate(False)
        ctk.CTkLabel(avatar, text=service[0].upper() if service else "?", font=ctk.CTkFont(size=18, weight="bold"), text_color=("#1D4ED8", "#93C5FD")).place(relx=0.5, rely=0.5, anchor="center")

        details_box = ctk.CTkFrame(card, fg_color="transparent")
        details_box.grid(row=0, column=1, rowspan=2, sticky="w", pady=10, padx=(0, 10))

        title_box = ctk.CTkFrame(details_box, fg_color="transparent")
        title_box.pack(anchor="w", pady=(0, 2))
        ctk.CTkLabel(title_box, text=service, font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")

        status = get_account_status(acc.get("last_changed", ""))
        badge = ctk.CTkFrame(title_box, fg_color=status["color"], corner_radius=6)
        badge.pack(side="left", padx=10)
        ctk.CTkLabel(badge, text=status["badge_text"], font=ctk.CTkFont(size=10, weight="bold"), text_color="white").pack(padx=8, pady=2)

        ctk.CTkLabel(details_box, text=f"👤 {acc.get('username', '')}", font=ctk.CTkFont(size=12), text_color=("gray50", "#94A3B8")).pack(anchor="w", pady=(0, 2))

        # Show / Hide Password Toggle Line inside Card
        pass_line = ctk.CTkFrame(details_box, fg_color="transparent")
        pass_line.pack(anchor="w", pady=(2, 0))

        raw_password = acc.get("password", "")
        is_showing = False

        pass_lbl = ctk.CTkLabel(pass_line, text="🔑 ••••••••••••", font=ctk.CTkFont(size=12), text_color=("gray50", "#94A3B8"))
        pass_lbl.pack(side="left")

        def toggle_password_visibility():
            nonlocal is_showing
            is_showing = not is_showing
            if is_showing:
                pass_lbl.configure(text=f"🔑 {raw_password}", font=ctk.CTkFont(family="Consolas", size=12, weight="bold"), text_color="#60A5FA")
                toggle_btn.configure(text="🙈 Hide", fg_color=("#DBEAFE", "#1E3A8A"), text_color=("#1D4ED8", "#93C5FD"))
            else:
                pass_lbl.configure(text="🔑 ••••••••••••", font=ctk.CTkFont(size=12), text_color=("gray50", "#94A3B8"))
                toggle_btn.configure(text="👁️ Show", fg_color=("gray85", "#334155"), text_color=("black", "white"))

        toggle_btn = ctk.CTkButton(pass_line, text="👁️ Show", width=65, height=22, font=ctk.CTkFont(size=11, weight="bold"), fg_color=("gray85", "#334155"), text_color=("black", "white"), hover_color=("gray75", "#475569"), corner_radius=6, command=toggle_password_visibility)
        toggle_btn.pack(side="left", padx=8)

        actions_frame = ctk.CTkFrame(card, fg_color="transparent")
        actions_frame.grid(row=0, column=2, rowspan=2, padx=15, pady=15, sticky="e")

        ctk.CTkButton(actions_frame, text="📋 Password", width=90, height=34, font=ctk.CTkFont(size=12, weight="bold"), fg_color="#3B82F6", command=lambda: self.copy_to_clipboard(raw_password, "Password copied!")).pack(side="left", padx=3)
        ctk.CTkButton(actions_frame, text="👤 User", width=70, height=34, font=ctk.CTkFont(size=12, weight="bold"), fg_color=("gray85", "#334155"), text_color=("black", "white"), command=lambda: self.copy_to_clipboard(acc.get("username", ""), "Username copied!")).pack(side="left", padx=3)
        ctk.CTkButton(actions_frame, text="✏️", width=36, height=34, font=ctk.CTkFont(size=13), fg_color=("gray85", "#334155"), command=lambda: self.open_edit_modal(service, acc)).pack(side="left", padx=3)
        ctk.CTkButton(actions_frame, text="🗑️", width=36, height=34, font=ctk.CTkFont(size=13), fg_color="#EF4444", command=lambda: self.delete_account_confirm(service)).pack(side="left", padx=3)

    def copy_to_clipboard(self, text, msg):
        pyperclip.copy(text)
        self.show_toast(msg)

    def show_toast(self, text):
        toast = ctk.CTkFrame(self.container, fg_color="#10B981", corner_radius=20)
        toast.place(relx=0.5, rely=0.92, anchor="center")
        ctk.CTkLabel(toast, text=f"✅  {text}", font=ctk.CTkFont(size=13, weight="bold"), text_color="white").pack(padx=20, pady=8)
        self.after(2200, toast.destroy)

    def open_add_modal(self):
        self.build_modal("Add New Account", False)

    def open_edit_modal(self, service, acc):
        self.build_modal(f"Edit Account: {service}", True, service, acc)

    def build_modal(self, title, is_edit, orig_service="", orig_acc=None):
        modal = ctk.CTkToplevel(self)
        modal.title(title)
        modal.geometry("450x520")
        modal.grab_set()

        card = ctk.CTkFrame(modal, fg_color=("white", "#1E293B"))
        card.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(15, 20))

        service_entry = ctk.CTkEntry(card, width=370, height=40)
        service_entry.pack(padx=20, pady=8)
        if is_edit: service_entry.insert(0, orig_service); service_entry.configure(state="disabled")

        username_entry = ctk.CTkEntry(card, width=370, height=40)
        username_entry.pack(padx=20, pady=8)
        if is_edit and orig_acc: username_entry.insert(0, orig_acc.get("username", ""))

        pass_frame = ctk.CTkFrame(card, fg_color="transparent")
        pass_frame.pack(padx=20, pady=8, fill="x")

        password_entry = ctk.CTkEntry(pass_frame, width=280, height=40, show="•")
        password_entry.pack(side="left")
        if is_edit and orig_acc: password_entry.insert(0, orig_acc.get("password", ""))

        is_modal_pass_shown = False
        def toggle_modal_pass():
            nonlocal is_modal_pass_shown
            is_modal_pass_shown = not is_modal_pass_shown
            password_entry.configure(show="" if is_modal_pass_shown else "•")
            eye_btn.configure(text="🙈" if is_modal_pass_shown else "👁️")

        eye_btn = ctk.CTkButton(pass_frame, text="👁️", width=50, height=40, font=ctk.CTkFont(size=14), fg_color=("gray85", "#334155"), command=toggle_modal_pass)
        eye_btn.pack(side="right")

        err_lbl = ctk.CTkLabel(card, text="", text_color="#EF4444")
        err_lbl.pack(pady=4)

        def save_action():
            s = service_entry.get().strip() if not is_edit else orig_service
            u = username_entry.get().strip()
            p = password_entry.get().strip()
            if not s or not u or not p: err_lbl.configure(text="Please fill in all fields."); return
            if not is_edit and s in self.vault: err_lbl.configure(text="Account already exists!"); return

            self.vault[s] = {"username": u, "password": p, "last_changed": datetime.now().strftime("%Y-%m-%d")}
            save_vault(self.vault, self.master_password, self.salt)
            modal.destroy()
            self.refresh_account_list()
            self.build_sidebar()
            self.show_toast(f"Saved account '{s}'")

        ctk.CTkButton(card, text="Save Account", fg_color="#10B981", height=40, command=save_action).pack(pady=20)

    def delete_account_confirm(self, service):
        if messagebox.askyesno("Confirm Delete", f"Delete account for '{service}'?"):
            if service in self.vault:
                del self.vault[service]
                save_vault(self.vault, self.master_password, self.salt)
                self.refresh_account_list()
                self.build_sidebar()
                self.show_toast(f"Deleted account '{service}'")

    def render_generator_view(self):
        card = ctk.CTkFrame(self.content_area, fg_color=("white", "#1E293B"), corner_radius=16)
        card.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(card, text="⚡ Password Generator", font=ctk.CTkFont(size=22, weight="bold")).pack(pady=(25, 20))

        out_frame = ctk.CTkFrame(card, fg_color=("gray95", "#0F172A"), corner_radius=12)
        out_frame.pack(fill="x", padx=40, pady=10)

        self.gen_pass_label = ctk.CTkLabel(out_frame, text="", font=ctk.CTkFont(family="Consolas", size=20, weight="bold"), text_color="#3B82F6")
        self.gen_pass_label.pack(side="left", padx=20, pady=15)

        ctk.CTkButton(out_frame, text="📋 Copy", width=90, height=38, fg_color="#10B981", command=lambda: self.copy_to_clipboard(self.gen_pass_label.cget("text"), "Copied password!")).pack(side="right", padx=15)

        self.strength_bar = ctk.CTkProgressBar(card, height=10)
        self.strength_bar.pack(fill="x", padx=40, pady=(15, 5))
        self.strength_lbl = ctk.CTkLabel(card, text="", font=ctk.CTkFont(size=12, weight="bold"))
        self.strength_lbl.pack()

        ctk.CTkButton(card, text="🔄 Generate New Password", height=44, fg_color="#3B82F6", command=self.update_gen_pass).pack(pady=20)
        self.update_gen_pass()

    def update_gen_pass(self):
        p = generate_password(length=16)
        self.gen_pass_label.configure(text=p)
        st = evaluate_password_strength(p)
        self.strength_bar.configure(progress_color=st["color"])
        self.strength_bar.set(st["score"] / 100)
        self.strength_lbl.configure(text=f"Strength: {st['label']} ({st['score']}%)", text_color=st["color"])

    def render_audit_view(self):
        scroll = ctk.CTkScrollableFrame(self.content_area, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        ctk.CTkLabel(scroll, text="🔔 Password Security & Health Audit", font=ctk.CTkFont(size=20, weight="bold")).pack(anchor="w", pady=(10, 20))
        for service, acc in self.vault.items():
            st = get_account_status(acc.get("last_changed", ""))
            if st["level"] in ["due", "overdue", "warning"]:
                card = ctk.CTkFrame(scroll, fg_color=("white", "#1E293B"), corner_radius=12)
                card.pack(fill="x", pady=4)
                ctk.CTkLabel(card, text=f"🔑 {service}", font=ctk.CTkFont(size=15, weight="bold")).pack(side="left", padx=15, pady=12)
                ctk.CTkLabel(card, text=st["badge_text"], font=ctk.CTkFont(size=11, weight="bold"), text_color=st["color"]).pack(side="right", padx=15)

    def render_settings_view(self):
        card = ctk.CTkFrame(self.content_area, fg_color=("white", "#1E293B"), corner_radius=16)
        card.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(card, text="⚙️ Preferences", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=30)

    def lock_vault(self):
        self.vault = {}
        self.master_password = None
        self.salt = None
        self.show_auth_screen()


def main():
    app = VaultGuardApp()
    app.mainloop()


if __name__ == "__main__":
    main()
