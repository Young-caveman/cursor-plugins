---
name: swarm
description: "Run only when the user asks for this skill by name or a workflow the user started routes here. Fan out N parallel workers, drain them, and return one report. Use for /swarm, 'swarm this', or parallel coverage, races, gauntlets, and exploration."
disable-model-invocation: true
---

# Swarm

Fan out N parallel workers through T3. They cover separate slices, race the same brief, or both. The parent waits, aggregates, and returns one report. Delegate per [T3 delegation](../setup-pstack/references/t3-delegation.md).

## 1. Frame

1. State the done predicate and what the swarm must return.
2. Choose the shape: partition into slices, race N workers on one brief, or mix. For a race, declare the selection rule before launching: `first pass`, `rank all`, or `best-of`.
3. Set N from the user, or derive it from the shape. N counts workers, not concurrency.
4. Pick each worker's pool entry and dry-run it with `model_policy.py resolve --id <entry> --snapshot <capabilities.json>`. For a model race, give each arm a different entry and name them up front. A target outside the pool needs the user's explicit authorization.
5. Decide who writes. Read-only workers run as `delegate_task` children. Workers that edit files each get their own worktree via `t3_thread_launch`, because `delegate_task` children share this checkout.

## 2. Fan out

Launch read-only `delegate_task` workers with `mode: "async"`, a stable `clientRequestId` (`swarm-<slug>-<n>`), and `interactionMode: "plan"`. Launch each writer with `t3_thread_launch` in its own worktree, passing the resolved entry as `modelSelection`; that tool has no `mode` or `clientRequestId`. After a lost launch response, inspect `t3_thread_list` before retrying. Then end the turn; follow launched threads with `t3_thread_wait` and `t3_thread_read`.

Every brief stands alone, since a worker sees nothing but its brief: goal, scope, the exact slice or race arm, how to verify, and what to report. Reports start with `PASS`, `ISSUES`, or `BLOCKED` and cite evidence.

## 3. Aggregate

Read delegated results with `task_status`, or launched worktree threads with `t3_thread_wait` and `t3_thread_read`. Coverage needs a result for every slice; a race applies the rule declared in step 1. A failed or silent worker is a dropout: continue with N−1 and note it. Check claims against evidence before trusting them; don't paste raw worker output.

## 4. Report

One in-chat report: a compact table (worker, pool entry, model, status, finding), one-line evidenced issues, gaps and dropouts, and the race rule if used.
