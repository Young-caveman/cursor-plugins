# Delegating work under T3 orchestration v2

Every PStack workflow that spawns agents (`arena`, `swarm`, `interrogate`, `architect`, `poteto-mode` playbooks) delegates through T3's `t3-code` MCP tools. Harness-native subagent tools, Cursor `Task` fields, and agent types are not used. Model choice follows [the pool contract](model-routing.md).

## Tool for the job

| Need | Tool | Where it runs |
|---|---|---|
| Read-only work: research, review, judging | `delegate_task` | the parent's checkout (same project, branch, worktree) |
| One writer at a time | `delegate_task` | the parent's checkout |
| Several writers in parallel (arena candidates, race arms that edit code) | `t3_thread_launch` with `workspaceStrategy: {type: "worktree", baseRef: <current branch>, branch: <new>, startFromOrigin: false}`, one per writer | its own new worktree |

`delegate_task` children always share the parent's checkout, so parallel writers there overwrite each other. `t3_thread_launch` creates top-level threads in the same project, which `t3_thread_wait` and `t3_thread_read` can follow. It requires a full-access or default parent, and has no retry key: after an error, check `t3_thread_list` before launching again.

## Briefs

A child receives only its task prompt and optional `role` (`implementation`, `research`, `review`, `design`, `test`, `general`). No conversation history is copied. Every brief stands alone: goal, scope, files or diff, how to verify, what to report, and any skill the child should read (by path). Paste required agent instructions into the brief; T3 has no agent types.

## Target

1. Pick a pool entry and run `model_policy.py resolve --id <entry> --snapshot <capabilities.json>`.
2. Pass its `providerInstanceId`, `model`, and `options` as `target`. Never omit `model` for a non-inherited provider: T3 then picks that provider's first advertised model.
3. Where model diversity is the point (reviewers, judges, race arms), prefer entries from different providers and say when two arms share a model.

## Modes

- Children may only narrow the parent's permissions. For reviewers and judges, pass `interactionMode: "plan"` and say "do not edit files" in the brief. Plan mode's enforcement differs by provider and has not been verified per provider.
- Pass a stable `clientRequestId` per child (for example `<workflow>-<slug>-<n>`) so a retried call returns the same child instead of spawning another.

## Waiting

- Launch all children in one message with `mode: "async"`, then end the turn. Each child's completion wakes the parent; do not poll or spawn watchers.
- Use `mode: "wait"` only when the very next step needs that one result.
- Read results with `task_status` (delegated tasks) or `t3_thread_wait` + `t3_thread_read` (launched threads). A `wait` timeout does not cancel the child.
- A child that fails or times out is a dropout: continue with N−1 and report it.

## Report

For every child, report its pool entry (or explicit authorization), provider, model, and terminal status. Review each result yourself; a child's "done" is a claim, not evidence.
