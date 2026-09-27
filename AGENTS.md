# PStack handoff

State and rules for working on PStack, as of 2026-09-27. History and test results: `pstack/develop-log/` (newest first). The user's latest instructions win.

## Goal

PStack (originally for Cursor) is the user's personal skill set for Claude Code, Codex, OpenCode, and Pi, all run under T3 Code orchestrator V2. OSes: macOS, Omarchy/Arch.

## T3 target

- The user's fork `Young-caveman/t3code`, branch `yash/swiftui-orchestrator-v2-support` (upstream `pingdotgg/t3code`). It still reports version `0.0.42`, so the version doesn't identify the code. Users build it themselves; the README says so.
- Source: `/cave/t3code` here, `/Users/jimmy/coding/t3code` on the Mac. Read-only. Check T3 behavior there, not from memory or tool descriptions: `docs/orchestration-v2/orchestrator-mcp-server.md`, `apps/server/src/mcp/toolkits/*/tools.ts`, `packages/contracts/src/orchestratorMcp.ts`, `apps/server/src/provider/T3OrchestrationInstructions.ts`, `docs/internals/remote.md`.
- One T3 server is one environment. No thread or delegation tool takes an environment argument, so delegation from an Omarchy thread cannot reach the Mac. Exception: `device_*` tools reach simulators on SSH device hosts configured in that environment (`packages/contracts/src/device.ts`, `SshDeviceHost.ts`); not tested here. Mac work goes through a thread the user opens there, or Wisdio's `t3-thread-handoff` skill on the user's explicit request (no completion notice).

## T3 features PStack uses

The contract is `pstack/skills/setup-pstack/references/t3-delegation.md`; the README table "What PStack uses from T3" and the guide mirror it. Change all three together.

| T3 feature | PStack use | Where |
|---|---|---|
| `orchestrator_capabilities` | providers, models, options for the pool; `runtimeMode`/`interactionMode` gate for launches | `setup-pstack`, every delegating workflow |
| `delegate_task` (`target`, `mode`, `clientRequestId`, `interactionMode`), `task_status`, `task_cancel` | read-only helpers and one-at-a-time writers in the parent's checkout, instead of the harness's own subagents | `interrogate`, `why`, `reflect`, `architect`, `recall`, `automate-me`, playbooks |
| `t3_thread_launch` (`title`, `message`, `modelSelection`, worktree `workspaceStrategy`) | parallel writers, one worktree thread each; parent must be `full-access` + `default` | `arena`, `swarm`, autopilot, multi-phase, orchestrate, hillclimb, shipping, opening-a-pr |
| `t3_thread_wait`, `t3_thread_read`, `t3_thread_send` (`queue`/`steer`/`restart`), `t3_thread_interrupt`, `t3_queue_*` | follow, steer, stop launched threads | `arena`, `swarm`, orchestrate, autopilot, pause-safely |
| `t3_pending_request_*` | answer a worker's question (never approvals) | orchestrate, autopilot, multi-phase |
| `schedule_task` + update/delete/list/run-now | recurring check-ins; paused on pause, deleted at the end | autonomous-run, autopilot, multi-phase, babysit, shipping, orchestrate |
| `t3_worktree_status`, `t3_worktree_handoff`, `link_pull_request` | move this thread into a worktree; attach every PR layer | opening-a-pr |
| `t3_thread_search`, `t3_thread_list` | find earlier threads | `recall`, `automate-me` (via `transcripts.md`) |
| `preview_*`, `device_*` | drive and capture the app | `create-verification-skill` |

Unused on purpose: `t3_thread_fork`, `t3_thread_merge_back`, `create_threads` (briefs stand alone), project/environment tools. Inside a PStack workflow, `t3-delegation.md` overrides T3's own advice to prefer native subagents and to launch threads only on request.

## Rules

- Models come only from the pool `~/.config/pstack/models.json` (v2: `id`, `providerInstanceId`, `model`, `options`, `tier`; a missing tier means `default`). It holds only cheap entries: Codex Luna max, Sonnet 5 levels, OpenCode DeepSeek and MiMo. No `escalation` entry; Opus 5.5 or any other model outside the pool needs the user's OK per task.
- Never silently substitute a model or raise reasoning effort; effort levels don't carry across models. T3's Claude adapter remaps some effort values (`effortMap`): warn, don't build a remap table.
- Invocation: the 23 principle skills, `unslop`, `typescript-best-practices`, and `setup-pstack` may auto-trigger. The 20 workflow skills have `disable-model-invocation: true` and a description opening "Run only when the user asks for this skill by name…". Claude Code and Pi enforce the field; Codex and OpenCode ignore it, so there it is only an instruction.
- Plan mode is a hint; the brief's "do not edit files" is the guard (user decision). T3's Pi adapter ignores plan mode. `why` and `reflect` keep default mode so reviewers keep MCP access.
- A surface only another machine can drive is `verified-unreachable` from here. Never claim it verified or fake a delegation to it.
- PStack writes nothing tracked into a user project: no lock files, `.gitignore` entries, or `AGENTS.md` lines.
- Anything checkable by reading files is a script. Scripts prove state; only a harness run proves behavior.
- Keep skill text short; current models over-follow ceremony.
- Keep work under `pstack/`. The repo is sparse-checkout (`/*`, `!/*/`, `/pstack/`); `git sparse-checkout add <dir>` before a new top-level dir, never disable it.
- The user runs installs and harness tests.
- Push, and fast-forward `main` to `t3-orchestration`, only with the user's OK. Edit on `t3-orchestration`.

## Layout

