#!/usr/bin/env bash

set -euo pipefail

echo
echo "================================"
echo " Git AI Setup"
echo "================================"
echo

# ============================================================
# Python
# ============================================================

echo "Checking Python..."

if ! command -v python3 >/dev/null 2>&1; then

    echo "[MISSING] Python 3"

elif ! python3 -c '
import sys
sys.exit(0 if sys.version_info >= (3, 9) else 1)
'; then

    echo "[ERROR] Python 3.9+ is required."

else

    echo "[OK] $(python3 --version)"

fi

# ============================================================
# GitHub CLI
# ============================================================

echo
echo "Checking GitHub CLI..."

if command -v gh >/dev/null 2>&1; then

    echo "[OK] $(gh --version | head -n 1)"

else

    echo "[MISSING] GitHub CLI"
    echo "Required for git ai-publish."

fi

# ============================================================
# Ollama
# ============================================================

echo
echo "Checking Ollama..."

if command -v ollama >/dev/null 2>&1; then

    echo "[OK] Ollama CLI installed."

else

    echo "[MISSING] Ollama CLI"
    echo "A remote Ollama API can still be used."

fi

# ============================================================
# Ollama API and Model
# ============================================================

MODEL="${OLLAMA_GIT_MODEL:-qwen3.5:9b}"

URL="${OLLAMA_GIT_URL:-http://127.0.0.1:11434/api/chat}"

echo
echo "Model: $MODEL"
echo "API: $URL"
echo

if command -v python3 >/dev/null 2>&1; then

    if python3 -c '
import sys
sys.exit(0 if sys.version_info >= (3, 9) else 1)
'; then

        python3 - "$URL" "$MODEL" <<'PY'
import json
import sys
import urllib.error
import urllib.request
from urllib.parse import urlsplit

url = sys.argv[1]
model = sys.argv[2]

parsed = urlsplit(url)

if not (
    parsed.scheme in ("http", "https")
    and parsed.path.endswith("/api/chat")
):
    print("[WARNING] Expected Ollama /api/chat URL.")
    sys.exit(0)

tags_url = url.rsplit("/", 1)[0] + "/tags"

try:

    with urllib.request.urlopen(
        tags_url,
        timeout=3,
    ) as response:

        data = json.load(response)

except (
    urllib.error.URLError,
    TimeoutError,
    ValueError,
    OSError,
) as error:

    print("[WARNING] Ollama API unavailable.")
    print(f"Details: {error}")
    sys.exit(0)

print("[OK] Ollama API available.")

models = {
    item.get("name")
    for item in data.get("models", [])
}

if model in models:

    print(f"[OK] Model installed: {model}")

else:

    print(f"[MISSING] Model: {model}")
    print(f"Install locally with: ollama pull {model}")

PY

    fi

fi

echo
echo "================================"
echo " Git AI setup check completed"
echo "================================"
