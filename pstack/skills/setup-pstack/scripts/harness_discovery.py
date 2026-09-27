#!/usr/bin/env python3
"""Which PStack skills did a harness actually offer its model in a project?

Reads the skill list each harness recorded in its newest session log for the
project: Codex's injected skill catalog, Claude Code's `skill_listing`
attachment, and the `<available_skills>` block in Pi's system message. Claude
Code and Pi hide `disable-model-invocation` skills, and Claude Code offers
`paths:` skills only near matching files; those are excluded from the expected
sets. OpenCode records no skill list, so it is reported as unverifiable.
Harnesses without a session in the project are listed but don't fail the
check. Read-only; start a session in the project first.
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


def newest_pi_session(sessions, project):
    for path in sorted(sessions.glob("*/*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True):
        with path.open(encoding="utf-8") as f:
            first = json.loads(f.readline() or "{}")
        if first.get("type") == "session" and first.get("cwd") == str(project):
            return path
    return None


def pi_skills(path):
    for line in path.read_text(encoding="utf-8").splitlines():
        entry = json.loads(line)
        message = entry.get("message") or {}
        if entry.get("type") == "message" and message.get("role") == "system":
            block = (message.get("sections") or {}).get("skills", "")
            return {n: {"prefix": None} for n in re.findall(r"<name>([\w.:-]+)</name>", block)}
    return None


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
    parser.add_argument("--pi-sessions", type=Path, default=Path.home() / ".pi/agent/sessions")
    args = parser.parse_args(argv)
    project, skills = args.project.resolve(), source_skills(args.source.resolve())
    frontmatter = {p.parent.name: p.read_text(encoding="utf-8").split("\n---", 1)[0]
                   for p in args.source.resolve().glob("*/SKILL.md")}
    hidden = {n for n, fm in frontmatter.items() if "\ndisable-model-invocation: true" in fm}
    conditional = {n for n, fm in frontmatter.items() if "\npaths:" in fm}

    codex = newest_codex_session(args.codex_sessions, project)
    claude = newest_claude_session(args.claude_projects, project)
    pi = newest_pi_session(args.pi_sessions, project)
    pi_offered = pi_skills(pi) if pi else {}
    results = [
        compare("codex", codex, codex_skills(codex) if codex else {}, skills),
        compare("claude", claude, claude_skills(claude) if claude else {}, skills - hidden - conditional),
        compare("pi", pi, pi_offered, skills - hidden) if pi_offered is not None else
        {"harness": "pi", "session": str(pi), "status": "unverifiable: this Pi session recorded no system message; ask the model"},
        {"harness": "opencode", "status": "unverifiable: OpenCode does not record the skill list; ask the model"},
    ]
    print(json.dumps(results, indent=2))
    return 1 if any(r["status"] == "differs" for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
