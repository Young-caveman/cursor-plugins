---
name: setup-pstack
description: Configure PStack's user-owned model pool for T3 Code sessions. Use for /setup-pstack, "configure pstack models", or changing PStack's model and reasoning choices.
---

# Set up the PStack model pool

Keep one user-owned policy at `~/.config/pstack/models.json`. Version 2 records a **pool of concrete delegation targets**: each entry names a T3 `providerInstanceId`, a model ID, and the option values confirmed for it. The pool is shared by every task role; there are no mandatory per-role tables or fixed combinations. Read [the pool contract](references/model-routing.md) before creating or changing the policy.

T3 Code is the runtime boundary. Discover what can run with `orchestrator_capabilities` in this thread and pass the resolved `providerInstanceId`, `model`, and `options` to `delegate_task`. Provider catalogs and option names differ: Codex advertises `reasoningEffort`, OpenCode advertises `variant`, Claude advertises `effort`, and options such as `serviceTier`, `fastMode`, and `contextWindow` are separate. Discover each provider from this thread's snapshot; never carry a model or option name from another provider, harness, or older session.

## 1. Discover this thread's capabilities

Call `orchestrator_capabilities` and save the result as JSON for the helper. For each provider record `providerInstanceId`, `models`, `canRunChildTask`, `canRunCrossProviderChildTask`, and `constraints`. Any runnable provider from this snapshot is eligible, including providers other than the session's own; a provider with constraints or without child-task capability is not a pool target. The helper contains no per-provider claims, including for Claude.

For a model the user is considering, run:

```bash
python3 scripts/model_policy.py propose --snapshot <capabilities.json> --provider-instance-id <id> --model <model>
```

It prints every option descriptor for that model: label, type, description, current value, per-choice labels/descriptions/defaults, and `promptInjectedValues` when advertised. It reads no policy file, so it also works before one exists or when the saved policy is still version 1.

Descriptor order has no guaranteed strength semantics and the helper ranks nothing. Recommend a value only when the descriptor's own label, description, default, `promptInjectedValues`, or current provider evidence establishes it; otherwise show the advertised choices and ask. Never sort by hand, never assume `max` exists, and never treat `serviceTier`, `fastMode`, `contextWindow`, `agent`, or similar options as reasoning settings or raise them automatically.

If `~/.config/pstack/models.json` exists, read it before changing anything:

- **Version 2**: treat it as the user's current pool.
- **Version 1**: leave the file untouched. Run `python3 scripts/model_policy.py convert` to print a reviewed draft. Explain that v1 role restrictions do not carry into the shared pool, re-verify each entry against the current snapshot, and convert only entries the user confirms.

## 2. Agree on the pool

Ask which discovered models belong in the pool. The pool is shared across all task roles, so one selection covers every PStack workflow; a model can also stay out. For each selected model, show the exact model ID, label, defaults, and the full reasoning choices; recommend a strongest value only when evidence establishes it, otherwise ask. The user accepts, picks another advertised value, or leaves an option at its provider default. Store only confirmed, advertised values. Do not promise billing, cost-cap, concurrency, retry, or nesting behavior; reasoning effort and pool size affect cost separately.

Setup is a default, not an exemption. Preserve a specialist agent's own instructions and tools, but the pool or an existing explicit authorization still governs every routed call's model. When a specialist or native path selects its own model or reasoning option, verify the effective model and options match a pool entry or the authorization before running; a changed reasoning option is an out-of-pool target. The main chat model stays unchanged.

## 3. Save the policy

Write version 2 to `~/.config/pstack/models.json`, preserving unrelated user settings. Each entry stores `providerInstanceId`, `model`, and concrete `options`. Later setup runs start from the saved values and never silently upgrade them; changing a saved combination requires the user. If migration applies, save only the reviewed entries.

Then verify:

```bash
python3 scripts/model_policy.py validate
python3 scripts/model_policy.py ready --snapshot <capabilities.json>
python3 scripts/model_policy.py resolve --id <entry-id> --snapshot <capabilities.json>
```

`validate` proves structure. `ready --snapshot` proves each saved entry is currently advertised and each saved option value is legal. Neither proves a target runs: only delegated work that succeeds does, and setup does not spend model calls to find out. Report invocation as unverified.

## 4. Use the pool when delegating

`resolve` is the dry run for choosing and checking targets. Pick one pool entry for a call, or several when a task benefits from different strengths; temporary mixtures for comparison are allowed. A target outside the saved pool needs the user's explicit authorization for the current task; the current instruction counts, so do not ask twice. `--authorize-explicit` carries that actual instruction as evidence, keeps the target one-off, and does not add it to the policy; the helper cannot verify consent, so never invent an instruction or treat the flag as a permission check. Nested subagents inherit the same authorization scope. When a workflow requires a specific agent type or prompt, preserve it and supply the pool target through the invocation parameters.

## 5. Report

Report the providers discovered, the saved pool entries, that the policy is structurally valid and advertised as available, that invocation is unverified until real delegated work succeeds, any v1 migration left for review, and whether a new session is needed. This skill configures models only: it does not offer or create project verification skills, and role-based skills are not migrated by this revision.
