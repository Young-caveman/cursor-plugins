# PStack handoff

Current state and rules for working on PStack as of 2026-09-26. History, research, and test results live in `pstack/develop-log/` (newest file first). The user's latest instructions take precedence.

## Goal

Turn PStack (originally for Cursor) into the user's personal skill set for Codex, OpenCode, and Claude Code, all run under T3 Code. T3's `orchestrator_capabilities` (what can run) and `delegate_task` (run it) are the contract. OSes: macOS, Omarchy/Arch.

## T3 target

PStack targets the user's T3 Code fork, branch `yash/swiftui-orchestrator-v2-support` (remote `origin` `Young-caveman/t3code`; upstream is `pingdotgg/t3code`). The fork keeps release version `0.0.42` but replaces the orchestrator with V2, so the version number does not identify the code. Sources: `/cave/t3code` on Omarchy, `/Users/jimmy/coding/t3code` on the Mac. `docs/operations/custom-fork-host-setup.md` there records the revision each host was built from and the SSH bootstrap.

Check T3 behavior against that checkout, not against memory, upstream `main`, or a tool description. Read:

- `docs/orchestration-v2/orchestrator-mcp-server.md`, `apps/server/src/mcp/toolkits/*/tools.ts`, `packages/contracts/src/orchestratorMcp.ts`: the tools skills call.
- `apps/server/src/provider/T3OrchestrationInstructions.ts`: what T3 tells every agent about delegation.
- `docs/internals/remote.md`: environments.

Verified from that source on 2026-09-27:

- One T3 server is one environment. A project and its threads belong to one environment, and `remote.md` says repository identity "never routes work between" environments. The `t3-code` MCP endpoint is `127.0.0.1:<port>/mcp` on that server, with a token scoped to the environment, parent thread, and provider session. No orchestrator or thread tool takes an environment or machine argument (`orchestratorMcp.ts` has no such field).
- So `delegate_task`, `t3_thread_launch`, and `create_threads` run only where the calling thread's server runs. From an Omarchy thread they cannot start work on the Mac, and PStack skills must not assume they can.
- The Mac is reachable as its own environment (SSH from the desktop app). Work for it goes through a thread the user opens there, or through a project's own out-of-band handoff (Wisdio's `t3-thread-handoff` skill tunnels to the Mac server and sends to an existing thread; it needs the user's explicit request and gives no completion notice).
- Not yet tested against the live Mac: opening a Mac thread while the Omarchy app is the client, and whether `t3_thread_list` or `t3_project_list` ever show Mac state. Treat "unreachable from here" as the working assumption until a run shows otherwise.

## Rules

- A surface that only a different machine can drive is `verified-unreachable` from this one, stated as such in the generated verification skill. Never claim it was verified, and never fake a delegation to it.
- Models live in one v2 pool, `~/.config/pstack/models.json`: `providerInstanceId` + model + confirmed options + optional `tier`. Anything outside the pool needs the user's explicit authorization.
- Cost: the pool holds only cheap `default`-tier entries (Luna max, DeepSeek, MiMo, Sonnet 5). The user removed Opus 5.5 on 2026-09-27, so there is no `escalation` entry; a harder model needs the user's explicit authorization per task.
- Never silently substitute a model or raise reasoning effort. Effort levels don't carry across models.
- Invocation: principle skills, `unslop`, `typescript-best-practices`, and `setup-pstack` may auto-trigger; the 21 workflow skills keep `disable-model-invocation: true` (Claude-only field).
- PStack writes nothing tracked into a user project: no lock files, no `.gitignore` entries, no pointer lines in the project's `AGENTS.md`.
- Anything checkable by reading files is a script, not manual inspection. Scripts prove state; only a harness run proves behavior.
- Spawned agents follow `setup-pstack/references/t3-delegation.md`: `delegate_task` takes `target`, `mode`, and `clientRequestId` and shares the parent's checkout; parallel writers get `t3_thread_launch` worktrees with `modelSelection`, not those delegate fields. Briefs stand alone.
- Keep skill text short. Current models over-follow ceremony (forced todos, always-test, stop-for-review).
- Keep work under `pstack/`. This repo is sparse-checkout (`/*`, `!/*/`, `/pstack/`). Run `git sparse-checkout add <dir>` before creating a new top-level dir; never disable sparse-checkout.
- The user runs installs and harness tests. Prefer free OpenCode models (Muse Spark 1.3 Free) for tests and delegated research.

## Layout

