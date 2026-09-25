#!/usr/bin/env bash

set -euo pipefail

OS="$(uname -s)"

echo "Installing terminal dependencies..."

# ============================================================
# System packages
# ============================================================

install_packages() {

    local packages=()

    case "$OS" in

        Darwin)

            for package in zoxide tmux; do
                if ! command -v "$package" >/dev/null 2>&1; then
                    packages+=("$package")
                fi
            done

            if (( ${#packages[@]} > 0 )); then

                if command -v brew >/dev/null 2>&1; then
                    brew install "${packages[@]}"

                elif [[ -x /opt/homebrew/bin/brew ]]; then
                    /opt/homebrew/bin/brew install "${packages[@]}"

                elif [[ -x /usr/local/bin/brew ]]; then
                    /usr/local/bin/brew install "${packages[@]}"

                else
                    echo "Homebrew is required."
                    exit 1
                fi

            fi
            ;;

        Linux)

            for package in zsh git zoxide tmux; do
                if ! command -v "$package" >/dev/null 2>&1; then
                    packages+=("$package")
                fi
            done

            if (( ${#packages[@]} == 0 )); then
                echo "System packages already installed."
                return
            fi

            local prefix=()

            if (( EUID != 0 )); then
                prefix=(sudo)
            fi

            if command -v dnf >/dev/null 2>&1; then

                "${prefix[@]}" dnf install -y "${packages[@]}"

            elif command -v apt-get >/dev/null 2>&1; then

                "${prefix[@]}" apt-get update

                "${prefix[@]}" apt-get install -y "${packages[@]}"

            else

                echo "Unsupported Linux package manager."
                exit 1

            fi
            ;;

        *)

            echo "Unsupported operating system: $OS"
            exit 1
            ;;

    esac

}

install_packages

# ============================================================
# Git
# ============================================================

if ! command -v git >/dev/null 2>&1; then
    echo "Git is required."
    exit 1
fi

# ============================================================
# Clone helper
# ============================================================

clone_if_missing() {

    local repository="$1"
    local destination="$2"

    if [[ -d "$destination" ]]; then

        echo "Already exists: $destination"
        return

    fi

    if [[ -e "$destination" || -L "$destination" ]]; then
        echo "Path exists but is not a directory: $destination"
        exit 1
    fi

    git clone --depth=1 "$repository" "$destination"

}

# ============================================================
# Oh My Zsh
# ============================================================

clone_if_missing \
    "https://github.com/ohmyzsh/ohmyzsh.git" \
    "$HOME/.oh-my-zsh"

ZSH_CUSTOM="$HOME/.oh-my-zsh/custom"

# ============================================================
# Powerlevel10k
# ============================================================

clone_if_missing \
    "https://github.com/romkatv/powerlevel10k.git" \
    "$ZSH_CUSTOM/themes/powerlevel10k"

# ============================================================
# Plugins
# ============================================================

clone_if_missing \
    "https://github.com/zsh-users/zsh-autosuggestions.git" \
    "$ZSH_CUSTOM/plugins/zsh-autosuggestions"

clone_if_missing \
    "https://github.com/zsh-users/zsh-syntax-highlighting.git" \
    "$ZSH_CUSTOM/plugins/zsh-syntax-highlighting"

# ============================================================
# Complete
# ============================================================

echo
echo "All terminal dependencies are installed."
