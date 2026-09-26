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

1. List candidates with `model_policy.py list --tier default`. Use `default` entries unless the task is genuinely hard: a previous attempt failed, the change is cross-cutting or subtle, or the user asks. Only then use `--tier escalation` entries, and say why.
2. Dry-run the chosen entry with `model_policy.py resolve --id <entry> --snapshot <capabilities.json>`. The snapshot is this thread's `orchestrator_capabilities` result; write it to a temp file or pipe it in with `--snapshot -`.
3. For `delegate_task`, pass the resolved `providerInstanceId`, `model`, and `options` as `target`. For `t3_thread_launch`, pass them as `modelSelection: {instanceId: providerInstanceId, model, options}`. Never omit `model` when selecting a different provider: T3 may choose that provider's default instead.

## Several models on one task

- **Finding problems** (review, diagnosis, exploration): prefer entries from different providers. Differently trained models miss different things; the union of their findings is the value. Say when two arms share a model.
- **Producing one result** (a fix, a design, an answer): one strong entry beats a mix. Mixing adds the weaker model's mistakes.
- **Judging**: the judge checks evidence (a failing-then-passing reproduction, test output, a quoted line), not which answer sounds better. A judge that must weigh opinions needs a model at least as strong as the ones it judges.

## Agent instructions

T3 has no agent types. When a workflow names a reviewer persona, read its instructions from that workflow's skill tree (for example `no-comments/references/comment-sicko.md`) and paste them into the brief.

## Modes

- Children may only narrow the parent's permissions. For `delegate_task` reviewers and judges, pass `interactionMode: "plan"` and say "do not edit files" in the brief. Plan mode's enforcement differs by provider and has not been verified per provider. `t3_thread_launch` accepts `interactionMode` too, but launches that write code need `default` and a separate worktree.
- For `delegate_task`, pass a stable `clientRequestId` per child (for example `<workflow>-<slug>-<n>`) so a retried call returns the same child. `t3_thread_launch` has no retry key; after an error or lost response, inspect `t3_thread_list` before trying again.

## Waiting

- Launch `delegate_task` children in one message with `mode: "async"`, then end the turn. Each completion wakes the parent; do not poll or spawn watchers. `t3_thread_launch` starts a separate top-level thread and has no `mode` parameter.
- Use `delegate_task` with `mode: "wait"` only when the very next step needs that one result.
- Read results with `task_status` (delegated tasks) or `t3_thread_wait` + `t3_thread_read` (launched threads). A `wait` timeout does not cancel the child.
- A child that fails or times out is a dropout: continue with N−1 and report it.

## Report

For every child, report its pool entry (or explicit authorization), provider, model, and terminal status. Review each result yourself; a child's "done" is a claim, not evidence.
