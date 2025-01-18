# restore-brew.sh
#!/bin/bash

echo "Restoring Homebrew taps..."
xargs brew tap < brew-taps.txt

echo "Installing formulas..."
xargs brew install < brew-formulas.txt

echo "Installing casks..."
xargs brew install --cask < brew-casks.txt

echo "All packages restored successfully!"

