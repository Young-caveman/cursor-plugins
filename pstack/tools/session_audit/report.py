"""Text and JSON rendering for session audits."""

from __future__ import annotations

import json
import sys

from .policy import routing_report, load_policy
from .schema import SessionAudit


def print_report(audit: SessionAudit, policy: dict | None = None):
    if policy is None:
        policy = load_policy()
    meta = audit.meta
    print(f"== {meta.harness} {meta.session_id} ==")
    parts = [f"cli={meta.cli_version}", f"originator={meta.originator}", f"provider={meta.provider}"]
    print(" ".join(p for p in parts if p.split("=")[1] != "None"))
    print(f"cwd={meta.cwd}")
    print(f"source={meta.source}")
    print()

    print("-- routing --")
    for ln in routing_report(audit, policy):
        print(" ", ln)
    print()

    print("-- skills --")
    print(f"  advertised={audit.skills_advertised}")
    for s in audit.skills:
        path = f" <- {s.path}" if s.path else ""
        print(f"  {s.kind:<14} {s.name}{path}")
    print()

    print("-- tools --")
    for t in audit.tools:
        flag = " ERR" if t.errors else ""
        cmd = t.cmd or t.input_preview
        print(f"  {t.name}{flag}  {cmd[:160]}")
    print()

    errs = [(t, e) for t in audit.tools for e in t.errors]
    print(f"-- errors ({len(errs)}) --")
    for t, e in errs:
        print(f"  [{t.name}] {e}")
    print()

    print("-- timeline --")
    for ev in audit.timeline:
        ts = (ev.ts or "")[11:19]
        print(f"  {ts} {ev.kind:<13} {ev.detail}")
    print()

    tk = audit.tokens
    if tk:
        print(
            f"-- tokens: in={tk.get('input_tokens')} cached={tk.get('cached_input_tokens')} "
            f"out={tk.get('output_tokens')} reasoning={tk.get('reasoning_output_tokens')} --"
        )


def print_json(audit: SessionAudit, policy: dict | None = None):
    if policy is None:
        policy = load_policy()
    data = audit.to_dict()
    data["policy"] = policy
    data["routing_report"] = routing_report(audit, policy)
    json.dump(data, sys.stdout, indent=2, ensure_ascii=False)
    print()
