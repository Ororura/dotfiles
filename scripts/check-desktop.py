#!/usr/bin/env python3
"""Offline checks for tracked desktop sources; does not start a compositor."""
from pathlib import Path
import ast
import json
import subprocess
import tomllib

root = Path(__file__).resolve().parents[1]
files = []
for folder in ['niri', 'waybar', 'mako', 'swaylock', 'yazi', 'desktop', 'systemd', 'scripts']:
    for path in (root / folder).rglob('*'):
        if not path.is_file() or '__pycache__' in path.parts or path.suffix in ['.ttf', '.png', '.jpg']:
            continue
        data = path.read_text()
        if path.suffix == '.py':
            ast.parse(data, filename=str(path))
        if path.suffix in ['.json', '.jsonc']:
            # The tracked Waybar JSONC intentionally uses strict JSON.
            json.loads(data)
        if path.suffix == '.toml':
            tomllib.loads(data)
        if data.startswith('#!/bin/bash') or data.startswith('#!/usr/bin/env bash'):
            subprocess.run(['bash', '-n', str(path)], check=True)
        if path.suffix not in ['.md']:
            assert ('/home/' + 'ororura/') not in data and ('Documents/' + 'Codex') not in data, path
        files.append(path)

server = json.loads((root / 'desktop/profiles/ororura-desktop/rgb/OpenRGB.json').read_text())
client = json.loads((root / 'desktop/profiles/ororura-desktop/rgb/client/OpenRGB.json').read_text())
assert {k for k, v in server['Detectors']['detectors'].items() if v} == {
    'Corsair Commander Core', 'Gigabyte RGB Fusion 2 USB'}
assert not any(client['Detectors']['detectors'].values())
assert server['Detectors']['hid_safe_mode'] and client['Detectors']['hid_safe_mode']
assert server['Server']['default_host'] == '127.0.0.1'
assert (root / 'desktop/fonts/JetBrainsMonoNerdFont/OFL.txt').is_file()
print(f'[OK] {len(files)} desktop source files; syntax, JSON/TOML, portable paths, RGB allowlist.')