| Path | Purpose |
|---|---|
| this worktree (`t3-orchestration`) | PStack source |
| `/cave/t3code` | T3 fork source, read-only |
| `/cave/Wisdio` (`develop1-engine`) | normal Wisdio work, no PStack |
| `/cave/Wisdio-pstack` (`pstack-test`) | test bench: Wisdio + PStack links in `.agents/skills` (Codex, OpenCode, Pi) and `.claude/skills`. PStack never mentions Wisdio in its own docs or skills. |
| Mac `~/.local/share/pstack/` | the user's clone of `main`, user-level install per the README |
| Mac `~/coding/Wisdio` / `~/coding/Wisdio-pstack` | normal work / Mac test bench (no links; the user-level install covers it) |

## Routine

Scripts are in `pstack/skills/setup-pstack/scripts/`.

1. Edit skills here.
2. Added, renamed, or removed a skill → `pstack_link.py --project /cave/Wisdio-pstack --harness codex --harness opencode --harness claude --apply`. Text edits need nothing.
3. Test from a T3 thread in `/cave/Wisdio-pstack`; start new sessions after edits (OpenCode caches skills).
4. After a test → `bench_check.py --project /cave/Wisdio-pstack --base develop1-engine [--reset]`. Reset can't undo effects outside the checkout (databases, servers, pushes).
5. Broken → `pstack_doctor.py --project /cave/Wisdio-pstack` first; read other projects' runs with `audit-rollout.py`.
6. Commit here; log results in `pstack/develop-log/`.

Update the bench: `git -C /cave/Wisdio-pstack merge develop1-engine`.

## Two machines

- The Mac is the new-user test: the user installs and updates PStack there by hand (`git pull`, rerun `npx skills add`, `npx skills remove -g -s <name> -y` for removed skills). Agents don't install, link, or configure PStack there.
- The pool is per machine: the user runs `/setup-pstack` on the Mac. Never copy `models.json`.
- Wisdio syncs only through commits on GitHub `develop1-engine`. To move a generated skill (e.g. `.agents/skills/verify-<app>/`): commit it alone on the bench, cherry-pick onto `develop1-engine` in the normal checkout and push (never push `pstack-test`), pull and merge on the other machine, and only then reset the source bench.
- Before any Mac step, compare `git -C /cave/Wisdio rev-parse --short HEAD` with `ssh mac 'git -C ~/coding/Wisdio rev-parse --short HEAD'`. Ask before committing or discarding Mac changes.
- Mac git over SSH: add `-c url.git@github-wisdio:.insteadOf=git@github.com:` to each call (zsh: write it out, not via a variable); don't change the remote.

## Tools

- `model_policy.py`: validate / ready / resolve / list / propose / convert the pool. Read-only.
- `pstack_doctor.py`: drift between source and a linked project. Read-only; exit 1 on `stale`.
- `pstack_link.py`: skill links + managed `.git/info/exclude` block. Dry run unless `--apply`.
- `bench_check.py`: what a test left on the bench; `--reset` asks, then `reset --hard` + `clean -fd` (links survive).
- `harness_discovery.py`: which skills Codex, Claude Code, and Pi offered their model in the newest session (OpenCode logs none).
- `pstack/tools/audit-rollout.py`: which model and effort actually ran in Codex/OpenCode/Pi sessions, matched to the pool.
- Tests: `for t in test_model_policy test_pstack_doctor test_pstack_link test_harness_discovery test_bench_check; do python3 pstack/skills/setup-pstack/scripts/$t.py; done` (78 pass), plus `bun test` in `pstack/skills/poteto-mode/scripts` (52 pass).

## State

Verified:
- Every pool model answered a delegated call. `swarm` passed and `interrogate` returned a three-reviewer verdict in real T3 runs. A delegated Pi call (MiMo 2.6 Pro) and a Codex Luna review ran on 2026-09-27.
- Pi reads `~/.agents/skills` (no `-a pi` needed), honors `disable-model-invocation`, starts skills with `/skill:<name>`, uses the `thinking` option, and logs to `~/.pi/agent/sessions`.
- Cursor-only parts are gone (`make-bot-ui`, `automations/benny`, Cursor frontmatter, `/goal`, the Cursor Origin forge; PRs go through `gh`). Programs keep their objective in `goal.md`. `poteto-mode` "Clean up what you start" requires deleting schedules, stopping children, and linking PRs.
- README and guide describe the T3 requirement, Pi, the T3 feature table, and a new-user smoke test (`01-setup.md` "Test your setup").

Not verified:
- Most workflows end to end, and each harness as the main chat (Pi not at all).
- Whether each harness obeys the native-subagent override, and whether Codex/OpenCode respect manual-only workflows.
- Plan-mode enforcement and MCP retention per provider.
- Open decisions (user): `orchestrate`'s frontier needs Graphite (`gt`, also in `orch.ts`) while other playbooks say never require it; Babysit's triage keys on Cursor's Bugbot (`watch-pr/policy.ts`); `opening-a-pr` makes a delegated PR opener always run `interrogate`.
- No Pi pool entry yet. The doctor doesn't compare `pstack-generated-by` stamps.
- Claude Code with Haiku 4.5 as main model truncates the skill list (~8,000 characters); larger models showed all descriptions.

## Next

1. The user runs "Test your setup" in each harness.
2. First real Wisdio task: `/create-verification-skill` in `/cave/Wisdio-pstack` for a macOS verification skeleton, then prove it on one feature.
3. Later: shorten skill descriptions if Haiku runs the main chat; evals to pick models per task.

## Safety

Remove links with `rm <link>` (no trailing slash) or `pstack_link.py`. `rm -rf <link>/` deletes the source.
