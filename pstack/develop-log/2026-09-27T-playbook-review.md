# Playbook and docs review, 2026-09-27

Two read-only T3 children reviewed the work before push.

- Codex `gpt-6-luna` (max), docs: counts and pool correct. Fixed: T3 tables missed users (`recall`, `automate-me`, `hillclimb`, `shipping`, `opening-a-pr`, `arena`/`swarm` wait); "one machine" was too broad, since `device_*` reach simulators on SSH device hosts (`packages/contracts/src/device.ts`, `SshDeviceHost.ts`); AGENTS.md lost the `--reset` caveat and the macOS target.
- OpenCode MiMo 2.6 Pro, all 23 playbooks: tool names and referenced files all exist. Fixed:
  - Origin is Cursor's git forge (launched June 2026); removed from babysit, shipping, opening-a-pr, autopilot-full/stack, multi-phase-plan, SKILL.md, README, guide. PRs use `gh`.
  - Schedules never deleted and children never stopped (autonomous-run, bug-fix, babysit, shipping, visual-parity, hillclimb, orchestrate): one "Clean up what you start" rule in `poteto-mode/SKILL.md`, plus explicit steps in autonomous-run, hillclimb, orchestrate Close, shipping, babysit.
  - `link_pull_request` missing outside opening-a-pr: added to the SKILL.md rule, autopilot owners, multi-phase PR mechanics, autopilot-stack appends.
  - Verifiers at a PR head can't be `delegate_task` children (shared checkout): swarm and `t3-delegation.md` now send read-only work at a different commit to a worktree thread.
  - Orchestrate: launched writers send no completion notification, so drains check `t3_thread_list`; `orch.ts` path is skill-dir based.
  - multi-phase-plan: undefined "agent store" replaced by `~/.local/state/pstack/plans/<repo>/`; template paths use `<skills>/`.
  - hillclimb `decision.tsv` → `decisions.tsv`, no `.gitignore` edits; eval and visual-parity name the launch tool; worktree-cleanup simulator step is macOS-only.
- T3 reported MiMo's summary as an early interim message ("Now let me read all playbooks…"); the real report was the last assistant item in the child thread. Read the thread when a summary looks truncated.

Left for the user: Graphite in orchestrate, Bugbot-specific triage, unconditional `interrogate` for delegated PR openers.
