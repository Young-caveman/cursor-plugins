# Install and set up PStack

This page covers installing PStack, choosing a shared model pool, and running a first task. PStack runs inside T3 Code with Claude Code, Codex, OpenCode, or Pi. You need the T3 Code build named in the [README](../../README.md#requirements) (the orchestrator V2 fork, built from source), `git`, Node.js (for `npx`), and Python 3.9 or later.

## Install

```bash
git clone --depth 1 https://github.com/Young-caveman/cursor-plugins ~/.local/share/pstack
DO_NOT_TRACK=1 npx skills add ~/.local/share/pstack/pstack -g -a claude-code -a codex -a opencode -s '*' -y
```

The first line downloads PStack. The second uses the [`skills`](https://github.com/vercel-labs/skills) installer to copy all 46 skills into `~/.agents/skills`, which Codex, OpenCode, and Pi read, and to link each one from `~/.claude/skills` for Claude Code. Every project on this machine now sees them. Drop the `-a` flags for harnesses you don't use. `DO_NOT_TRACK=1` turns off the installer's usage reporting.

Check it worked: open a new T3 thread in any project and ask the agent which PStack skills it can see. It should name `poteto-mode` and `setup-pstack` among them.

**Updating.** Pull the clone and rerun the installer:

```bash
git -C ~/.local/share/pstack pull
DO_NOT_TRACK=1 npx skills add ~/.local/share/pstack/pstack -g -a claude-code -a codex -a opencode -s '*' -y
```

Then start new sessions; OpenCode caches skills until you do. A skill PStack removed stays installed until you run `npx skills remove -g -s <name> -y`.

**Your own skills.** The installed skills are copies, and the next update overwrites them. Put a skill of your own in `~/.agents/skills/<name>/` under a name PStack doesn't use, and link it into `~/.claude/skills/` for Claude Code. [Make it yours](./09-make-it-yours.md) shows how PStack writes one for you. Changing PStack's own skills is covered in [Developing PStack](../development.md).

## Why the setup looks like this

PStack isn't finished when you install it. You keep bending it until it fits how you work. Three decisions follow from that.

**Installed once, for every project.** The skills describe how you work, not how one repo works, so they live in your home folder and every project sees them. Nothing is written into a project's git.

**The model pool is yours, not the project's.** `~/.config/pstack/models.json` records which models your T3 Code can run and which ones you're willing to pay for. Those are facts about you, and they don't change from repo to repo. One file means one setup covers Claude Code, Codex, OpenCode, and Pi everywhere, and no model choice ever lands in a project's git history. The pool is per machine, though: a provider that works on one computer may not be logged in on another, so run setup on each machine rather than copying the file.

**Anything a skill writes will drift.** The main one is the `verify-<app>` skill from `/create-verification-skill`. It's committed to the project and describes the app as it was on the day it was generated. When the app changes, run [`/maintain-verification-skill`](../../skills/maintain-verification-skill/SKILL.md). The generator stamps its output with `metadata.pstack-generated-by: create-verification-skill@1`, but nothing compares that stamp yet, so you'll have to notice an outdated verification skill yourself.

## How skills get invoked

The principle skills, `unslop`, `typescript-best-practices`, and `setup-pstack` may trigger on their own. The 20 workflow skills run only when you ask for them by name, or when a workflow you started routes to one (`/poteto-mode` calling `/how`, for example). Claude Code and Pi enforce this through `disable-model-invocation: true`, so there a workflow starts only when you type its name. Codex and OpenCode ignore that field, so each workflow's description opens with the same rule as an instruction to the model. That is a request, not a lock: if a model starts a workflow you didn't ask for, stop it and report it. Start one by name: `/name` in Claude Code, `$name` in Codex, `/skill:name` in Pi, or ask the OpenCode agent to use the skill.

## Pick your models

Invoke [`setup-pstack`](../../skills/setup-pstack/SKILL.md) from a T3 Code thread. It reads the thread's `orchestrator_capabilities`: which providers can run child tasks, which models each advertises, and which option values the orchestrator accepts. It shows the exact descriptors, defaults, and advertised choices. List order has no strength meaning; setup recommends a strongest reasoning value only when the descriptor's own semantics or current provider evidence establishes one, and otherwise asks. It saves only the values you confirm.

> **How workflows use the pool.** Every workflow that spawns agents uses T3's tools per [`t3-delegation.md`](../../skills/setup-pstack/references/t3-delegation.md): `default`-tier pool entries normally, `escalation`-tier entries only for genuinely hard work. `delegate_task` children share the parent's checkout; parallel writers get their own worktree through `t3_thread_launch`.

Setup saves one shared pool at `~/.config/pstack/models.json`, and one setup covers every harness. Each entry has a unique `id`, a `providerInstanceId`, a model, its confirmed options, and an optional `tier` (`default` or `escalation`). Keep at least one `default` entry for routine work; setup asks which others are expensive enough to reserve for hard tasks. There are no per-role tables and no required cost, concurrency, or retry settings. Setup does not raise `serviceTier`, `fastMode`, or other non-reasoning options on its own and does not change your main chat model. Reasoning options differ per provider (Codex `reasoningEffort`, OpenCode `variant`, Claude `effort`, Pi `thinking`), so a level never carries from one model to another. T3's Claude adapter can also remap some effort values, so check what actually ran.

The pool is the model-setup contract: a task may use one entry or several. Reviewing and diagnosing prefer entries from different providers, since differently trained models miss different things. Producing one result prefers one strong entry, and judges check evidence rather than opinions. A model outside the pool needs your explicit authorization for that task; a one-off target is never added to the pool automatically. PStack does not enforce spending limits.

## A verification skill is a separate choice

`setup-pstack` configures models only. If you want a scripted way to prove app behavior, invoke [`/create-verification-skill`](../../skills/create-verification-skill/SKILL.md) yourself; [Verify and ship](./06-verify-and-ship.md#create-a-project-verification-skill) covers when it earns its place.

## Test your setup

Run these once, in order, in a throwaway branch of a real project. Each step checks one piece; stop at the first one that fails.

1. **Skills are visible.** Open a new T3 thread and ask: "Which PStack skills can you see?" It should name `poteto-mode` and `setup-pstack`.
2. **The pool works.** Run `setup-pstack` and save at least one entry. It ends by running `model_policy.py validate`; that must pass.
3. **Delegation works.** Run `/interrogate` and point it at one small file or diff. The reviewers should show up as child tasks under your thread in the T3 sidebar, each on a pool model, and the final report names each child's pool entry and model. If the agent reviews the change itself, or uses its harness's own subagents instead of T3's, that is a bug: report it.
4. **Parallel writers work.** Run `/arena` or `/swarm` on a tiny task ("two candidates for a `--version` flag"). The agent should first tell you in one line how many worktree threads it will open, then each writer appears as its own T3 thread on its own new branch. This needs the thread in **full access** and **default** (not plan) mode; otherwise the agent tells you to switch.
5. **Clean up.** Delete the test branches and worktrees, or ask for [`/poteto-mode` worktree cleanup](../../skills/poteto-mode/playbooks/worktree-cleanup.md).

Try each harness you use as the main chat: a step that passes in Claude Code may not pass in Pi.

## Run your first task

Pick something real but small, and describe it the way you'd describe it to a colleague:

```text
Use poteto-mode: add a --json flag to this command. Text output stays byte-identical. Verify both.
```

`poteto-mode` refuses to start until `model_policy.py validate` passes, so run `setup-pstack` first. It resolves a chosen pool entry against live capabilities before delegation.

Watch the todo list. Its first items are the matched playbook's steps copied in, the Feature playbook for this prompt. If poteto-mode skips a step, the step stays in the list with `skip: <reason>`, so you can see what it chose not to do.

From here you can type normal follow-ups. Poteto mode stays on for the conversation until you opt out by saying so.

Next: [Route work through `/poteto-mode`](./02-poteto-mode.md).
