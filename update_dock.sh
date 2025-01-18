#!/bin/bash

# Устанавливаем задержку автоскрытия Dock в 0
defaults write com.apple.dock autohide-delay -int 0

# Устанавливаем модификатор времени скрытия Dock
defaults write com.apple.dock autohide-time-modifier -float 0.45

# Перезапускаем Dock, чтобы изменения вступили в силу
killall Dock

echo "Dock settings updated successfully!"
