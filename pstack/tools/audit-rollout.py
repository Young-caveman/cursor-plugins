#!/usr/bin/env python3
"""Audit Codex and OpenCode session history.

Extracts a verifiable timeline from a harness session: which skills loaded,
which tools ran (with the shell command inside exec/bash), the model route
each turn or message actually used, and every error in tool output. Emits
text for reading or --json for a later instruction-checker to consume.

Backends:
  codex    ~/.codex/sessions/**/rollout-*.jsonl
  opencode ~/.local/share/opencode/opencode.db (SQLite, read-only)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from session_audit import codex, opencode
from session_audit.policy import load_policy
from session_audit.report import print_json, print_report

BACKENDS = {"codex": codex, "opencode": opencode}


def pick_backend(harness: str, session: str):
    if harness in BACKENDS:
        return BACKENDS[harness]
    if session.endswith(".jsonl") or Path(session).is_file():
        return codex
    if session.startswith("ses_"):
        return opencode
    for be in (codex, opencode):
        try:
            be.resolve_session(session)
            return be
        except (FileNotFoundError, ValueError):
            continue
    sys.exit(f"no codex or opencode session matching {session!r}")


def cmd_list(args):
    rows = []
    for name, be in BACKENDS.items():
        if args.harness in (name, "all"):
            rows.extend(be.list_sessions(limit=args.limit))
    rows.sort(key=lambda r: str(r.get("started") or ""))
    if args.limit:
        rows = rows[-args.limit :]
    for r in rows:
        if r["harness"] == "codex":
            print(
                f"codex    {r['session_id']}  turns={r['turns']:<3} "
                f"{str(r['started'])[:19]:<20} {r['cli_version'] or '?':<8} {r['cwd']}"
            )
        else:
            print(
                f"opencode {r['session_id']}  "
                f"{str(r['started'])[:19]:<20} {r.get('model')}/{r.get('variant')}  {r['cwd']}"
            )


def cmd_show(args):
    be = pick_backend(args.harness, args.session)
    path = be.resolve_session(args.session)
    data = be.audit(path)
    policy = load_policy()
    if args.json:
        print_json(data, policy)
    else:
        print_report(data, policy)


def cmd_follow(args):
    be = pick_backend(args.harness, args.session)
    path = be.resolve_session(args.session)
    if be is codex:
        follow_codex(path, args)
    else:
        opencode.follow(path, interval=args.interval, from_start=args.from_start)


def follow_codex(path: Path, args):
    import json
    import time

    from session_audit.textmarks import SKILL_DOLLAR_RE, SKILL_TAG_RE, extract_exec_cmd, find_errors

    def content_text(payload):
        content = payload.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "\n".join(c.get("text", "") for c in content if isinstance(c, dict))
        return ""

    def output_text(payload):
        out = payload.get("output", "")
        return out if isinstance(out, str) else content_text({"content": out})

    print(f"following {path} (ctrl-c to stop)")
    pos = 0 if args.from_start else path.stat().st_size
    tools = {}
    try:
        while True:
            with path.open() as f:
                f.seek(pos)
                for line in f:
                    pos = f.tell()
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    rtype = obj.get("type")
                    pl = obj.get("payload", {})
                    ts = (obj.get("timestamp") or "")[11:19]
                    if rtype == "turn_context":
                        print(f"{ts} TURN   model={pl.get('model')} effort={pl.get('effort')}")
                    elif rtype == "response_item":
                        itype = pl.get("type")
                        if itype == "custom_tool_call":
                            name = pl.get("name")
                            cmd = extract_exec_cmd(pl.get("input", "")) if name == "exec" else None
                            tools[pl.get("call_id")] = name
                            print(f"{ts} TOOL   {name}: {(cmd or pl.get('input', ''))[:160]}")
                        elif itype == "custom_tool_call_output":
                            name = tools.pop(pl.get("call_id"), "?")
                            text = output_text(pl)
                            errs = find_errors(text)
                            flag = f"  ERRORS({len(errs)})" if errs else ""
                            print(f"{ts} OUT    {name} -> {len(text)}B{flag}")
                            for e in errs[:3]:
                                print(f"         {e}")
                        elif itype == "message":
                            role = pl.get("role")
                            text = content_text(pl)
                            for m in SKILL_TAG_RE.finditer(text):
                                print(f"{ts} SKILL  loaded {m.group('name')}")
                            if role == "user":
                                m = SKILL_DOLLAR_RE.match(text.strip())
                                if m:
                                    print(f"{ts} SKILL  invoked ${m.group('name')}")
                            elif role == "assistant" and text.strip():
                                print(f"{ts} SAY    {text.strip()[:160]}")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="list known sessions")
    p_list.add_argument("--limit", type=int, default=0, help="show only the N most recent")
    p_list.add_argument(
        "--harness", choices=["codex", "opencode", "all"], default="all", help="filter by harness"
    )
    p_list.set_defaults(func=cmd_list)

    p_show = sub.add_parser("show", help="full audit of one session")
    p_show.add_argument("session", help="session id fragment or path to rollout jsonl")
    p_show.add_argument(
        "--harness",
        choices=["codex", "opencode", "auto"],
        default="auto",
        help="force a backend (default: detect)",
    )
    p_show.add_argument("--json", action="store_true", help="emit machine-readable audit")
    p_show.set_defaults(func=cmd_show)

    p_follow = sub.add_parser("follow", help="live-monitor a session")
    p_follow.add_argument("session", help="session id fragment or path to rollout jsonl")
    p_follow.add_argument(
        "--harness",
        choices=["codex", "opencode", "auto"],
        default="auto",
        help="force a backend (default: detect)",
    )
    p_follow.add_argument("--interval", type=float, default=0.5)
    p_follow.add_argument("--from-start", action="store_true", help="replay existing content first")
    p_follow.set_defaults(func=cmd_follow)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
