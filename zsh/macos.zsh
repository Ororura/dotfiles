# ============================================================
# macOS Configuration
# ============================================================

# Homebrew

if [[ -x /opt/homebrew/bin/brew ]]; then

    eval "$(/opt/homebrew/bin/brew shellenv)"

elif [[ -x /usr/local/bin/brew ]]; then

    eval "$(/usr/local/bin/brew shellenv)"

fi

# PostgreSQL CLI

for dir in \
    /opt/homebrew/opt/libpq/bin \
    /usr/local/opt/libpq/bin
do
    [[ -d "$dir" ]] && path=("$dir" $path)
done

