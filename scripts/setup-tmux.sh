#!/usr/bin/env bash

set -euo pipefail

TPM_DIR="$HOME/.tmux/plugins/tpm"
TMUX_CONFIG="$HOME/.tmux.conf"

echo
echo "================================"
echo " tmux Plugin Setup"
echo "================================"
echo

# ============================================================
# Dependencies
# ============================================================

for tool in git tmux bash; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "[ERROR] Required command not found: $tool"
        exit 1
    fi
done

# ============================================================
# Configuration
# ============================================================

if [[ ! -f "$TMUX_CONFIG" ]]; then
    echo "[ERROR] tmux configuration not found: $TMUX_CONFIG"
    exit 1
fi

# ============================================================
# TPM
# ============================================================

if [[ -f "$TPM_DIR/tpm" &&
      -f "$TPM_DIR/bin/install_plugins" ]]; then

    echo "[OK] TPM is already installed."

elif [[ -e "$TPM_DIR" || -L "$TPM_DIR" ]]; then

    echo "[ERROR] TPM directory exists but installation is incomplete:"
    echo "$TPM_DIR"
    echo "Inspect it manually before retrying."
    exit 1

else

    echo "Installing TPM..."

    mkdir -p "$(dirname "$TPM_DIR")"

    git clone --depth 1 \
        https://github.com/tmux-plugins/tpm \
        "$TPM_DIR"

    echo "[OK] TPM installed."

fi

# ============================================================
# Plugins
# ============================================================

echo
echo "Installing tmux plugins..."
echo

bash "$TPM_DIR/bin/install_plugins"

echo
echo "tmux plugins installed successfully."
