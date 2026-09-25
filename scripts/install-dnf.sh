#!/usr/bin/env bash

set -euo pipefail

DOTFILES_DIR="$(
    cd "$(dirname "${BASH_SOURCE[0]}")/.." &&
    pwd -P
)"

PACKAGE_FILE="$DOTFILES_DIR/dnf/packages.txt"

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

if [[ "$(uname -s)" != Linux ]]; then
    echo "[ERROR] DNF Bundle supports Linux only."
    exit 1
fi

if ! command -v dnf >/dev/null 2>&1; then
    echo "[ERROR] DNF not found."
    exit 1
fi

if [[ ! -f "$PACKAGE_FILE" ]]; then
    echo "[ERROR] Package list not found: $PACKAGE_FILE"
    exit 1
fi

packages=()

while IFS= read -r line || [[ -n "$line" ]]; do

    # Remove comments
    line="${line%%#*}"

    # Split the remaining line into words
    read -r -a words <<< "$line"

    if (( ${#words[@]} == 0 )); then
        continue
    fi

    if (( ${#words[@]} != 1 )); then
        echo "[ERROR] Expected one package per line: $line"
        exit 1
    fi

    package="${words[0]}"

    if [[ ! "$package" =~ ^[a-zA-Z0-9][a-zA-Z0-9._+-]*$ ]]; then
        echo "[ERROR] Invalid package name: $package"
        exit 1
    fi

    packages+=("$package")

done < "$PACKAGE_FILE"

if (( ${#packages[@]} == 0 )); then
    echo "[INFO] No packages configured."
    exit 0
fi

echo
echo "================================"
echo " Fedora DNF Bundle"
echo "================================"
echo

printf '  %s\n' "${packages[@]}"

echo

if [[ "$DRY_RUN" == true ]]; then
    echo "[DRY RUN] Would request the packages listed above."
    exit 0
fi

if (( EUID == 0 )); then
    dnf install -y "${packages[@]}"
else
    sudo dnf install -y "${packages[@]}"
fi

echo
echo "[OK] DNF Bundle completed."
