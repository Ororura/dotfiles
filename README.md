# Ororura Dotfiles

Shared terminal and development configuration for **macOS, Fedora, and Ubuntu**. This repository manages Zsh, Git, tmux, Neovim (LazyVim), Ghostty, and optional macOS Homebrew applications.

> **Clone to `~/.dotfiles`.** The Zsh configuration and Git AI aliases currently depend on this path.

## Quick start

Prerequisites: Git and Bash. Install Homebrew before using `--brew` on macOS. The full installer installs missing terminal basics (Zoxide/tmux on macOS; Zsh/Git/Zoxide/tmux via DNF or APT on Linux), Oh My Zsh, Powerlevel10k, Zsh plugins, and TPM plugins.

### macOS

~~~bash
git clone https://github.com/Ororura/dotfiles.git ~/.dotfiles
cd ~/.dotfiles

# Inspect the curated application list first:
cat brew/Brewfile

# Preview the operation before installing:
bash install.sh --full --brew --nvim --ghostty --dry-run

# Install dependencies and link your configurations:
bash install.sh --full --brew --nvim --ghostty

exec zsh
bash install.sh --doctor
~~~

`--brew` installs the curated Brewfile (including Ghostty and Neovim), but does **not** install Homebrew itself.

### Fedora / Ubuntu

~~~bash
# Fedora:
sudo dnf install -y git bash

# Ubuntu alternative:
# sudo apt-get update && sudo apt-get install -y git bash

git clone https://github.com/Ororura/dotfiles.git ~/.dotfiles
cd ~/.dotfiles

bash install.sh --full --nvim --ghostty --dry-run
bash install.sh --full --nvim --ghostty

exec zsh
bash install.sh --doctor
~~~

On Linux, **Neovim, Ghostty, Ollama, and an Ollama model are not installed automatically**. Install the applications separately; `--nvim` and `--ghostty` connect the tracked configs.

The installer does not change your default login shell. `exec zsh` starts Zsh in the current terminal.

## Installation modes

All commands below run from `~/.dotfiles`.

| Command | Behavior |
| --- | --- |
| `bash install.sh` | Link Zsh, Git, tmux, and Powerlevel10k configs; no dependency installation. |
| `bash install.sh --minimal` | Link only Zsh and Git configuration. Have Zsh installed beforehand. |
| `bash install.sh --full` | Install missing terminal tools, Oh My Zsh/Powerlevel10k/Zsh plugins, TPM/tmux plugins; check Git AI dependencies. |
| `bash install.sh --full --brew` | Also install `brew/Brewfile`; macOS only. |
| `bash install.sh --nvim` | Also link Neovim config. |
| `bash install.sh --ghostty` | Also link Ghostty config. |
| `bash install.sh --nvim --ghostty` | Link both editor and terminal configs. |
| `bash install.sh --dry-run` | Preview the selected operation without changes. |
| `bash install.sh --doctor` | Diagnose configuration links and optional tools. |

Combine `--nvim` and `--ghostty` with `--full` if desired. They cannot be combined with `--minimal`. `--brew` requires `--full`. `--doctor` is a standalone mode.

### Installed links

| Repository path | Destination |
| --- | --- |
| `zsh/.zshrc` | `~/.zshrc` |
| `zsh/.p10k.zsh` | `~/.p10k.zsh` (non-minimal mode) |
| `tmux/tmux.conf` | `~/.tmux.conf` (non-minimal mode) |
| `git/config` | Included via global Git `include.path`; does not replace `~/.gitconfig` |
| `nvim/` | `${XDG_CONFIG_HOME:-$HOME/.config}/nvim` with `--nvim` |
| `ghostty/config` | `${XDG_CONFIG_HOME:-$HOME/.config}/ghostty/config` with `--ghostty` |

All config files remain in the Git repository. A linked config updates immediately when you edit its source; re-running the installer is normally unnecessary.

## Where to make changes

