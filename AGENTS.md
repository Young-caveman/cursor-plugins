# Project handoff

Handoff plan for PStack. Keep it current when project work changes. The user's latest instructions take precedence. Last revised 2026-09-26.

## 1. Goal

Turn PStack (originally written for Cursor) into the user's personal engineering skill set for driving **Codex, OpenCode, and Claude Code under T3 Code**. Cursor-specific setup is being removed. Primary OSes: macOS and Omarchy/Arch Linux.

T3 Code is the outer session/worktree environment, not a peer harness. Its contract:

- `orchestrator_capabilities` — which providers can run child tasks, their models, and legal option values.
- `delegate_task` — run work on a resolved target (`providerInstanceId` + `model` + `options`).

## 2. Decisions

- Model choices live in one user-owned v2 **pool** at `~/.config/pstack/models.json`: entries of `providerInstanceId` + model + confirmed option values, shared across roles. A target outside the pool needs the user's explicit authorization for that task.
- Never silently substitute a model or raise reasoning effort. Effort levels are not comparable across models or providers (confirmed by both Anthropic and OpenAI, see section 6).
- One shared skill source tree. Harness-specific install and model config live at each harness boundary.
- The user performs real installs and harness tests. Prefer a free OpenCode model (Muse Spark 1.3 Free) for manual tests and delegated research.
- Keep working files under `pstack/`. This repo is cone-mode sparse-checkout (`/*`, `!/*/`, `/pstack/`); T3 checkpoints run `git add -A -- .`, which fails for paths outside the cone. Use `git sparse-checkout add <dir>` before writing a new top-level directory. Do not disable sparse-checkout.
- **PStack never writes a tracked file in a user project unless a skill's explicit purpose is to generate one** (see 4.3).

## 3. Current state

### 3.1 Done — model setup (v2 pool)

`skills/setup-pstack/scripts/model_policy.py` — `validate`, `ready`, `resolve`, `propose`, `convert`. Read-only; the agent, not the script, writes `models.json`. v1 policies and `--harness` are refused with a migration message. `propose` ranks nothing.

### 3.2 Done — project tooling

In `skills/setup-pstack/scripts/`, standard library only:

- `pstack_doctor.py --project <repo>` — read-only drift check between the source and one project (see 4.2). Exit 1 on any `stale` finding.
- `pstack_link.py --project <repo> --harness codex|opencode|claude … [--apply]` — reconciles links: links every source skill into the chosen harness dirs, unlinks PStack links for removed skills or deselected harnesses, never touches real directories, and keeps the links out of git with a managed block in the clone's `info/exclude`. Dry run by default. After `--apply`, the doctor reports no drift.

Principle: anything checkable by reading files is a script, not an agent reading files by hand. Scripts prove *state*; only a real harness run proves *behavior*.

Tests (46 + 13 + 6): `for t in test_model_policy test_pstack_doctor test_pstack_link; do python3 pstack/skills/setup-pstack/scripts/$t.py; done`. No harness has run a PStack skill yet.

### 3.3 Not done

- **Role workflows** (`poteto-mode`, `arena`, `swarm`, `interrogate`, and skills that name roles) still call the removed `ready --harness` and stop at a migration diagnostic. Intentional staging. Do not claim they work.
- **Cursor-era paths remain in skill text.** `create-verification-skill` / `maintain-verification-skill` write and read `.cursor/skills/verify-*` — no current harness discovers that path. `recall`, `reflect`, `show-me-your-work`, `automate-me`, and `poteto-mode/playbooks/session-pickup.md` read `~/.cursor/projects/*/agent-transcripts`. All need a harness-neutral rewrite.
- **Claude Code install** (section 5).

### 3.4 Branch state

Everything above is committed on `t3-orchestration`, not yet merged to `main`. `main` still ships v1 skill text; Wisdio's links point at this worktree, not `main`.

## 4. Testing in Wisdio, and artifact lag

### 4.1 Topology (as of 2026-09-26)

PStack is isolated by **directory**, not branch: git branches cannot isolate untracked files, so links in a checkout are live on every branch of it.

| Path | Branch | PStack |
|---|---|---|
| `/cave/Wisdio` | `develop1-engine` | none — the user's normal project checkout |
| `/cave/Wisdio-pstack` | `pstack-test` (from `develop1-engine` at `eb9bc32`) | 47 links in `.agents/skills` (Codex, OpenCode) and 47 in `.claude/skills` (Claude Code) |

- Links point at this worktree's `pstack/skills/<skill>` by absolute path, so source edits are live there immediately.
- Links are kept out of git by a managed block in `/cave/Wisdio/.git/info/exclude` (shared by both worktrees; its patterns match nothing in `/cave/Wisdio`). No `.gitignore` entries and no `skills-lock.json` entries for PStack.
- Relink after adding, renaming, or removing a skill: `pstack_link.py --project /cave/Wisdio-pstack --harness codex --harness opencode --harness claude --apply`. Check with `pstack_doctor.py --project /cave/Wisdio-pstack`.
- Retired 2026-09-26: local branches `pstack-codex` (was `bedb046`) and `pstack-opencode` (was `5ac7731`), never pushed; recoverable from reflog for a while. Wisdio `eb9bc32` removed the stale `simplified-pstack-router` pointer from `AGENTS.md`.
- `~/.config/pstack/models.json` does not exist yet.

