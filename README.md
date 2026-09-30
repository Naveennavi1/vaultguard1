# 🔐 VaultGuard - Professional Python Password Manager

VaultGuard is a high-security, desktop password manager with a modern **CustomTkinter** visual interface, AES-256 Fernet encryption, and a 120-day password rotation policy tracker.

---

## 🌟 Key Features

1. **🔐 Military-Grade Security**:
   - Master Password derived using PBKDF2-HMAC-SHA256 with 100,000 key stretching iterations and random 16-byte cryptographic salts.
   - Symmetric vault encryption with `cryptography.fernet`.
   - Backward compatible with existing `master.dat` and `vault.enc` vault files.

2. **🎨 Modern Professional CustomTkinter Frontend**:
   - Sleek Dark / Light theme options.
   - Interactive Sidebar navigation with live Vault Health Score indicator.
   - Real-time search filter across all stored services & accounts.
   - Initial avatar badges for quick visual identity.

3. **📋 One-Click Clipboard Copying**:
   - Instant 1-click **Copy Password** and **Copy Username** buttons with auto-dismiss toast alerts.

4. **⚡ Cryptographic Password Generator**:
   - Adjustable password length slider (8 to 48 characters).
   - Character set toggles (Uppercase, Lowercase, Digits, Symbols).
   - Real-time visual strength meter (0-100% entropy score with color indicators).

5. **🔔 Password Health & Rotation Audit**:
   - Automatic 120-day password expiration tracking (`Good`, `Warning`, `Due Today`, `Overdue`).
   - Dedicated Audit tab listing accounts overdue for password rotation with direct "Update Now" action buttons.

---

## 📁 File Structure

```text
vaultguard/
├── vaultguard_core.py     # Cryptography engine & JSON storage read/write
├── vaultguard_gui.py      # CustomTkinter modern desktop GUI app
├── run_app.py             # Launcher entry point
├── master.dat             # Encrypted salt + hashed master password
└── vault.enc              # Fernet encrypted password vault
```

---

## 🚀 How to Run

### 1. Install Dependencies
```bash
pip install customtkinter cryptography pyperclip pillow
```

### 2. Launch VaultGuard Desktop App
```bash
python run_app.py
```
*(or run `python vaultguard_gui.py` directly)*

---

## 🔒 Security Highlights

- **Zero-Knowledge Architecture**: Your master password is never stored anywhere on disk; only its salted PBKDF2 hash is stored in `master.dat`.
- **Automatic Upgrades**: Existing accounts are automatically updated with rotation timestamp tracking upon decryption.
