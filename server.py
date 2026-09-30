"""
VaultGuard - Multi-User Flask REST API Backend Server
"""

import os
import sys
import webbrowser
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

from vaultguard_core import (
    register_user,
    login_user,
    save_user_vault,
    get_account_status,
    generate_password,
    evaluate_password_strength,
    get_vault_stats
)

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.urandom(24)
CORS(app)

# Session state dictionary (user_info per active session)
session_data = {
    "unlocked": False,
    "user_info": None  # Stores: user_id, email, password, salt_bytes, vault
}


@app.route("/")
def index():
    """Serves the main React application."""
    return render_template("index.html")


@app.route("/api/status", methods=["GET"])
def get_status():
    """Returns lock status and logged-in user profile info."""
    if session_data["unlocked"] and session_data["user_info"]:
        return jsonify({
            "unlocked": True,
            "user": {
                "email": session_data["user_info"]["email"],
                "user_id": session_data["user_info"]["user_id"]
            }
        })
    return jsonify({
        "unlocked": False,
        "user": None
    })


@app.route("/api/register", methods=["POST"])
def register_endpoint():
    """Register a new user account."""
    data = request.json or {}
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()

    if not email or not password:
        return jsonify({"success": False, "error": "Email and password are required."}), 400

    ok, msg, user_info = register_user(email, password)
    if ok and user_info:
        session_data["unlocked"] = True
        session_data["user_info"] = user_info
        return jsonify({
            "success": True,
            "message": msg,
            "user": {
                "email": user_info["email"],
                "user_id": user_info["user_id"]
            }
        })

    return jsonify({"success": False, "error": msg}), 400


@app.route("/api/login", methods=["POST"])
def login_endpoint():
    """Authenticate user with email & master password."""
    data = request.json or {}
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()

    if not email or not password:
        return jsonify({"success": False, "error": "Email and master password are required."}), 400

    ok, msg, user_info = login_user(email, password)
    if ok and user_info:
        session_data["unlocked"] = True
        session_data["user_info"] = user_info
        return jsonify({
            "success": True,
            "message": msg,
            "user": {
                "email": user_info["email"],
                "user_id": user_info["user_id"]
            }
        })

    return jsonify({"success": False, "error": msg}), 401


@app.route("/api/logout", methods=["POST"])
def logout_endpoint():
    """Lock vault and log out active user."""
    session_data["unlocked"] = False
    session_data["user_info"] = None
    return jsonify({"success": True, "message": "Logged out successfully."})


@app.route("/api/accounts", methods=["GET"])
def get_accounts():
    """Get stored accounts & stats for the active user."""
    if not session_data["unlocked"] or not session_data["user_info"]:
        return jsonify({"success": False, "error": "Vault is locked. Please log in."}), 403

    user = session_data["user_info"]
    vault = user["vault"]
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
    """Add or update an account for the logged-in user."""
    if not session_data["unlocked"] or not session_data["user_info"]:
        return jsonify({"success": False, "error": "Vault is locked."}), 403

    data = request.json or {}
    service = data.get("service", "").strip()
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    is_edit = data.get("is_edit", False)

    if not service or not username or not password:
        return jsonify({"success": False, "error": "Please fill in all fields."}), 400

    user = session_data["user_info"]
    vault = user["vault"]

    if not is_edit and service in vault:
        return jsonify({"success": False, "error": "An account for this service already exists!"}), 400

    from datetime import datetime
    vault[service] = {
        "username": username,
        "password": password,
        "last_changed": datetime.now().strftime("%Y-%m-%d")
    }

    save_user_vault(user["user_id"], vault, user["password"], user["salt_bytes"])
    return jsonify({"success": True, "message": f"Account '{service}' saved successfully!"})


@app.route("/api/account/<service>", methods=["DELETE"])
def delete_account_endpoint(service):
    """Delete an account from the user's vault."""
    if not session_data["unlocked"] or not session_data["user_info"]:
        return jsonify({"success": False, "error": "Vault is locked."}), 403

    user = session_data["user_info"]
    vault = user["vault"]

    if service in vault:
        del vault[service]
        save_user_vault(user["user_id"], vault, user["password"], user["salt_bytes"])
        return jsonify({"success": True, "message": f"Account '{service}' deleted."})

    return jsonify({"success": False, "error": "Account not found."}), 404


@app.route("/api/generate-password", methods=["POST"])
def generate_password_endpoint():
    """Generate a random password."""
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


def run_server(port=5000, open_browser=True):
    if open_browser:
        webbrowser.open(f"http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=False)


if __name__ == "__main__":
    run_server()
