#!/usr/bin/env python3
"""Tests for the PStack link reconciler. Standard library only."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pstack_doctor
import pstack_link


class LinkTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self.source = root / "pstack/skills"
        for name in ["alpha", "beta"]:
            (self.source / name).mkdir(parents=True)
            (self.source / name / "SKILL.md").write_text(f"---\nname: {name}\n---\n")
        self.project = root / "project"
        subprocess.run(["git", "init", "-q", str(self.project)], check=True)
        self.policy = root / "models.json"

    def run_link(self, *harnesses, apply=True):
        args = ["--project", str(self.project), "--source", str(self.source)]
        for h in harnesses:
            args += ["--harness", h]
        return pstack_link.main(args + (["--apply"] if apply else []))

    def drift(self):
        found = pstack_doctor.diagnose(self.project, self.source, self.policy)
        return {f["kind"] for f in found if f["level"] != "info"}

    def test_apply_leaves_doctor_clean_and_git_status_empty(self):
        self.assertEqual(self.run_link("codex", "claude"), 0)
        self.assertTrue((self.project / ".claude/skills/alpha").is_symlink())
        self.assertEqual(self.drift(), set())
        status = subprocess.run(["git", "-C", str(self.project), "status", "--porcelain"],
                                capture_output=True, text=True).stdout
        self.assertEqual(status, "")

    def test_dry_run_changes_nothing(self):
        self.run_link("codex", apply=False)
        self.assertFalse((self.project / ".agents").exists())

    def test_removed_skill_and_deselected_harness_are_unlinked(self):
        self.run_link("codex", "claude")
        (self.source / "beta/SKILL.md").unlink()
        (self.source / "beta").rmdir()
        self.run_link("codex")
        self.assertFalse((self.project / ".agents/skills/beta").is_symlink())
        self.assertFalse((self.project / ".claude/skills/alpha").is_symlink())
        self.assertTrue((self.source / "alpha/SKILL.md").exists())
        self.assertEqual(self.drift(), set())

    def test_real_directory_is_a_conflict_and_survives(self):
        (self.project / ".agents/skills/alpha").mkdir(parents=True)
        (self.project / ".agents/skills/alpha/SKILL.md").write_text("local")
        self.assertEqual(self.run_link("codex"), 1)
        self.assertEqual((self.project / ".agents/skills/alpha/SKILL.md").read_text(), "local")

    def test_exclude_block_is_replaced_not_duplicated(self):
        exclude = self.project / ".git/info/exclude"
        exclude.write_text("user-pattern\n")
        self.run_link("codex")
        self.run_link("claude")
        text = exclude.read_text()
        self.assertEqual(text.count(pstack_link.BEGIN), 1)
        self.assertIn("user-pattern", text)
        self.assertIn("/.claude/skills/alpha", text)
        self.assertNotIn("/.agents/skills/alpha", text)

    def test_second_run_is_in_sync(self):
        self.run_link("codex")
        self.assertEqual(pstack_link.plan(self.project, self.source, ["codex"])[0], [])


if __name__ == "__main__":
    unittest.main()
