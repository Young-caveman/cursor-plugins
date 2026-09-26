#!/usr/bin/env python3
"""Which PStack skills did a harness actually offer its model in a project?

Reads the skill list each harness recorded in its newest session log for the
project: Codex's injected skill catalog and Claude Code's `skill_listing`
attachment. Claude Code hides `disable-model-invocation` skills and offers
`paths:` skills only near matching files; both are excluded from its expected
set. OpenCode records no skill list, so it is reported as unverifiable.
Read-only; start a session in the project first.
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from pstack_doctor import source_skills

CODEX_ENTRY = re.compile(r"^- (?:([\w.-]+):)?([\w.-]+): .*\(file: ([^)]+)\)\s*$", re.M)
CODEX_ROOT = re.compile(r"^- `(r\d+)` = `([^`]+)`", re.M)


def newest_codex_session(sessions, project):
    for path in sorted(sessions.glob("**/rollout-*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True):
        with path.open(encoding="utf-8") as f:
            first = json.loads(f.readline() or "{}")
        if first.get("payload", {}).get("cwd") == str(project):
            return path
    return None


def codex_skills(path):
    text = path.read_text(encoding="utf-8").replace("\\n", "\n").replace('\\"', '"')
    roots = dict(CODEX_ROOT.findall(text))
    found = {}
    for prefix, name, file in CODEX_ENTRY.findall(text):
        alias, _, rest = file.partition("/")
        found[name] = {"prefix": prefix or None, "file": f"{roots.get(alias, alias)}/{rest}" if rest else file}
    return found


def newest_claude_session(projects, project):
    folder = projects / re.sub(r"[^A-Za-z0-9]", "-", str(project))
    files = sorted(folder.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def claude_skills(path):
    listing = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        attachment = json.loads(line).get("attachment")
        if isinstance(attachment, dict) and attachment.get("type") == "skill_listing":
            described = set(re.findall(r"^- ([\w:.-]+): ", attachment.get("content", ""), re.M))
            listing = {n.rpartition(":")[2]: {"prefix": n.rpartition(":")[0] or None, "described": n in described}
                       for n in attachment.get("names", [])}
    return listing


def compare(harness, session, offered, skills):
    if session is None:
        return {"harness": harness, "session": None, "status": "no session for this project"}
    pstack = {n: v for n, v in offered.items() if n in skills}
    prefixes = sorted({v["prefix"] for v in pstack.values() if v["prefix"]})
    return {
        "harness": harness,
        "session": str(session),
        "offered": len(pstack),
        "expected": len(skills),
        "missing": sorted(skills - set(pstack)),
        "prefixes": prefixes,
        "undescribed": sorted(n for n, v in pstack.items() if v.get("described") is False),
        "status": "ok" if len(pstack) == len(skills) and not prefixes else "differs",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--codex-sessions", type=Path, default=Path.home() / ".codex/sessions")
    parser.add_argument("--claude-projects", type=Path, default=Path.home() / ".claude/projects")
    args = parser.parse_args(argv)
    project, skills = args.project.resolve(), source_skills(args.source.resolve())
    frontmatter = {p.parent.name: p.read_text(encoding="utf-8").split("\n---", 1)[0]
                   for p in args.source.resolve().glob("*/SKILL.md")}
    hidden = {n for n, fm in frontmatter.items() if "\ndisable-model-invocation: true" in fm}
    conditional = {n for n, fm in frontmatter.items() if "\npaths:" in fm}

    codex = newest_codex_session(args.codex_sessions, project)
    claude = newest_claude_session(args.claude_projects, project)
    results = [
        compare("codex", codex, codex_skills(codex) if codex else {}, skills),
        compare("claude", claude, claude_skills(claude) if claude else {}, skills - hidden - conditional),
        {"harness": "opencode", "status": "unverifiable: OpenCode does not record the skill list; ask the model"},
    ]
    print(json.dumps(results, indent=2))
    return 0 if all(r["status"] == "ok" for r in results if r["harness"] != "opencode") else 1


if __name__ == "__main__":
    raise SystemExit(main())
