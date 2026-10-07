#!/usr/bin/env bash

set -euo pipefail

DOTFILES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
PACKAGE_FILE="$DOTFILES_DIR/apt/packages.txt"
DRY_RUN=false

case "${1:-}" in
    "") ;;
    --dry-run) DRY_RUN=true ;;
    *) echo "[ERROR] Unknown argument: $1"; exit 1 ;;
esac

if [[ "$(uname -s)" != Linux ]] || ! command -v apt-get >/dev/null 2>&1; then
    echo "[ERROR] APT Bundle requires Linux with apt-get."
    exit 1
fi

if [[ ! -f "$PACKAGE_FILE" ]]; then
    echo "[ERROR] Package list not found: $PACKAGE_FILE"
    exit 1
fi

packages=()
while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%%#*}"
    read -r -a words <<< "$line"
    if (( ${#words[@]} == 0 )); then
        continue
    fi
    if (( ${#words[@]} != 1 )) ||
       [[ ! "${words[0]}" =~ ^[a-zA-Z0-9][a-zA-Z0-9._+-]*$ ]]; then
        echo "[ERROR] Invalid package line: $line"
        exit 1
    fi
    packages+=("${words[0]}")
done < "$PACKAGE_FILE"

if (( ${#packages[@]} == 0 )); then
    echo "[INFO] No packages configured."
    exit 0
fi

echo
echo "================================"
echo " APT Bundle"
echo "================================"
echo
printf '  %s\n' "${packages[@]}"
echo

if [[ "$DRY_RUN" == true ]]; then
    echo "[DRY RUN] Would update APT indexes and install the packages listed above."
    exit 0
fi

prefix=()
if (( EUID != 0 )); then
    if ! command -v sudo >/dev/null 2>&1; then
        echo "[ERROR] Run as root or install sudo before using --apt."
        exit 1
    fi
    prefix=(sudo)
fi

"${prefix[@]}" apt-get update
"${prefix[@]}" apt-get install -y "${packages[@]}"

echo "[OK] APT Bundle completed."
