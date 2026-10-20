#!/usr/bin/python3
"""Niri-only quick controls. Existing PipeWire, BlueZ, tuned-ppd and Mako."""
from pathlib import Path
import argparse
import fcntl
import hashlib
import json
import os
import subprocess
import sys

HOME = Path.home()
SCRIPT = HOME / '.config/niri/scripts/quick-settings.py'
PROFILE_NAME = 'org.freedesktop.UPower.PowerProfiles'
PROFILE_PATH = '/org/freedesktop/UPower/PowerProfiles'
PROFILES = {'power-saver': 'Энергосбережение', 'balanced': 'Сбалансированный',
            'performance': 'Производительность'}


def run(args, check=True, timeout=5):
    return subprocess.run(args, capture_output=True, text=True, check=check, timeout=timeout)


def session_dir():
    runtime = Path(os.environ['XDG_RUNTIME_DIR'])
    # A new Niri socket means a new session: presentation never leaks to GNOME
    # or to a subsequent Niri login, even if the user manager keeps running.
    identity = os.environ.get('NIRI_SOCKET', '')
    if not identity or os.environ.get('XDG_CURRENT_DESKTOP') != 'niri':
        raise RuntimeError('Эти настройки доступны только в сеансе Niri')
    token = hashlib.sha256(identity.encode()).hexdigest()[:16]
    directory = runtime / ('niri-controls-' + token)
    directory.mkdir(mode=0o700, exist_ok=True)
    return directory


def presenting():
    return (session_dir() / 'presentation').exists()


