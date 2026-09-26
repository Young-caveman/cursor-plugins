#!/usr/bin/env python3
"""Reconcile one project's PStack skill links with the source.

Links every source skill into the chosen harness directories, removes PStack
links whose skill is gone or whose harness was not chosen, and keeps them out
of git through a marked block in the clone's `info/exclude`. Real directories
are never touched. Dry run by default; `--apply` performs the plan.
"""

import argparse
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from pstack_doctor import PSTACK_MARK, git, source_skills

HARNESS_DIRS = {
    "codex": ".agents/skills",
    "opencode": ".agents/skills",
    "claude": ".claude/skills",
}
BEGIN, END = "# >>> pstack links (managed by pstack_link.py)", "# <<< pstack links"


def is_pstack_link(path):
    return path.is_symlink() and PSTACK_MARK in os.readlink(path)


def plan(project, source, harnesses):
    skills = source_skills(source)
    wanted = {HARNESS_DIRS[h] for h in harnesses}
    actions, keep = [], []
    for rel in sorted(set(HARNESS_DIRS.values())):
        root = project / rel
        for name in sorted(skills) if rel in wanted else []:
            link, target = root / name, source / name
            if is_pstack_link(link) and os.readlink(link) == str(target):
                keep.append(link)
            elif is_pstack_link(link):
                actions += [("unlink", link, "points elsewhere"), ("link", link, target)]
                keep.append(link)
            elif link.exists() or link.is_symlink():
                actions.append(("conflict", link, "not a PStack link; left alone"))
            else:
                actions.append(("link", link, target))
                keep.append(link)
        if root.is_dir():
            for entry in sorted(root.iterdir()):
                if is_pstack_link(entry) and (rel not in wanted or entry.name not in skills):
                    reason = "harness not selected" if rel not in wanted else "skill no longer in source"
                    actions.append(("unlink", entry, reason))
    return actions, sorted(str(p.relative_to(project)) for p in keep)


def exclude_path(project):
    result = git(project, "rev-parse", "--git-path", "info/exclude")
    if result.returncode != 0:
        return None
    path = Path(result.stdout.strip())
    return path if path.is_absolute() else project / path


def rewrite_exclude(text, entries):
    lines = text.splitlines()
    if BEGIN in lines and END in lines:
        lines = lines[: lines.index(BEGIN)] + lines[lines.index(END) + 1 :]
    while lines and not lines[-1].strip():
        lines.pop()
    if entries:
        lines += ["", BEGIN, *(f"/{e}" for e in entries), END]
    return "\n".join(lines) + "\n" if lines else ""


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument(
        "--harness", action="append", choices=sorted(HARNESS_DIRS), required=True,
        help="repeat for each harness that should see PStack in this project",
    )
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    project, source = args.project.resolve(), args.source.resolve()
    actions, entries = plan(project, source, args.harness)
    exclude = exclude_path(project)

    for kind, path, detail in actions:
        print(f"{kind:8} {path.relative_to(project)}  {detail}")
    if {"claude", "opencode"} <= set(args.harness):
        print("note: OpenCode reads both .agents/skills and .claude/skills; duplicates are untested")
    new_exclude = None
    if exclude is not None:
        old = exclude.read_text(encoding="utf-8") if exclude.is_file() else ""
        new_exclude = rewrite_exclude(old, entries)
        if new_exclude != old:
            print(f"exclude  {exclude}  {len(entries)} managed entries")
            new_exclude = (exclude, new_exclude)
        else:
            new_exclude = None
    if not actions and new_exclude is None:
        print("in sync")
        return 0
    if not args.apply:
        print("dry run; re-run with --apply")
        return 0

    for kind, path, detail in actions:
        if kind == "unlink":
            path.unlink()
        elif kind == "link":
            path.parent.mkdir(parents=True, exist_ok=True)
            path.symlink_to(detail, target_is_directory=True)
    if new_exclude:
        new_exclude[0].parent.mkdir(parents=True, exist_ok=True)
        new_exclude[0].write_text(new_exclude[1], encoding="utf-8")
    conflicts = [a for a in actions if a[0] == "conflict"]
    return 1 if conflicts else 0


if __name__ == "__main__":
    raise SystemExit(main())
