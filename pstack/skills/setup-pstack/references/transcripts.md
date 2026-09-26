# Reading past conversations

Skills that mine history (`recall`, `reflect`, `show-me-your-work`, `automate-me`, poteto-mode's eval and session pickup) read it here. Stay inside the current project: never read another project's conversations, since that exposes unrelated private work.

## Under T3 (preferred)

- **This thread:** `orchestrator_capabilities` returns `parentThreadId`, the calling thread. Read it with `t3_thread_read` (`view: "activity"` includes tool calls; continue with `afterPosition`).
- **Other threads in this project:** `t3_thread_list` (newest first; `includeSubagents` for delegated children), then `t3_thread_read`. These tools only see the calling thread's project, which is the boundary you want.
- **Delegated children:** `task_status` for their result; `t3_thread_read` on the child thread for its work.

## Harness logs (fallback, or for detail T3 does not keep)

| Harness | Location | Find this project's sessions |
|---|---|---|
| Claude Code | `~/.claude/projects/<cwd with every non-alphanumeric character replaced by ->/<session>.jsonl` | the folder for the current working directory |
| Codex | `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl` | first line's `payload.cwd` equals the project path |
| OpenCode | `~/.local/share/opencode/opencode.db` (SQLite; `session`, `message`, `part`) | `session` rows whose directory is the project path; open read-only |

`pstack/tools/audit-rollout.py` in the PStack source summarizes Codex and OpenCode sessions (model, effort, tools, errors). Open the SQLite file read-only (`file:...?mode=ro`); never write to any harness store.
