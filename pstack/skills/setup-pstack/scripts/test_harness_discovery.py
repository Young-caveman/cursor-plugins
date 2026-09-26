#!/usr/bin/env python3
"""Tests for the harness discovery check. Standard library only."""

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

import harness_discovery


class DiscoveryTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.source = self.root / "pstack/skills"
        skills = {
            "alpha": "",
            "beta": "disable-model-invocation: true\n",
            "gamma": 'paths: ["**/*.ts"]\n',
        }
        for name, extra in skills.items():
            (self.source / name).mkdir(parents=True)
            (self.source / name / "SKILL.md").write_text(f"---\nname: {name}\n{extra}---\n\nbody\n")
        self.project = self.root / "project"
        self.project.mkdir()
        self.codex = self.root / "codex"
        self.claude = self.root / "claude"

    def codex_session(self, entries):
        day = self.codex / "2026/09/26"
        day.mkdir(parents=True, exist_ok=True)
        catalog = "### Available skills\\n" + "".join(f"- {e}: does things. (file: r6/{e.split(':')[-1]}/SKILL.md)\\n" for e in entries)
        catalog += f"- `r6` = `{self.project}/.agents/skills`\\n"
        lines = [
            json.dumps({"type": "session_meta", "payload": {"cwd": str(self.project)}}),
            '{"type":"response_item","payload":{"content":[{"text":"' + catalog + '"}]}}',
        ]
        (day / "rollout-1.jsonl").write_text("\n".join(lines) + "\n")

    def claude_session(self, names, described):
        folder = self.claude / re.sub(r"[^A-Za-z0-9]", "-", str(self.project))
        folder.mkdir(parents=True)
        content = "\n".join(f"- {n}: text" if n in described else f"- {n}" for n in names)
        attachment = {"type": "skill_listing", "names": names, "content": content}
        (folder / "s.jsonl").write_text(json.dumps({"type": "attachment", "attachment": attachment}) + "\n")

    def run_check(self):
        args = ["--project", str(self.project), "--source", str(self.source),
                "--codex-sessions", str(self.codex), "--claude-projects", str(self.claude)]
        return harness_discovery.main(args)

    def capture(self):
        from io import StringIO
        from contextlib import redirect_stdout
        out = StringIO()
        with redirect_stdout(out):
            code = self.run_check()
        return code, {r["harness"]: r for r in json.loads(out.getvalue())}

    def test_all_offered_is_ok(self):
        self.codex_session(["alpha", "beta", "gamma"])
        self.claude_session(["alpha", "other"], described={"alpha"})
        code, r = self.capture()
        self.assertEqual(code, 0)
        self.assertEqual(r["codex"]["status"], "ok")
        self.assertEqual(r["claude"]["expected"], 1)
        self.assertEqual(r["claude"]["undescribed"], [])

    def test_plugin_prefix_is_reported(self):
        self.codex_session(["pstack:alpha", "pstack:beta", "pstack:gamma"])
        self.claude_session(["alpha"], described=set())
        code, r = self.capture()
        self.assertEqual(code, 1)
        self.assertEqual(r["codex"]["prefixes"], ["pstack"])
        self.assertEqual(r["claude"]["undescribed"], ["alpha"])

    def test_missing_skill_and_absent_session(self):
        self.codex_session(["alpha"])
        code, r = self.capture()
        self.assertEqual(code, 1)
        self.assertEqual(r["codex"]["missing"], ["beta", "gamma"])
        self.assertEqual(r["claude"]["status"], "no session for this project")
        self.assertTrue(r["opencode"]["status"].startswith("unverifiable"))


if __name__ == "__main__":
    unittest.main()
