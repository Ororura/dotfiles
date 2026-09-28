"""Focused tests for the unified local Git AI CLI."""

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "git/scripts/git-ai.py"
spec = importlib.util.spec_from_file_location("git_ai", SCRIPT)
ai = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ai)


class PureHelperTests(unittest.TestCase):
    def test_model_output(self):
        self.assertEqual(ai.parse_branch("`feat/projects-app`\n"), "feat/projects-app")
        self.assertEqual(ai.parse_commit("feat(git): add AI CLI"), "feat(git): add AI CLI")
        for bad in ("main", "feat/Bad", "feat/with space", "feat/x..y"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                ai.parse_branch(bad)
        with self.assertRaises(ValueError):
            ai.parse_commit("Here is your message:\nfeat: update")

    def test_sensitive_paths(self):
        for path in (".env", "config/.env.local", "x/private.pem", "x/a.p12",
                     "x/a.pfx", "x/a.key", "keys/id_rsa", "keys/id_ed25519",
                     "credentials.json"):
            with self.subTest(path=path):
                self.assertTrue(ai.is_sensitive(path))
        for path in (".env.example", ".env.sample", "src/app.py"):
            self.assertFalse(ai.is_sensitive(path))

    def test_environment(self):
        with patch.dict(os.environ, {"OLLAMA_GIT_CONTEXT": "invalid"}):
            with self.assertRaisesRegex(ValueError, "invalid OLLAMA_GIT_CONTEXT value"):
                ai.config()
        with patch.dict(os.environ, {"OLLAMA_GIT_MAX_DIFF_CHARS": "1999"}):
            with self.assertRaisesRegex(ValueError, "OLLAMA_GIT_MAX_DIFF_CHARS"):
                ai.config()
        with patch.dict(os.environ, {"OLLAMA_GIT_MODEL": "default",
                                     "OLLAMA_GIT_COMMIT_MODEL": "special"}):
            self.assertEqual(ai.model_for("commit", None, ai.config()), "special")
            self.assertEqual(ai.model_for("review", None, ai.config()), "default")

    def test_chunking_covers_entire_diff(self):
        diff = "diff --git a/a b/a\n" + "a" * 3500 + "\n" + "diff --git a/b b/b\n" + "b" * 3000
        chunks = ai.review_chunks(diff, 2000)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= 2000 for chunk in chunks))
        reconstructed = "".join(line for chunk in chunks for line in chunk.splitlines(keepends=True)
                                if not line.startswith("[CONTINUATION:"))
        self.assertEqual(reconstructed, diff)

    def test_publish_preconditions(self):
        self.assertIn("main", ai.publish_precondition("main", "origin/main", False, False, 1))
        self.assertIn("uncommitted", ai.publish_precondition("feat/x", "main", True, False, 1))
        self.assertIn("Staged", ai.publish_precondition("feat/x", "main", False, True, 1))
        self.assertIn("No commits", ai.publish_precondition("feat/x", "main", False, False, 0))
        self.assertIsNone(ai.publish_precondition("feat/x", "main", False, False, 1))

    def test_split_output_rejects_invented_paths(self):
        valid = '{"groups":[{"message":"feat: add app","files":["app.py"],"reason":"feature"}]}'
        self.assertEqual(ai.parse_split_output(valid, ["app.py"])["groups"][0]["files"], ["app.py"])
        with self.assertRaisesRegex(ValueError, "invented file paths"):
            ai.parse_split_output(valid, ["other.py"])
        with self.assertRaisesRegex(ValueError, "invalid split JSON"):
            ai.parse_split_output('{"groups":["invalid"]}', ["app.py"])


class GitRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.old_cwd = Path.cwd()
        os.chdir(self.tmp.name)
        self.addCleanup(os.chdir, self.old_cwd)
        self.env = os.environ.copy()
        self.env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1",
                        OLLAMA_GIT_URL="http://127.0.0.1:1/api/chat")
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.invalid")
        Path("note.txt").write_text("initial\n")
        self.git("add", "note.txt")
        self.git("-c", "core.hooksPath=/dev/null", "commit", "-qm", "initial")

    def git(self, *args):
        return subprocess.run(["git", *args], env=self.env, text=True,
                              capture_output=True, check=True).stdout.strip()

    def test_base_selection(self):
        self.assertEqual(ai.pick_base(), "main")
        self.git("update-ref", "refs/remotes/origin/main", "HEAD")
        self.assertEqual(ai.pick_base(), "origin/main")
        self.git("symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")
        self.assertEqual(ai.pick_base(), "origin/main")
        with self.assertRaisesRegex(ValueError, "Base ref not found"):
            ai.pick_base("missing")

    def test_sensitive_commit_stops_before_http(self):
        Path(".env").write_text("FAKE_SECRET=fixture\n")
        self.git("add", ".env")
        result = subprocess.run([sys.executable, str(SCRIPT), "commit"], env=self.env,
                                capture_output=True, text=True, timeout=15)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Sensitive-looking", result.stderr)

    def test_publish_rejects_dirty_tree_before_push(self):
        self.git("switch", "-qc", "feat/topic")
        Path("note.txt").write_text("changed\n")
        result = subprocess.run([sys.executable, str(SCRIPT), "publish"], env=self.env,
                                capture_output=True, text=True, timeout=15)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Working tree has uncommitted changes", result.stderr)


if __name__ == "__main__":
    unittest.main()
