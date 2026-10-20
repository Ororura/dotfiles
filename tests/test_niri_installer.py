"""Desktop migration tests: dry runs, backups, rollback and portable paths."""
from pathlib import Path
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import niri_assets


class DesktopInstallerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.home = self.base / 'new user'
        self.home.mkdir()
        self.bin = self.base / 'bin'
        self.bin.mkdir()
        for name in ['fc-cache', 'update-desktop-database']:
            path = self.bin / name
            path.write_text('#!/bin/sh\nexit 0\n')
            path.chmod(0o755)
        self.env = os.environ.copy()
        self.env.update(HOME=str(self.home), XDG_CONFIG_HOME=str(self.home / '.config'),
                        PATH=str(self.bin) + os.pathsep + os.environ['PATH'])
        self.env.pop('DBUS_SESSION_BUS_ADDRESS', None)

    def run_install(self, *args):
        return subprocess.run([sys.executable, str(ROOT / 'scripts/install_niri.py'),
                               '--no-systemd', *args], env=self.env,
                              capture_output=True, text=True, timeout=30)

    def assert_ok(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_dry_run_does_not_write_home(self):
        self.assert_ok(self.run_install('--dry-run'))
        self.assertEqual(list(self.home.iterdir()), [])

    def test_install_repeat_and_restore_preserve_original(self):
        original = self.home / '.config/waybar/config.jsonc'
        original.parent.mkdir(parents=True)
        original.write_text('original user configuration\n')
        original.chmod(0o600)
        self.assert_ok(self.run_install())
        self.assertTrue(original.is_symlink())
        self.assertEqual(original.resolve(), ROOT / 'waybar/config.jsonc')
        root_config = self.home / '.config/niri/config.kdl'
        self.assertFalse(root_config.is_symlink())
        self.assertIn('config.d/workspaces.kdl', root_config.read_text())
        fuzzel = (self.home / '.config/fuzzel/fuzzel.ini').read_text()
        self.assertIn(str(self.home), fuzzel)
        self.assertNotIn('/home/ororura', fuzzel)
        self.assertFalse((self.home / '.config/niri/rgb/hardware.json').exists())
        self.assertFalse((self.home / '.config/systemd/user/niri.service.wants/niri-rgb.service').exists())
        backups = list((self.home / '.dotfiles-backups').iterdir())
        self.assertEqual(len(backups), 1)
        self.assert_ok(self.run_install())
        self.assertEqual(list((self.home / '.dotfiles-backups').iterdir()), backups)
        self.assert_ok(self.run_install('--restore', str(backups[0])))
        self.assertFalse(original.is_symlink())
        self.assertEqual(original.read_text(), 'original user configuration\n')
        self.assertEqual(original.stat().st_mode & 0o777, 0o600)
        self.assertFalse(root_config.exists())
        self.assertFalse((self.home / '.config/mako/config').exists())

    def test_directory_symlink_is_rejected_before_mutation(self):
        external = self.base / 'external'
        external.mkdir()
        (external / 'config.jsonc').write_text('keep this\n')
        (self.home / '.config').mkdir()
        (self.home / '.config/waybar').symlink_to(external, target_is_directory=True)
        result = self.run_install()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('directory is a symlink', result.stderr)
        self.assertEqual((external / 'config.jsonc').read_text(), 'keep this\n')
        self.assertFalse((self.home / '.dotfiles-backups').exists())

    def test_failed_validation_does_not_replace_configs(self):
        niri = self.bin / 'niri'
        niri.write_text('#!/bin/sh\nexit 37\n')
        niri.chmod(0o755)
        result = self.run_install()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_rgb_requires_explicit_hardware_profile(self):
        result = self.run_install('--rgb')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('--rgb requires', result.stderr)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_bad_asset_checksum_never_installs_a_binary(self):
        response = io.BytesIO(b'not the pinned release')
        with patch('niri_assets.urllib.request.urlopen', return_value=response):
            with self.assertRaisesRegex(RuntimeError, 'checksum mismatch'):
                niri_assets.tool_plans(ROOT, self.home, enabled=True, rgb=False, dry_run=False)
        self.assertFalse((self.home / '.local/bin/yazi').exists())
        self.assertFalse(list((self.home / '.cache/dotfiles/assets').glob('*.part')))


if __name__ == '__main__':
    unittest.main()
