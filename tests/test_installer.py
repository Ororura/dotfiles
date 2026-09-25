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


if __name__ == "__main__":
    unittest.main()
