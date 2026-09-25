#!/usr/bin/env bash

set -euo pipefail

DOTFILES_DIR="$(
    cd "$(dirname "${BASH_SOURCE[0]}")/.." &&
    pwd -P
)"

FAILURES=0

echo
echo "================================"
echo " Dotfiles Doctor"
echo "================================"
echo

echo "OS: $(uname -s)"
echo "Architecture: $(uname -m)"
echo "Dotfiles: $DOTFILES_DIR"

# ============================================================
# Helpers
# ============================================================

check_command() {

    local command_name="$1"

    if command -v "$command_name" >/dev/null 2>&1; then

        echo "[OK] $command_name"

    else

        echo "[MISSING] $command_name"

    fi

}

check_link() {

    local name="$1"
    local source="$2"
    local target="$3"
    local required="$4"

    if [[ ! -f "$source" ]]; then

        echo "[ERROR] Missing source: $source"

        FAILURES=$((FAILURES + 1))

        return

    fi

    if [[ -L "$target" ]] &&
       [[ "$(readlink "$target")" == "$source" ]]; then

        echo "[OK] $name"

        return

    fi

    if [[ "$required" == true ]]; then

        echo "[ERROR] $name is not installed correctly"

        FAILURES=$((FAILURES + 1))

    else

        echo "[WARNING] $name is not installed"

    fi

}

# ============================================================
# Zsh
# ============================================================

echo
echo "Zsh configuration:"
echo

check_command zsh

check_link \
    ".zshrc" \
    "$DOTFILES_DIR/zsh/.zshrc" \
    "$HOME/.zshrc" \
    true

# ============================================================
# Git
# ============================================================

echo
echo "Git configuration:"
echo

if command -v git >/dev/null 2>&1; then

    echo "[OK] $(git --version)"

    if git config --global --get-all include.path 2>/dev/null |
       grep -Fxq "$DOTFILES_DIR/git/config"; then

        echo "[OK] Shared Git configuration"

    else

        echo "[ERROR] Shared Git configuration not installed"

        FAILURES=$((FAILURES + 1))

    fi

else

    echo "[ERROR] Git not installed"

    FAILURES=$((FAILURES + 1))

fi

# ============================================================
# tmux
# ============================================================

echo
echo "Tmux configuration:"
echo

check_command tmux

check_link \
    ".tmux.conf" \
    "$DOTFILES_DIR/tmux/tmux.conf" \
    "$HOME/.tmux.conf" \
    false

# ============================================================
# TPM
# ============================================================

echo
echo "tmux Plugin Manager:"
echo

if [[ -f "$HOME/.tmux/plugins/tpm/tpm" &&
      -f "$HOME/.tmux/plugins/tpm/bin/install_plugins" ]]; then

    echo "[OK] TPM installed"

else

    echo "[WARNING] TPM not installed"
    echo "Run ./install.sh --full to install tmux plugins."

fi

# ============================================================
# Powerlevel10k
# ============================================================

echo
echo "Powerlevel10k:"
echo

if [[ -f "$DOTFILES_DIR/zsh/.p10k.zsh" ]]; then

    check_link \
        ".p10k.zsh" \
        "$DOTFILES_DIR/zsh/.p10k.zsh" \
        "$HOME/.p10k.zsh" \
        false

fi

if [[ -f "$HOME/.oh-my-zsh/custom/themes/powerlevel10k/powerlevel10k.zsh-theme" ]]; then

    echo "[OK] Powerlevel10k theme"

else

    echo "[WARNING] Powerlevel10k theme not installed"

fi

# ============================================================
# Development Tools
# ============================================================

echo
echo "Development tools:"
echo

for tool in \
    python3 \
    nvim \
    zoxide \
    ollama \
    gh \
    docker \
    java \
    node \
    npm
do

    check_command "$tool"

done

# ============================================================
# Summary
# ============================================================

echo
echo "================================"

if (( FAILURES > 0 )); then

    echo "Found $FAILURES configuration problem(s)."

    exit 1

fi

echo "Required configurations are valid."

echo "================================"
