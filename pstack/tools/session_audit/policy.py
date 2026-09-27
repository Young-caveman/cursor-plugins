"""PStack model-policy loading and routing comparison."""

from __future__ import annotations

import json
from pathlib import Path

from .schema import SessionAudit

POLICY_PATH = Path.home() / ".config" / "pstack" / "models.json"


def load_policy() -> dict | None:
    if not POLICY_PATH.is_file():
        return None
    try:
        return json.loads(POLICY_PATH.read_text())
    except json.JSONDecodeError:
        return {"error": f"unparseable {POLICY_PATH}"}


REASONING_OPTION = {"codex": "reasoningEffort", "opencode": "variant", "pi": "thinking"}


def pool_routes(policy: dict, harness: str) -> dict[str, tuple[str | None, str | None]]:
    """Pool entries for this harness as (model, reasoning) pairs; None reasoning means provider default."""
    out = {}
    for entry in policy.get("pool") or []:
        if entry.get("providerInstanceId") != harness:
            continue
        options = entry.get("options") or {}
        out[entry.get("id", "?")] = (entry.get("model"), options.get(REASONING_OPTION.get(harness, "")))
    return out


def _actual_route(harness: str, r) -> tuple[str | None, str | None]:
    if harness == "codex":
        return (r.model, r.effort)
    return (
        f"{r.provider}/{r.model}" if r.provider and r.model else r.model,
        r.effort,
    )


def drift_lines(audit: SessionAudit) -> list[str]:
    seen = {_actual_route(audit.meta.harness, r) for r in audit.routing}
    if len(seen) <= 1:
        return []
    return [
        f"DRIFT: session used {len(seen)} distinct model routes: "
        + ", ".join(f"{m}/{e}" for m, e in sorted(seen, key=lambda x: str(x)))
    ]


def routing_report(audit: SessionAudit, policy: dict | None) -> list[str]:
    harness = audit.meta.harness
    drift = drift_lines(audit)
    if not policy:
        return [f"no policy at {POLICY_PATH} (routing unverified)"] + drift
    if "error" in policy:
        return [policy["error"]] + drift
    if policy.get("version") != 2:
        return [f"{POLICY_PATH} is not a version 2 pool (run model_policy.py convert)"] + drift
    models = pool_routes(policy, harness)
    lines = []
    seen = set()
    for r in audit.routing:
        actual = _actual_route(harness, r)
        match = [p for p, (m, e) in models.items() if m == actual[0] and e in (None, actual[1])]
        status = f"pool~{match[0]}" if match else "NOT IN POOL"
        key = (r.scope, actual, status)
        if key in seen:
            continue
        seen.add(key)
        scope = r.scope if len(audit.routing) <= 40 else r.scope[:8]
        lines.append(f"{scope}  {actual[0]} / {actual[1]}  [{status}]")
    return lines + drift
