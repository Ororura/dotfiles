"""Safety checks for Git AI tools."""

import subprocess
from pathlib import Path


SENSITIVE_NAMES = {
    ".env",
    "id_rsa",
    "id_ed25519",
    "credentials.json",
    "secrets.yml",
    "secrets.yaml",
}

SENSITIVE_EXTENSIONS = (
    ".pem",
    ".p12",
    ".pfx",
    ".key",
)

ALLOWED_ENV_SUFFIXES = (
    ".example",
    ".sample",
    ".template",
    ".dist",
)


def is_sensitive(path):
    name = Path(path).name.lower()

    if name in SENSITIVE_NAMES:
        return True

    if name.startswith(".env."):
        return not name.endswith(ALLOWED_ENV_SUFFIXES)

    return name.endswith(SENSITIVE_EXTENSIONS)


def changed_files(include_unstaged=False):
    commands = [
        ["git", "diff", "--cached", "--name-only", "-z"],
    ]

    if include_unstaged:
        commands.append(
            ["git", "diff", "--name-only", "-z"]
        )

    files = set()

    for command in commands:
        result = subprocess.run(
            command,
            capture_output=True,
            check=True,
            timeout=60,
        )

        paths = result.stdout.decode(
            "utf-8",
            errors="replace",
        ).split("\0")

        files.update(
            path for path in paths if path
        )

    return files


def check_sensitive_changes(include_unstaged=False):
    files = changed_files(include_unstaged)

    suspicious = sorted(
        path
        for path in files
        if is_sensitive(path)
    )

    if suspicious:
        raise ValueError(
            "Sensitive-looking files detected:\n"
            + "\n".join(suspicious)
            + "\nReview the changes before sending them to Ollama."
        )
