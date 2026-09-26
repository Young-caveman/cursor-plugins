#!/usr/bin/env python3
"""Tests for the test bench check. Standard library only."""

import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

import bench_check
import pstack_link


def git(cwd, *args):
    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True)


class BenchTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self.source = root / "pstack/skills"
        (self.source / "alpha").mkdir(parents=True)
        (self.source / "alpha/SKILL.md").write_text("---\nname: alpha\n---\n")
        main = root / "main"
        git(root, "init", "-q", "-b", "work", str(main))
        git(main, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "base")
        self.bench = root / "bench"
        git(main, "worktree", "add", "-q", "-b", "bench", str(self.bench))
        with redirect_stdout(StringIO()):
            pstack_link.main(["--project", str(self.bench), "--source", str(self.source),
                              "--harness", "codex", "--apply"])
        self.policy = root / "models.json"

    def run_check(self, *extra):
        out = StringIO()
        with redirect_stdout(out):
            code = bench_check.main(["--project", str(self.bench), "--base", "work",
                                     "--source", str(self.source), "--policy", str(self.policy), *extra])
        return code, out.getvalue()

    def test_linked_bench_is_clean(self):
        code, out = self.run_check()
        self.assertEqual(code, 0, out)

    def test_reset_discards_run_but_keeps_links(self):
        (self.bench / "scratch.txt").write_text("left by a run")
        git(self.bench, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "run")
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("commits past base: 1", out)
        self.assertIn("scratch.txt", out)
        code, _ = self.run_check("--reset", "--yes")
        self.assertEqual(code, 0)
        self.assertFalse((self.bench / "scratch.txt").exists())
        self.assertTrue((self.bench / ".agents/skills/alpha").is_symlink())
        self.assertEqual(self.run_check()[0], 0)

    def test_refuses_to_reset_the_base_branch(self):
        with self.assertRaises(SystemExit), redirect_stdout(StringIO()):
            bench_check.main(["--project", str(self.bench.parent / "main"), "--base", "work",
                              "--source", str(self.source), "--policy", str(self.policy), "--reset", "--yes"])


if __name__ == "__main__":
    unittest.main()
