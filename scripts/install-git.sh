#!/usr/bin/env bash

set -euo pipefail

DOTFILES_DIR="$(
    cd "$(dirname "${BASH_SOURCE[0]}")/.." &&
    pwd -P
)"

CONFIG="$DOTFILES_DIR/git/config"

echo
echo "Installing Git configuration..."
echo

# ============================================================
# Check Git
# ============================================================

if ! command -v git >/dev/null 2>&1; then

    echo "[ERROR] Git is not installed."
    exit 1

fi

# ============================================================
# Check configuration
# ============================================================

if [[ ! -f "$CONFIG" ]]; then

    echo "[ERROR] Configuration not found: $CONFIG"
    exit 1

fi

# ============================================================
# Check existing include
# ============================================================

if git config --global --get-all include.path 2>/dev/null |
   grep -Fxq "$CONFIG"; then

    echo "[OK] Git configuration already installed."
    exit 0

fi

# ============================================================
# Backup
# ============================================================

if [[ -f "$HOME/.gitconfig" ]]; then

    BACKUP_DIR="$HOME/.dotfiles-backups"

    mkdir -p "$BACKUP_DIR"

    BACKUP_FILE="$(
        mktemp "$BACKUP_DIR/gitconfig.XXXXXX"
    )"

    cp -p "$HOME/.gitconfig" "$BACKUP_FILE"

    echo "[BACKUP] $BACKUP_FILE"

fi

# ============================================================
# Install
# ============================================================

git config --global --add include.path "$CONFIG"

echo "[INSTALLED] $CONFIG"

echo
echo "Git configuration installed successfully."
