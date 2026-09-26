# Install and set up PStack

This page covers linking PStack into a project, choosing a shared model pool, and running a first task. PStack runs inside T3 Code with Codex, Claude Code, or OpenCode.

## Why it's built this way

No shoe fits every foot, so PStack ships as a workbench, not a monument. Three choices fall out of that:

**Symlinks, not copies.** A copy is a fossil: it goes stale the second the source improves. A symlink means an edit to a skill is live in your project on the next turn — change it, run it against real work, keep what fits. You don't install PStack so much as tune it.

**One pool in your home directory.** The models are what *your* T3 account can run — the same fact in every repo — so the pool lives in `~/.config/pstack/models.json`, not in your project. A per-project copy would just be another fossil.

**Snapshots are the exception.** When a skill *writes* into your project — a generated `verify-<app>` skill is the big one — that file is a snapshot and it will drift. The doctor names what drifted; `/maintain-verification-skill` brings it back. Details under [What counts as drift](#what-counts-as-drift).

## Link the skills into your project

Skills are symlinks to this checkout, so a text edit to a skill is live. From the `pstack` directory, preview and then apply:

```bash
python3 skills/setup-pstack/scripts/pstack_link.py --project /path/to/repo --harness codex --harness opencode --harness claude
python3 skills/setup-pstack/scripts/pstack_link.py --project /path/to/repo --harness codex --harness opencode --harness claude --apply
```

Pass only the `--harness` flags you use. Each harness reads its own directory:

- Codex reads `.agents/skills`.
- Claude Code reads only `.claude/skills`, not `.agents/`.
- OpenCode reads both and de-duplicates by name.

The links stay out of git through a managed block in the repo's `.git/info/exclude`. PStack writes no lock file, no `.gitignore` entry, and no line in your project's `AGENTS.md`. Real directories are never touched.

Rerun the command whenever you add, rename, or remove a skill. Text edits need no relinking: Claude Code and Codex see them live, while OpenCode caches skills, so start a new session after an edit. `pstack_link.py` handles project installs; global installation is not covered by this script.

Check the result any time:

```bash
python3 skills/setup-pstack/scripts/pstack_doctor.py --project /path/to/repo
python3 skills/setup-pstack/scripts/harness_discovery.py --project /path/to/repo
```

`pstack_doctor.py` is a read-only report of drift between the source and the project. `harness_discovery.py` reads the newest Codex and Claude Code session logs for the project and lists which skills each harness actually offered its model; OpenCode records no such list, so ask the model there.

## What counts as drift

Skill *text* is always current — the links are symlinks, so an edit to the source is the edit in your project. What can go stale is anything a skill *writes into* the project: a generated `verify-<app>` skill, a leftover lock file, a link to a deleted skill, a real directory shadowing a link. Those are snapshots; the source moved on and they didn't.

`pstack_doctor.py` names each one (`dangling-link`, `shadowing-copy`, `cursor-era-skill`, `lock-pins-live-source`, `unlinked-skill`, and friends). Fix links with `pstack_link.py --apply`; refresh a drifted verify skill with `/maintain-verification-skill`; delete other leftovers by hand once the doctor names them. The doctor can see that a snapshot mismatches the source, but it cannot yet tell *how old* a generated artifact is — version stamps for that are not built. Until then, regenerate instead of trusting an old copy.

## How skills get invoked

The principle skills, `unslop`, `typescript-best-practices`, and `setup-pstack` may trigger on their own. The 21 workflow skills carry `disable-model-invocation: true`. Only Claude Code honours that field, so there they run only when you type `/name`. Codex and OpenCode ignore it, so select a workflow by name (`$poteto-mode` in Codex; ask the OpenCode agent to use the skill).

## Pick your models

Invoke [`setup-pstack`](../../skills/setup-pstack/SKILL.md) from a T3 Code thread. It reads the thread's `orchestrator_capabilities`: which providers can run child tasks, which models each advertises, and which option values the orchestrator accepts. It shows the exact descriptors, defaults, and advertised choices. List order has no strength meaning; setup recommends a strongest reasoning value only when the descriptor's own semantics or current provider evidence establishes one, and otherwise asks. It saves only the values you confirm.

> **How workflows use the pool.** Every workflow that spawns agents uses T3's tools per [`t3-delegation.md`](../../skills/setup-pstack/references/t3-delegation.md): `default`-tier pool entries normally, `escalation`-tier entries only for genuinely hard work. `delegate_task` children share the parent's checkout; parallel writers get their own worktree through `t3_thread_launch`.

Setup saves one shared pool at `~/.config/pstack/models.json`, and one setup covers every harness. Home, not project, because the models are what your T3 account can run — the same fact in every repo — and a per-project copy would fossilize the moment your account changes. Each entry has a unique `id`, a `providerInstanceId`, a model, its confirmed options, and an optional `tier` (`default` or `escalation`). Keep at least one `default` entry for routine work; setup asks which others are expensive enough to reserve for hard tasks. There are no per-role tables and no required cost, concurrency, or retry settings. Setup does not raise `serviceTier`, `fastMode`, or other non-reasoning options on its own and does not change your main chat model. Reasoning options differ per provider (Codex `reasoningEffort`, OpenCode `variant`, Claude `effort`), so a level never carries from one model to another. T3's Claude adapter can also remap some effort values, so check what actually ran.

You can inspect the pool with `python3 skills/setup-pstack/scripts/model_policy.py validate`, `list`, and `ready --snapshot <capabilities.json>`. `validate` checks structure and requires at least one `default` entry; `ready` checks advertised availability against a saved capabilities snapshot. Before each delegated call, resolve the entry against live capabilities. Only a successful delegated run proves the target works.

The pool is the model-setup contract: a task may use one entry or several. Reviewing and diagnosing prefer entries from different providers, since differently trained models miss different things. Producing one result prefers one strong entry, and judges check evidence rather than opinions. A model outside the pool needs your explicit authorization for that task; a one-off target is never added to the pool automatically. PStack does not enforce spending limits.

If you already have a version 1 role policy, setup leaves the file untouched and shows a reviewed conversion (`model_policy.py convert`). Old per-role restrictions do not become blanket pool authorization; only entries you confirm are carried over.

## A verification skill is a separate choice

`setup-pstack` configures models only. If you want a scripted way to prove app behavior, invoke [`/create-verification-skill`](../../skills/create-verification-skill/SKILL.md) yourself; [Verify and ship](./06-verify-and-ship.md#create-a-project-verification-skill) covers when it earns its place.

## Run your first task

Pick something real but small, and describe it the way you'd describe it to a colleague:

```text
Use poteto-mode: add a --json flag to this command. Text output stays byte-identical. Verify both.
```

`poteto-mode` refuses to start until `model_policy.py validate` passes, so run `setup-pstack` first. It resolves a chosen pool entry against live capabilities before delegation.

Watch the todo list. Its first items are the matched playbook's steps copied in, the Feature playbook for this prompt. If poteto-mode skips a step, the step stays in the list with `skip: <reason>`, so you can see what it chose not to do.

From here you can type normal follow-ups. Poteto mode stays on for the conversation until you opt out by saying so.

Next: [Route work through `/poteto-mode`](./02-poteto-mode.md).
