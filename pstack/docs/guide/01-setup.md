# Set up pstack

This page covers PStack's model setup and a first task. Model routing currently targets Codex and OpenCode 1.x; their installation and skill-invocation commands differ.

## Install the plugin

Make the PStack skills available in your active harness first. The Cursor plugin command `/add-plugin pstack` is Cursor-specific; it does not install PStack into Codex or OpenCode.

## Pick your models

Invoke [`setup-pstack`](../../skills/setup-pstack/SKILL.md) through your harness's skill interface, or ask the agent to use it. It checks the active subagent API, installed version, available model IDs, and current harness settings. It then shows the role table, model profiles, supported reasoning options, and panel sizes for your choice.

Setup saves one PStack policy at `~/.config/pstack/models.json`. It may also create namespaced Codex TOML or OpenCode agent definitions when the active invocation path can use them. The policy remains the source of truth; setup does not rewrite your main chat model or general harness config. Skills use a role's default profile and may choose only a profile you allowed for that role. A missing role requires setup or an explicit choice, not a stale hard-coded model.

`inherit-parent` expresses an intention to use the parent session's model and reasoning. It is offered only when the current Codex or OpenCode invocation path can honor it. The old Cursor `auto`/`inherit-parent` entries and Cursor model slugs are not copied as native IDs. A panel list still starts one subagent per entry; `swarm workers` sets the worker default unless a race specifies its arms.

## Accept the verification offer, or don't

At the end of setup, `setup-pstack` looks for a way to prove app behavior in your project, either a `verify-*` skill or an existing harness. If it finds neither, it offers once to generate one with [`/create-verification-skill`](../../skills/create-verification-skill/SKILL.md).

The verification skill's destination depends on the harness. It is separate from model routing; say no if you only want to configure models. [Verify and ship](./06-verify-and-ship.md#create-a-project-verification-skill) covers when it earns its place.

Start a new session if your harness needs one to load new agent definitions. Setup should report this after inspecting the active harness.

## Run your first task

Pick something real but small, and describe it the way you'd describe it to a colleague:

```text
/poteto-mode add a --json flag to this command. text output stays byte-identical. verify both.
```

Watch the todo list. Its first items are the matched playbook's steps copied in, the Feature playbook for this prompt. If `/poteto-mode` skips a step, the step stays in the list with `skip: <reason>`, so you can see what it chose not to do.

From here you can type normal follow-ups. `/poteto-mode` is sticky. It stays on for the conversation until you opt out by saying so.

Next: [Route work through `/poteto-mode`](./02-poteto-mode.md).
