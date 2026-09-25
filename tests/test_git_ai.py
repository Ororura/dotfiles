"""Offline smoke tests for local Git AI commands."""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

SCRIPTS = ROOT / "git" / "scripts"

sys.path.insert(0, str(SCRIPTS))

from git_ai_safety import check_sensitive_changes, is_sensitive


class GitAiTests(unittest.TestCase):

    def setUp(self):

        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

        self.old_cwd = Path.cwd()

        os.chdir(self.tmp.name)

        self.addCleanup(os.chdir, self.old_cwd)

        self.env = os.environ.copy()

        self.env["GIT_CONFIG_GLOBAL"] = os.devnull

        self.env["GIT_CONFIG_NOSYSTEM"] = "1"

        self.env["OLLAMA_GIT_URL"] = (
            "http://127.0.0.1:1/api/chat"
        )

        self.git("init", "-q")

        self.git("config", "user.name", "Test")

        self.git(
            "config",
            "user.email",
            "test@example.invalid",
        )

        Path("note.txt").write_text("initial\n")

        self.git("add", "note.txt")

        self.git(
            "-c",
            "core.hooksPath=/dev/null",
            "commit",
            "-qm",
            "initial",
        )

    def git(self, *args):

        return subprocess.run(
            ["git", *args],
            env=self.env,
            capture_output=True,
            text=True,
            check=True,
        )

    def run_ai(self, script, *args):

        return subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / script),
                *args,
            ],
            env=self.env,
            capture_output=True,
            text=True,
            timeout=15,
        )

    def test_filename_filter(self):

        for name in (
            ".env",
            "config/.env.local",
            "keys/id_ed25519",
            "private.pem",
        ):

            with self.subTest(name=name):

                self.assertTrue(
                    is_sensitive(name)
                )

        for name in (
            ".env.example",
            "src/app.py",
            "docs/README.md",
        ):

            with self.subTest(name=name):

                self.assertFalse(
                    is_sensitive(name)
                )

    def test_staged_sensitive_file_blocks_ai_before_http(self):

        Path(".env").write_text(
            "FAKE_SECRET=fixture\n"
        )

        self.git("add", ".env")

        with self.assertRaisesRegex(
            ValueError,
            "Sensitive-looking",
        ):

            check_sensitive_changes()

        for script in (
            "git-ai-msg.py",
            "git-ai-branch.py",
        ):

            with self.subTest(script=script):

                result = self.run_ai(script)

                self.assertNotEqual(
                    result.returncode,
                    0,
                )

                self.assertIn(
                    "Sensitive-looking",
                    result.stderr,
                )

    def test_unstaged_sensitive_file_blocks_branch(self):

        Path("note.txt").write_text(
            "changed\n"
        )

        Path(".env.local").write_text(
            "FAKE_SECRET=fixture\n"
        )

        self.git("add", ".env.local")

        self.git(
            "-c",
            "core.hooksPath=/dev/null",
            "commit",
            "-qm",
            "fixture",
        )

        Path(".env.local").write_text(
            "FAKE_SECRET=updated\n"
        )

        with self.assertRaisesRegex(
            ValueError,
            "Sensitive-looking",
        ):

            check_sensitive_changes(
                include_unstaged=True
            )

        result = self.run_ai(
            "git-ai-branch.py"
        )

        self.assertNotEqual(
            result.returncode,
            0,
        )

        self.assertIn(
            "Sensitive-looking",
            result.stderr,
        )

    def test_oversized_diff_fails_instead_of_truncating(self):

        Path("large.txt").write_text(
            "X" * 25000 + "\n"
        )

        self.git("add", "large.txt")

        for script in (
            "git-ai-msg.py",
            "git-ai-branch.py",
        ):

            with self.subTest(script=script):

                result = self.run_ai(script)

                self.assertNotEqual(
                    result.returncode,
                    0,
                )

                self.assertIn(
                    "limit",
                    result.stderr,
                )

                self.assertNotIn(
                    "truncated",
                    result.stderr.lower(),
                )


if __name__ == "__main__":
    unittest.main()
