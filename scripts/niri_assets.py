"""Pinned user-space tools; no OpenRGB hardware detection during installation."""
from pathlib import Path
import hashlib
import json
import platform
import subprocess
import tempfile
import urllib.request
import zipfile


def sha256(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def tool_plans(root, home, enabled, rgb, dry_run):
    lock = json.loads((root / 'desktop/assets.lock.json').read_text())
    plans = []

    def download(name):
        asset = lock[name]
        if platform.machine() != 'x86_64':
            raise RuntimeError('Pinned tool downloads support Linux x86_64; install tools separately on this architecture.')
        cache = home / '.cache/dotfiles/assets'
        cache.mkdir(parents=True, exist_ok=True)
        target = cache / (name + '-' + asset['sha256'])
        if not target.exists() or sha256(target) != asset['sha256']:
            print('[DOWNLOAD]', asset['url'], flush=True)
            temporary = target.with_suffix('.part')
            try:
                with urllib.request.urlopen(asset['url'], timeout=60) as response, temporary.open('wb') as out:
                    size = 0
                    while data := response.read(1024 * 1024):
                        size += len(data)
                        if size > 128 * 1024 * 1024:
                            raise RuntimeError('Unexpectedly large release asset')
                        out.write(data)
                if sha256(temporary) != asset['sha256']:
                    raise RuntimeError('Release checksum mismatch: ' + name)
                temporary.replace(target)
            finally:
                temporary.unlink(missing_ok=True)
        return target

    yazi = lock['yazi']
    missing = [name for name, digest in yazi['files'].items()
               if not (home / '.local/bin' / name).is_file()
               or sha256(home / '.local/bin' / name) != digest]
    if missing and enabled:
        if dry_run:
            print('[DRY RUN] Download verified Yazi', yazi['version'], 'and install:', ', '.join(missing))
        else:
            archive = download('yazi')
            with zipfile.ZipFile(archive) as zip_file:
                for name in missing:
                    data = zip_file.read('yazi-x86_64-unknown-linux-gnu/' + name)
                    if hashlib.sha256(data).hexdigest() != yazi['files'][name]:
                        raise RuntimeError('Yazi binary checksum mismatch')
                    plans.append({'target': '.local/bin/' + name, 'data': data, 'mode': 0o755})
    elif missing:
        print('[NOTE] Pinned Yazi is not installed. Use --packages to restore it, or provide yazi in PATH.')

    if rgb:
        target = home / '.local/share/niri-rgb/openrgb-1.1'
        binary = target / 'usr/bin/OpenRGB'
        installed = binary.is_file() and sha256(binary) == lock['openrgb']['binary_sha256']
        if not installed and not enabled and not dry_run:
            raise RuntimeError('OpenRGB 1.1 is missing; repeat with --packages --rgb to download it.')
        if not installed and enabled:
            if dry_run:
                print('[DRY RUN] Download verified OpenRGB 1.1 AppImage, extract without launching the GUI.')
            else:
                archive = download('openrgb')
                archive.chmod(0o700)
                # The AppImage runtime only unpacks; it does not start OpenRGB.
                extracted = Path(tempfile.mkdtemp(prefix='openrgb-', dir=archive.parent))
                try:
                    subprocess.run([str(archive), '--appimage-extract'], cwd=extracted,
                                   stdout=subprocess.DEVNULL, check=True, timeout=60)
                    tree = extracted / 'squashfs-root'
                    if sha256(tree / 'usr/bin/OpenRGB') != lock['openrgb']['binary_sha256']:
                        raise RuntimeError('Extracted OpenRGB binary checksum mismatch')
                    plans.append({'target': str(target.relative_to(home)), 'tree': tree, 'mode': 0o755})
                except Exception:
                    import shutil
                    shutil.rmtree(extracted)
                    raise
    return plans
