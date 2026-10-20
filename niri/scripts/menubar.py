#!/usr/bin/python3
"""Working desktop menus for Waybar; window actions use Niri's public IPC."""
from pathlib import Path
import argparse
import fcntl
import importlib.util
import json
import re
import subprocess

HOME = Path.home()
SCRIPTS = HOME / '.config/niri/scripts'
APP_REWRITES = {
    r'^com\.mitchellh\.ghostty$': 'Ghostty',
    r'^org\.gnome\.Nautilus$': 'Файлы',
    r'^org\.gnome\.Settings$': 'Настройки',
    r'^org\.gnome\.TextEditor$': 'Текстовый редактор',
    r'^org\.telegram\.desktop$': 'Telegram',
    r'^google-chrome(-.*)?$': 'Chrome',
    r'^chromium(-browser)?$': 'Chromium',
    r'^(firefox|org\.mozilla\.firefox)$': 'Firefox',
    r'^(Code|code|code-url-handler|com\.visualstudio\.code)$': 'VS Code',
    r'^jetbrains-idea.*$': 'IntelliJ IDEA',
    r'^jetbrains-webstorm.*$': 'WebStorm',
    r'^(Chatgpt|chatgpt|com\.openai\.ChatGPT)$': 'ChatGPT',
    r'^(discord|com\.discordapp\.Discord)$': 'Discord',
    r'^(Slack|slack|com\.slack\.Slack)$': 'Slack',
    r'^(pavucontrol|org\.pulseaudio\.pavucontrol)$': 'Звук',
    r'^$': 'Рабочий стол',
}


def app_name(app_id):
    for pattern, name in APP_REWRITES.items():
        if re.fullmatch(pattern, app_id or ''):
            return name
    return app_id or 'Рабочий стол'


def controls():
    spec = importlib.util.spec_from_file_location('niri_controls', SCRIPTS / 'quick-settings.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def pick(title, entries):
    labels = [label.replace('\n', ' ').replace('\r', ' ') for _, label in entries]
    result = subprocess.run(['fuzzel', '--dmenu', '--keyboard-focus=on-demand', '--no-icons', '--width=56', '--lines=10',
                             '--anchor=top-left', '--x-margin=8', '--y-margin=0',
                             '--prompt=' + title + ' ❯ '], input='\n'.join(labels) + '\n',
                            text=True, capture_output=True)
    if result.returncode:
        return None
    selected = result.stdout.rstrip('\n')
    return next((key for (key, _), label in zip(entries, labels) if label == selected), None)


def about():
    release = {}
    for line in Path('/etc/os-release').read_text().splitlines():
        if '=' in line:
            key, value = line.split('=', 1)
            release[key] = value.strip('"')
    cpu = next((line.split(':', 1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines()
                if line.startswith('model name')), 'CPU')
    ram = next(int(line.split()[1]) / 1024**2 for line in Path('/proc/meminfo').read_text().splitlines()
               if line.startswith('MemTotal:'))
    version = subprocess.check_output(['niri', '--version'], text=True).strip()
    pick('Об этом компьютере', [(str(i), value) for i, value in enumerate([
        release.get('PRETTY_NAME', 'Fedora Linux'), version + ' · Wayland', cpu,
        f'Оперативная память: {ram:.1f} GiB', 'Оформление: Catppuccin Mocha',
        'Конфигурации: ~/.config/niri и ~/.config/waybar', 'Esc — закрыть'])])


def system_menu(control):
    choice = pick('Система', [
        ('about', 'Об этом компьютере'), ('settings', 'Быстрые настройки…        Super+S'),
        ('apps', 'Приложения…                  Super+D'),
        ('files', 'Файлы · Nautilus'), ('yazi', 'Файлы · Yazi                 Super+E'),
        ('terminal', 'Терминал · Ghostty           Super+Enter'),
        ('config', 'Открыть папку конфигурации Niri'),
        ('lock', 'Заблокировать экран         Super+Shift+L'),
        ('power', 'Выход и питание…')])
    if choice == 'about': about()
    elif choice == 'settings': control.menu()
    elif choice == 'apps': control.launch(['fuzzel'])
    elif choice == 'files': control.launch(['nautilus', '--new-window'])
    elif choice == 'yazi': control.launch([str(SCRIPTS / 'yazi-terminal')])
    elif choice == 'terminal': control.launch([str(SCRIPTS / 'ghostty-mocha')])
    elif choice == 'config': control.launch(['nautilus', str(HOME / '.config/niri')])
    elif choice == 'lock': control.run(['systemctl', '--user', 'start', 'niri-lock.service'], timeout=20)
    elif choice == 'power': control.run([str(SCRIPTS / 'power-menu')], timeout=None)


def window_menu(control):
    windows = json.loads(control.run(['niri', 'msg', '--json', 'windows']).stdout)
    window = next((w for w in windows if w.get('is_focused')), None)
    if window is None:
        pick('Окно', [('overview', 'Открытых окон на этом пространстве нет · обзор Super+O')])
        return
    floating = window.get('is_floating', False)
    entries = [('fullscreen', 'Полноэкранный режим                Super+F')]
    if not floating:
        entries += [('maximize', 'На всю ширину / вернуть             Super+M'),
                    ('width', 'Следующая ширина колонки             Super+R'),
                    ('center', 'Центрировать колонку                 Super+C')]
    entries += [('floating', ('Вернуть в тайлинг' if floating else 'Сделать плавающим') + '              Super+Shift+Space'),
                ('overview', 'Обзор рабочих пространств            Super+O'),
                ('close', 'Закрыть окно                         Super+Q')]
    choice = pick(app_name(window.get('app_id')), entries)
    if choice is None:
        return
    # The menu may outlive its source window. Never apply an action to whichever
    # other window happens to become focused after that window has closed.
    current = json.loads(control.run(['niri', 'msg', '--json', 'windows']).stdout)
    if not any(w['id'] == window['id'] for w in current):
        return
    actions = {'fullscreen': 'fullscreen-window', 'maximize': 'maximize-column',
               'width': 'switch-preset-column-width', 'center': 'center-column',
               'floating': 'toggle-window-floating', 'overview': 'toggle-overview', 'close': 'close-window'}
    control.run(['niri', 'msg', 'action', 'focus-window', '--id', str(window['id'])])
    control.run(['niri', 'msg', 'action', actions[choice]])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('menu', choices=['system', 'window', 'about'])
    args = parser.parse_args()
    control = controls()
    with (control.session_dir() / 'menubar.lock').open('w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        if args.menu == 'system': system_menu(control)
        elif args.menu == 'window': window_menu(control)
        else: about()


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        subprocess.run(['notify-send', '--app-name=Niri', 'Меню панели', str(error)])
        raise SystemExit(1)
