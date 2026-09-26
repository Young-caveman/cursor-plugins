# PStack handoff

Current state and rules for working on PStack. History, research, and test results live in `pstack/develop-log/` (newest file first). The user's latest instructions take precedence.

## Goal

Turn PStack (originally for Cursor) into the user's personal skill set for Codex, OpenCode, and Claude Code, all run under T3 Code. T3's `orchestrator_capabilities` (what can run) and `delegate_task` (run it) are the contract. OSes: macOS, Omarchy/Arch.

## Rules

- Models live in one v2 pool, `~/.config/pstack/models.json`: `providerInstanceId` + model + confirmed options. Anything outside the pool needs the user's explicit authorization.
- Never silently substitute a model or raise reasoning effort. Effort levels don't carry across models.
- PStack writes nothing tracked into a user project: no lock files, no `.gitignore` entries, no pointer lines in the project's `AGENTS.md`.
- Anything checkable by reading files is a script, not manual inspection. Scripts prove state; only a harness run proves behavior.
- Keep skill text short. Current models over-follow ceremony (forced todos, always-test, stop-for-review).
- Keep work under `pstack/`. This repo is sparse-checkout (`/*`, `!/*/`, `/pstack/`). Run `git sparse-checkout add <dir>` before creating a new top-level dir; never disable sparse-checkout.
- The user runs installs and harness tests. Prefer free OpenCode models (Muse Spark 1.3 Free) for tests and delegated research.

## Layout

| Path | Purpose |
|---|---|
| this worktree (`t3-orchestration`) | PStack source; edit skills here |
| `/cave/Wisdio` (`develop1-engine`) | normal Wisdio work; no PStack |
| `/cave/Wisdio-pstack` (`pstack-test`) | Wisdio + PStack links in `.agents/skills` (Codex, OpenCode) and `.claude/skills` (Claude Code) |

## Routine

Scripts are in `pstack/skills/setup-pstack/scripts/`.

1. Edit skills here.
2. Added, renamed, or removed a skill → `pstack_link.py --project /cave/Wisdio-pstack --harness codex --harness opencode --harness claude --apply`. Text edits need nothing.
3. Test from a T3 thread in `/cave/Wisdio-pstack`. OpenCode caches skills: start a new session after edits.
4. Something looks broken → run `pstack_doctor.py --project /cave/Wisdio-pstack` first.
5. Commit here; log results in `pstack/develop-log/`.

Update the test copy: `git -C /cave/Wisdio-pstack merge develop1-engine`.

## Tools

- `model_policy.py` — validate / ready / resolve / propose / convert the pool. Read-only.
- `pstack_doctor.py` — reports drift between the source and a project. Read-only; exit 1 on `stale`.
- `pstack_link.py` — reconciles skill links and a managed `.git/info/exclude` block. Dry run unless `--apply`.
- `pstack/tools/audit-rollout.py` — reads Codex/OpenCode session logs and reports which model and effort actually ran.
- Tests: `for t in test_model_policy test_pstack_doctor test_pstack_link; do python3 pstack/skills/setup-pstack/scripts/$t.py; done`

## Not done

- No PStack skill has run in a real harness yet.
- Role workflows (`poteto-mode`, `arena`, `swarm`, `interrogate`) still call the removed `ready --harness`. Don't claim they work.
- Cursor-era paths: `create-verification-skill` / `maintain-verification-skill` use `.cursor/skills`. `recall`, `reflect`, `show-me-your-work`, `automate-me`, and `poteto-mode` read `~/.cursor` transcripts.
- `test_model_policy.py` Claude fixtures are invented; re-derive them from a real snapshot.
- T3's Claude adapter silently remaps some effort values (`effortMap`). Warn the user; don't build a remap table.
- `main` still has v1 skill text; the current source is `t3-orchestration`.

## Next

1. User: discovery test in `/cave/Wisdio-pstack` for all three harnesses. Check whether OpenCode lists duplicates, since it reads both skill dirs.
2. User: run `setup-pstack` in each harness; log the results.
3. Re-derive the Claude test fixtures.
4. Replace Cursor-era paths.
5. Migrate `poteto-mode`'s gate to the v2 pool, then `arena` / `swarm` / `interrogate`, after step 2 has a real result.

## Safety

Remove links with `rm <link>` without a trailing slash, or with `pstack_link.py`. `rm -rf <link>/` deletes the source.