| Task | File |
| --- | --- |
| Simple shell shortcuts | `zsh/aliases.zsh` |
| Multi-step shell helpers | `zsh/functions.zsh` |
| Shared shell initialization and PATH | `zsh/.zshrc` |
| macOS-only / Linux-only shell settings | `zsh/macos.zsh` / `zsh/linux.zsh` |
| Machine-only settings and model selection | `~/.zshrc.local` (not tracked) |
| Terminal prompt appearance | `zsh/.p10k.zsh` or `p10k configure` |
| Shared Git settings / aliases | `git/config` |
| Git AI behavior | `git/scripts/`; defaults in `git/ai.env.example` |
| Mac applications | `brew/Brewfile` |
| tmux keys and plugins | `tmux/tmux.conf` |
| Neovim options / keymaps / plugins | `nvim/lua/config/` / `nvim/lua/plugins/` |
| Ghostty font, colors, window settings | `ghostty/config` |
| Installer / diagnostic behavior | `install.sh` / `scripts/doctor.sh` |

Example additions:

~~~zsh
# zsh/aliases.zsh:
alias dps="docker compose ps"

# zsh/functions.zsh:
backend-check() {
  ./gradlew test || return 1
  ./gradlew build || return 1
}
~~~

After changing shared Zsh files, run `exec zsh`. Git reads changes to `git/config` on the next command. Reload tmux with `tmux source-file ~/.tmux.conf`.

## Machine-local configuration

`zsh/.zshrc` automatically sources `~/.zshrc.local` when it exists. Keep settings that differ between MacBook, Fedora, and a VPS there rather than committing several copies of `.zshrc`.

~~~zsh
# ~/.zshrc.local — not in this repository
export OLLAMA_GIT_MODEL="qwen3.5:9b"
export OLLAMA_GIT_URL="http://127.0.0.1:11434/api/chat"
~~~

Keep secrets outside the public repository, preferably in an appropriate credential store. Configure Git identity separately on every machine:

~~~bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
~~~

### Shell helpers

- `dotfiles` — jump to `~/.dotfiles`.
- `n` — launch Neovim.
- `commitctx` — copy staged Git status/diff into the clipboard (review it for secrets).
- `git-clean-branches` — fetch, switch/update `main`, and remove **local** merged branches that are not used by worktrees.
- `dotfiles-update` — pull the **currently checked-out dotfiles branch** and restart Zsh. Switch to `main` first if that is what you intend to update.

## Git AI (local Ollama)

The shared `git/config` defines these commands:

| Command | Action |
| --- | --- |
| `git ai-msg` | Generate a staged-diff commit message without committing. |
| `git ai-commit` | Generate a message, open an editor, commit. |
| `git ai-branch "describe the task"` | Suggest a branch name and ask before creating it. |
| `git ai-review` | Review staged changes; `--worktree` reviews tracked changes relative to HEAD. |
| `git ai-split` | Suggest groups of commits; does **not** modify Git or create commits. |
| `git ai-pr --base main` | Describe **committed** branch changes for a PR. |
| `git ai-publish` | Push the branch, draft a PR body, invoke GitHub CLI. |
| `git ai-changelog --base v1.0.0` | Draft release notes from a tag/commit. |
| `git ai-explain HEAD` | Explain a commit. |

Typical flow:

~~~bash
git add -p
git diff --cached --check
git ai-review
git ai-commit
git ai-publish
~~~

The default model is `qwen3.5:9b` and the default endpoint is `http://127.0.0.1:11434/api/chat`. `git/ai.env.example` documents environment overrides. `--full` checks Git AI requirements; it does **not** install Ollama, pull a model, or log in to GitHub CLI. Use `gh auth login` separately if needed.

The AI tools inspect diffs. Review staged changes before invoking them: file-name safety checks cannot guarantee secret detection. If you configure a remote Ollama endpoint, the selected changes are sent to that server.

## Neovim

`nvim/` is a LazyVim starter-based setup. The installer links this directory, while lazy.nvim downloads plugins separately on each machine.

~~~bash
bash install.sh --nvim --dry-run
bash install.sh --nvim
nvim
~~~

| Path | Purpose |
| --- | --- |
| `nvim/lua/config/options.lua` | Editor options |
| `nvim/lua/config/keymaps.lua` | Key mappings |
| `nvim/lua/config/autocmds.lua` | Autocommands |
| `nvim/lua/config/lazy.lua` | lazy.nvim / LazyVim initialization |
| `nvim/lua/plugins/` | Plugin definitions and overrides |
| `nvim/lazy-lock.json` | Locked plugin revisions |

Inside Neovim: `:Lazy` inspects plugins, `:Lazy restore` restores lockfile revisions, and `:checkhealth` diagnoses the environment. Do **not** commit `~/.local/share/nvim`, Mason binaries, editor state, or caches.

## Ghostty

