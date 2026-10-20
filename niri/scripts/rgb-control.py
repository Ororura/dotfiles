#!/usr/bin/python3
"""Niri lighting switch: only the two explicitly allowed USB controllers."""
from pathlib import Path
import argparse
import fcntl
import json
import os
import re
import socket
import struct
import subprocess
import sys
import time
from rgb_sdk import snapshot
from rgb_gpu import apply_color as apply_gpu_color

HOME = Path.home()
APP = HOME / '.local/share/niri-rgb/openrgb-1.1/AppRun'
CONFIG = HOME / '.config/niri/rgb/client'
SERVICE = 'niri-rgb.service'
STATE_DIR = Path(os.environ.get('XDG_STATE_HOME', str(HOME / '.local/state'))) / 'niri'
STATE = STATE_DIR / 'rgb.json'
TARGETS = {'Corsair Commander Core': 'Direct', 'B550 AORUS PRO V2': 'Static'}
ON_COLOR = '89B4FA'
RED_COLOR = 'FF0000'
# H115i Elite Capellix ML140: 8 physical LEDs per fan. The OpenRGB
# driver forces 34 RGB positions per port; fill the whole port to avoid
# uninitialised padding bytes in its fixed-stride packet. PWM is untouched.
ZONE_SIZES = {
    'Corsair Commander Core': {f'Corsair Fan Header {i}': 'capacity' for i in range(1, 7)},
    # Full declared capacity for a uniform hardware Static effect; this is
    # not a claim that 1024 physical LEDs are installed on either header.
    'B550 AORUS PRO V2': {'D_LED1': 'capacity', 'D_LED2': 'capacity'},
}


def command(args, timeout=15):
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=True)


def service_pid():
    result = subprocess.run(['systemctl', '--user', 'show', SERVICE, '-p', 'MainPID', '--value'],
                            capture_output=True, text=True, timeout=3)
    try: return int(result.stdout.strip())
    except ValueError: return 0


def read_state():
    try: return json.loads(STATE.read_text())
    except (OSError, ValueError): return {}


def status():
    state = read_state()
    pid = service_pid()
    if not pid or state.get('server_pid') != pid:
        return {'mode': 'hardware', 'label': 'аппаратный режим / не задана'}
    color_name = {ON_COLOR: 'Mocha Blue', RED_COLOR: 'Красный'}.get(state.get('color'), '#' + state.get('color', '??????'))
    return {'mode': state.get('mode', 'unknown'),
            'label': 'включена · ' + color_name if state.get('mode') == 'on' else 'выключена',
            'applied_at': state.get('applied_at'), 'devices': state.get('devices', [])}


def receive(sock, size):
    data = b''
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk: raise RuntimeError('RGB SDK connection closed')
        data += chunk
    return data


def controller_count():
    # Public SDK request 0: get controller count. This does not change lighting.
    with socket.create_connection(('127.0.0.1', 6743), timeout=2) as sock:
        sock.sendall(struct.pack('<4sIII', b'ORGB', 0, 0, 0))
        magic, device, packet, length = struct.unpack('<4sIII', receive(sock, 16))
        if magic != b'ORGB' or packet != 0 or length != 4:
            raise RuntimeError('Unexpected RGB SDK response')
        return struct.unpack('<I', receive(sock, length))[0]


def client(args):
    # No --nodetect: OpenRGB also skips fetching remote devices with that flag.
    # The separate client configuration has ALL hardware detectors disabled.
    result = command([str(APP), '--config', str(CONFIG), '--noautoconnect',
                      '--client', '127.0.0.1:6743'] + args, timeout=20)
    output = result.stdout + result.stderr
    if re.search(r'(^|\n)\s*(Error:|Fatal:|Wrong number of colors)|\[Error\s*\]' , output, re.I):
        raise RuntimeError(output.strip()[-1200:])
    return result.stdout


def set_lighting(action):
    mode = 'off' if action == 'off' else 'on'
    color = {'on': ON_COLOR, 'red': RED_COLOR, 'off': '000000'}[action]
    if os.environ.get('XDG_CURRENT_DESKTOP') != 'niri':
        raise RuntimeError('Переключатель рассчитан на сеанс Niri')
    if not (HOME / '.config/niri/rgb/hardware.json').is_file():
        raise RuntimeError('Сначала установите проверенный RGB-профиль этого компьютера')
    STATE_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (STATE_DIR / 'rgb.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        command(['systemctl', '--user', 'start', SERVICE], timeout=25)
        deadline = time.monotonic() + 15
        while True:
            try:
                if controller_count() == len(TARGETS): break
            except (OSError, RuntimeError): pass
            if time.monotonic() > deadline:
                raise RuntimeError('Не найдены оба RGB-контроллера; настройки не применены. Проверьте журнал niri-rgb.service.')
            time.sleep(.2)
        controllers = snapshot()
        names = [item['name'] for item in controllers]
        if set(names) != set(TARGETS) or len(names) != len(TARGETS):
            raise RuntimeError('Список RGB-устройств отличается от разрешённого; настройки не применены')
        resize_args = []
        desired = {}
        for item in controllers:
            name = item['name']
            zones = {zone['name']: zone for zone in item['zones']}
            desired[name] = {}
            for zone_name, size in ZONE_SIZES[name].items():
                zone = zones[zone_name]
                count = zone['max'] if size == 'capacity' else size
                if not zone['min'] <= count <= zone['max'] or count <= 0:
                    raise RuntimeError('Недопустимый размер RGB-зоны: ' + zone_name)
                desired[name][zone_name] = count
                if zone['count'] != count:
                    resize_args += ['--device', name, '--zone', str(zone['id']), '--size', str(count),
                                    '--mode', TARGETS[name], '--color', color]
        if resize_args:
            client(resize_args)
            for item in snapshot():
                for zone in item['zones']:
                    count = desired.get(item['name'], {}).get(zone['name'])
                    if count is not None and zone['count'] != count:
                        raise RuntimeError('Не применился размер RGB-зоны: ' + zone['name'])
        args = []
        for name, effect in TARGETS.items():
            args += ['--device', name, '--mode', effect, '--color', color]
        client(args)
        # Verify the actual server mode/colour tables, not just CLI exit 0.
        actual = snapshot()
        if {item['name'] for item in actual} != set(TARGETS):
            raise RuntimeError('Соединение с контроллерами потеряно во время применения')
        expected = int.from_bytes(bytes.fromhex(color) + b'\0', 'little')
        for item in actual:
            active = item['modes'][item['active_mode']]
            values = item['colors'] if TARGETS[item['name']] == 'Direct' else active['colors']
            if active['name'] != TARGETS[item['name']] or not values or any(value != expected for value in values):
                raise RuntimeError('Не подтверждён цвет RGB-контроллера: ' + item['name'])
        gpu = apply_gpu_color(color)
        state = {'mode': mode, 'color': color, 'server_pid': service_pid(),
                 'devices': names + [gpu['name']], 'gpu': gpu, 'zones': desired, 'applied_at': time.time()}
        temporary = STATE.with_suffix('.tmp')
        temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2))
        temporary.chmod(0o600)
        temporary.replace(STATE)
        print(json.dumps(state, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['on', 'red', 'off', 'status'])
    args = parser.parse_args()
    if args.action == 'status': print(json.dumps(status(), ensure_ascii=False))
    else: set_lighting(args.action)


if __name__ == '__main__':
    try: main()
    except Exception as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
