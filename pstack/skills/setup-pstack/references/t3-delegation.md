# Delegating work under T3 orchestration v2

Every PStack workflow that spawns agents (`arena`, `swarm`, `interrogate`, `architect`, `poteto-mode` playbooks) delegates through T3's `t3-code` MCP tools. Model choice follows [the pool contract](model-routing.md).

Inside a PStack workflow, these rules replace T3's general delegation advice:

- Call `delegate_task` even when the harness has its own subagent tool (Claude Code's Task/Agent, Codex's, OpenCode's; Pi has none), and even for same-provider work. Native subagents bypass the pool's model and options.
- T3 says to open top-level threads only on the user's explicit request. Before the first `t3_thread_launch` in a workflow, tell the user in one line how many worktree threads you will open and why. The user starting a workflow that runs parallel writers (`arena`, `swarm`, the autopilot and multi-phase playbooks) is that request; say it, don't wait for a second confirmation.

## Tool for the job

| Need | Tool | Where it runs |
|---|---|---|
| Read-only work: research, review, judging | `delegate_task` | the parent's checkout (same project, branch, worktree) |
| One writer at a time | `delegate_task` | the parent's checkout |
| Several writers in parallel (arena candidates, race arms that edit code), or read-only work that must build or run a different commit (a verifier at a PR head) | `t3_thread_launch` with `workspaceStrategy: {type: "worktree", baseRef: <current branch>, branch: <new>, startFromOrigin: false}`, one per writer | its own new worktree |

`delegate_task` children always share the parent's checkout, so parallel writers there overwrite each other.

`t3_thread_launch` creates a top-level thread in the same project. The call needs:

- `title` (required).
- `message`: the full brief. Without it the thread is created idle and never starts; `task` and `prompt` are not launch fields.
- `modelSelection` (see Target), `workspaceStrategy`, and optionally `interactionMode`.

Only a parent whose runtime mode is `full-access` **and** whose interaction mode is `default` may launch; check `runtimeMode` and `interactionMode` in `orchestrator_capabilities` first. Otherwise don't launch. In `plan` mode no child can write (children only narrow permissions), so tell the user to switch the thread to default mode, or keep the workflow read-only. With `default` interaction but a narrower runtime mode, tell the user and run the writers one at a time through `delegate_task`. Launches have no retry key: after an error or lost response, check `t3_thread_list` before launching again. Follow a launched thread with `t3_thread_wait` and `t3_thread_read`; it does not wake the parent.

To move **this** thread into a fresh worktree (for example before opening a PR), use `t3_worktree_status`, then `t3_worktree_handoff` with `continuationPrompt` holding the remaining work, as the last call of the turn. `git worktree add` plus `cd` does not rebind the T3 thread.

## One machine only

A T3 server is one environment, and its `t3-code` tools act only inside it. `delegate_task`, `t3_thread_launch`, and `create_threads` take no machine argument and always run where this thread's server runs. Only the `device_*` tools reach further, to simulators on SSH device hosts configured in this environment (`device_list` shows them). Another computer connected to the user's T3 app is a separate environment: no PStack workflow can start, read, or steer work there. When a step needs it (a check only that OS can run, a checkout that exists only there):

1. Do everything that can run here, then write the remaining step as a standalone task file: goal, branch or commit to use, commands, and the evidence to bring back.
2. Hand it off through the project's own handoff skill if it has one and the user asked for it, otherwise give the file to the user. Never send work to another environment on your own.
3. Report that step as `not run: needs <machine>`. A step you couldn't run is not verified.

## Briefs

A child receives only its task prompt and optional `role` (`implementation`, `research`, `review`, `design`, `test`, `general`). No conversation history is copied. Every brief stands alone: goal, scope, files or diff, how to verify, what to report, and any skill the child should read (by path). Paste required agent instructions into the brief; T3 has no agent types.

## Target

1. List candidates with `model_policy.py list --tier default`. Use `default` entries unless the task is genuinely hard: a previous attempt failed, the change is cross-cutting or subtle, or the user asks. Only then use `--tier escalation` entries, and say why.
2. Dry-run the chosen entry with `model_policy.py resolve --id <entry> --snapshot <capabilities.json>`. The snapshot is this thread's `orchestrator_capabilities` result; write it to a temp file or pipe it in with `--snapshot -`.
3. For `delegate_task`, pass the resolved `providerInstanceId`, `model`, and `options` as `target`. For `t3_thread_launch`, pass them as `modelSelection: {instanceId: providerInstanceId, model, options}`. Never omit `model` when selecting a different provider: T3 may choose that provider's default instead.

## Several models on one task

- **Finding problems** (review, diagnosis, exploration): prefer entries whose models come from different vendors. Differently trained models miss different things; the union of their findings is the value. Pi and OpenCode can run the same `opencode-go/...` model, and that counts as one model, not two. Say when two arms share a model.
- **Producing one result** (a fix, a design, an answer): one strong entry beats a mix. Mixing adds the weaker model's mistakes.
- **Judging**: the judge checks evidence (a failing-then-passing reproduction, test output, a quoted line), not which answer sounds better. A judge that must weigh opinions needs a model at least as strong as the ones it judges.

## Agent instructions

T3 has no agent types. When a workflow names a reviewer persona, read its instructions from that workflow's skill tree (for example `no-comments/references/comment-sicko.md`) and paste them into the brief.

## Modes

- Children may only narrow the parent's permissions. For `delegate_task` reviewers and judges, pass `interactionMode: "plan"` and say in the brief: "Do not edit files. Your deliverable is findings, not an implementation plan." The brief is the guard that holds everywhere: T3's Pi adapter ignores plan mode, and other providers' enforcement varies. `t3_thread_launch` accepts `interactionMode` too, but launches that write code need `default` and a separate worktree.
- For `delegate_task`, pass a stable `clientRequestId` per child (for example `<workflow>-<slug>-<n>`) so a retried call returns the same child. `t3_thread_launch` has no retry key; after an error or lost response, inspect `t3_thread_list` before trying again.

## Waiting

- Launch `delegate_task` children in one message with `mode: "async"`, then end the turn. Each completion wakes the parent; do not poll or spawn watchers. `t3_thread_launch` starts a separate top-level thread and has no `mode` parameter.
- Use `delegate_task` with `mode: "wait"` only when the very next step needs that one result.
- Read results with `task_status` (delegated tasks) or `t3_thread_wait` + `t3_thread_read` (launched threads). A `wait` timeout does not cancel the child.
- A child that failed before doing any work because its provider couldn't run (not logged in, provider unavailable, binary missing) gets one rerun: same brief, a new `clientRequestId`, and another `default` pool entry from a different provider. Report the swap and the original error. A provider that failed this way stays unused for the rest of the workflow.
- Any other failure or timeout is a dropout: continue with N−1 and report it. Never rerun a child that did work and failed its task, and never go outside the pool.

## Stopping and steering

- Cancel a delegated child with `task_cancel` (its `taskId`). Interrupt a launched thread's running turn with `t3_thread_interrupt`. A stood-down or replaced worker is stopped this way, not just ignored.
- Message a launched thread with `t3_thread_send`: `mode: "queue"` for a follow-up turn, `"steer"` to correct an active turn, `"restart"` to interrupt and restart it. `t3_queue_list`, `t3_queue_edit`, `t3_queue_cancel`, and `t3_queue_promote_to_steer` inspect and fix what is waiting.
- A worker that looks stuck may be waiting on a question: check `t3_pending_request_list` on its thread and answer with `t3_pending_request_respond` when the answer is yours to give. Permission approvals stay with the user.

## Scheduled runs

`schedule_task` arms a recurring run (`schedule` is an object, never JSON text). Keep the returned `scheduledTaskId`. `update_scheduled_task` with `enabled: false` pauses it, `delete_scheduled_task` removes it, `list_scheduled_tasks` finds it again, and `run_scheduled_task_now` runs a tick immediately; it takes the same id as `taskId`, while update and delete take `scheduledTaskId`. A workflow that armed a schedule removes it when it ends.

## Pull requests

After opening a PR, call `link_pull_request` with its URL so T3 tracks it on the thread. For a stack, link every layer.

## Report

For every child, report its pool entry (or explicit authorization), provider, model, and terminal status. Review each result yourself; a child's "done" is a claim, not evidence.
