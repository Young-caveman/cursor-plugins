# Developing PStack

This page is for changing PStack's own skills. To use PStack, follow the [guide](./guide/01-setup.md) instead.

## Link instead of install

A development copy links the skills from your clone into one project, so a text edit is live there with nothing to reinstall. Don't combine this with the user-level install on one machine: the project would show every skill twice. A link is untracked, so it shows up on every branch of that checkout; to try a change in isolation, use a separate worktree.

From the clone's `pstack` directory, preview and then apply:

```bash
python3 skills/setup-pstack/scripts/pstack_link.py --project /path/to/repo --harness codex --harness opencode --harness claude
python3 skills/setup-pstack/scripts/pstack_link.py --project /path/to/repo --harness codex --harness opencode --harness claude --apply
```

Pass only the `--harness` flags you use. Codex reads `.agents/skills`; Claude Code reads only `.claude/skills`; OpenCode reads both and de-duplicates by name.

The links stay out of git through a managed block in the repo's `.git/info/exclude`. PStack writes no lock file, no `.gitignore` entry, and no line in the project's `AGENTS.md`. Real directories are never touched.

Rerun the command after you add, rename, or remove a skill. Text edits need no relinking: Claude Code and Codex see them live; OpenCode caches skills, so start a new session.

## Check a linked project

```bash
python3 skills/setup-pstack/scripts/pstack_doctor.py --project /path/to/repo
python3 skills/setup-pstack/scripts/harness_discovery.py --project /path/to/repo
python3 skills/setup-pstack/scripts/bench_check.py --project /path/to/repo --base <branch>
```

- `pstack_doctor.py` reports drift between the source and the project, read-only. It only understands linked installs.
- `harness_discovery.py` lists which skills Codex and Claude Code offered their model in the newest session there. OpenCode records no such list, so ask the model.
- `bench_check.py` lists what a test run left in a test worktree; `--reset` asks, then resets it to the base branch and keeps the links.

Doctor findings, including what older PStack versions left behind:

| What drifted | Doctor finding | Fix |
|---|---|---|
| Links missing, dangling, pointing into another checkout, or shadowed by a real copy | `unlinked-skill`, `dangling-link`, `foreign-source`, `shadowing-copy` | `pstack_link.py --apply` (re-link from the right checkout for `foreign-source`; inspect a copy before replacing it) |
| Links showing as untracked files | `unignored-links` | `pstack_link.py --apply` |
| `skills-lock.json` pinning PStack hashes, or an instruction line pointing at a removed skill | `lock-pins-live-source`, `dangling-reference` | Delete the entry or line by hand |
| A verification skill still under `.cursor/skills` | `cursor-era-skill` | Move it to `.agents/skills` and link it into `.claude/skills` |
| `verify-<app>`'s feature map no longer matches the app | none; the doctor can't see app behavior | [`/maintain-verification-skill`](../skills/maintain-verification-skill/SKILL.md) |

## Inspect the model pool

```bash
python3 skills/setup-pstack/scripts/model_policy.py validate
python3 skills/setup-pstack/scripts/model_policy.py list
python3 skills/setup-pstack/scripts/model_policy.py ready --snapshot <capabilities.json>
```

`validate` checks structure and requires at least one `default` entry; `ready` checks advertised availability against a saved capabilities snapshot. Only a successful delegated run proves a target works. A version 1 role policy is left untouched; `model_policy.py convert` shows a reviewed conversion.

`pstack/tools/audit-rollout.py` reads Codex and OpenCode session logs and reports which model and effort actually ran.

## Tests

```bash
for t in test_model_policy test_pstack_doctor test_pstack_link test_harness_discovery test_bench_check; do python3 skills/setup-pstack/scripts/$t.py; done
```

Scripts prove state; only a run in a harness proves behavior.
