# Project handoff

This file records the current PStack project state for agents and collaborators. Keep the status and decisions current when project work changes. The user's latest instructions take precedence.

## Goal

Turn PStack into a practical personal engineering baseline. Initial harness targets are Codex and OpenCode running inside T3 Code; primary operating systems are macOS and Omarchy/Arch Linux. T3 Code is the outer session/worktree environment, not a peer harness.

## Decisions

- Skills choose work by role and may select only user-allowed model profiles. The active harness resolves a profile to a concrete model and reasoning option.
- Codex and OpenCode have different configuration and inheritance behavior. Do not treat their automatic or inherited model selection as interchangeable.
- Never silently substitute a model or raise reasoning effort. Model and effort mappings need confirmation in the active harness.
- The shared PStack skills stay in one source tree. Harness-specific installation and model configuration belong at their respective harness boundaries.
- For manual install testing, use a worktree's project-scoped skill install so it does not replace a global installation. The user will perform real install and harness testing.
- Prefer a free or low-cost OpenCode model, such as Muse Spark 1.3 Contributor, for the user's manual tests when available.
- Keep working files under `pstack/`. This repo is cone-mode sparse-checkout (`/*`, `!/*/`, `/pstack/`), and T3 Code checkpoints run `git add -A -- .`, which git refuses (exit 1) for paths outside the sparse cone; that turn's filesystem checkpoint is then unavailable. If a new top-level directory is required, run `git sparse-checkout add <dir>` before writing into it. Do not disable sparse-checkout to work around this.

## Current state

- `main` is at `179e0d82f65f90126ad3701c26d5aeb357dd4b6c`, with the model-routing foundation committed locally.
- Harness installation guidance is being prepared on this branch. It recommends the Vercel Skills CLI for Codex/OpenCode targets, project-scoped links for isolated tests, and a copy only when a snapshot is wanted.
- `Make Bot UI` and `Poteto Mode` skill names were normalized to match their directory names.
- No installer was run for these latest changes, and no real harness call was made. Static diff and skill-name checks passed.
- `PLUGINS.md` retains the original root plugin catalog. `README.md` links to that catalog and this handoff file.
- `develop-log/` was moved to `pstack/develop-log/` (uncommitted on `main`) so T3 Code checkpoints capture it. T3 Code itself was not patched.

## Manual test branches

- `test/codex-install`: reserved for the user's Codex install test.
- `test/opencode-install`: reserved for the user's OpenCode install test.
- Both branches start from the same commit containing the current adapter and documentation changes. They are local branches; no test worktrees are attached.

To install from either branch without changing a global install, run from the repository root:

```bash
npx skills add ./pstack/skills --agent codex --agent opencode
```

Choose the symlink option. The project-scoped install belongs to that worktree. For the Codex-only or OpenCode-only branch, select only that harness.

## Handoff

The user will perform the actual installation and model tests. Record the harness version, selected skill/profile, model ID, reasoning setting if observable, and any discovery or invocation errors here after results are reported. Keep harness-specific test artifacts out of the shared PStack skill source unless the user asks to productize them.
