#!/usr/bin/env python3
"""Read-only drift check between the PStack source and one project.

Skill text is live (symlinked), but what PStack left behind in a project is a
snapshot: links, lock entries, instruction-file pointers, the model pool. This
reports each artifact that no longer matches the current source. It never
writes, never deletes, and never contacts a provider; every fix is printed for
the user to run.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HARNESS_DIRS = {
    ".agents/skills": "Codex, OpenCode",
    ".claude/skills": "Claude Code, OpenCode",
    ".opencode/skills": "OpenCode",
}
INSTRUCTION_FILES = ["AGENTS.md", "AGENTS.override.md", "CLAUDE.md", "CLAUDE.local.md"]
INSTRUCTION_GLOBS = [".cursor/rules/*.mdc", ".claude/rules/*.md"]
SKILL_REF = re.compile(r"(\.(?:agents|claude|cursor|opencode)/skills/[A-Za-z0-9_.-]+)")
PSTACK_MARK = "/pstack/skills/"
ORDER = {"stale": 0, "warn": 1, "info": 2}


def finding(level, kind, path, detail, fix=None):
    return {"level": level, "kind": kind, "path": str(path), "detail": detail, "fix": fix}


def source_skills(source):
    return {p.parent.name for p in source.glob("*/SKILL.md")}


def git(project, *args):
    return subprocess.run(
        ["git", "-C", str(project), *args], capture_output=True, text=True, check=False
    )


def check_links(project, source, skills):
    found, links = [], []
    for rel, harnesses in HARNESS_DIRS.items():
        root = project / rel
        if not root.is_dir():
            continue
        linked = set()
        for entry in sorted(root.iterdir()):
            if entry.is_symlink():
                target = os.readlink(entry)
                if PSTACK_MARK not in target:
                    continue
                links.append(entry)
                linked.add(entry.name)
                resolved = Path(target) if os.path.isabs(target) else entry.parent / target
                if not resolved.exists():
                    found.append(finding(
                        "stale", "dangling-link", entry,
                        f"points at {target}, which no longer exists (skill renamed or removed, or worktree moved)",
                        "pstack_link.py --apply (or rm the link, no trailing slash)",
                    ))
                elif resolved.resolve().parent != source:
                    found.append(finding(
                        "warn", "foreign-source", entry,
                        f"resolves into {resolved.resolve().parent}, not the source being checked ({source})",
                        "re-link from the source you are testing",
                    ))
            elif entry.is_dir() and entry.name in skills:
                found.append(finding(
                    "stale", "shadowing-copy", entry,
                    "a real directory with a PStack skill name; it is a frozen copy and hides the live source",
                    f"inspect, then replace with a link to {source / entry.name}",
                ))
        if linked:
            missing = sorted(skills - linked)
            if missing:
                found.append(finding(
                    "stale", "unlinked-skill", root,
                    f"source has skills this project never linked: {', '.join(missing)}",
                    "pstack_link.py --apply",
                ))
    if not any(l.parent == project / ".claude/skills" for l in links) and links:
        found.append(finding(
            "info", "harness-coverage", project / ".claude/skills",
            "no PStack links here; Claude Code does not read .agents/skills, so it sees none of PStack",
        ))
    return found, links


def check_ignored(project, links):
    if not links or git(project, "rev-parse", "--git-dir").returncode != 0:
        return []
    rels = [str(l.relative_to(project)) for l in links]
    ignored = set(git(project, "check-ignore", "--no-index", *rels).stdout.split())
    loose = [r for r in rels if r not in ignored]
    if not loose:
        return []
    return [finding(
        "warn", "unignored-links", project,
        f"{len(loose)} PStack links show as untracked on the current branch (a committed .gitignore only covers the branches that carry it)",
        "pstack_link.py --apply (writes a managed block in .git/info/exclude)",
    )]


def check_lock(project, skills):
    lock = project / "skills-lock.json"
    if not lock.is_file():
        return []
    try:
        entries = json.loads(lock.read_text(encoding="utf-8")).get("skills", {})
    except (json.JSONDecodeError, AttributeError):
        return [finding("warn", "lock-unreadable", lock, "not valid skills-lock JSON")]
    pinned = sorted(
        name for name, meta in entries.items()
        if name in skills or "pstack" in str(meta.get("source", ""))
    )
    if not pinned:
        return []
    return [finding(
        "stale", "lock-pins-live-source", lock,
        f"hash-pins {len(pinned)} PStack skills; every source edit makes these hashes wrong",
        "drop PStack entries from the lock; links need no lock",
    )]


def instruction_files(project):
    files = [project / name for name in INSTRUCTION_FILES if (project / name).is_file()]
    for pattern in INSTRUCTION_GLOBS:
        files.extend(sorted(project.glob(pattern)))
    config = project / "opencode.json"
    if config.is_file():
        try:
            for pattern in json.loads(config.read_text(encoding="utf-8")).get("instructions", []):
                if "://" not in pattern:
                    files.extend(sorted(project.glob(pattern)))
        except (json.JSONDecodeError, AttributeError):
            pass
    return files


def check_refs(project):
    found = []
    for path in instruction_files(project):
        text = path.read_text(encoding="utf-8", errors="replace")
        for number, line in enumerate(text.splitlines(), 1):
            for ref in sorted(set(SKILL_REF.findall(line))):
                where = f"{path.relative_to(project)}:{number}"
                if not (project / ref).exists():
                    found.append(finding(
                        "stale", "dangling-reference", where,
                        f"instructs agents to read {ref}, which does not exist",
                        "remove or repoint the line",
                    ))
                elif ref.startswith(".cursor/"):
                    found.append(finding(
                        "warn", "cursor-reference", where,
                        f"points at {ref}; Codex, OpenCode, and Claude Code do not discover .cursor/skills",
                    ))
    return found


def check_cursor_skills(project):
    root = project / ".cursor/skills"
    if not root.is_dir():
        return []
    names = sorted(p.name for p in root.iterdir() if (p / "SKILL.md").is_file())
    if not names:
        return []
    return [finding(
        "warn", "cursor-era-skill", root,
        f"{', '.join(names)}: generated for Cursor; no current harness discovers this directory",
        "move each into .agents/skills (and link it into .claude/skills for Claude Code)",
    )]


def check_policy(policy):
    if not policy.is_file():
        return [finding("info", "policy-absent", policy, "no model pool yet; run setup-pstack")]
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import model_policy

    try:
        model_policy.validate(json.loads(policy.read_text(encoding="utf-8")))
    except model_policy.MigrationRequired as exc:
        return [finding("stale", "policy-migration", policy, str(exc), "re-run setup-pstack")]
    except (json.JSONDecodeError, model_policy.PolicyError) as exc:
        return [finding("stale", "policy-invalid", policy, str(exc), "re-run setup-pstack")]
    return [finding(
        "info", "policy-structure", policy,
        "structurally valid for this source; availability still needs `model_policy.py ready --snapshot`",
    )]


def diagnose(project, source, policy):
    source = source.resolve()
    skills = source_skills(source)
    found, links = check_links(project, source, skills)
    found += check_ignored(project, links)
    found += check_lock(project, skills)
    found += check_refs(project)
    found += check_cursor_skills(project)
    found += check_policy(policy)
    return sorted(found, key=lambda f: ORDER[f["level"]])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument(
        "--source", type=Path, default=Path(__file__).resolve().parents[2],
        help="PStack skills directory to compare against (default: the one holding this script)",
    )
    parser.add_argument("--policy", type=Path, default=Path.home() / ".config/pstack/models.json")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    project, source = args.project.resolve(), args.source.resolve()
    found = diagnose(project, source, args.policy)
    if args.json:
        print(json.dumps(found, indent=2, ensure_ascii=False))
    else:
        print(f"project {project}\nsource  {source}\n")
        for f in found:
            print(f"[{f['level']}] {f['kind']}: {f['path']}\n    {f['detail']}")
            if f["fix"]:
                print(f"    fix: {f['fix']}")
        if not found:
            print("no drift found")
    return 1 if any(f["level"] == "stale" for f in found) else 0


if __name__ == "__main__":
    raise SystemExit(main())
