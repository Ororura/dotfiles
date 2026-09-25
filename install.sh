#!/usr/bin/env bash

set -euo pipefail

DOTFILES_DIR="$(
    cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P
)"

DRY_RUN=false
FULL=false
MINIMAL=false
DOCTOR=false
BREW=false
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

        --brew)
            BREW=true
            ;;

        --minimal)
            MINIMAL=true
            ;;

        --doctor)
            DOCTOR=true
            ;;

        --help)
            echo "Usage: ./install.sh [--full [--brew] | --minimal | --doctor] [--dry-run]"
            exit 0
            ;;

        *)
            echo "Unknown argument: $arg"
            exit 1
            ;;

    esac

done

# ============================================================
# Argument validation
# ============================================================

if [[ "$FULL" == true && "$MINIMAL" == true ]]; then
    echo "[ERROR] --full and --minimal cannot be combined."
    exit 1
fi

if [[ "$BREW" == true && "$FULL" != true ]]; then
    echo "[ERROR] --brew requires --full."
    exit 1
fi

if [[ "$DOCTOR" == true ]]; then

    if [[ "$FULL" == true ||
          "$MINIMAL" == true ||
          "$DRY_RUN" == true ]]; then

        echo "[ERROR] --doctor cannot be combined with installation flags."
        exit 1

    fi

    bash "$DOTFILES_DIR/scripts/doctor.sh"
    exit $?

fi

if ! command -v git >/dev/null 2>&1; then

    echo "[ERROR] Git is required for installation."
    exit 1

fi

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
if [[ "$BREW" == true && "$OS" != Darwin ]]; then
    echo "[ERROR] --brew is supported only on macOS."
    exit 1
fi

echo "Platform: $PLATFORM"
echo "Directory: $DOTFILES_DIR"
echo

# ============================================================
# Preflight Checks
# ============================================================

echo "Checking required files..."

required_files=(
    "$DOTFILES_DIR/zsh/.zshrc"
    "$DOTFILES_DIR/git/config"
    "$DOTFILES_DIR/scripts/install-git.sh"
)

if [[ "$MINIMAL" == false ]]; then

    required_files+=(
        "$DOTFILES_DIR/tmux/tmux.conf"
    )

fi

if [[ "$FULL" == true ]]; then
    required_files+=(
        "$DOTFILES_DIR/scripts/install-deps.sh"
        "$DOTFILES_DIR/scripts/setup-git-ai.sh"
        "$DOTFILES_DIR/scripts/setup-tmux.sh"
    )
fi

if [[ "$BREW" == true ]]; then
    required_files+=("$DOTFILES_DIR/brew/Brewfile")
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
# Homebrew Bundle (macOS, opt-in)
# ============================================================

if [[ "$BREW" == true ]]; then

    echo
    echo "Homebrew Bundle:"
    echo

    if [[ "$DRY_RUN" == true ]]; then

        echo "[DRY RUN] Would install brew/Brewfile."

    else

        if command -v brew >/dev/null 2>&1; then
            BREW_BIN="$(command -v brew)"

        elif [[ -x /opt/homebrew/bin/brew ]]; then
            BREW_BIN=/opt/homebrew/bin/brew

        elif [[ -x /usr/local/bin/brew ]]; then
            BREW_BIN=/usr/local/bin/brew

        else
            echo "[ERROR] Homebrew is not installed."
            echo "Install Homebrew before using --brew."
            exit 1
        fi

        "$BREW_BIN" bundle install \
            --file="$DOTFILES_DIR/brew/Brewfile" \
            --no-upgrade

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

if [[ "$MINIMAL" == false ]]; then

    install_link \
        "$DOTFILES_DIR/tmux/tmux.conf" \
        "$HOME/.tmux.conf"

    if [[ -f "$DOTFILES_DIR/zsh/.p10k.zsh" ]]; then

        install_link \
            "$DOTFILES_DIR/zsh/.p10k.zsh" \
            "$HOME/.p10k.zsh"

    fi

fi

# ============================================================
# tmux Plugins
# ============================================================

if [[ "$FULL" == true ]]; then

    echo
    echo "Setting up tmux plugins..."
    echo

    if [[ "$DRY_RUN" == true ]]; then

        echo "[DRY RUN] Would install TPM and tmux plugins."

    else

        bash "$DOTFILES_DIR/scripts/setup-tmux.sh"

    fi

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
# Git AI Setup
# ============================================================

if [[ "$FULL" == true ]]; then

    if [[ "$DRY_RUN" == true ]]; then

        echo "[DRY RUN] Would check Git AI dependencies."

    else

        bash "$DOTFILES_DIR/scripts/setup-git-ai.sh"

    fi

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
