# Install and set up PStack

This page covers installing PStack into Codex or OpenCode, choosing a shared model pool, and running a first task.

## Install for your harness

For a personal install from a local checkout, run this in the `pstack` directory:

```bash
npx skills add ./skills --global --agent codex --agent opencode
```

The [Vercel Skills CLI](https://github.com/vercel-labs/skills) installs PStack to the selected harnesses' skill locations. Choose symlink in its prompt to keep this checkout as the source of truth; add `--copy` to install a snapshot. To install for just one harness, pass only `--agent codex` or `--agent opencode`. This external CLI needs Node.js/npm for installation; PStack itself does not require Node.js or `npx` at runtime.

For a branch/worktree test that must stay separate from your global install, run this from the repository root of that worktree instead:

```bash
npx skills add ./pstack/skills --agent codex --agent opencode
```

Omit `--global` and choose symlink so the Skills CLI installs project-scoped links under `.agents/skills/` in that worktree. Both Codex and OpenCode discover this shared project skill location.

If you use Cursor, its separate plugin flow is `/add-plugin pstack`.

## Pick your models

Invoke [`setup-pstack`](../../skills/setup-pstack/SKILL.md) through your harness's skill interface, or ask the agent to use it. In Codex, skills can be explicitly selected with `$setup-pstack`; in OpenCode, ask the agent to use the `setup-pstack` skill. In a T3 Code session, setup reads the current thread's orchestrator capabilities: which providers can run child tasks, which models each advertises, and which option values the orchestrator accepts. It shows the exact descriptors, defaults, and advertised choices. List order has no strength meaning; setup recommends a strongest reasoning value only when the descriptor's own semantics or current provider evidence establishes one, and otherwise asks. It saves only the values you confirm.

> **How workflows use the pool.** Every workflow that spawns agents delegates through T3 per [`t3-delegation.md`](../../skills/setup-pstack/references/t3-delegation.md): `default`-tier pool entries normally, `escalation`-tier entries only for genuinely hard work.

Setup saves one shared pool at `~/.config/pstack/models.json`. The pool has no per-role tables and no required cost, concurrency, or retry settings. Setup does not raise `serviceTier`, `fastMode`, or other non-reasoning options on its own, does not change your main chat model, and preserves specialist agents' own instructions and tools. It validates the file structure and, from the session's capability snapshot, verifies each entry is currently advertised with legal option values; that still does not prove a target runs, so setup reports invocation as unverified.

The pool is the model-setup contract: a task may use one entry or several, including temporary mixtures for comparison. A model outside the pool needs your explicit authorization for that task; a one-off target is never added to the pool automatically, nested subagents inherit the same scope, and the helper records the caller's evidence rather than verifying consent. A specialist's own model choice is not exempt: it must match a pool entry or an existing authorization. PStack does not guarantee provider billing behavior or enforce spending limits.

If you already have a version 1 role policy, setup leaves the file untouched and shows a reviewed conversion. Old per-role restrictions do not become blanket pool authorization; only entries you confirm are carried over.

## A verification skill is a separate choice

`setup-pstack` configures models only. If you want a scripted way to prove app behavior, invoke [`/create-verification-skill`](../../skills/create-verification-skill/SKILL.md) yourself; [Verify and ship](./06-verify-and-ship.md#create-a-project-verification-skill) covers when it earns its place.

## Run your first task

Pick something real but small, and describe it the way you'd describe it to a colleague:

```text
Use poteto-mode: add a --json flag to this command. Text output stays byte-identical. Verify both.
```

Reminder: this revision is model setup only. Until workflow integration lands (see the transition note above), `poteto-mode`'s legacy readiness gate reports migration required.

Watch the todo list. Its first items are the matched playbook's steps copied in, the Feature playbook for this prompt. If poteto-mode skips a step, the step stays in the list with `skip: <reason>`, so you can see what it chose not to do.

From here you can type normal follow-ups. Poteto mode stays on for the conversation until you opt out by saying so.

Next: [Route work through `/poteto-mode`](./02-poteto-mode.md).
