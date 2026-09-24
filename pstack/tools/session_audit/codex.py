"""Codex backend: parse rollout JSONL session files into SessionAudit."""

from __future__ import annotations

import json
from pathlib import Path

from .schema import (
    RoutingEntry,
    SessionAudit,
    SessionMeta,
    SkillEvent,
    TimelineEvent,
    ToolCall,
)
from .textmarks import (
    SKILL_DOLLAR_RE,
    SKILL_LIST_RE,
    SKILL_TAG_RE,
    extract_exec_cmd,
    find_errors,
)

SESSIONS_ROOT = Path.home() / ".codex" / "sessions"


def resolve_session(arg: str) -> Path:
    p = Path(arg)
    if p.is_file():
        return p
    matches = sorted(SESSIONS_ROOT.rglob(f"*{arg}*.jsonl"))
    if not matches:
        raise FileNotFoundError(f"no codex session matching {arg!r} under {SESSIONS_ROOT}")
    if len(matches) > 1:
        raise ValueError(f"ambiguous id {arg!r}:\n  " + "\n  ".join(str(m) for m in matches))
    return matches[0]


def iter_records(path: Path):
    with path.open() as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield lineno, json.loads(line)
            except json.JSONDecodeError:
                yield lineno, None


def content_text(payload: dict) -> str:
    content = payload.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(c.get("text", "") for c in content if isinstance(c, dict))
    return ""


def output_text(payload: dict) -> str:
    out = payload.get("output", "")
    if isinstance(out, str):
        return out
    return content_text({"content": out})


def list_sessions(limit: int = 0) -> list[dict]:
    files = sorted(SESSIONS_ROOT.rglob("rollout-*.jsonl"))
    if limit:
        files = files[-limit:]
    rows = []
    for p in files:
        meta = {}
        turns = 0
        for _, obj in iter_records(p):
            if not obj:
                continue
            if obj.get("type") == "session_meta":
                meta = obj.get("payload", {})
            elif obj.get("type") == "turn_context":
                turns += 1
        rows.append(
            {
                "harness": "codex",
                "session_id": meta.get("session_id", p.stem),
                "turns": turns,
                "started": meta.get("timestamp"),
                "cli_version": meta.get("cli_version"),
                "cwd": meta.get("cwd"),
                "source": str(p),
            }
        )
    return rows


def audit(path: Path) -> SessionAudit:
    meta_raw = {}
    routing: list[RoutingEntry] = []
    skills: list[SkillEvent] = []
    tools: list[ToolCall] = []
    timeline: list[TimelineEvent] = []
    skills_advertised = False
    token_events = []
    pending: dict[str, dict] = {}

    for lineno, obj in iter_records(path):
        if obj is None:
            timeline.append(TimelineEvent(None, "bad-json", f"line {lineno}"))
            continue
        rtype = obj.get("type")
        ts = obj.get("timestamp")
        pl = obj.get("payload", {})

        if rtype == "session_meta":
            meta_raw = pl
        elif rtype == "turn_context":
            tid = pl.get("turn_id", "")
            routing.append(
                RoutingEntry(ts, tid[:8] or "?", pl.get("model"), pl.get("effort"))
            )
            timeline.append(
                TimelineEvent(ts, "turn", f"model={pl.get('model')} effort={pl.get('effort')}")
            )
        elif rtype == "response_item":
            itype = pl.get("type")
            if itype == "message":
                role = pl.get("role")
                text = content_text(pl)
                if SKILL_LIST_RE.search(text):
                    skills_advertised = True
                for m in SKILL_TAG_RE.finditer(text):
                    ev = SkillEvent("loaded", m.group("name"), ts, m.group("path"))
                    if ev not in skills:
                        skills.append(ev)
                        timeline.append(TimelineEvent(ts, "skill-loaded", f"{ev.name} <- {ev.path}"))
                if role == "user":
                    m = SKILL_DOLLAR_RE.match(text.strip())
                    if m:
                        skills.append(SkillEvent("invoked", m.group("name"), ts))
                        timeline.append(TimelineEvent(ts, "skill-invoked", f"${m.group('name')}"))
                elif role == "assistant" and text.strip():
                    timeline.append(TimelineEvent(ts, "assistant", text.strip()[:300]))
            elif itype == "custom_tool_call":
                name = pl.get("name", "?")
                call_id = pl.get("call_id")
                cmd = extract_exec_cmd(pl.get("input", "")) if name == "exec" else None
                pending[call_id] = {
                    "ts": ts,
                    "name": name,
                    "cmd": cmd,
                    "input_preview": (pl.get("input") or "")[:200],
                }
                timeline.append(
                    TimelineEvent(ts, "tool-call", f"{name}: {(cmd or pending[call_id]['input_preview'])[:180]}")
                )
            elif itype == "custom_tool_call_output":
                call_id = pl.get("call_id")
                text = output_text(pl)
                errs = find_errors(text)
                call = pending.pop(call_id, {"ts": ts, "name": "?"})
                t = ToolCall(
                    ts=call.get("ts"),
                    name=call.get("name", "?"),
                    cmd=call.get("cmd"),
                    input_preview=call.get("input_preview", ""),
                    output_len=len(text),
                    errors=errs,
                )
                tools.append(t)
                detail = f"{t.name} -> {t.output_len}B"
                if errs:
                    detail += f"  ERRORS({len(errs)})"
                    timeline.append(TimelineEvent(ts, "tool-error", errs[0][:200]))
                timeline.append(TimelineEvent(ts, "tool-out", detail))
        elif rtype == "event_msg":
            if pl.get("type") == "token_count":
                token_events.append((pl.get("info") or {}).get("total_token_usage") or {})
        elif rtype == "token_usage_record":
            tu = pl.get("usage") or pl.get("turn_token_usage") or {}
            if tu:
                token_events.append(tu)

    for call in pending.values():
        tools.append(
            ToolCall(
                ts=call.get("ts"),
                name=call.get("name", "?"),
                cmd=call.get("cmd"),
                input_preview=call.get("input_preview", ""),
            )
        )

    tokens = {}
    if token_events:
        last = token_events[-1]
        tokens = {
            "input_tokens": last.get("input_tokens"),
            "cached_input_tokens": last.get("cached_input_tokens"),
            "output_tokens": last.get("output_tokens"),
            "reasoning_output_tokens": last.get("reasoning_output_tokens"),
        }

    meta = SessionMeta(
        harness="codex",
        session_id=meta_raw.get("session_id", path.stem),
        source=str(path),
        cwd=meta_raw.get("cwd"),
        cli_version=meta_raw.get("cli_version"),
        originator=meta_raw.get("originator"),
        provider=meta_raw.get("model_provider"),
        started=meta_raw.get("timestamp"),
    )
    return SessionAudit(
        meta=meta,
        routing=routing,
        skills_advertised=skills_advertised,
        skills=skills,
        tools=tools,
        timeline=timeline,
        tokens=tokens,
    )
