"""
VaultGuard Launcher Script
Run this script to open the VaultGuard desktop interface.
"""

import sys
import os

# Ensure local directory is in Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vaultguard_gui import main

if __name__ == "__main__":
    main()
