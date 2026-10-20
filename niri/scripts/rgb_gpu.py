"""Narrow RGB Fusion control for the identified Gigabyte 1458:4020 GPU.

Byte transactions match OpenRGB release_1.1's GigabyteRGBFusionGPUController.
Only the verified PCI device, NVIDIA adapter 1 and address 0x47 are allowed.
No EEPROM save, clock, voltage or fan-speed operations are implemented.
"""
from pathlib import Path
import subprocess
import json

EXPECTED = {'vendor': '0x10de', 'device': '0x21c4',
            'subsystem_vendor': '0x1458', 'subsystem_device': '0x4020'}


def adapter():
    profile = json.loads((Path.home() / '.config/niri/rgb/hardware.json').read_text())
    if (profile.get('profile') != 'ororura-desktop'
            or any(profile['gpu'].get(key) != value for key, value in EXPECTED.items())
            or profile['gpu'].get('adapter_index') != 1 or profile['gpu'].get('address') != '0x47'):
        raise RuntimeError('GPU RGB: требуется проверенный профиль Gigabyte 1458:4020')
    devices = [path for path in Path('/sys/bus/pci/devices').iterdir()
               if all((path / key).is_file() and (path / key).read_text().strip().lower() == value
                      for key, value in EXPECTED.items())]
    if len(devices) != 1:
        raise RuntimeError('GPU RGB: не найдена единственная проверенная видеокарта')
    gpu = devices[0]
    adapters = [path for path in Path('/sys/bus/i2c/devices').glob('i2c-*')
                if gpu.resolve() in path.resolve().parents
                and (path / 'name').read_text().strip().startswith('NVIDIA i2c adapter 1 at ')]
    if len(adapters) != 1:
        raise RuntimeError('GPU RGB: не найден единственный адаптер NVIDIA 1')
    return adapters[0].name.removeprefix('i2c-')


def write_byte(bus, value):
    result = subprocess.run(['/usr/bin/i2cset', '-y', bus, '0x47', hex(value)],
                            capture_output=True, text=True, timeout=2)
    if result.returncode:
        raise RuntimeError('GPU RGB: ' + result.stderr.strip())


def apply_color(color):
    rgb = bytes.fromhex(color)
    if len(rgb) != 3:
        raise ValueError('GPU RGB: expected RRGGBB')
    bus = adapter()
    # OpenRGB identification request, not a scan of the bus.
    for value in [0xAB, 0, 0, 0]:
        write_byte(bus, value)
    response = []
    for _ in range(4):
        value = subprocess.check_output(['/usr/bin/i2cget', '-y', bus, '0x47'], text=True, timeout=2)
        response.append(int(value.strip(), 16))
    if response[0] != 0xAB or response[1] not in [0x10, 0x11, 0x12, 0x14]:
        raise RuntimeError('GPU RGB: контроллер не прошёл проверку сигнатуры; цвет не отправлен')
    # REG_MODE=0x88, Static=1, speed=0, brightness=99, as in OpenRGB.
    # REG_COLOR=0x40 followed by the R, G, B bytes. Never send REG_SAVE=0xAA.
    for value in [0x88, 0x01, 0x00, 0x63, 0x40, *rgb]:
        write_byte(bus, value)
    return {'name': 'Gigabyte GTX 1660 SUPER RGB', 'adapter': 'i2c-' + bus,
            'address': '0x47', 'signature': bytes(response).hex(), 'color': color}