def toggle_presentation():
    directory = session_dir()
    with (directory / 'toggle.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        flag = directory / 'presentation'
        was_on = flag.exists()
        if was_on:
            flag.unlink()
        else:
            flag.touch(mode=0o600)
        try:
            # Restart resets the idle deadlines on either transition. The same
            # daemon retains before-sleep and explicit logind lock handlers.
            run(['systemctl', '--user', 'restart', 'niri-idle.service'])
            run(['niri', 'msg', 'action', 'power-on-monitors'])
        except Exception:
            if was_on:
                flag.touch(mode=0o600)
            else:
                flag.unlink(missing_ok=True)
            run(['systemctl', '--user', 'restart', 'niri-idle.service'], check=False)
            raise


def idle_action(action):
    if presenting():
        return
    if action == 'lock':
        run(['systemctl', '--user', 'start', 'niri-lock.service'], timeout=20)
    else:
        run(['niri', 'msg', 'action', 'power-off-monitors'])


def modes():
    result = run(['makoctl', 'mode'], check=False)
    return result.stdout.splitlines() if result.returncode == 0 else []


def volume(device):
    result = run(['wpctl', 'get-volume', device], check=False)
    if result.returncode:
        return 'недоступен'
    fields = result.stdout.split()
    try:
        return f'{float(fields[1]) * 100:.0f}%' + (' · выкл.' if '[MUTED]' in fields else '')
    except (ValueError, IndexError):
        return 'недоступен'


def dbus_call(dest, path, interface, method, parameters, timeout=4000):
    from gi.repository import Gio
    bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
    return bus.call_sync(dest, path, interface, method, parameters, None,
                         Gio.DBusCallFlags.NONE, timeout, None).unpack()


def profile_state():
    from gi.repository import GLib
    try:
        return dbus_call(PROFILE_NAME, PROFILE_PATH, 'org.freedesktop.DBus.Properties',
                         'GetAll', GLib.Variant('(s)', (PROFILE_NAME,)))[0]
    except Exception:
        return {}


def set_profile(profile):
    from gi.repository import GLib
    state = profile_state()
    allowed = [p['Profile'] for p in state.get('Profiles', [])]
    if profile not in allowed:
        raise RuntimeError('Этот профиль питания сейчас недоступен')
    dbus_call(PROFILE_NAME, PROFILE_PATH, 'org.freedesktop.DBus.Properties', 'Set',
              GLib.Variant('(ssv)', (PROFILE_NAME, 'ActiveProfile', GLib.Variant('s', profile))), timeout=30000)


def bluetooth_state():
    try:
        objects = dbus_call('org.bluez', '/', 'org.freedesktop.DBus.ObjectManager',
                            'GetManagedObjects', None)[0]
        adapters = {path: data['org.bluez.Adapter1'] for path, data in objects.items()
                    if 'org.bluez.Adapter1' in data}
        devices = {path: data['org.bluez.Device1'] for path, data in objects.items()
                   if 'org.bluez.Device1' in data}
        return adapters, devices
    except Exception:
        return {}, {}


def pick(title, entries):
    labels = [label.replace('\n', ' ').replace('\r', ' ') for _, label in entries]
    if not entries:
        return None
    result = subprocess.run(['fuzzel', '--dmenu', '--keyboard-focus=on-demand', '--no-icons', '--width=60', '--lines=10',
                             '--anchor=top-right', '--x-margin=12', '--y-margin=0',
                             '--prompt=' + title + ' ❯ '], input='\n'.join(labels) + '\n',
                            capture_output=True, text=True)
    if result.returncode:
        return None
    selected = result.stdout.strip('\n')
    return next((key for (key, _), label in zip(entries, labels) if label == selected), None)


def launch(args, env=None):
    subprocess.Popen(args, env=env, stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)


def audio_menu():
    while True:
        choice = pick('Звук', [
            ('output', '󰕾  Звук: ' + volume('@DEFAULT_AUDIO_SINK@') + ' · вкл./выкл.'),
            ('up', '＋  Громкость +5%'), ('down', '−  Громкость −5%'),
            ('mic', '󰍬  Микрофон: ' + volume('@DEFAULT_AUDIO_SOURCE@') + ' · вкл./выкл.'),
            ('mixer', '󰒓  Устройства, громкость приложений и входы…')])
        if choice is None:
            return
        if choice == 'mixer':
            launch(['pavucontrol'])
            return
        if choice in ('output', 'mic'):
            device = '@DEFAULT_AUDIO_SOURCE@' if choice == 'mic' else '@DEFAULT_AUDIO_SINK@'
            run(['wpctl', 'set-mute', device, 'toggle'])
        else:
            run(['wpctl', 'set-volume', '-l', '1.0', '@DEFAULT_AUDIO_SINK@',
                 '5%+' if choice == 'up' else '5%-'])


def bluetooth_menu():
    from gi.repository import GLib
    adapters, devices = bluetooth_state()
    if not adapters:
        raise RuntimeError('Bluetooth-адаптер недоступен')
    path, adapter = next(iter(adapters.items()))
    entries = [('power', '  Bluetooth: ' + ('включён' if adapter.get('Powered') else 'выключен') + ' · переключить')]
    for device_path, device in devices.items():
        if device.get('Paired') or device.get('Connected'):
            label = device.get('Alias', device.get('Address', device_path))
            entries.append((device_path, ('● ' if device.get('Connected') else '○ ') +
                            label + ' · ' + ('отключить' if device.get('Connected') else 'подключить')))
    entries.append(('settings', '󰒓  Поиск и сопряжение устройств…'))
    choice = pick('Bluetooth', entries)
    if choice == 'power':
        dbus_call('org.bluez', path, 'org.freedesktop.DBus.Properties', 'Set',
                  GLib.Variant('(ssv)', ('org.bluez.Adapter1', 'Powered',
                                        GLib.Variant('b', not adapter.get('Powered', False)))))
    elif choice == 'settings':
        # App-local override lets this existing GNOME settings panel open in
        # Niri; neither the session environment nor GNOME settings is changed.
        env = dict(os.environ, XDG_CURRENT_DESKTOP='GNOME')
        launch(['gnome-control-center', 'bluetooth'], env=env)
    elif choice in devices:
        method = 'Disconnect' if devices[choice].get('Connected') else 'Connect'
        dbus_call('org.bluez', choice, 'org.bluez.Device1', method, None, timeout=25000)


def network_menu():
    devices = run(['nmcli', '-t', '-f', 'TYPE', 'device', 'status'], check=False)
    entries = []
    if 'wifi' in devices.stdout.splitlines():
        entries.append(('wifi', '󰖩  Wi-Fi и доступные сети…'))
    entries += [('network', '󰈀  Проводная сеть и VPN…'),
                ('editor', '󰒓  Редактор сохранённых подключений…')]
    choice = pick('Сеть', entries)
    if choice == 'editor':
        launch(['nm-connection-editor'])
    elif choice in ('wifi', 'network'):
        launch(['gnome-control-center', choice], env=dict(os.environ, XDG_CURRENT_DESKTOP='GNOME'))


def lighting_menu():
    if not (HOME / '.config/niri/rgb/hardware.json').is_file():
        raise RuntimeError('RGB-профиль не установлен: install-niri.sh --profile ororura-desktop --rgb')
    script = HOME / '.config/niri/scripts/rgb-control.py'
    try:
        state = json.loads(run([str(script), 'status']).stdout)
        label = state.get('label', 'неизвестно')
    except Exception:
        label = 'неизвестно'
    choice = pick('Подсветка · ' + label, [
        ('on', '󰌵  Включить · Mocha Blue'),
        ('off', '󰹏  Выключить')])
    if choice:
        result = run([str(script), choice], check=False, timeout=60)
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or 'Не удалось переключить подсветку')


