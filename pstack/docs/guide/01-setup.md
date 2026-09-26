# Install and set up PStack

This page covers linking PStack into a project, choosing a shared model pool, and running a first task. PStack runs inside T3 Code with Codex, Claude Code, or OpenCode.

## Why the setup looks like this

PStack isn't finished when you install it. You keep bending it until it fits how you work. Three decisions follow from that.

**Skills are symlinks.** Every project points back at one PStack checkout. Change a skill there and the next session in every linked project runs the new text. There's nothing to reinstall and no stale copy hiding in some repo. The catch: a link is untracked, so it shows up on every branch of that checkout. To try a PStack change in isolation, use a separate worktree; a branch won't isolate it.

**The model pool is yours, not the project's.** `~/.config/pstack/models.json` records which models your T3 Code can run and which ones you're willing to pay for. Those are facts about you, and they don't change from repo to repo. One file means one setup covers Codex, Claude Code, and OpenCode everywhere, and no model choice ever lands in a project's git history. Per-project pools would each need re-checking whenever a provider renames a model or you move one to the `escalation` tier.

**Anything a skill writes will drift.** Links follow the source; files don't. The main one is the `verify-<app>` skill from `/create-verification-skill`. It's committed to the project and describes the app as it was on the day it was generated. Older PStack versions also left lock files, `AGENTS.md` pointers, and `.cursor/skills` output behind. Run `pstack_doctor.py` to name them, then fix by case:

| What drifted | Doctor finding | Fix |
|---|---|---|
| Links missing, dangling, pointing into another checkout, or shadowed by a real copy | `unlinked-skill`, `dangling-link`, `foreign-source`, `shadowing-copy` | `pstack_link.py --apply` (re-link from the right checkout for `foreign-source`; inspect a copy before replacing it) |
| Links showing as untracked files | `unignored-links` | `pstack_link.py --apply` |
| `skills-lock.json` pinning PStack hashes, or an instruction line pointing at a removed skill | `lock-pins-live-source`, `dangling-reference` | Delete the entry or line by hand |
| A verification skill still under `.cursor/skills` | `cursor-era-skill` | Move it to `.agents/skills` and link it into `.claude/skills` |
| `verify-<app>`'s feature map no longer matches the app | none; the doctor can't see app behavior | [`/maintain-verification-skill`](../../skills/maintain-verification-skill/SKILL.md) |

The generator stamps its output with `metadata.pstack-generated-by: create-verification-skill@1`. The doctor doesn't compare that stamp yet, so it can't tell you a verification skill predates the current generator. You'll have to check that yourself.

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

## How skills get invoked

The principle skills, `unslop`, `typescript-best-practices`, and `setup-pstack` may trigger on their own. The 21 workflow skills run only when you ask for them by name, or when a workflow you started routes to one (`/poteto-mode` calling `/how`, for example). Claude Code enforces this through `disable-model-invocation: true`, so there a workflow starts only when you type `/name`. Codex and OpenCode ignore that field, so each workflow's description opens with the same rule as an instruction to the model. That is a request, not a lock: if a model starts a workflow you didn't ask for, stop it and report it. Start one by name: `/name` in Claude Code, `$name` in Codex, or ask the OpenCode agent to use the skill.

## Pick your models

Invoke [`setup-pstack`](../../skills/setup-pstack/SKILL.md) from a T3 Code thread. It reads the thread's `orchestrator_capabilities`: which providers can run child tasks, which models each advertises, and which option values the orchestrator accepts. It shows the exact descriptors, defaults, and advertised choices. List order has no strength meaning; setup recommends a strongest reasoning value only when the descriptor's own semantics or current provider evidence establishes one, and otherwise asks. It saves only the values you confirm.

> **How workflows use the pool.** Every workflow that spawns agents uses T3's tools per [`t3-delegation.md`](../../skills/setup-pstack/references/t3-delegation.md): `default`-tier pool entries normally, `escalation`-tier entries only for genuinely hard work. `delegate_task` children share the parent's checkout; parallel writers get their own worktree through `t3_thread_launch`.

Setup saves one shared pool at `~/.config/pstack/models.json`, and one setup covers every harness. Each entry has a unique `id`, a `providerInstanceId`, a model, its confirmed options, and an optional `tier` (`default` or `escalation`). Keep at least one `default` entry for routine work; setup asks which others are expensive enough to reserve for hard tasks. There are no per-role tables and no required cost, concurrency, or retry settings. Setup does not raise `serviceTier`, `fastMode`, or other non-reasoning options on its own and does not change your main chat model. Reasoning options differ per provider (Codex `reasoningEffort`, OpenCode `variant`, Claude `effort`), so a level never carries from one model to another. T3's Claude adapter can also remap some effort values, so check what actually ran.

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
