# Reading past conversations

Skills that mine history (`recall`, `reflect`, `show-me-your-work`, `automate-me`, poteto-mode's eval and session pickup) read it here. Stay inside the current project: never read another project's conversations, since that exposes unrelated private work.

## Under T3 (preferred)

- **This thread:** `orchestrator_capabilities` returns `parentThreadId`, the calling thread. Read it with `t3_thread_read` (`view: "activity"` for the summarized timeline; continue with `afterPosition`). Long items are cut at 20,000 characters: when an item has `textTruncated`, read it again with its `itemId` and `textOffset: nextTextOffset`.
- **Other threads in this project:** for a topic, `t3_thread_search` (`query`, titles and content, bounded results) first, then `t3_thread_read` only the matches. For a time range, `t3_thread_list` (newest first; delegated children are included unless you pass `includeSubagents: false`). These tools only see the calling thread's project, which is the boundary you want.
- **Delegated children:** `task_status` for their result; `t3_thread_read` on the child thread for its work.

## Harness logs (fallback, or for detail T3 does not keep)

| Harness | Location | Find this project's sessions |
|---|---|---|
| Claude Code | `~/.claude/projects/<cwd with every non-alphanumeric character replaced by ->/<session>.jsonl` | the folder for the current working directory |
| Codex | `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl` | first line's `payload.cwd` equals the project path |
| OpenCode | `~/.local/share/opencode/opencode.db` (SQLite; `session`, `message`, `part`) | `session` rows whose directory is the project path; open read-only |
| Pi | `~/.pi/agent/sessions/<cwd with / replaced by ->/<timestamp>_<id>.jsonl` | first line's `cwd` equals the project path; `model_change` and `thinking_level_change` lines record what ran |

`pstack/tools/audit-rollout.py` in the PStack source summarizes Codex, OpenCode, and Pi sessions (model, effort, tools, errors). Open the SQLite file read-only (`file:...?mode=ro`); never write to any harness store.
