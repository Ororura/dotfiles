#!/usr/bin/python3
"""Restore one desktop installer backup, retaining the replaced current files."""
from pathlib import Path
import subprocess
import sys
root = Path(__file__).resolve().parents[2]
if len(sys.argv) != 2:
    print('Usage: restore-original.py ~/.dotfiles-backups/niri-TIMESTAMP-ID')
    sys.exit(1)
sys.exit(subprocess.call([sys.executable, str(root / 'scripts/install_niri.py'), '--restore', sys.argv[1]]))
