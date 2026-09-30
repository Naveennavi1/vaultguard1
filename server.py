"""
VaultGuard - Flask REST API Backend for React Frontend
"""

import os
import sys
import webbrowser
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS

# Import core engine
from vaultguard_core import (
    is_master_password_set,
    create_master_password,
    verify_master_password,
    save_vault,
    get_account_status,
    generate_password,
    evaluate_password_strength,
    get_vault_stats,
    ROTATION_DAYS
)

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)

# In-memory active session state
session_data = {
    "unlocked": False,
    "vault": {},
    "master_password": None,
    "salt": None
}


@app.route("/")
def index():
    """Serves the main React application."""
    return render_template("index.html")


@app.route("/api/status", methods=["GET"])
def get_status():
    """Returns whether master password is configured and vault lock state."""
    return jsonify({
        "master_set": is_master_password_set(),
        "unlocked": session_data["unlocked"]
    })


@app.route("/api/setup", methods=["POST"])
def setup_master():
    """Create new master password."""
    data = request.json or {}
    password = data.get("password", "").strip()

    if not password or len(password) < 6:
        return jsonify({"success": False, "error": "Master password must be at least 6 characters."}), 400

    success, msg = create_master_password(password)
    if success:
        ok, _, vault, salt = verify_master_password(password)
        if ok:
            session_data["unlocked"] = True
            session_data["vault"] = vault
            session_data["master_password"] = password
            session_data["salt"] = salt
            return jsonify({"success": True, "message": "Master password created and vault unlocked!"})
    
    return jsonify({"success": False, "error": msg}), 500


@app.route("/api/login", methods=["POST"])
def login():
    """Verify master password and unlock vault."""
    data = request.json or {}
    password = data.get("password", "").strip()

    if not password:
        return jsonify({"success": False, "error": "Password cannot be empty."}), 400

    ok, msg, vault, salt = verify_master_password(password)
    if ok:
        session_data["unlocked"] = True
        session_data["vault"] = vault
        session_data["master_password"] = password
        session_data["salt"] = salt
        return jsonify({"success": True, "message": "Vault unlocked!"})
    
    return jsonify({"success": False, "error": "Incorrect master password."}), 401


@app.route("/api/lock", methods=["POST"])
def lock_vault():
    """Lock the active vault session."""
    session_data["unlocked"] = False
    session_data["vault"] = {}
    session_data["master_password"] = None
    session_data["salt"] = None
    return jsonify({"success": True, "message": "Vault locked."})


@app.route("/api/accounts", methods=["GET"])
def get_accounts():
    """Get stored accounts, audit alerts, and stats."""
    if not session_data["unlocked"]:
        return jsonify({"success": False, "error": "Vault is locked."}), 403

    vault = session_data["vault"]
    stats = get_vault_stats(vault)

    account_list = []
    for service, acc in vault.items():
        status = get_account_status(acc.get("last_changed", ""))
        pass_eval = evaluate_password_strength(acc.get("password", ""))
        account_list.append({
            "service": service,
            "username": acc.get("username", ""),
            "password": acc.get("password", ""),
            "last_changed": acc.get("last_changed", ""),
            "status": status,
            "strength": pass_eval
        })

    return jsonify({
        "success": True,
        "accounts": account_list,
        "stats": stats
    })


@app.route("/api/account", methods=["POST"])
def save_account_endpoint():
    """Add or update an account in the vault."""
    if not session_data["unlocked"]:
        return jsonify({"success": False, "error": "Vault is locked."}), 403

    data = request.json or {}
    service = data.get("service", "").strip()
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    is_edit = data.get("is_edit", False)

    if not service or not username or not password:
        return jsonify({"success": False, "error": "Please fill in all fields."}), 400

    vault = session_data["vault"]

    if not is_edit and service in vault:
        return jsonify({"success": False, "error": "An account for this service already exists!"}), 400

    from datetime import datetime
    vault[service] = {
        "username": username,
        "password": password,
        "last_changed": datetime.now().strftime("%Y-%m-%d")
    }

    save_vault(vault, session_data["master_password"], session_data["salt"])
    return jsonify({"success": True, "message": f"Account '{service}' saved successfully!"})


@app.route("/api/account/<service>", methods=["DELETE"])
def delete_account_endpoint(service):
    """Delete an account from the vault."""
    if not session_data["unlocked"]:
        return jsonify({"success": False, "error": "Vault is locked."}), 403

    vault = session_data["vault"]
    if service in vault:
        del vault[service]
        save_vault(vault, session_data["master_password"], session_data["salt"])
        return jsonify({"success": True, "message": f"Account '{service}' deleted."})

    return jsonify({"success": False, "error": "Account not found."}), 404


@app.route("/api/generate-password", methods=["POST"])
def generate_password_endpoint():
    """Generate a cryptographically random password."""
    data = request.json or {}
    length = int(data.get("length", 16))
    upper = bool(data.get("upper", True))
    lower = bool(data.get("lower", True))
    digits = bool(data.get("digits", True))
    symbols = bool(data.get("symbols", True))

    pwd = generate_password(length, upper, lower, digits, symbols)
    strength = evaluate_password_strength(pwd)

    return jsonify({
        "password": pwd,
        "strength": strength
    })


@app.route("/api/change-master", methods=["POST"])
def change_master_password():
    """Change master password."""
    if not session_data["unlocked"]:
        return jsonify({"success": False, "error": "Vault is locked."}), 403

    data = request.json or {}
    new_pass = data.get("password", "").strip()

    if not new_pass or len(new_pass) < 6:
        return jsonify({"success": False, "error": "New master password must be at least 6 characters."}), 400

    create_master_password(new_pass)
    ok, msg, vault, salt = verify_master_password(new_pass)
    if ok:
        session_data["vault"] = vault
        session_data["master_password"] = new_pass
        session_data["salt"] = salt
        return jsonify({"success": True, "message": "Master password updated successfully!"})

    return jsonify({"success": False, "error": "Failed to update master password."}), 500


def run_server(port=5000, open_browser=True):
    if open_browser:
        webbrowser.open(f"http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=False)


if __name__ == "__main__":
    run_server()
