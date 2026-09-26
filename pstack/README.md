# pstack

A personal skill set for doing rigorous work with coding agents under T3 Code, the harness control surface that drives Codex, Claude Code, and OpenCode from one session. It began as [poteto](https://x.com/poteto)'s skill set — she wrote it after working on millions of lines of code at Meta, Netflix, and Cursor, and on the React core team — and this fork keeps her principles while wiring every workflow to T3's orchestration.

**Go deep before parallel.** AI writes too much slop code; throughput without quality is not the goal. Trust one agent to write good, verifiable code, then parallelize with confidence.

**Use the right model for the work.** T3's `orchestrator_capabilities` reports what can run, and every workflow delegates through `delegate_task` or `t3_thread_launch`. Models come from one shared pool, so work lands where its strengths help, and several pool entries can collaborate on one task when different strengths matter.

**Write less, better code.** The goal is not to maximize loc. The skills enforce deep understanding, deliberate structure, and verified results.

## Status

The skill workflows delegate through T3 Code's orchestration tools. Fork status, harness test evidence, and open gaps live in [AGENTS.md](../AGENTS.md) and [the development log](./develop-log/).

## Install

PStack runs inside T3 Code with Codex, Claude Code, or OpenCode. Skills are installed as symlinks from this checkout, so an edit to a skill is the edit everywhere.

Link them into a project with the bundled script, run from this `pstack` directory (dry run without `--apply`; the other scripts below live beside it in `skills/setup-pstack/scripts/`):

```bash
python3 skills/setup-pstack/scripts/pstack_link.py --project /path/to/repo \
  --harness codex --harness opencode --harness claude --apply
```

- Codex reads `.agents/skills`. Claude Code reads only `.claude/skills`, not `.agents/`. OpenCode reads both and de-duplicates by name. Pass only the `--harness` flags you use.
- The links stay out of git through a managed block in the repo's `.git/info/exclude`. PStack adds no lock file, no `.gitignore` entry, and no line in your project's `AGENTS.md`.
- Rerun the command after you add, rename, or remove a skill. Text edits need no relinking: Claude Code and Codex see them live; OpenCode caches skills, so start a new session.
- `pstack_doctor.py --project /path/to/repo` reports drift between the source and a project. `harness_discovery.py --project /path/to/repo` shows which skills Codex and Claude Code actually offered their model in the newest session there.
- To test PStack on a real repo, give it a separate worktree on its own branch. `bench_check.py --project <bench> --base <branch>` lists what a test run left there; `--reset` asks, then resets the bench to the base branch and keeps the links.
- `pstack_link.py` handles project installs. Global installation is not covered by this script.

## Get started

Two steps:

1. Run [`setup-pstack`](./skills/setup-pstack/SKILL.md) in a T3 Code thread and choose the models that go in one shared pool, with the reasoning option you confirm for each. One setup covers every harness.
2. Invoke [`poteto-mode`](./skills/poteto-mode/SKILL.md) whenever you're doing anything that requires rigor. In Claude Code, type `/poteto-mode`; in Codex, `$poteto-mode`; in OpenCode, ask the agent to use the `poteto-mode` skill.

> **Delegation.** Every workflow that spawns agents uses T3's `orchestrator_capabilities` and the tools in [`t3-delegation.md`](./skills/setup-pstack/references/t3-delegation.md): cheap `default`-tier pool entries normally, `escalation` entries only for hard work. `delegate_task` children share the parent's checkout; parallel writers get their own worktree through `t3_thread_launch`.

> **Invocation.** The principles, `unslop`, `typescript-best-practices`, and `setup-pstack` may trigger on their own. The twenty-one workflow skills run only when you ask for them by name or a workflow you started routes to one. Claude Code enforces this through `disable-model-invocation: true`; Codex and OpenCode ignore that field, so each workflow's description states the rule for the model instead.

Skill names shown with a leading slash below are shorthand for the harness's skill selector; they are not all literal slash commands.

New here? The [pstack guide](./docs/guide/README.md) walks you through a first real task, from setup and prompting through verification and overnight runs.

That's it. The other skills are situational; the mode skill uses them for you as needed. Setup discovers the models your T3 Code thread can delegate to and saves them in one user-owned pool at `~/.config/pstack/models.json`.

## Usage

Use [`poteto-mode`](./skills/poteto-mode/SKILL.md) at the start of a task. It reads your request, picks from a set of playbooks, and runs the other skills as the steps need them.

### Just use [`poteto-mode`](./skills/poteto-mode/SKILL.md)

This skill is the main shortcut. Use it whenever the agent is doing anything that requires rigor. It comes with twenty-three playbooks:

```
Use poteto-mode: this PR has a subtle bug where the scroll drifts every 750ms even when idle. Reproduce it first.
```

```
Use poteto-mode: I'm going to bed. Land the stack even if CI flakes. I want everything merged by morning.
```

<details>
<summary>the twenty-three playbooks</summary>

| playbook | for |
|---|---|
| [investigation](./skills/poteto-mode/playbooks/investigation.md) | a read-only question. how does x work, why was y built this way, are we sure. |
| [bug fix](./skills/poteto-mode/playbooks/bug-fix.md) | reproduce a defect, root-cause it, and fix with runtime evidence. |
| [perf](./skills/poteto-mode/playbooks/perf-issue.md) | trace a measured slowness and improve it against a baseline. |
| [hillclimb](./skills/poteto-mode/playbooks/hillclimb.md) | sustained, scientific improvement of one metric against a target, looping hypotheses with before/after measurement and one commit per accepted win. |
| [runtime forensics](./skills/poteto-mode/playbooks/runtime-forensics.md) | diagnose a live symptom (leak, idle-cpu spin, glitch) from instrumentation. |
| [trace forensics](./skills/poteto-mode/playbooks/trace-forensics.md) | diagnose a captured profiling artifact (cpuprofile, trace, spindump, heap snapshot). |
| [feature](./skills/poteto-mode/playbooks/feature.md) | new or changed behavior, built from a named data shape. |
| [refactoring](./skills/poteto-mode/playbooks/refactoring.md) | a behavior-preserving change to structure or shape. |
| [prototype](./skills/poteto-mode/playbooks/prototype.md) | a throwaway sketch to make a design or behavioral decision cheaply, or to settle an empirical fork by observing it. |
| [visual parity](./skills/poteto-mode/playbooks/visual-parity.md) | pixel-exact ui equivalence between two implementations. |
| [authoring a skill](./skills/poteto-mode/playbooks/authoring-a-skill.md) | writing or editing a SKILL.md. |
| [eval](./skills/poteto-mode/playbooks/eval.md) | test how a skill or prompt change affects agent behavior, blinded. |
| [babysit](./skills/poteto-mode/playbooks/babysit.md) | drive a pr or a stack to merge-ready: conflicts, review threads, ci. |
| [shipping](./skills/poteto-mode/playbooks/shipping.md) | independently verify a green stack, then land the contiguous verified run bottom-up through github by default or origin when available. |
| [autonomous run](./skills/poteto-mode/playbooks/autonomous-run.md) | drive a long task to completion without stopping. |
| [orchestrate](./skills/poteto-mode/playbooks/orchestrate.md) | a standing project handed to one coordinator chat: multi-day, many stacked prs, fleets of subagents. |
| [autopilot-full](./skills/poteto-mode/playbooks/autopilot-full.md) | run independent prs to merged with one owner per pr and root verification of each merge-ready head. |
| [autopilot-stack](./skills/poteto-mode/playbooks/autopilot-stack.md) | build and verify one linear base-branch stack for the operator to review and land. |
| [session pickup](./skills/poteto-mode/playbooks/session-pickup.md) | resume or take over a prior agent's in-flight work. |
| [pause safely](./skills/poteto-mode/playbooks/pause-safely.md) | suspend in-flight work cleanly so it can be resumed later. |
| [multi-phase plan](./skills/poteto-mode/playbooks/multi-phase-plan.md) | work that spans phases or stacked PRs. |
| [worktree cleanup](./skills/poteto-mode/playbooks/worktree-cleanup.md) | reclaim disk by pruning merged or abandoned worktrees and stale ios simulators, safety-gated. |
| [opening a pr](./skills/poteto-mode/playbooks/opening-a-pr.md) | open a ready pr from small ordered commits with a conventional commits title and a briefing-style body. invoked at the end of every other playbook. |

</details>



When invoked it:

1. Matches your task to a [playbook](./skills/poteto-mode/playbooks/) and opens a todo list whose first items are its steps, copied in verbatim. It refuses to start until `setup-pstack` has saved a valid pool.
2. Routes to the other skills as the steps fire.
3. Writes unslopped replies framed for the consumer and the maintainer.

The full rules and playbooks live in [`skills/poteto-mode/SKILL.md`](./skills/poteto-mode/SKILL.md).

[`/poteto-mode`](./skills/poteto-mode/SKILL.md) is also a sticky mode: once entered it stays on across turns, applying itself when a playbook matches or the task needs rigor and staying out of the way otherwise. Opt out any time by saying so.

For long runs, the [autonomous run playbook](./skills/poteto-mode/playbooks/autonomous-run.md) wakes itself with T3's `schedule_task` or, in Claude Code, `/loop`. You can leave it working for many hours without sacrificing rigor.

## Skills

[`/poteto-mode`](./skills/poteto-mode/SKILL.md) runs most of these for you when a step needs them (`how`, `why`, `architect`, `arena`, `swarm`, `interrogate`, `unslop`, `no-comments`, `technical-writing`, `tdd`, and the principles). The table below is for when you want one directly:

```
/how do we cancel runs? do we have an n+1 when we look up every run to cancel?
```

```
/interrogate review this pr.
```

<details>
<summary>all skills</summary>

| skill | use it when |
|---|---|
| [`/poteto-mode`](./skills/poteto-mode/SKILL.md) | default entry point for any non-trivial task. |
| [`/how`](./skills/how/SKILL.md) | you want a walkthrough of how a subsystem works. |
| [`/why`](./skills/why/SKILL.md) | you want to know why something was built this way. discovers available MCPs at run time and queries each evidence category in parallel (source control, issue tracker, long-form docs, real-time chat, infra observability, error tracking, analytics warehouse). |
| [`/recall`](./skills/recall/SKILL.md) | you're starting or resuming work and want your recent context on a topic rebuilt from your own chat history and the shared record, handed back as a tight current-state brief. |
| [`/blast-radius`](./skills/blast-radius/SKILL.md) | you have a small-looking change and want to know what else it could break, with the one fact it's safe because of proven by running code, not asserted. |
| [`/architect`](./skills/architect/SKILL.md) | you're about to write code that crosses a function boundary and want the caller's usage, types, and module shape settled first. |
| [`/arena`](./skills/arena/SKILL.md) | you want N parallel attempts at the same thing, then to grab the best parts of each. |
| [`/swarm`](./skills/swarm/SKILL.md) | you want N parallel workers across different slices or races, then one aggregated report. |
| [`/interrogate`](./skills/interrogate/SKILL.md) | you have a diff and want reviewers from different pool entries to try to break it, including a strict code-quality lens. |
| [`/automate-me`](./skills/automate-me/SKILL.md) | you want your own `-mode` skill, drafted from how you've actually worked. |
| [`/make-bot-ui`](./skills/make-bot-ui/SKILL.md) | you want a page or dashboard whose buttons wake a Grok Bot over a webhook, including the sender-key handoff and Tailscale. |
| [`/setup-pstack`](./skills/setup-pstack/SKILL.md) | you want to configure PStack's shared model pool for T3 Code sessions (all harnesses). |
| [`/reflect`](./skills/reflect/SKILL.md) | a long task landed and you want the recipe captured as a skill edit. |
| [`/teach`](./skills/teach/SKILL.md) | you want to actually understand a change or subsystem, not just have it summarized. runs how + why and weaves one plain explanation, built up diagram by diagram. |
| [`/tdd`](./skills/tdd/SKILL.md) | you're fixing a bug and there's a cheap local test path. write the failing test first, then the fix. |
| [`/no-comments`](./skills/no-comments/SKILL.md) | strip comments before review; delegates to Comment Sicko, fixes accepted findings, offers encodings for claimed constraints. |
| [`/typescript-best-practices`](./skills/typescript-best-practices/SKILL.md) | you're reading or editing typescript. grounds the type-system-discipline principle in syntax. |
| [`/figure-it-out`](./skills/figure-it-out/SKILL.md) | no bundled playbook fits. designs a rigorous, auditable playbook for the task. |
| [`/show-me-your-work`](./skills/show-me-your-work/SKILL.md) | you want a reviewable decision trail. logs decisions to a tsv you can commit. |
| [`/create-verification-skill`](./skills/create-verification-skill/SKILL.md) | your project has no scripted way to prove app behavior. generates a project-local `verify-<app>` skill in `.agents/skills/` (linked into `.claude/skills/`) with a feature map, for any language or platform. |
| [`/maintain-verification-skill`](./skills/maintain-verification-skill/SKILL.md) | your verify skill's feature map has drifted from the app. source wave + one live pass, at most one PR of proven corrections. |
| [`/unslop`](./skills/unslop/SKILL.md) | you're cleaning up writing. removes AI tells. |
| [`/bro`](./skills/bro/SKILL.md) | you want the last message restated in plain human language, no jargon. |
| [`/technical-writing`](./skills/technical-writing/SKILL.md) | layered doc standard (Diátaxis + Google developer style + STE + Global English) for docs, RFCs, readmes, PR descriptions, commit messages. |

</details>



### Examples

Type [`/poteto-mode`](./skills/poteto-mode/SKILL.md) at the start of a task and let it route to a playbook. The other skills fire as the steps need them. A few you may want directly.


<details>
<summary>all the examples</summary>

```
bug fix:           /poteto-mode this pr has a subtle bug where the scroll drifts every 750ms even
                   when idle. repro first, then fix and verify.
perf:              /poteto-mode a big list takes a second or two to load even though we virtualize.
                   run a cpu trace and tell me why.
feature:           /poteto-mode build a small feature behind a feature flag. verify it really works.
prototype:         /poteto-mode build two prototypes of the markdown renderer so we can compare.
                   spawn an agent for each.
multi-phase:       /poteto-mode open source these skills as a plugin. nothing internal leaks, work
                   in a temp dir, show me the dependency graph first.
overnight run:     /poteto-mode i'm going to bed. land the stack even if ci flakes. i want
                   everything merged by morning.
babysit:           /poteto-mode check on pr 123. anything outstanding?
visual parity:     /poteto-mode the row spacing is too tall when this flag is on. the second image
                   is correct. repro and fix until it matches.
figure it out:     /poteto-mode i'm stepping away. migrate every caller from the synchronous store
                   to the new async one, keeping behavior identical. i want to trust it was done
                   right when i'm back.
how:               /how do we cancel runs? do we have an n+1 when we look up every run to cancel?
why:               /why is this feature flag not on yet?
architect:         design this instrumentation to be high signal with no false positives. /architect
                   this first.
arena:             /arena take my prompt to the arena verbatim. i want to compare their proposals
                   with yours.
swarm:             /swarm check every package under packages/ against its check.sh. one worker per
                   package. one report.
interrogate:       /interrogate review this pr.
tdd:               /tdd implement
unslop:            can we unslop and tighten the new changes?
reflect:           /reflect that took too long. capture what we learned so the next run doesn't
                   repeat it.
show-me-your-work: /show-me-your-work keep a decision trail i can review when i'm back.
automate-me:       /automate-me
```

</details>

## Delegated agents

T3 has no agent types, so agent instructions travel in the brief. A `poteto-mode` delegate's brief opens with "read `poteto-mode/SKILL.md` in full first". [Comment Sicko](./skills/no-comments/references/comment-sicko.md) is pasted verbatim by [`/no-comments`](./skills/no-comments/SKILL.md).

## Principles

Twenty-three short skills, one principle each. `poteto-mode` indexes them inline and reads that index at task start. The standalone files are there so other skills can reference a principle by name, and so the index can point at the full rule for each.

<details>
<summary>all twenty-three principles</summary>

| principle | group | rule |
|---|---|---|
| [laziness-protocol](./skills/principle-laziness-protocol/SKILL.md) | core | Bias toward deletion and the smallest change that solves the problem. |
| [foundational-thinking](./skills/principle-foundational-thinking/SKILL.md) | core | Apply before writing logic: choosing core types and data structures, sequencing scaffold-vs-feature work, asking what concurrent actors share. Get the data structures right so downstream code becomes obvious. |
| [redesign-from-first-principles](./skills/principle-redesign-from-first-principles/SKILL.md) | core | Redesign as if the requirement had been a foundational assumption from day one, instead of bolting it on. |
| [attack-the-premise](./skills/principle-attack-the-premise/SKILL.md) | core | Apply when two or more fixes that share one premise have failed the same gate. Take a census of which actors hold the imbalance before the next fix, then question the premise instead of writing another fix that assumes it. |
| [subtract-before-you-add](./skills/principle-subtract-before-you-add/SKILL.md) | core | Remove dead weight, redundant validators, and stub references first, then build on the simpler base. |
| [minimize-reader-load](./skills/principle-minimize-reader-load/SKILL.md) | core | Count layers between question and answer, and hidden state in the reader's head; collapse one-caller wrappers and shrink mutable scope. |
| [outcome-oriented-execution](./skills/principle-outcome-oriented-execution/SKILL.md) | core | Apply during planned rewrites and migrations with explicit phase boundaries. Converge on the target architecture; don't preserve smooth intermediate states with throwaway compatibility code. |
| [experience-first](./skills/principle-experience-first/SKILL.md) | core | Choose user delight over implementation convenience; ship fewer polished features over more rough ones. |
| [exhaust-the-design-space](./skills/principle-exhaust-the-design-space/SKILL.md) | core | Build 2-3 competing prototypes and compare side by side before committing. |
| [build-the-lever](./skills/principle-build-the-lever/SKILL.md) | core | Apply to any non-trivial work, not just bulk work: edits, migrations, analyses, checks. Build the tool that does it or proves it (codemod, script, generator, or a skill your subagents follow) instead of working by hand. The tool is the artifact a reviewer can rerun. |
| [model-the-domain](./skills/principle-model-the-domain/SKILL.md) | architecture | Encode the domain in a structure instead of scattered conditionals. |
| [boundary-discipline](./skills/principle-boundary-discipline/SKILL.md) | architecture | Concentrate guards at system boundaries (CLI, config, network, external APIs); trust internal types and keep business logic in pure functions. |
| [type-system-discipline](./skills/principle-type-system-discipline/SKILL.md) | architecture | Make illegal states unrepresentable, brand semantic primitives, parse external data at boundaries, refuse to lie to the compiler, exhaust variants, derive from authoritative schemas. |
| [make-operations-idempotent](./skills/principle-make-operations-idempotent/SKILL.md) | architecture | Converge to the same end state regardless of partial prior runs. |
| [migrate-callers-then-delete-legacy-apis](./skills/principle-migrate-callers-then-delete-legacy-apis/SKILL.md) | architecture | Migrate callers and delete the old API in the same wave instead of preserving compatibility layers. |
| [separate-before-serializing-shared-state](./skills/principle-separate-before-serializing-shared-state/SKILL.md) | architecture | Eliminate the sharing first; serialize structurally only when one shared writer is a real invariant. |
| [prove-it-works](./skills/principle-prove-it-works/SKILL.md) | verification | Apply after completing a task, before declaring done. Verify against the real artifact (run the feature, read the actual value, inspect the diff), not a proxy, self-report, or 'it compiles.'. |
| [fix-root-causes](./skills/principle-fix-root-causes/SKILL.md) | verification | Trace each symptom to its root cause and fix it there; reproduce first, ask why until you reach it, resist nil-check guards that silence crashes. |
| [sequence-verifiable-units](./skills/principle-sequence-verifiable-units/SKILL.md) | verification | Apply to multi-step work (sweeps, migrations, runs of similar edits) and to how you stack commits and PRs. Break work into small units that each end in a verifiable state, check each before the next, and order delivery so the sequence proves itself to a reviewer. |
| [test-behavior-not-implementation](./skills/principle-test-behavior-not-implementation/SKILL.md) | verification | Apply when you write, change, or keep a test. Call the code the way its users do and assert the result they observe against a literal expected value. If the test would still pass when every imported function returns undefined, rewrite the assertion or delete the test. |
| [guard-the-context-window](./skills/principle-guard-the-context-window/SKILL.md) | delegation | Route bulk to subagents; keep summaries in the main thread, not raw payloads. |
| [never-block-on-the-human](./skills/principle-never-block-on-the-human/SKILL.md) | delegation | Proceed, present the result, let the human course-correct after the fact; reserve confirmation for irreversible actions. |
| [encode-lessons-in-structure](./skills/principle-encode-lessons-in-structure/SKILL.md) | meta | Encode the rule as a lint, metadata flag, runtime check, or script instead of more text. |

</details>

## Not shipped here

A few things other setups bundle that PStack doesn't:

- code slop pass: use Claude Code's `simplify` skill, or review the diff yourself for dead defensive code, needless abstraction, and duplicated logic.
- driving an app: [`/create-verification-skill`](./skills/create-verification-skill/SKILL.md) writes a project-local verify skill.
- writing a skill: use `skill-creator` when installed, or follow the [skill-authoring playbook](./skills/poteto-mode/playbooks/authoring-a-skill.md) to write `SKILL.md` directly.

## Why are there no planning skills?

The harnesses offer plan modes, but their read-only enforcement and MCP access under T3 have not been verified for every provider. If you want a plan, [`/poteto-mode`](./skills/poteto-mode/SKILL.md) covers it without requiring plan mode.

## Make it yours

`poteto-mode` encodes poteto's style. You may not want exactly that.

Type [`/automate-me`](./skills/automate-me/SKILL.md). It mines your recent T3 threads (falling back to harness logs), drafts a `<your-name>-mode` skill from how you've actually worked, and routes through PStack underneath. You keep PStack as the base and end up with your own routing skill alongside `poteto-mode`.

Models are configurable too. Use [`setup-pstack`](./skills/setup-pstack/SKILL.md). It keeps one user-owned pool at `~/.config/pstack/models.json` (optionally tiered `default` or `escalation`), discovered from what your T3 Code thread can actually run. Every workflow that spawns agents draws from it; the pool contract is that a task may mix entries when different strengths help, a model outside it needs your explicit go-ahead, and setup never upgrades a saved choice on its own.

## Automations

PStack also ships a dormant [benny automation pack](./automations/benny/), written for Cursor automations and not adapted to T3 Code. Treat it as untested here.

## License

MIT