| Path | Purpose |
|---|---|
| this worktree (`t3-orchestration`) | PStack source; edit skills here |
| `/cave/t3code` (`yash/swiftui-orchestrator-v2-support`) | T3 fork source; read-only reference for T3 behavior, never edited from PStack work |
| `/cave/Wisdio` (`develop1-engine`) | normal Wisdio work; no PStack |
| Mac `~/coding/Wisdio` (`develop1-engine`, via `ssh mac`) | normal Wisdio work on the Mac; no PStack |
| Mac `~/coding/Wisdio-pstack` (`pstack-test`) | Mac test bench: worktree of the Mac's Wisdio, linked to the installed copy below |
| Mac `~/.local/share/pstack/` | installed PStack: sparse clone of `origin` `main` (`pstack/` only), updated by `git pull`, never edited (see [Two machines](#two-machines)) |
| `/cave/Wisdio-pstack` (`pstack-test`) | **test bench only** — Wisdio + PStack links in `.agents/skills` (Codex, OpenCode) and `.claude/skills` (Claude Code). Wisdio here is just the app under test; PStack stays project-agnostic and never mentions Wisdio in its own docs or skills. |

## Routine

Scripts are in `pstack/skills/setup-pstack/scripts/`.

1. Edit skills here.
2. Added, renamed, or removed a skill → `pstack_link.py --project /cave/Wisdio-pstack --harness codex --harness opencode --harness claude --apply`. Text edits need nothing.
3. Test from a T3 thread in `/cave/Wisdio-pstack`. OpenCode caches skills: start a new session after edits.
4. After a test → `bench_check.py --project /cave/Wisdio-pstack --base develop1-engine` lists what the run left; add `--reset` to discard it (asks first, keeps the links). Git can't undo effects outside the checkout.
5. Something looks broken → run `pstack_doctor.py --project /cave/Wisdio-pstack` first. Threads in another T3 project can't be read via `t3_thread_read`; read harness logs with `audit-rollout.py`.
6. Commit here; log results in `pstack/develop-log/`.

Update the test copy: `git -C /cave/Wisdio-pstack merge develop1-engine`.

## Two machines

The Mac has an installed PStack but no PStack source: edit PStack only here. Wisdio stays in sync only through commits on GitHub `develop1-engine`; uncommitted work and each machine's local `pstack-test` branch never travel. Mac checked 2026-09-27 in a Mac thread: environment, skills, links, and doctor correct; a Claude delegation failed on login.

- **Update the Mac install:** commit here, fast-forward `main` to `t3-orchestration`, push both (needs the user's OK), then `ssh mac 'git -C ~/.local/share/pstack pull -q'`. It clones over HTTPS (the fork is public), so no Mac key is needed. Text edits need nothing more. Added, renamed, or removed a skill: run `pstack_link.py` there too (next item). OpenCode caches skills: new session after an update.
- **Mac bench links:** `ssh mac 'python3 ~/.local/share/pstack/pstack/skills/setup-pstack/scripts/pstack_link.py --project ~/coding/Wisdio-pstack --harness codex --harness opencode --harness claude --apply'`. Doctor and `bench_check.py` run the same way from that scripts folder. The scripts must keep working on the Mac's Python 3.9.6.
- **Pool:** per machine. Run `/setup-pstack` in a thread on each machine; its provider probe leaves out what that machine can't run (the Mac's Claude is not logged in as of 2026-09-27). The Mac's current file is a copy of this one, awaiting that rerun.
- **PStack links never travel through git:** `pstack_link.py` excludes each link by exact name in `.git/info/exclude`. A skill PStack *generates* (for example `.agents/skills/verify-<app>/` plus its `.claude/skills` relative link) is a real directory, so git tracks it like any Wisdio file.
- **Sending a generated skill to the other machine:**
  1. Commit it on the bench (`pstack-test`), in a commit that holds only the skill.
  2. Cherry-pick it onto `develop1-engine` in the normal checkout (`/cave/Wisdio` or Mac `~/coding/Wisdio`) and push. Never push `pstack-test`.
  3. On the other machine, pull `develop1-engine` into the normal checkout, then `git merge develop1-engine` in its bench.
  4. Only then reset the source bench: a reset before step 2 destroys the skill.
- **Before any Mac step**, check both sides are at the same commit: `git -C /cave/Wisdio rev-parse --short HEAD` and `ssh mac 'git -C ~/coding/Wisdio rev-parse --short HEAD'`. If the Mac has uncommitted changes, ask the user before committing or discarding them.
- **Mac git over non-interactive SSH:** its `origin` (`git@github.com`) fails there with `Permission denied (publickey)`, because the key agent only exists in the user's own terminal. Add `-c url.git@github-wisdio:.insteadOf=git@github.com:` to each `git` call instead, and don't change the remote. The Mac shell is zsh, so write the flag out; a variable holding it won't split into words.
- **Mac agents are started by the user**, or through Wisdio's `t3-thread-handoff` (see [T3 target](#t3-target)). Agents here cannot delegate there.

## Tools

- `model_policy.py` — validate / ready / resolve / list / propose / convert the pool. Read-only.
- `pstack_doctor.py` — reports drift between the source and a project. Read-only; exit 1 on `stale`.
- `pstack_link.py` — reconciles skill links and a managed `.git/info/exclude` block. Dry run unless `--apply`.
- `bench_check.py --project <bench> --base <branch> [--reset]` — commits, uncommitted files, and PStack drift on a test bench; `--reset` confirms, then `reset --hard` + `clean -fd` (no `-x`, so links survive).
- `harness_discovery.py --project <repo>` — which skills Codex and Claude Code actually offered their model in the newest session there (from their logs). OpenCode records none; ask the model.
- `pstack/tools/audit-rollout.py` — reads Codex/OpenCode session logs and reports which model and effort actually ran.
- Tests: `for t in test_model_policy test_pstack_doctor test_pstack_link test_harness_discovery test_bench_check; do python3 pstack/skills/setup-pstack/scripts/$t.py; done`

## State and gaps

- Discovery works in all three harnesses; the model pool is saved and every model in it answered a delegated call.
- All workflows are migrated to T3 delegation (`38550b1`). Onboarding and stale references were repaired in `178a2d7`; the review follow-up in `bc5bb53` corrected launch arguments, added skill-authoring fallback, and tightened pool/reviewer/verification behavior. The three-reviewer `/interrogate` verdict is recorded in `pstack/develop-log/2026-09-26T120832Z-progress.md`.
- State checks on 2026-09-27: 75 script tests passed (50 model policy, 13 doctor, 6 link, 3 discovery, 3 bench); pool validation, Wisdio-pstack doctor and bench check, and `git diff --check` passed. These checks do not prove workflow behavior.
- Real T3 runs so far: `swarm` passed; `interrogate` ran and returned a three-reviewer verdict. The remaining workflows have not been exercised end to end in the harnesses.
- A pool with no `default` entry now fails validation. Before each delegated call, resolve the chosen entry against live T3 capabilities; structural validation alone does not establish availability.
- Skill authoring uses `skill-creator` when installed and direct `SKILL.md` authoring otherwise. Do not assume OpenCode has that skill.
- Workflows are manual-only everywhere (user decision 2026-09-27): each of the 21 workflow descriptions opens "Run only when the user asks for this skill by name or a workflow the user started routes here." Claude Code enforces it via `disable-model-invocation: true`; in Codex and OpenCode it is an instruction only, not yet tested in a harness. `automate-me` writes the same rule into generated mode skills.
- Claude Code's skill-listing budget scales with the main model's context: Haiku 4.5 sessions cut the list at ~8,000 characters (23 of 25 PStack skills lost their descriptions), while Sonnet 5 and Opus 5.5 sessions kept all 52 descriptions (21,754 characters). Shortening only matters for small-context main models.
- Plan mode's read-only enforcement and whether it keeps MCP servers are unverified per provider; `why` and `reflect` avoid plan mode for that reason. User decision 2026-09-27: leave as is for now, deal with it later.
- `make-bot-ui` targets a Grok Bot webhook on `cursor.sh`; left as is.
- T3's Claude adapter silently remaps some effort values (`effortMap`). Warn the user; don't build a remap table.
- `pstack/docs/guide/01-setup.md` opens with "Why the setup looks like this": symlinks, the user-level pool, and the artifact-drift table. The doctor does not yet compare `pstack-generated-by` stamps.
- `main` was fast-forwarded to `t3-orchestration` and pushed on 2026-09-27; keep editing on `t3-orchestration`.

## Next

1. First real Wisdio task: run `/create-verification-skill` in `/cave/Wisdio-pstack` for a macOS verification skeleton, then prove its generated instructions on one feature. This is still pending; the user runs harness tests.
2. Low priority: shorten skill descriptions, only needed if a small-context model (Haiku 4.5) runs the main Claude chat.
3. Later: evals and audits to pick models per task (user's plan; not now).

## Safety

Remove links with `rm <link>` without a trailing slash, or with `pstack_link.py`. `rm -rf <link>/` deletes the source.
