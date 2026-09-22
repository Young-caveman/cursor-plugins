---
name: setup-pstack
description: Configure PStack's role-based model routing for Codex and OpenCode. Use for /setup-pstack, "configure pstack models", or changing PStack's reasoning and model choices.
---

# Set up PStack model routing

Keep one user-owned policy at `~/.config/pstack/models.json`. It records **intent**: named model profiles, each role's default profile, and the profiles that role may choose at runtime. The policy is the source of truth. Harness configuration is an output of setup, not a second place to choose PStack models. Read [the policy and adapter contract](references/model-routing.md) when creating, changing, or consuming this configuration.

## 1. Inspect the active harness

Identify whether this session is Codex, OpenCode, or another wrapper such as T3 Code around one of them. Inspect the actual subagent tool schema; do not infer it from the outer UI. Record whether a call can choose an agent type, a model, and a reasoning setting separately. Check the installed harness version and its effective user/project model settings. This adapter supports OpenCode 1.x; if the active OpenCode has another major version, do not generate or apply OpenCode profiles until that version has an adapter. Existing harness settings may override a generated default or prevent parent inheritance.

Collect model IDs the user can actually select in each active harness. Use the harness's model picker or catalog and, when useful, `opencode models`; a catalog entry alone does not prove entitlement. Confirm each requested reasoning effort or variant for that model. Save only confirmed model/effort combinations in a ready policy. If availability cannot be checked, ask the user to provide or confirm a selectable ID before saving; this schema has no unverified-status field, so do not store unverified mappings or silently substitute another model. Codex model IDs, OpenCode 1.x `provider/model` IDs, and provider-specific reasoning options are different namespaces.

If `~/.config/pstack/models.json` exists, read it as the current choice. An old `~/.cursor/rules/pstack-models.mdc` may inform migration, but its Cursor slugs and `auto` marker are not valid Codex/OpenCode IDs. Do not copy them without translation and validation.

## 2. Agree on routing and cost

Ask which active harnesses to configure. Show the effective parent/default model, then offer named profiles such as `fast`, `balanced`, and `deep`; these are user-editable names, not model tiers. For each profile show the exact model ID and supported reasoning setting in each harness. Reasoning effort changes compute use; it is not a guarantee of answer quality or a monetary spending cap.

Show every role in the policy contract. A role has one default profile and may list additional **allowed** profiles that its skill can select based on task difficulty. The user may lock a role by allowing only its default. Panel roles contain ordered profile lists; each entry launches one agent, including repeated or inherited entries. `arena cross-judge pool` is a candidate pool for one judge. `swarm workers` is the default profile for each worker unless the user specifies race arms. Show these counts and likely cost before accepting the choices. Preserve explicit user model requirements and any restrictions on provider, reasoning, or escalation.

Treat `inherit-parent` as an intent, not as a model ID. Offer it only when the active harness can resolve it as requested. In Codex, omitting a spawn model may still use `agents.default_subagent_model`, `agents.default_subagent_reasoning_effort`, or a custom agent's settings. In OpenCode, an unconfigured subagent model inherits its caller's session model. If the current invocation path cannot guarantee inheritance, mark that profile unsupported for that path and request a concrete model or a configuration change.

## 3. Save one policy and sync native configuration

Write `~/.config/pstack/models.json` in the [documented schema](references/model-routing.md), preserving existing unrelated user settings. A saved policy may contain only confirmed model/effort combinations; if a required mapping remains unverified, ask the user to confirm it before saving. The current user's explicit task choice outranks a role default. A skill may switch only to a profile in that role's `allowed` list and must state the chosen profile when it differs from the default. No automatic move to a higher reasoning tier or another model family.

Where native agent profiles are usable, create or update only PStack-namespaced files: `$CODEX_HOME/agents/pstack-<profile>.toml` (or `~/.codex/agents/` when `CODEX_HOME` is unset) for Codex and `$XDG_CONFIG_HOME/opencode/agents/` (or `~/.config/opencode/agents/` when `XDG_CONFIG_HOME` is unset) for OpenCode 1.x. Keep the same profile names as the policy. Do not rewrite Codex's main `config.toml`, `opencode.json`, or project settings merely to install PStack. Preserve non-PStack files and any user edits to a previously generated file; show a diff and ask how to reconcile a conflict. A native profile must contain the policy's exact model and supported effort/variant, with no role-specific instructions, tools, or permission changes. Standalone Codex agent files require `developer_instructions`; use only a neutral instruction to follow the invoking task and its constraints. OpenCode 1.x uses `model: provider/model` and provider-specific agent options such as `reasoningEffort`; do not assume `model#variant` works there. For another OpenCode major version, report the adapter as unsupported and do not apply its files.

When the available subagent tool can pass model/effort but cannot select a native profile agent, resolve the policy profile into explicit invocation parameters. This is the path exposed by some Codex sessions under T3 Code. When a workflow requires an existing agent type or prompt, preserve it and use explicit parameters if supported; model routing must not silently replace that agent's instructions. Native files are useful only on invocation paths that actually load them. If neither route can honor a choice, report the mismatch before running work.

## 4. Verify and report

Use `scripts/model_policy.py validate` after saving the policy and `resolve` for each role/profile that will be used. Use `render-agent` when generating native agent files, then validate their TOML/frontmatter syntax. These checks establish structure only. Separately confirm model availability, reasoning support, and effective config precedence with the active harness. For an unresolvable model, stop that call and ask for a confirmed replacement or use a fallback the user explicitly approved in the policy. Never pick the closest or highest-reasoning model on your own.

Report the saved policy path, generated native files, active harnesses, any mappings left unsaved pending confirmation, precedence conflicts, and whether a new session is needed to load them. Re-running setup updates PStack's own policy and generated files; it does not change the user's main chat model.

## 5. Offer project verification once

As before, check whether the project already has a way to drive the real app for proof. If it has neither a `verify-*` skill nor an existing harness, offer once to create a project-local verification skill. Do so only if the user accepts; this is separate from model routing.
