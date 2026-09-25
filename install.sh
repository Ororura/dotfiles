#!/usr/bin/env bash

set -euo pipefail

DOTFILES_DIR="$(
    cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P
)"

DRY_RUN=false
FULL=false
BACKUP_DIR=""

# ============================================================
# Arguments
# ============================================================

for arg in "$@"; do

    case "$arg" in

        --dry-run)
            DRY_RUN=true
            ;;

        --full)
            FULL=true
            ;;

        --help)
            echo "Usage: ./install.sh [--full] [--dry-run]"
            exit 0
            ;;

        *)
            echo "Unknown argument: $arg"
            exit 1
            ;;

    esac

done

# ============================================================
# System
# ============================================================

OS="$(uname -s)"

case "$OS" in

    Darwin)
        PLATFORM="macOS"
        ;;

    Linux)
        PLATFORM="Linux"
        ;;

    *)
        echo "Unsupported OS: $OS"
        exit 1
        ;;

esac

echo
echo "================================"
echo " Dotfiles Installer"
echo "================================"
echo
echo "Platform: $PLATFORM"
echo "Directory: $DOTFILES_DIR"
echo

# ============================================================
# Preflight Checks
# ============================================================

echo "Checking required files..."

required_files=(
    "$DOTFILES_DIR/zsh/.zshrc"
    "$DOTFILES_DIR/tmux/tmux.conf"
    "$DOTFILES_DIR/git/config"
    "$DOTFILES_DIR/scripts/install-git.sh"
)

if [[ "$FULL" == true ]]; then
    required_files+=(
        "$DOTFILES_DIR/scripts/install-deps.sh"
    )
fi

for source in "${required_files[@]}"; do

    if [[ ! -f "$source" ]]; then

        echo "[ERROR] Required file not found: $source"
        exit 1

    fi

    echo "[OK] $source"

done

echo

# ============================================================
# Dependencies
# ============================================================

if [[ "$FULL" == true ]]; then

    if [[ "$DRY_RUN" == true ]]; then

        echo "[DRY RUN] Would install terminal dependencies."

    else

        bash "$DOTFILES_DIR/scripts/install-deps.sh"

    fi

fi

# ============================================================
# Symlink installation
# ============================================================

install_link() {

    local source="$1"
    local target="$2"

    if [[ ! -f "$source" ]]; then

        echo "Source not found: $source"
        return 1

    fi

    if [[ -L "$target" ]] &&
       [[ "$(readlink "$target")" == "$source" ]]; then

        echo "[OK] $target"
        return

    fi

    if [[ "$DRY_RUN" == true ]]; then

        echo "[DRY RUN] $target -> $source"

        if [[ -e "$target" || -L "$target" ]]; then
            echo "[DRY RUN] Would backup $target"
        fi

        return

    fi

    # Backup existing file

    if [[ -e "$target" || -L "$target" ]]; then

        if [[ -z "$BACKUP_DIR" ]]; then

            mkdir -p "$HOME/.dotfiles-backups"

            BACKUP_DIR="$(
                mktemp -d \
                    "$HOME/.dotfiles-backups/$(date +%Y%m%d-%H%M%S).XXXXXX"
            )"

        fi

        mv "$target" "$BACKUP_DIR/$(basename "$target")"

        echo "[BACKUP] $target"

    fi

    # Create symlink

    ln -s "$source" "$target"

    echo "[INSTALLED] $target"

}

# ============================================================
# Configurations
# ============================================================

echo
echo "Installing configurations..."
echo

install_link \
    "$DOTFILES_DIR/zsh/.zshrc" \
    "$HOME/.zshrc"

install_link \
    "$DOTFILES_DIR/tmux/tmux.conf" \
    "$HOME/.tmux.conf"

if [[ -f "$DOTFILES_DIR/zsh/.p10k.zsh" ]]; then

    install_link \
        "$DOTFILES_DIR/zsh/.p10k.zsh" \
        "$HOME/.p10k.zsh"

fi

# ============================================================
# Git Configuration
# ============================================================

echo
echo "Installing Git configuration..."
echo

if [[ "$DRY_RUN" == true ]]; then

    echo "[DRY RUN] Would configure Git include.path."

else

    bash "$DOTFILES_DIR/scripts/install-git.sh"

fi

# ============================================================
# Complete
# ============================================================

echo

if [[ "$DRY_RUN" == true ]]; then

    echo "Dry run completed. No changes made."

else

    echo "Dotfiles installed successfully."

    if [[ -n "$BACKUP_DIR" ]]; then
        echo "Backup directory: $BACKUP_DIR"
    fi

    echo
    echo "Restart your shell with: exec zsh"

fi
