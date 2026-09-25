#!/usr/bin/env bash

set -euo pipefail

DOTFILES_DIR="$(
    cd "$(dirname "${BASH_SOURCE[0]}")/.." &&
    pwd -P
)"

SOURCE="$DOTFILES_DIR/ghostty/config"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/ghostty"
TARGET="$CONFIG_DIR/config"

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

case "$(uname -s)" in
    Darwin|Linux)
        ;;
    *)
        echo "[ERROR] Unsupported operating system."
        exit 1
        ;;
esac

echo
echo "================================"
echo " Ghostty Configuration Setup"
echo "================================"
echo

if [[ ! -f "$SOURCE" ]]; then
    echo "[ERROR] Missing configuration: $SOURCE"
    exit 1
fi

if [[ -L "$TARGET" ]] &&
   [[ "$(readlink "$TARGET")" == "$SOURCE" ]]; then

    echo "[OK] Ghostty configuration already installed."
    exit 0
fi

if [[ "$DRY_RUN" == true ]]; then

    echo "[DRY RUN] Would link:"
    echo "$TARGET -> $SOURCE"

    if [[ -e "$TARGET" || -L "$TARGET" ]]; then
        echo "[DRY RUN] Would backup existing configuration."
    fi

    exit 0
fi

mkdir -p "$CONFIG_DIR"

if [[ -e "$TARGET" || -L "$TARGET" ]]; then

    mkdir -p "$HOME/.dotfiles-backups"

    BACKUP_DIR="$(
        mktemp -d \
            "$HOME/.dotfiles-backups/ghostty-$(date +%Y%m%d-%H%M%S).XXXXXX"
    )"

    mv "$TARGET" "$BACKUP_DIR/config"

    echo "[BACKUP] $BACKUP_DIR/config"
fi

ln -s "$SOURCE" "$TARGET"

echo "[INSTALLED] $TARGET -> $SOURCE"

echo
echo "Ghostty configuration setup completed."
