#!/usr/bin/env bash

set -euo pipefail

DOTFILES_DIR="$(
    cd "$(dirname "${BASH_SOURCE[0]}")/.." &&
    pwd -P
)"

SOURCE="$DOTFILES_DIR/nvim"

CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"

TARGET="$CONFIG_HOME/nvim"

DRY_RUN=false

case "${1:-}" in
    "")
        ;;

    --dry-run)
        DRY_RUN=true
        ;;

    *)
        echo "[ERROR] Unknown argument: $1"
        exit 1
        ;;
esac

echo
echo "================================"
echo " Neovim Configuration Setup"
echo "================================"
echo

# Check source configuration

if [[ ! -f "$SOURCE/init.lua" ]]; then

    echo "[ERROR] Neovim configuration not found:"
    echo "$SOURCE/init.lua"

    exit 1

fi

# Check existing installation

if [[ -L "$TARGET" ]] &&
   [[ "$(readlink "$TARGET")" == "$SOURCE" ]]; then

    echo "[OK] Neovim configuration already installed."

    exit 0

fi

# Dry run

if [[ "$DRY_RUN" == true ]]; then

    echo "[DRY RUN] Would link:"
    echo "$TARGET -> $SOURCE"

    if [[ -e "$TARGET" || -L "$TARGET" ]]; then

        echo "[DRY RUN] Would backup existing configuration."

    fi

    exit 0

fi

# Prepare configuration directory

mkdir -p "$CONFIG_HOME"

# Backup existing configuration

if [[ -e "$TARGET" || -L "$TARGET" ]]; then

    mkdir -p "$HOME/.dotfiles-backups"

    BACKUP_DIR="$(
        mktemp -d \
          "$HOME/.dotfiles-backups/nvim-$(date +%Y%m%d-%H%M%S).XXXXXX"
    )"

    mv "$TARGET" "$BACKUP_DIR/nvim"

    echo "[BACKUP] $BACKUP_DIR/nvim"

fi

# Install symlink

ln -s "$SOURCE" "$TARGET"

echo "[INSTALLED] $TARGET -> $SOURCE"

if ! command -v nvim >/dev/null 2>&1; then

    echo "[WARNING] Neovim executable not found."
    echo "The configuration was installed, but Neovim must be installed separately."

fi

echo
echo "Neovim configuration setup completed."
