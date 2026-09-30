"""
VaultGuard React + CSS Application Launcher
Run this script to start the VaultGuard web application powered by Flask + React + CSS.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server import run_server

if __name__ == "__main__":
    print("🚀 Starting VaultGuard React Application...")
    run_server(port=5000, open_browser=True)
