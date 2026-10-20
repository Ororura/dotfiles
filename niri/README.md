# Niri: Catppuccin Mocha

Основная инструкция по переносу, зависимостям, профилям оборудования и откату:
`~/.dotfiles/desktop/README.md`.

Конфигурации подключены из `~/.dotfiles`; скрипты находятся здесь в `scripts/`.
Главный файл: `config.kdl`; разделы: `config.d/`.

После изменения профиля мониторов или шаблонов повторите установку:

```bash
bash ~/.dotfiles/scripts/install-niri.sh --profile ororura-desktop --rgb
```

Для другого компьютера используйте профиль по умолчанию без `--rgb`.
Горячие клавиши: Super+F1 или `scripts/shortcuts.py --list`.
Логи: `journalctl --user -b -u niri.service -u waybar.service`.

Повторная установка сохраняет заменяемые файлы в `~/.dotfiles-backups/`.
Для отката передайте каталог конкретной копии скрипту `scripts/restore-original.py`.
