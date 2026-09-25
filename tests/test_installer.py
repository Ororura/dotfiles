"""Tests for dotfiles installer modes."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

INSTALLER = ROOT / "install.sh"


class InstallerTests(unittest.TestCase):

    def setUp(self):

        self.home = tempfile.TemporaryDirectory()

        self.addCleanup(self.home.cleanup)

        self.env = os.environ.copy()

        self.env["HOME"] = self.home.name

        self.env["GIT_CONFIG_GLOBAL"] = os.devnull

        self.env["GIT_CONFIG_NOSYSTEM"] = "1"

    def run_installer(self, *arguments):

        return subprocess.run(
            [
                "bash",
                str(INSTALLER),
                *arguments,
            ],
            env=self.env,
            capture_output=True,
            text=True,
            timeout=15,
        )

    def test_minimal_dry_run(self):

        result = self.run_installer(
            "--minimal",
            "--dry-run",
        )

        self.assertEqual(
            result.returncode,
            0,
            result.stderr,
        )

        self.assertIn(
            "zsh/.zshrc",
            result.stdout,
        )

        self.assertNotIn(
            "tmux/tmux.conf",
            result.stdout,
        )

        self.assertFalse(
            (Path(self.home.name) / ".zshrc").exists()
        )

    def test_full_and_minimal_are_incompatible(self):

        result = self.run_installer(
            "--full",
            "--minimal",
        )

        self.assertNotEqual(
            result.returncode,
            0,
        )

        self.assertIn(
            "cannot be combined",
            result.stdout,
        )

    def test_doctor_does_not_modify_home(self):

        result = self.run_installer(
            "--doctor",
        )

        self.assertNotEqual(
            result.returncode,
            0,
        )

        self.assertIn(
            "Dotfiles Doctor",
            result.stdout,
        )

        self.assertEqual(
            list(Path(self.home.name).iterdir()),
            [],
        )

    def test_minimal_install(self):

        home = Path(self.home.name)

        self.env["GIT_CONFIG_GLOBAL"] = str(
            home / ".gitconfig"
        )

        result = self.run_installer("--minimal")

        self.assertEqual(
            result.returncode,
            0,
            result.stdout + result.stderr,
        )

        zshrc = home / ".zshrc"

        self.assertTrue(zshrc.is_symlink())

        self.assertEqual(
            zshrc.resolve(),
            ROOT / "zsh" / ".zshrc",
        )

        self.assertFalse(
            (home / ".tmux.conf").exists()
        )

        self.assertFalse(
            (home / ".p10k.zsh").exists()
        )

        config = subprocess.run(
            [
                "git",
                "config",
                "--global",
                "--get-all",
                "include.path",
            ],
            env=self.env,
            capture_output=True,
            text=True,
            check=True,
        )

        self.assertEqual(
            config.stdout.strip(),
            str(ROOT / "git" / "config"),
        )

    def test_minimal_install_is_idempotent(self):

        home = Path(self.home.name)

        self.env["GIT_CONFIG_GLOBAL"] = str(
            home / ".gitconfig"
        )

        first = self.run_installer("--minimal")

        self.assertEqual(
            first.returncode,
            0,
            first.stdout + first.stderr,
        )

        second = self.run_installer("--minimal")

        self.assertEqual(
            second.returncode,
            0,
            second.stdout + second.stderr,
        )

        self.assertTrue(
            (home / ".zshrc").is_symlink()
        )

        self.assertFalse(
            (home / ".dotfiles-backups").exists()
        )

    def test_existing_zshrc_is_backed_up(self):

        home = Path(self.home.name)

        self.env["GIT_CONFIG_GLOBAL"] = str(
            home / ".gitconfig"
        )

        zshrc = home / ".zshrc"

        zshrc.write_text(
            "original configuration\n"
        )

        result = self.run_installer("--minimal")

        self.assertEqual(
            result.returncode,
            0,
            result.stdout + result.stderr,
        )

        self.assertTrue(
            zshrc.is_symlink()
        )

        backups = list(
            home.glob(
                ".dotfiles-backups/*/.zshrc"
            )
        )

        self.assertEqual(
            len(backups),
            1,
        )

        self.assertEqual(
            backups[0].read_text(),
            "original configuration\n",
        )

if __name__ == "__main__":
    unittest.main()
