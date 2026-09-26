# PStack model-pool contract

`~/.config/pstack/models.json` is the only PStack source of concrete model choices. Version 2 records one **pool** of delegation targets shared by every task role. T3 Code is the runtime boundary: a target is the `providerInstanceId`, `model`, and `options` that `delegate_task` accepts, discovered from the current thread's `orchestrator_capabilities`.

## Policy v2

```json
{
  "version": 2,
  "pool": [
    {
      "id": "codex-gpt-6-astra-high",
      "providerInstanceId": "codex",
      "model": "gpt-6-astra",
      "options": {"reasoningEffort": "high"}
    },
    {
      "id": "opencode-deepseek-v4-1-flash-max",
      "providerInstanceId": "opencode",
      "model": "opencode-go/deepseek-v4.1-flash",
      "options": {"variant": "max"}
    }
  ]
}
```

- `id`: stable lowercase reference for `resolve` and reports; unique in the pool.
- `providerInstanceId`: exact id from this thread's capability snapshot.
- `model`: exact model id advertised for that provider instance.
- `options`: optional map of advertised option ids to string or boolean values. Omitted options keep the provider default. Store only values the user confirmed.
- `tier`: optional, `default` (the default) or `escalation`. Workflows use `default` entries unless the task is genuinely hard; `escalation` marks entries the user wants spent only then, usually the expensive ones.

The example is illustrative. A saved pool contains only model ids and option values that this thread advertised.

## Capability snapshot

`orchestrator_capabilities` returns `inheritedProviderInstanceId`, `inheritedModel`, and `providers[]`. Each provider carries `providerInstanceId`, `models[]` with `options[]` descriptors, `canRunChildTask`, `canRunCrossProviderChildTask`, and `constraints`. Save the JSON and pass it with `--snapshot`.

The helper uses:

- `providers[].providerInstanceId`, `models[].id`, and `models[].options`.
- Descriptor type `select` (legal values are its `options[].id`) and `boolean` (legal value is `true`/`false`). Other descriptor types are not selectable.
- `constraints`, `canRunChildTask`, `canRunCrossProviderChildTask`, and `inheritedProviderInstanceId` for runnable checks. A provider is runnable when it reports no constraints, advertises child tasks, and either is the inherited provider or advertises cross-provider child tasks.

Option verification mirrors T3's own target validation: unknown option ids and values outside the advertised choices are rejected. Provider catalogs and option names are per-provider and change over time; Codex uses `reasoningEffort`, OpenCode uses `variant`, and Claude uses `effort` (label "Reasoning"), with `fastMode` and `contextWindow` on some models and `thinking` instead of `effort` on Haiku 4.5. Claude's `effort` choices vary by model and can include `ultracode` and `ultrathink`; `ultrathink` is also advertised as a `promptInjectedValues` entry. `contextWindow` is applied as a model suffix, not a separate API flag. Claude is discovered like any other provider; the helper hardcodes no support claims for it.

Claude models may remap a saved option value to a different runtime value via the provider's `effortMap` (for example a legacy model's `xhigh` running as `max`), and `orchestrator_capabilities` does not expose that mapping. Store what was advertised and tell the user a remap is possible; do not encode a remap table here, since it would go stale.

## Reasoning choices

`propose` lists every descriptor for one model: id, label, type, description, current value, `promptInjectedValues` when advertised, and each select choice's label, description, and default flag. It reads no policy file, so it works before one exists and with a version 1 policy still in place.

Descriptor order reflects the provider catalog and has no guaranteed strength semantics; the helper ranks nothing and reports no proposed value. Recommend a value only when the descriptor's own label, description, default, injected values, or current provider evidence establishes it; otherwise show the choices and ask. `serviceTier`, `fastMode`, `contextWindow`, `agent`, and similar options are never treated as reasoning settings. The user confirms, chooses another advertised value, or keeps the provider default.

## Selection and authorization

- One pool is shared across task roles. No per-role tables, cost caps, concurrency, retry, or nesting settings are required or implied.
- A task may use one entry or several; temporary MOA combinations are allowed.
- A combination outside the saved pool requires the user's explicit authorization for the current task. A current instruction counts, and the same authorization is not requested twice. `--authorize-explicit` carries the caller's evidence of that instruction, keeps the target one-off, and never writes to the pool; the helper cannot verify consent, so the caller must supply the real instruction and must not treat the flag as a permission check. Nested children share their parent call's authorization scope.
- Specialist agents keep their own instructions and tools, but their models are not exempt: a routed call's effective model and options must match a pool entry or an existing explicit authorization, including when a specialist or native path selects them. Verify the effective target before the call runs. The main chat model is untouched.
- PStack cannot guarantee provider billing behavior or enforce prompt-level spending limits. Reasoning effort, pool size, retries, and provider pricing affect cost separately.

## Readiness levels

`validate` proves structural validity only. `ready --snapshot` adds currently advertised availability: every pool entry must map to a runnable provider, an advertised model, and legal option values. Invocation success is a third level that no offline check proves; only a delegated call that succeeds does, and `ready` always reports `invocation: unverified`. A mismatch means stop and ask for a confirmed target; never guess a replacement.

## CLI

| command | purpose |
|---|---|
| `validate [--policy PATH]` | Structural check of the v2 policy; v1 reports migration required. |
| `ready [--snapshot PATH\|-]` | Structure plus advertised availability for every pool entry. Exit 1 when snapshot verification fails. |
| `list [--tier default\|escalation]` | Print pool entries with their tier; no snapshot needed. |
| `resolve --id ID` | Dry-run a saved pool entry. |
| `resolve --provider-instance-id ID --model M [--option KEY=VALUE]...` | Resolve an exact saved combination, or a one-off with `--authorize-explicit REASON`. `REASON` is the user's actual instruction supplied as caller evidence; the helper cannot verify consent. Boolean values use `true`/`false`. |
| `propose --snapshot PATH\|- --provider-instance-id ID --model M` | Print descriptors, choices, and defaults; ranks nothing and reads no policy. |
| `convert` | Print a reviewed v2 draft for a v1 file plus per-entry warnings. |

`--snapshot -` reads the snapshot from stdin. The helper never writes user files and never invokes a model.

## Migration from v1 and the legacy boundary

Version 1 (`profiles`, `harnesses`, `roles`) is not read by this helper. The file is preserved, and `validate`, `ready`, and `resolve` fail with a migration-required diagnostic. `convert` prints a draft: each proposed entry carries the v1 profiles and roles that used it plus warnings that v1 role restrictions do not carry into the shared pool and that v1 harness-native option names must be re-verified against the current snapshot. Save only entries the user confirms.

Workflows consume the pool through [T3 delegation](t3-delegation.md): they list `default`-tier entries, escalate only for genuinely hard work, and pass the resolved target to `delegate_task` or `t3_thread_launch`. Native agent-file generation (`render-agent`) is removed: the T3 delegation target is the supported route.
