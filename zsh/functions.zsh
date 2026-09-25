# ============================================================
# Clipboard
# ============================================================

_copy_to_clipboard() {

    if [[ "$(uname -s)" == "Darwin" ]] &&
       command -v pbcopy >/dev/null 2>&1; then

        pbcopy

    elif command -v wl-copy >/dev/null 2>&1; then

        wl-copy

    elif command -v xclip >/dev/null 2>&1; then

        xclip -selection clipboard

    elif command -v xsel >/dev/null 2>&1; then

        xsel --clipboard --input

    else

        print -u2 "Clipboard utility not found."
        return 1

    fi

}

# ============================================================
# Git Commit Context
# ============================================================

commitctx() {

    git rev-parse --is-inside-work-tree \
        >/dev/null 2>&1 || return 1

    {
        git status --short

        printf '\n'

        git diff --cached --stat

        printf '\n'

        git diff --cached

    } | _copy_to_clipboard

}

# ============================================================
# Git Clean Merged Branches
# ============================================================

git-clean-branches() {

    git rev-parse --is-inside-work-tree \
        >/dev/null 2>&1 || return 1

    echo "Fetching remote branches..."

    git fetch origin --prune || return 1

    echo "Switching to main..."

    git switch main || return 1

    git pull --ff-only origin main || return 1

    echo "Cleaning merged branches..."

    local branch

    while IFS= read -r branch; do

        case "$branch" in
            main|master|develop)
                continue
                ;;
        esac

        # Skip branches used by worktrees

        if git worktree list --porcelain |
           grep -Fxq "branch refs/heads/$branch"; then

            echo "Skipping worktree branch: $branch"
            continue

        fi

        # Delete only merged branches

        git branch -d -- "$branch" ||
            echo "Could not delete: $branch"

    done < <(
        git for-each-ref \
            --merged=refs/heads/main \
            --format='%(refname:short)' \
            refs/heads
    )

    echo "Branch cleanup completed."

}

# ============================================================
# Dotfiles Update
# ============================================================

dotfiles-update() {

    git -C "$HOME/.dotfiles" pull --ff-only || return 1

    echo "Dotfiles updated."

    exec zsh

}