The tracked configuration is `ghostty/config`. It specifies JetBrainsMono Nerd Font Mono, Xcode Dark, and window preferences. The font and theme must be available on the target machine. `macos-option-as-alt` and some other settings are specific to macOS.

~~~bash
bash install.sh --ghostty --dry-run
bash install.sh --ghostty

ls -l "${XDG_CONFIG_HOME:-$HOME/.config}/ghostty/config"
~~~

**The same XDG path is used on macOS and Linux:**

~~~text
${XDG_CONFIG_HOME:-$HOME/.config}/ghostty/config
    -> ~/.dotfiles/ghostty/config
~~~

macOS can also have a separate legacy file at `~/Library/Application Support/com.mitchellh.ghostty/config`. Inspect and back it up if it exists. This installer only manages the XDG file; it does **not** reconcile or remove the legacy file, so avoid conflicting settings across locations.

Edit `ghostty/config` in the repository, then reload Ghostty configuration or restart Ghostty as needed. `--ghostty` does not install the app; the macOS Brewfile includes its cask, while Linux installation is separate.

## tmux

`tmux/tmux.conf` uses **Ctrl+A** as prefix and configures pane navigation, resizing, and plugins (TPM, tmux-sensible, tmux-resurrect, vim-tmux-navigator).

~~~bash
tmux new -s dev
tmux ls
tmux attach -t dev
tmux source-file ~/.tmux.conf
~~~

Inside tmux, use `Ctrl+A` then `d` to detach, `|` to split horizontally (side-by-side), or `-` to split vertically (top/bottom). `--full` bootstraps TPM and its plugins; to install declared plugins again:

~~~bash
bash ~/.tmux/plugins/tpm/bin/install_plugins
~~~

## Homebrew applications (macOS)

`brew/Brewfile` is curated. Add desired CLI tools with `brew "name"` and applications with `cask "name"`.

~~~bash
brew bundle check --file=brew/Brewfile --no-upgrade
brew bundle install --file=brew/Brewfile --no-upgrade
~~~

Removing an entry does not uninstall it from the current machine. Avoid overwriting the curated list with a complete `brew bundle dump --force` unless you deliberately intend to review and replace it.

## Backups, updates, diagnostics

Before replacing existing configs, installers move originals into timestamped locations under `~/.dotfiles-backups/`. The Git installer copies the existing `~/.gitconfig` before adding an include path. **Automatic restore is not implemented**; inspect and restore backups manually.

~~~bash
ls -lah ~/.dotfiles-backups/
bash ~/.dotfiles/install.sh --doctor

ls -l ~/.zshrc ~/.tmux.conf
git config --show-origin --get-all include.path
ls -l "${XDG_CONFIG_HOME:-$HOME/.config}/nvim"
ls -l "${XDG_CONFIG_HOME:-$HOME/.config}/ghostty/config"
~~~

`--doctor` checks required links plus optional programs and components. `[MISSING]` for an optional program does not necessarily indicate an installation failure.

To update another machine:

~~~bash
cd ~/.dotfiles
git switch main
git pull --ff-only
exec zsh
~~~

Re-run `--nvim` / `--ghostty` if you have not yet installed their links. `git pull` does not install newly added Brewfile packages automatically.

## Development, tests, and CI

Use a feature branch for shared changes:

~~~bash
cd ~/.dotfiles
git switch main
git pull --ff-only
git switch -c feat/my-change

# Edit and test.
git status --short
git diff --check
git add <files>
git commit -m "feat: describe the change"
git push -u origin HEAD
gh pr create --base main --fill
~~~

Run offline checks:

~~~bash
bash -n install.sh
find scripts -type f -name '*.sh' -print0 | xargs -0 -n 1 bash -n
zsh -n zsh/.zshrc
python3 -m unittest discover -s tests -v
~~~

GitHub Actions runs Bash/Zsh/Python syntax checks and Python tests on pull requests to `main`. It is not a full graphical Ghostty/Neovim integration test; verify app behavior manually on each OS.

## Repository structure

~~~text
.dotfiles/
├── .github/workflows/   CI
├── brew/                macOS application list
├── ghostty/             Shared Ghostty config
├── git/                 Git config and AI helpers
├── nvim/                LazyVim config and lockfile
├── scripts/             Installers and diagnostics
├── tests/               Offline tests
├── tmux/                tmux configuration
├── zsh/                 Shared and platform-specific Zsh settings
├── install.sh           Setup entry point
└── README.md
~~~
