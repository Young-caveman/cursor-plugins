#!/usr/bin/env python3
"""Tests for the PStack project drift doctor. Standard library only."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pstack_doctor


class DoctorTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self.source = root / "pstack/skills"
        for name in ["alpha", "beta", "gamma"]:
            (self.source / name).mkdir(parents=True)
            (self.source / name / "SKILL.md").write_text(f"---\nname: {name}\n---\n")
        self.project = root / "project"
        self.skills = self.project / ".agents/skills"
        self.skills.mkdir(parents=True)
        self.policy = root / "models.json"

    def link(self, name, target=None):
        (self.skills / name).symlink_to(target or self.source / name)

    def kinds(self):
        found = pstack_doctor.diagnose(self.project, self.source, self.policy)
        return {f["kind"]: f for f in found}

    def test_clean_project_reports_only_absent_policy_and_claude_coverage(self):
        for name in ["alpha", "beta", "gamma"]:
            self.link(name)
        self.assertEqual(set(self.kinds()), {"harness-coverage", "policy-absent"})

    def test_removed_skill_leaves_dangling_link(self):
        for name in ["alpha", "beta", "gamma"]:
            self.link(name)
        self.link("renamed-away", self.source / "renamed-away")
        found = self.kinds()["dangling-link"]
        self.assertEqual(found["level"], "stale")
        self.assertIn("pstack_link.py", found["fix"])

    def test_new_source_skill_is_reported_unlinked(self):
        self.link("alpha")
        self.assertIn("beta, gamma", self.kinds()["unlinked-skill"]["detail"])

    def test_copied_skill_shadows_source(self):
        self.link("alpha")
        self.link("beta")
        (self.skills / "gamma").mkdir()
        self.assertEqual(self.kinds()["shadowing-copy"]["level"], "stale")

    def test_link_into_other_worktree_is_foreign(self):
        other = self.project.parent / "other/pstack/skills/alpha"
        other.mkdir(parents=True)
        self.link("alpha", other)
        self.assertIn("foreign-source", self.kinds())

    def test_non_pstack_links_are_ignored(self):
        elsewhere = self.project.parent / "vendor/skill"
        elsewhere.mkdir(parents=True)
        self.link("vendor-skill", elsewhere)
        self.assertEqual(set(self.kinds()), {"policy-absent"})

    def test_instruction_file_pointing_at_missing_skill(self):
        (self.project / "AGENTS.md").write_text(
            "Read `.agents/skills/router/SKILL.md` and `.agents/skills/router/SKILL.md`.\n"
        )
        found = [
            f for f in pstack_doctor.diagnose(self.project, self.source, self.policy)
            if f["kind"] == "dangling-reference"
        ]
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["path"], "AGENTS.md:1")

    def test_opencode_instructions_are_scanned(self):
        (self.project / "docs").mkdir()
        (self.project / "docs/rules.md").write_text("See .claude/skills/gone\n")
        (self.project / "opencode.json").write_text(json.dumps({"instructions": ["docs/*.md"]}))
        self.assertEqual(self.kinds()["dangling-reference"]["path"], "docs/rules.md:1")

    def test_lock_entries_pinning_pstack(self):
        (self.project / "skills-lock.json").write_text(json.dumps({
            "version": 1,
            "skills": {
                "alpha": {"source": "../pstack/skills", "sourceType": "local"},
                "third-party": {"source": "someone/repo", "sourceType": "github"},
            },
        }))
        self.assertIn("1 PStack", self.kinds()["lock-pins-live-source"]["detail"])

    def test_cursor_generated_skill(self):
        (self.project / ".cursor/skills/verify-app").mkdir(parents=True)
        (self.project / ".cursor/skills/verify-app/SKILL.md").write_text("---\n---\n")
        self.assertIn("verify-app", self.kinds()["cursor-era-skill"]["detail"])

    def test_v1_policy_needs_migration(self):
        self.policy.write_text(json.dumps({"version": 1, "profiles": {}, "roles": {}}))
        self.assertEqual(self.kinds()["policy-migration"]["level"], "stale")

    def test_links_ignored_through_info_exclude_are_clean(self):
        subprocess.run(["git", "init", "-q", str(self.project)], check=True)
        for name in ["alpha", "beta", "gamma"]:
            self.link(name)
        self.assertIn("unignored-links", self.kinds())
        exclude = self.project / ".git/info/exclude"
        exclude.write_text("".join(f".agents/skills/{n}\n" for n in ["alpha", "beta", "gamma"]))
        self.assertNotIn("unignored-links", self.kinds())

    def test_cli_exit_code_reflects_stale(self):
        self.link("alpha")
        script = Path(pstack_doctor.__file__)
        args = [sys.executable, str(script), "--project", str(self.project),
                "--source", str(self.source), "--policy", str(self.policy), "--json"]
        result = subprocess.run(args, capture_output=True, text=True, env={**os.environ})
        self.assertEqual(result.returncode, 1)
        self.assertTrue(any(f["kind"] == "unlinked-skill" for f in json.loads(result.stdout)))


if __name__ == "__main__":
    unittest.main()
