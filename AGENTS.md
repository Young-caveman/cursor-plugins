# PStack handoff

Current state and rules for working on PStack. History, research, and test results live in `pstack/develop-log/` (newest file first). The user's latest instructions take precedence.

## Goal

Turn PStack (originally for Cursor) into the user's personal skill set for Codex, OpenCode, and Claude Code, all run under T3 Code. T3's `orchestrator_capabilities` (what can run) and `delegate_task` (run it) are the contract. OSes: macOS, Omarchy/Arch.

## Rules

- Models live in one v2 pool, `~/.config/pstack/models.json`: `providerInstanceId` + model + confirmed options + optional `tier`. Anything outside the pool needs the user's explicit authorization.
- Cost: `default`-tier entries (Luna max, DeepSeek, MiMo, Sonnet; cheap per the user) do the work; `escalation` entries (Opus 5.5; Astra if added) only for genuinely hard tasks.
- Never silently substitute a model or raise reasoning effort. Effort levels don't carry across models.
- Invocation: principle skills, `unslop`, `typescript-best-practices`, and `setup-pstack` may auto-trigger; the 21 workflow skills keep `disable-model-invocation: true` (Claude-only field).
- PStack writes nothing tracked into a user project: no lock files, no `.gitignore` entries, no pointer lines in the project's `AGENTS.md`.
- Anything checkable by reading files is a script, not manual inspection. Scripts prove state; only a harness run proves behavior.
- Spawned agents follow `setup-pstack/references/t3-delegation.md`: `delegate_task` children share the parent's checkout; parallel writers get `t3_thread_launch` worktrees; briefs stand alone.
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
4. Something looks broken → run `pstack_doctor.py --project /cave/Wisdio-pstack` first. Threads in another T3 project can't be read via `t3_thread_read`; read harness logs with `audit-rollout.py`.
5. Commit here; log results in `pstack/develop-log/`.

Update the test copy: `git -C /cave/Wisdio-pstack merge develop1-engine`.

## Tools

- `model_policy.py` — validate / ready / resolve / list / propose / convert the pool. Read-only.
- `pstack_doctor.py` — reports drift between the source and a project. Read-only; exit 1 on `stale`.
- `pstack_link.py` — reconciles skill links and a managed `.git/info/exclude` block. Dry run unless `--apply`.
- `harness_discovery.py --project <repo>` — which skills Codex and Claude Code actually offered their model in the newest session there (from their logs). OpenCode records none; ask the model.
- `pstack/tools/audit-rollout.py` — reads Codex/OpenCode session logs and reports which model and effort actually ran.
- Tests: `for t in test_model_policy test_pstack_doctor test_pstack_link test_harness_discovery; do python3 pstack/skills/setup-pstack/scripts/$t.py; done`

## State and gaps

- Discovery works in all three harnesses; the model pool is saved and every model in it answered a delegated call.
- All workflows are migrated to T3 delegation (`38550b1`). Real runs so far: `swarm` (passed), `interrogate` (see develop-log). The rest are migrated but unexercised.
- Claude Code drops most skill descriptions when the list is long: 23 of 25 PStack skills reach its model as a bare name. Descriptions need shortening.
- Plan mode's read-only enforcement and whether it keeps MCP servers are unverified per provider; `why` and `reflect` avoid plan mode for that reason.
- `make-bot-ui` targets a Grok Bot webhook on `cursor.sh`; left as is.
- T3's Claude adapter silently remaps some effort values (`effortMap`). Warn the user; don't build a remap table.
- `main` still has v1 skill text; the current source is `t3-orchestration`.

## Next

1. First real Wisdio task: plan a macOS verification skeleton with `/create-verification-skill` in `/cave/Wisdio-pstack`.
2. Shorten skill descriptions so Claude keeps them (listing budget ~8,000 characters).
3. Later: evals and audits to pick models per task (user's plan; not now).

## Safety

Remove links with `rm <link>` without a trailing slash, or with `pstack_link.py`. `rm -rf <link>/` deletes the source.
