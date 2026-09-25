# Ororura Dotfiles

Personal cross-platform terminal and development configuration.

Designed for macOS, Fedora and Ubuntu.

## Features

- Zsh with Oh My Zsh and Powerlevel10k
- Zsh autosuggestions and syntax highlighting
- Git aliases and shared Git configuration
- Ollama-powered Git AI commands
- tmux with TPM and plugins
- Homebrew Bundle for macOS
- Automatic backup of replaced configuration files
- Environment diagnostics
- Automated tests and GitHub Actions CI

## Requirements

Git and Bash are required before installation.

For a minimal installation, Zsh must also be installed.

On Linux, full installation uses DNF or APT and may require sudo.

On macOS, Homebrew is required when terminal packages are missing
or when using the --brew option.

## Installation

Clone the repository into ~/.dotfiles:

```bash
git clone https://github.com/Ororura/dotfiles.git ~/.dotfiles

cd ~/.dotfiles
```

Preview the installation:

```bash
bash install.sh --full --dry-run
```

Install:

```bash
bash install.sh --full
```

Restart Zsh:

```bash
exec zsh
```

The installer does not change your login shell automatically.

## Installation Modes

| Command | Description |
| --- | --- |
| `bash install.sh` | Install Zsh, Git, tmux and Powerlevel10k configuration |
| `bash install.sh --minimal` | Install Zsh and Git configuration only |
| `bash install.sh --full` | Install terminal dependencies, TPM plugins and check Git AI |
| `bash install.sh --full --brew` | Also install the macOS Brewfile |
| `bash install.sh --dry-run` | Preview changes |
| `bash install.sh --doctor` | Diagnose the environment |

The --brew option requires --full and is available only on macOS.

## Git AI

The following commands are available through the shared Git configuration:

| Command | Description |
| --- | --- |
| `git ai-msg` | Generate a commit message |
| `git ai-commit` | Create a commit using an AI-generated message |
| `git ai-branch` | Generate a branch name |
| `git ai-review` | Review Git changes |
| `git ai-pr` | Generate a pull request description |
| `git ai-publish` | Push a branch and create a pull request |
| `git ai-changelog` | Generate a changelog |
| `git ai-split` | Suggest how to split staged changes |
| `git ai-explain` | Explain Git changes |

Git AI uses Ollama.

Default model:

```text
qwen3.5:9b
```

Configure a different model:

```bash
export OLLAMA_GIT_MODEL="your-model"
```

Configure another Ollama endpoint:

```bash
export OLLAMA_GIT_URL="http://127.0.0.1:11434/api/chat"
```

Additional configuration examples are available in:

```text
git/ai.env.example
```

The installer checks Git AI dependencies but does not automatically
download an Ollama model.

GitHub CLI is required for git ai-publish.

## Local Configuration

Machine-specific Zsh settings belong in:

```text
~/.zshrc.local
```

Do not commit API keys, credentials or private environment files.

Git identity and credentials are intentionally not managed by
the shared Git configuration.

Configure Git identity separately on each machine:

```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

## Backups

Before replacing existing configuration files, the installer moves
them to:

```text
~/.dotfiles-backups/
```

The Git configuration installer also backs up an existing .gitconfig
before adding the shared include path.

Automatic restore is not implemented yet.

Inspect the backup directory before manually restoring files.

## Updating

```bash
git -C ~/.dotfiles pull --ff-only

bash ~/.dotfiles/install.sh --full
```

The second command may install missing terminal dependencies
and tmux plugins.

## Diagnostics

```bash
bash ~/.dotfiles/install.sh --doctor
```

## Testing

Run the offline Python tests:

```bash
python3 -m unittest discover -s tests -v
```

Check Bash syntax:

```bash
bash -n install.sh
```

Check all shell scripts:

```bash
find scripts -type f -name '*.sh' -print0 |
    xargs -0 -n 1 bash -n
```

GitHub Actions runs syntax checks and offline tests on pull requests.

## Repository Structure

```text
brew/       macOS Homebrew configuration
git/        Shared Git configuration and AI tools
scripts/    Installation and diagnostic scripts
tests/      Offline tests
tmux/       tmux configuration
zsh/        Zsh configuration
```

## Notes

The repository is intended to be cloned into ~/.dotfiles.

Some configuration and Git AI paths currently depend on that location.

A complete fresh-machine installation should be tested before relying
on this repository as the only backup of a working environment.
