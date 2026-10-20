#!/usr/bin/env python3
"""Install the tracked Niri desktop with per-file backups and explicit hardware profiles."""
from pathlib import Path
import argparse
import datetime
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

from niri_assets import tool_plans

ROOT = Path(__file__).resolve().parents[1]
WANTS = ['waybar.service', 'mako.service', 'niri-background.service',
         'niri-polkit.service', 'niri-idle.service',
         'niri-clipboard-text.service', 'niri-clipboard-image.service']


def packages(rgb):
    paths = [ROOT / 'desktop/packages-fedora.txt']
    if rgb:
        paths.append(ROOT / 'desktop/packages-rgb-fedora.txt')
    names = [line.split('#', 1)[0].strip() for path in paths for line in path.read_text().splitlines()]
    return [name for name in names if name]


def install_packages(rgb, dry_run):
    release = Path('/etc/os-release').read_text()
    if not re.search(r'^ID=["\']?fedora["\']?$', release, re.M):
        raise RuntimeError('--packages requires Fedora. Install dependencies manually on other distributions.')
    missing = [name for name in packages(rgb)
               if subprocess.run(['rpm', '-q', name], stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL).returncode]
    if not missing:
        print('[OK] Required Fedora packages already installed.')
        return
    command = ['sudo', 'dnf', '--disablerepo=*', '--enablerepo=fedora', '--enablerepo=updates',
               '--setopt=install_weak_deps=False', 'install', '-y', *missing]
    print('[PACKAGES]', shlex.join(command), flush=True)
    if not dry_run:
        subprocess.run(command, check=True)


def profile_hardware_valid(profile):
    """Read sysfs only. Never detect, initialise or change RGB while installing."""
    expected = json.loads((profile / 'rgb/hardware.json').read_text())
    board = Path('/sys/class/dmi/id/board_name').read_text().strip()
    if board != expected['motherboard']:
        raise RuntimeError('RGB profile motherboard mismatch: ' + board)
    ids = {key: expected['gpu'][key] for key in ['vendor', 'device', 'subsystem_vendor', 'subsystem_device']}
    matches = []
    for device in Path('/sys/bus/pci/devices').iterdir():
        if all((device / key).is_file() and (device / key).read_text().strip().lower() == value
               for key, value in ids.items()):
            matches.append(device)
    if len(matches) != 1:
        raise RuntimeError('RGB profile GPU mismatch; expected exactly one verified Gigabyte GPU.')


def plan_files(home, profile, rgb):
    plans = {}

    def source(target, path, copy=False):
        plans[target] = ({'target': target, 'data': path.read_bytes(), 'mode': path.stat().st_mode & 0o777}
                         if copy else {'target': target, 'link': str(path)})

    for name in ['niri', 'waybar', 'mako', 'swaylock', 'yazi']:
        for path in sorted((ROOT / name).rglob('*')):
            if path.is_file() and '__pycache__' not in path.parts:
                rel = str(path.relative_to(ROOT / name))
                # The root remains a regular file: relative includes resolve in
                # the installed config directory, including profile overrides.
                source('.config/' + name + '/' + rel, path, copy=name == 'niri' and rel == 'config.kdl')
    for path in sorted((ROOT / 'systemd/user').rglob('*')):
        if not path.is_file() or (path.name == 'niri-rgb.service' and not rgb):
            continue
        source('.config/systemd/user/' + str(path.relative_to(ROOT / 'systemd/user')), path)
    for path in sorted((ROOT / 'desktop/fonts').rglob('*')):
        if path.is_file():
            source('.local/share/fonts/' + str(path.relative_to(ROOT / 'desktop/fonts')), path)
    for path in (ROOT / 'desktop/autostart').iterdir():
        source('.config/autostart/' + path.name, path)
    source('.config/ghostty/config', ROOT / 'ghostty/config')
    templates = {'fuzzel.ini': '.config/fuzzel/fuzzel.ini',
                 'ghostty-mocha.conf': '.config/niri/ghostty-mocha.conf',
                 'niri-yazi.desktop': '.local/share/applications/niri-yazi.desktop'}
    for name, target in templates.items():
        text = (ROOT / 'desktop/templates' / name).read_text()
        text = text.replace('@TERMINAL@', shlex.quote(str(home / '.config/niri/scripts/ghostty-mocha')) + ' -e')
        replacement = str(home)
        if name.endswith('.desktop'):
            replacement = replacement.replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$')
        text = text.replace('@HOME@', replacement)
        plans[target] = {'target': target, 'data': text.encode(), 'mode': 0o644}
    if profile:
        for name in ['outputs.kdl', 'workspaces.kdl']:
            source('.config/niri/config.d/' + name, profile / name)
    if rgb:
        for name in ['OpenRGB.json', 'client/OpenRGB.json']:
            # OpenRGB writes its config; do not let it modify the repository.
            source('.config/niri/rgb/' + name, profile / 'rgb' / name, copy=True)
        source('.config/niri/rgb/hardware.json', profile / 'rgb/hardware.json')
    else:
        plans['.config/niri/rgb/hardware.json'] = {'target': '.config/niri/rgb/hardware.json', 'absent': True}
    for name in WANTS:
        unit = ('/usr/lib/systemd/user/' + name if name in ['waybar.service', 'mako.service']
                else str(home / '.config/systemd/user' / name))
        target = '.config/systemd/user/niri.service.wants/' + name
        plans[target] = {'target': target, 'link': unit}
    # Switch the root config last, after adding any new include files.
    root = plans.pop('.config/niri/config.kdl')
    return list(plans.values()) + [root]