def menu():
    with (session_dir() / 'menu.lock').open('w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        profile = profile_state()
        active = profile.get('ActiveProfile', '')
        entries = [('sound', '󰕾  Звук и микрофон'), ('network', '󰖩  Сеть и подключения')]
        if bluetooth_state()[0]:
            entries.append(('bluetooth', '  Bluetooth'))
        if profile:
            entries.append(('profile', '󰓅  Питание: ' + PROFILES.get(active, active)))
        if (HOME / '.config/niri/rgb/hardware.json').is_file():
            entries.append(('lighting', '󰌵  Подсветка'))
        entries += [('dnd', '󰂛  Не беспокоить: ' + ('вкл.' if 'do-not-disturb' in modes() else 'выкл.')),
                    ('presentation', '󰅶  Просмотр / презентация: ' + ('вкл.' if presenting() else 'выкл.'))]
        choice = pick('Быстрые настройки', entries)
        if choice == 'sound': audio_menu()
        elif choice == 'network': network_menu()
        elif choice == 'bluetooth': bluetooth_menu()
        elif choice == 'lighting': lighting_menu()
        elif choice == 'profile':
            selected = pick('Профиль питания', [(p['Profile'], ('✓ ' if p['Profile'] == active else '  ') +
                            PROFILES.get(p['Profile'], p['Profile'])) for p in profile.get('Profiles', [])])
            if selected: set_profile(selected)
        elif choice == 'dnd': run(['makoctl', 'mode', '-t', 'do-not-disturb'])
        elif choice == 'presentation': toggle_presentation()


def status(presentation_only=False):
    on = presenting()
    if presentation_only:
        return {'text': '󰅶', 'class': 'active' if on else 'inactive',
                'tooltip': ('<b>Просмотр / презентация включён</b>\nАвтоблокировка и отключение экранов приостановлены.\n'
                            'Ручная блокировка и блокировка перед сном работают.\nНажмите, чтобы вернуть таймеры 10 / 11 минут.' if on else
                            '<b>Просмотр / презентация выключен</b>\nБлокировка: 10 минут · экраны: 11 минут.\n'
                            'Нажмите, чтобы временно отключить таймеры.') + '\nSuper+Shift+P'}
    dnd = 'do-not-disturb' in modes()
    profile = profile_state().get('ActiveProfile', 'недоступен')
    tooltip = '<b>Быстрые настройки · Super+S</b>\n'
    tooltip += 'Звук: ' + volume('@DEFAULT_AUDIO_SINK@') + '\n'
    tooltip += 'Микрофон: ' + volume('@DEFAULT_AUDIO_SOURCE@') + '\n'
    tooltip += 'Питание: ' + PROFILES.get(profile, profile) + '\n'
    tooltip += 'Не беспокоить: ' + ('вкл. · критические видны' if dnd else 'выкл.')
    return {'text': '󰂛' if dnd else '󰒓', 'class': 'dnd' if dnd else 'normal', 'tooltip': tooltip}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['lighting-menu', 'menu', 'sound-menu', 'network-menu', 'bluetooth-menu', 'status', 'presentation-status', 'presentation-toggle', 'idle-lock', 'idle-off', 'inspect'])
    args = parser.parse_args()
    session_dir()
    if args.action == 'lighting-menu': lighting_menu()
    elif args.action == 'menu': menu()
    elif args.action == 'sound-menu': audio_menu()
    elif args.action == 'network-menu': network_menu()
    elif args.action == 'bluetooth-menu': bluetooth_menu()
    elif args.action == 'presentation-toggle': toggle_presentation()
    elif args.action in ('idle-lock', 'idle-off'): idle_action('lock' if args.action == 'idle-lock' else 'off')
    elif args.action == 'inspect':
        adapters, devices = bluetooth_state()
        print(json.dumps({'presentation': presenting(), 'modes': modes(), 'power': profile_state(),
                          'bluetooth_adapters': len(adapters), 'bluetooth_devices': len(devices),
                          'speaker': volume('@DEFAULT_AUDIO_SINK@'), 'microphone': volume('@DEFAULT_AUDIO_SOURCE@')}, ensure_ascii=False))
    else: print(json.dumps(status(args.action == 'presentation-status'), ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(str(error), file=sys.stderr)
        run(['notify-send', '--app-name=Niri', '--urgency=normal', 'Быстрые настройки', str(error)], check=False)
        sys.exit(1)
