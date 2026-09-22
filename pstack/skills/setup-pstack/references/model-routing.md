# PStack model routing contract

`~/.config/pstack/models.json` is the only PStack source of concrete model choices. Skills name roles and, when permitted, select a profile. The active harness resolves the profile into a model and reasoning option. Native agent files may mirror profiles for direct harness use; a skill must not treat their presence as proof that its current subagent tool uses them.

## Policy shape

The example IDs below are placeholders. A saved ready policy may contain only model IDs and reasoning settings confirmed selectable in the active harness. If setup cannot confirm a combo, stop and ask the user to provide or confirm it; this schema has no unverified-status state.

The OpenCode adapter and policy format in this version target OpenCode 1.x (tested with 1.18.31). Setup must check the installed major version. For another major version, do not render or apply OpenCode native profiles until a version-specific adapter is defined. OpenCode 1.x keeps the model as `provider/model` and passes reasoning options separately; do not append `#variant` to the model ID.

```json
{
  "version": 1,
  "harnesses": ["codex", "opencode"],
  "profiles": {
    "fast": {
      "codex": {"model": "<codex-model>", "reasoning_effort": "medium"},
      "opencode": {"model": "<provider/model>", "options": {"reasoningEffort": "medium"}}
    },
    "parent": {
      "codex": {"selection": "inherit-parent"},
      "opencode": {"selection": "inherit-parent"}
    }
  },
  "roles": {
    "feature": {"default": "fast", "allowed": ["fast", "parent"]},
    "recall fanout": {"default": "fast", "allowed": ["fast"]},
    "arena runners": {"default": ["fast", "parent"]},
    "arena cross-judge pool": {"default": ["fast", "parent"]}
  }
}
```

A ready policy must define every role below and reference profiles available in each active harness. Each single-profile role has `default` and `allowed`, with the default included in `allowed`. Runtime selection outside `allowed` requires a new user instruction or setup change. A list role's `default` is an ordered list; repetitions are intentional. Profiles may use `selection: "inherit-parent"` instead of `model` only after the active invocation path has been checked for genuine inheritance. `options` contains provider-specific OpenCode agent options, not a universal reasoning ladder. Do not turn an unsupported effort into part of a model ID.

Single-profile roles: `feature`, `refactoring`, `bug-fix`, `perf-issue`, `hillclimb`, `judgment and prose`, `hardest tasks`, `how explorer`, `how explainer`, `why investigators`, `why synthesizer`, `reflect tooling`, `reflect judgment, divergent, synthesizer`, `swarm workers`, and `recall fanout`.

List roles: `arena runners`, `arena cross-judge pool`, `architect runners`, and `interrogate reviewers`. The cross-judge pool selects one entry; the other list lengths set their agent counts.

## Resolution at a call site

1. Honor the user's current explicit model or restriction. Otherwise use the role's default profile; switch within `allowed` only when the task justifies it and state the switch.
2. Read the active harness's entry for that profile. Check it against the harness's current model catalog and effective config. Do not guess a replacement.
3. If the subagent tool accepts explicit model and reasoning parameters, pass them, preserving a workflow-required agent type. If it instead selects a native profile agent, use the matching `pstack-<profile>` definition. A Codex custom agent's model settings can override spawn parameters, so verify the effective result when both are present.
4. An inherited profile must resolve to the parent session's actual model and reasoning, not merely to a harness default. If this cannot be demonstrated, stop and request a concrete mapping.
5. Record the requested profile and, when exposed by the harness, the effective model/effort. If they differ, report the mismatch rather than claiming the route succeeded.

Setup uses `scripts/model_policy.py validate` after saving, `resolve` to check role/profile references, and `render-agent` when it creates a native profile file. These commands validate structure and produce configuration text; they do not prove model entitlement, reasoning support, or effective harness precedence.

The policy does not cap money spent. Panel size, retries, model prices, provider billing, and reasoning effort all affect cost separately.