def target_path(home, relative):
    relative = Path(relative)
    if relative.is_absolute() or '..' in relative.parts:
        raise RuntimeError('Invalid manifest path: ' + str(relative))
    target = home / relative
    # Avoid writing through an existing configuration-directory symlink.
    # File symlinks are handled safely and backed up as symlinks.
    for parent in target.parents:
        if parent == home:
            break
        if parent.is_symlink():
            raise RuntimeError('Configuration directory is a symlink; migrate it first: ' + str(parent))
    return target


def unchanged(target, item):
    if item.get('absent'):
        return not target.exists() and not target.is_symlink()
    if 'link' in item:
        return target.is_symlink() and os.readlink(target) == item['link']
    if 'data' in item:
        return (target.is_file() and not target.is_symlink() and target.read_bytes() == item['data']
                and target.stat().st_mode & 0o777 == item['mode'])
    return False


def remove(path):
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink(missing_ok=True)


def save(path, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        destination.symlink_to(os.readlink(path))
    elif path.is_dir():
        shutil.copytree(path, destination, symlinks=True)
    else:
        shutil.copy2(path, destination)


def new_backup(home):
    base = home / '.dotfiles-backups'
    base.mkdir(mode=0o700, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix='niri-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S') + '-', dir=base))
    directory.chmod(0o700)
    return directory


def write_manifest(backup, records):
    path = backup / 'manifest.json'
    path.write_text(json.dumps({'format': 'dotfiles-niri-v1', 'entries': records}, indent=2) + '\n')
    path.chmod(0o600)


def restore(home, backup, no_systemd):
    document = json.loads((backup / 'manifest.json').read_text())
    if document.get('format') != 'dotfiles-niri-v1':
        raise RuntimeError('Not a Niri dotfiles backup')
    entries = document['entries']
    # Validate all targets before the first mutation.
    for record in entries:
        target_path(home, record['target'])
    current = new_backup(home)
    undo = []
    for record in reversed(entries):
        target = target_path(home, record['target'])
        existed = target.exists() or target.is_symlink()
        undo.append({'target': record['target'], 'existed': existed})
        if existed:
            save(target, current / 'files' / record['target'])
        write_manifest(current, undo)
        remove(target)
        if record['existed']:
            saved = backup / 'files' / record['target']
            target.parent.mkdir(parents=True, exist_ok=True)
            save(saved, target)
    reload_units(no_systemd)
    print('[RESTORED]', backup)
    print('[BEFORE RESTORE]', current)
    print('Packages and hardware colours are not reverted. Log in again to use restored session services.')


def validate_config(plans):
    if not shutil.which('niri'):
        print('[NOTE] niri is not installed; configuration validation is deferred.')
        return
    with tempfile.TemporaryDirectory(prefix='dotfiles-niri-validate-') as temporary:
        directory = Path(temporary)
        for item in plans:
            rel = Path(item['target'])
            if rel.parts[:2] != ('.config', 'niri') or rel.suffix != '.kdl':
                continue
            path = directory / Path(*rel.parts[2:])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(item['data'] if 'data' in item else Path(item['link']).read_bytes())
        subprocess.run(['niri', 'validate', '-c', str(directory / 'config.kdl')], check=True)


