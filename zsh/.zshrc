# ============================================================
# Powerlevel10k Instant Prompt
# ============================================================

if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
    source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
fi

# ============================================================
# Dotfiles
# ============================================================

export DOTFILES_DIR="$HOME/.dotfiles"

# Avoid duplicate PATH entries
typeset -U path PATH

# ============================================================
# PATH
# ============================================================

for dir in \
    "$HOME/.local/bin" \
    "$HOME/go/bin" \
    "$HOME/.opencode/bin" \
    "$HOME/.lmstudio/bin"
do
    [[ -d "$dir" ]] && path=("$dir" $path)
done

# ============================================================
# Operating System
# ============================================================

case "$(uname -s)" in
    Darwin)
        [[ -f "$DOTFILES_DIR/zsh/macos.zsh" ]] &&
            source "$DOTFILES_DIR/zsh/macos.zsh"
        ;;

    Linux)
        [[ -f "$DOTFILES_DIR/zsh/linux.zsh" ]] &&
            source "$DOTFILES_DIR/zsh/linux.zsh"
        ;;
esac


# ============================================================
# Oh My Zsh
# ============================================================

export ZSH="$HOME/.oh-my-zsh"

if [[ -f "$ZSH/oh-my-zsh.sh" ]]; then

    ZSH_THEME="robbyrussell"

    if [[ -f "$ZSH/custom/themes/powerlevel10k/powerlevel10k.zsh-theme" ]]; then
        ZSH_THEME="powerlevel10k/powerlevel10k"
    fi

    zstyle ':omz:update' mode auto

    plugins=(git)

    for plugin in \
        zsh-autosuggestions \
        zsh-syntax-highlighting
    do
        if [[ -d "$ZSH/custom/plugins/$plugin" ]]; then
            plugins+=("$plugin")
        fi
    done

    source "$ZSH/oh-my-zsh.sh"

fi

# ============================================================
# Zoxide
# ============================================================

if command -v zoxide >/dev/null 2>&1; then
    eval "$(zoxide init zsh)"
fi

# ============================================================
# Aliases and Functions
# ============================================================

for config in \
    aliases.zsh \
    functions.zsh
do
    [[ -f "$DOTFILES_DIR/zsh/$config" ]] &&
        source "$DOTFILES_DIR/zsh/$config"
done

# ============================================================
# NVM
# ============================================================

export NVM_DIR="$HOME/.nvm"

[[ -s "$NVM_DIR/nvm.sh" ]] &&
    source "$NVM_DIR/nvm.sh"

# ============================================================
# Powerlevel10k Configuration
# ============================================================

[[ -f "$HOME/.p10k.zsh" ]] &&
    source "$HOME/.p10k.zsh"

# ============================================================
# Local Configuration
# ============================================================

[[ -f "$HOME/.zshrc.local" ]] &&
    source "$HOME/.zshrc.local"

# ============================================================
# SDKMAN
# ============================================================

export SDKMAN_DIR="$HOME/.sdkman"

[[ -s "$SDKMAN_DIR/bin/sdkman-init.sh" ]] &&
    source "$SDKMAN_DIR/bin/sdkman-init.sh"
