#!/usr/bin/env python3
"""Report and optionally reset a PStack test bench worktree.

A test bench is a git worktree on its own branch with PStack linked in. After a
test run it lists what the run left behind: commits past the base branch,
uncommitted or untracked files, and PStack drift from pstack_doctor. With
--reset it asks first, then runs `git reset --hard <base>` and `git clean -fd`.
Without -x, git clean keeps ignored files, so the PStack links (listed in
.git/info/exclude) survive the reset. Git cannot undo effects outside the
checkout (databases, servers, pushes).
"""

import argparse
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pstack_doctor


def git(project, *args):
    return subprocess.run(
        ["git", "-C", str(project), *args], capture_output=True, text=True, check=False
    )


def inspect(project, base):
    branch = git(project, "branch", "--show-current").stdout.strip()
    if git(project, "rev-parse", "--verify", "--quiet", base).returncode != 0:
        raise SystemExit(f"base {base!r} is not a commit in {project}")
    commits = git(project, "log", "--oneline", f"{base}..HEAD").stdout.splitlines()
    behind = git(project, "rev-list", "--count", f"HEAD..{base}").stdout.strip()
    changes = git(project, "status", "--porcelain").stdout.splitlines()
    return branch, commits, int(behind or 0), changes


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True, help="test bench worktree")
    parser.add_argument("--base", required=True, help="branch the bench should match, e.g. your main work branch")
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--policy", type=Path, default=Path.home() / ".config/pstack/models.json")
    parser.add_argument("--reset", action="store_true", help="reset the bench to --base after confirming")
    parser.add_argument("--yes", action="store_true", help="skip the confirmation prompt for --reset")
    args = parser.parse_args(argv)
    project = args.project.resolve()

    branch, commits, behind, changes = inspect(project, args.base)
    drift = [f for f in pstack_doctor.diagnose(project, args.source.resolve(), args.policy)
             if f["level"] != "info"]

    print(f"bench   {project}\nbranch  {branch or '(detached)'}\nbase    {args.base}\n")
    print(f"commits past base: {len(commits)}")
    for line in commits:
        print(f"    {line}")
    if behind:
        print(f"behind base by {behind} commit(s); reset or merge to catch up")
    print(f"uncommitted or untracked files: {len(changes)}")
    for line in changes:
        print(f"    {line}")
    print(f"pstack drift: {len(drift)}")
    for f in drift:
        print(f"    [{f['level']}] {f['kind']}: {f['path']}")
    if drift:
        print("    run pstack_doctor.py for details and fixes")

    dirty = bool(commits or changes or behind)
    if not args.reset:
        print("\nclean" if not dirty and not drift else "")
        return 1 if dirty or drift else 0

    if branch == args.base:
        raise SystemExit(f"refusing to reset: the bench is on {args.base} itself")
    if not dirty:
        print("\nnothing to reset")
        return 0
    if not args.yes:
        answer = input(f"\ndiscard everything above and reset {branch} to {args.base}? [y/N] ")
        if answer.strip().lower() != "y":
            print("not reset")
            return 1
    for cmd in (["reset", "--hard", args.base], ["clean", "-fd"]):
        done = git(project, *cmd)
        if done.returncode != 0:
            raise SystemExit(f"git {' '.join(cmd)} failed: {done.stderr.strip()}")
    print(f"reset {branch} to {args.base}; PStack links kept")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