def reload_units(disabled):
    if not disabled and os.environ.get('DBUS_SESSION_BUS_ADDRESS'):
        subprocess.run(['systemctl', '--user', 'daemon-reload'], check=True)


def install(home, plans, dry_run, no_systemd):
    changes = []
    for item in plans:
        target = target_path(home, item['target'])
        if not unchanged(target, item):
            changes.append(item)
    for item in changes:
        print('[DRY RUN]' if dry_run else '[INSTALL]', item['target'])
    if dry_run:
        print('[DRY RUN] No configurations, packages, tools or services changed.')
        return None
    if not changes:
        print('[OK] Desktop already matches dotfiles; no new backup needed.')
        return None
    backup = new_backup(home)
    records = []
    try:
        for item in changes:
            target = target_path(home, item['target'])
            existed = target.exists() or target.is_symlink()
            if existed:
                save(target, backup / 'files' / item['target'])
            records.append({'target': item['target'], 'existed': existed})
            write_manifest(backup, records)
            target.parent.mkdir(parents=True, exist_ok=True)
            if item.get('absent'):
                remove(target)
                continue
            temporary = target.with_name(target.name + '.dotfiles-new')
            if temporary.exists() or temporary.is_symlink():
                raise RuntimeError('Unexpected temporary target already exists: ' + str(temporary))
            if 'link' in item:
                temporary.symlink_to(item['link'])
            elif 'tree' in item:
                shutil.copytree(item['tree'], temporary, symlinks=True)
            else:
                temporary.write_bytes(item['data'])
                temporary.chmod(item['mode'])
            if target.is_dir() and not target.is_symlink():
                remove(target)
            temporary.replace(target)
        reload_units(no_systemd)
    except Exception:
        print('[ERROR] Restoring previous configuration from', backup, file=sys.stderr)
        restore(home, backup, True)
        raise
    print('[BACKUP]', backup)
    if shutil.which('fc-cache'):
        subprocess.run(['fc-cache', str(home / '.local/share/fonts')], check=True)
    if shutil.which('update-desktop-database'):
        subprocess.run(['update-desktop-database', str(home / '.local/share/applications')], check=True)
    return backup


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--packages', action='store_true', help='install missing Fedora RPMs and verified user-space tools')
    parser.add_argument('--profile', default='generic', choices=['generic', 'ororura-desktop'])
    parser.add_argument('--rgb', action='store_true', help='opt in to the verified ororura-desktop lighting hardware')
    parser.add_argument('--restore', type=Path, metavar='BACKUP')
    parser.add_argument('--no-systemd', action='store_true', help='write session units without reloading the current user manager')
    args = parser.parse_args()
    if sys.platform != 'linux':
        parser.error('Niri desktop setup requires Linux')
    if args.restore and (args.packages or args.rgb or args.dry_run or args.profile != 'generic'):
        parser.error('--restore cannot be combined with installation options')
    home = Path.home()
    if os.environ.get('XDG_CONFIG_HOME', str(home / '.config')) != str(home / '.config'):
        parser.error('This desktop expects the standard ~/.config location')
    if args.restore:
        restore(home, args.restore.resolve(), args.no_systemd)
        return
    if args.rgb and args.profile != 'ororura-desktop':
        parser.error('--rgb requires --profile ororura-desktop')
    profile = ROOT / 'desktop/profiles' / args.profile if args.profile != 'generic' else None
    if args.rgb:
        profile_hardware_valid(profile)
    # Preflight before installing packages or changing user configuration.
    plans = plan_files(home, profile, args.rgb)
    for item in plans:
        target_path(home, item['target'])
    if args.packages:
        install_packages(args.rgb, args.dry_run)
    extras = tool_plans(ROOT, home, args.packages, args.rgb, args.dry_run)
    try:
        validate_config(plans)
        install(home, extras + plans, args.dry_run, args.no_systemd)
    finally:
        for item in extras:
            if 'tree' in item:
                shutil.rmtree(item['tree'].parent)
    print('Profile:', args.profile, '| RGB:', args.rgb)
    print('GNOME/GDM, shell settings and current graphical session are preserved.')
    print('Session services start on the next Niri login; none were restarted here.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print('[ERROR]', error, file=sys.stderr)
        sys.exit(1)