### 4.2 The problem and the fix

Skill text is live through the symlinks; everything PStack *left behind* is a snapshot. After a source change the project runs new skill text against old artifacts, and nothing looks stale. Observed instances:

| Artifact | Drift observed | Doctor finding |
|---|---|---|
| Instruction-file pointer | Wisdio `AGENTS.md` told agents to read `.agents/skills/simplified-pstack-router`, deleted in `cb1132f`. Fixed in `eb9bc32`. | `dangling-reference` |
| `skills-lock.json` | 47 `computedHash` values on the retired `pstack-*` branches, wrong after any source edit | `lock-pins-live-source` |
| Links | new skill never linked; renamed skill leaves a dangling link; link into a different worktree; a copied dir shadowing a link | `unlinked-skill`, `dangling-link`, `foreign-source`, `shadowing-copy` |
| Ignore rules | committed `.gitignore` on the retired test branches only | `unignored-links` |
| Generated skills | `create-verification-skill` output under `.cursor/skills` | `cursor-era-skill` |
| Model pool | v1 policy against v2 skills | `policy-migration` |

The fix has three parts:

1. **Detect, don't trust.** Run `pstack_doctor.py --project /cave/Wisdio-pstack` after every source change and before concluding a skill is broken. Presence of an artifact is never evidence that it matches the current source.
2. **Stop producing derived artifacts.** Links need no lock. Link ignores live in `.git/info/exclude`, written by `pstack_link.py`. PStack must not add pointer lines to a project's `AGENTS.md`; keep it about the project, and let skills trigger from their own descriptions. (All three done for Wisdio.)
3. **Classify what remains.** *Derived* artifacts (links, excludes, the pool's validity) are regenerated or deleted, never hand-edited. *Owned* artifacts (a generated `verify-<app>` skill after project knowledge is added) are migrated by a maintain skill, never regenerated. Proposed next: generator skills declare an artifact version and stamp it in output frontmatter (`metadata.pstack-generated-by: <skill>@<n>`) so the doctor can flag owned artifacts older than their generator. Not built yet.

For a clean-slate test beyond `/cave/Wisdio-pstack`, create another throwaway worktree, link it with `pstack_link.py`, and point `--policy` at a scratch file. Its artifacts are born from current skills and discarded after.

### 4.3 Rollback

1. Code: normal git in Wisdio; never reaches this worktree.
2. Pool: `mv ~/.config/pstack/models.json{,.bak}` — outside git.
3. Links: `pstack_link.py` reconciles them; to remove by hand use `rm <link>` **without** a trailing slash, or `find … -type l -lname '*pstack/skills*' -delete`. `rm -rf <link>/` deletes this worktree's source (verified in a sandbox).
4. Whole test checkout: `git -C /cave/Wisdio worktree remove /cave/Wisdio-pstack` (links are symlinks; the source is not touched).

## 5. Harness facts (sources checked 2026-09-26)

Skill discovery, from official docs unless marked:

| | Codex | OpenCode | Claude Code |
|---|---|---|---|
| Project skills | `.agents/skills` (cwd up to repo root) | `.opencode/skills`, `.claude/skills`, `.agents/skills` | `.claude/skills` only — **not** `.agents/skills` |
| User skills | `~/.agents/skills` | `~/.config/opencode/skills`, `~/.claude/skills`, `~/.agents/skills` | `~/.claude/skills` |
| Symlinked skill dirs | followed | not documented | followed; one target loaded once |
| Edits picked up | auto-detected; restart if not | cached until restart (GitHub issues #34408/#8751, not docs) | live, `SKILL.md` text only; `/reload-skills` for a new top-level dir |
| Frontmatter | name, description, `metadata` | name, description, license, compatibility, metadata; others ignored | adds `disable-model-invocation`, `allowed-tools`, `effort`, `context`, … |
| Instructions | `AGENTS.md` chain, rebuilt each run, 32 KiB cap | `AGENTS.md`, else `CLAUDE.md`; `instructions` in `opencode.json` | `AGENTS.md` natively (≥ 2.1.277) when no `CLAUDE.md`/`CLAUDE.local.md` exists; setting `claude-md-and-agents-md` reads both; `@AGENTS.md` import. Explicitly **not read**: anything under `.agents/` |

Sources: developers.openai.com/codex/build-skills, /codex/agent-configuration/agents-md, /codex/config-file/config-advanced; opencode.ai/docs/skills, /docs/rules; code.claude.com/docs/en/skills (fetched directly), /docs/en/memory.

Consequences:

- Wisdio's current links are invisible to Claude Code. A Claude install needs `.claude/skills` links. OpenCode reads both `.agents/skills` and `.claude/skills`, so linking both may show OpenCode duplicate names; **untested**.
- OpenCode needs a restart after a skill edit; Claude and Codex do not. Rule out a stale session before diagnosing a skill.
- `disable-model-invocation` (used by many PStack skills) is honoured only by Claude Code.
- Claude Code plugins cache a copy and update only on a `version` bump or commit tracking. That brings artifact lag back, so keep symlinks for the dev loop.

### 5.1 Capability snapshot (this thread, 2026-09-26)

`orchestrator_capabilities` advertised runnable `codex`, `claudeAgent`, `opencode`; `cursor`, `grok`, `antigravity`, `pi` disabled.

- **Claude** (11 models): `effort` varies per model. Opus 5.5 / Fable 5.1 / Fable 5 default `medium`; Opus 5 / 4.8 / 4.6 / 4.5, Sonnet 5 / 4.6 default `high`; Opus 4.7 `xhigh`. `ultracode` on Opus 5.5, Fable 5.1, Fable 5, Opus 5, Opus 4.8 only; `promptInjectedValues: ["ultrathink"]`. Haiku 4.5 has boolean `thinking`, no `effort`. `fastMode` on Opus models only (not Fable, not Sonnet). `contextWindow` absent on Opus 4.8 / 4.7 / 4.5 and Haiku 4.5. Claude descriptors carry no `currentValue`; Codex and OpenCode do.
- **Codex**: GPT-6 Astra/Sol and GPT-5.6 Sol/Terra advertise `reasoningEffort` up to `ultra`; the OpenAI API model page for GPT-6 Astra lists only `low…max`. Treat `ultra` as a Codex-side value; the pool stores it only if advertised and user-confirmed.
- `test_model_policy.py`'s `claudeAgent` fixtures are still invented; re-derive them from this snapshot.

### 5.2 Claude `effortMap` risk

T3's Claude adapter remaps saved values after they leave PStack (`model-manifest.json` `effortMap`; observed: `opus-4-7` `xhigh → max`, `sonnet-4-6` `max → high`, `ultracode → xhigh`, `ultrathink → null`). `orchestrator_capabilities` does not expose this. Store the advertised value, warn the user that Claude may remap it, and do not build a remap table in PStack. Read the catalog from `raw.githubusercontent.com/pingdotgg/t3code/main/apps/server/src/provider/model-manifest.json`, not a local `/cave/t3code` copy (stale snapshot).

## 6. Vendor guidance that shapes skill text

Checked 2026-09-26. These inform how PStack skills are *written*; none of it becomes pool contents.

- **Shorter skills win.** OpenAI, "Rethinking skills and prompts for GPT-6 Astra" (developers.openai.com/blog, 2026-09-11): descriptions "as short as possible while making it clear when the model should use them"; "overly specific guidance can now hinder results"; mandatory testing or stop-for-review steps make Astra over-test or stop early. GPT-5.6 guide: leaner system prompts scored ~10–15% higher with 41–66% fewer tokens.
- **GPT-6 obeys skill files more literally.** The latest-model guide recommends auditing skills and AGENTS.md, and adding: user instructions take precedence over a skill; if a skill makes the model pause or diverge, name the SKILL.md and quote the instruction.
- **Anthropic, Opus 5.5** (claude.dev/blog, Addy Osmani, 2026-09-22 and 09-25; Thariq Shihipar 09-25): default `medium`; raise to `high` when medium stalls; `xhigh`/`max` only with a measured gain; do not carry a level across models; a retry costs more than token savings; delete "think carefully" lines; give the whole task with a named finish line.
- Implication for the rewrite: audit PStack's long, Cursor-era skill bodies for mandatory ceremony (forced todo lists, always-run-tests, stop-for-review gates) and cut what the current models already do on their own.

## 7. Next actions

Ordered. The user runs harness-side steps; the agent handles source changes.

1. **Discovery test per harness** in `/cave/Wisdio-pstack` (user runs; open it as a T3 project/thread): confirm Codex, OpenCode, and Claude Code each list PStack skills, and whether OpenCode shows duplicates from `.agents/skills` + `.claude/skills`. If it does, pick one of: drop `--harness claude` and link Claude through `~/.claude/skills` (global: every project sees PStack), or accept the duplicates. Decide after the test.
2. **User runs setup in each harness** and reports harness version, pool entry, model ID, effort, errors. Record in section 8. Run the doctor first.
3. **Re-derive `claudeAgent` test fixtures** from the 5.1 snapshot.
4. **Rewrite Cursor-era paths** (3.3) to harness-neutral ones; add artifact-version stamps to generator skills.
5. **Migrate the `poteto-mode` gate** to the v2 pool, then `arena` / `swarm` / `interrogate` — only after step 2 has a real result. Apply section 6 while touching each skill.

## 8. Test log

| Date | Harness | Skill | Pool entry | Model | Reasoning | Result |
|---|---|---|---|---|---|---|
| 2026-09-26 | T3 → OpenCode | (delegated research) | none (inherited policy n/a) | opencode/muse-spark-1.3-contributor-free | variant medium, agent plan | 2 web-research tasks completed; `delegate_task` cross-provider works |
| — | — | — | — | — | — | pending user setup run |

Keep harness-specific test artifacts out of the shared skill source unless the user asks to productize them.
