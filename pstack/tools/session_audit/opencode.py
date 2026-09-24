"""OpenCode backend: read the session SQLite store into SessionAudit."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .schema import (
    RoutingEntry,
    SessionAudit,
    SessionMeta,
    SkillEvent,
    TimelineEvent,
    ToolCall,
)
from .textmarks import find_errors

DB_PATH = Path.home() / ".local" / "share" / "opencode" / "opencode.db"
TOOL_OUTPUT_DIR = Path.home() / ".local" / "share" / "opencode" / "tool-output"


def connect() -> sqlite3.Connection:
    if not DB_PATH.is_file():
        raise FileNotFoundError(f"no OpenCode database at {DB_PATH}")
    return sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)


def resolve_session(arg: str) -> str:
    db = connect()
    try:
        row = db.execute("SELECT id FROM session WHERE id = ?", (arg,)).fetchone()
        if row:
            return row[0]
        rows = db.execute(
            "SELECT id FROM session WHERE id LIKE ? ORDER BY time_created", (f"%{arg}%",)
        ).fetchall()
    finally:
        db.close()
    if not rows:
        raise FileNotFoundError(f"no opencode session matching {arg!r} in {DB_PATH}")
    if len(rows) > 1:
        raise ValueError(f"ambiguous id {arg!r}: " + ", ".join(r[0] for r in rows))
    return rows[0][0]


def list_sessions(limit: int = 0) -> list[dict]:
    db = connect()
    try:
        sql = (
            "SELECT s.id, s.directory, s.title, s.model, s.tokens_input, s.tokens_output, "
            "s.time_created, p.worktree "
            "FROM session s LEFT JOIN project p ON p.id = s.project_id "
            "ORDER BY s.time_created"
        )
        rows = db.execute(sql).fetchall()
    finally:
        db.close()
    if limit:
        rows = rows[-limit:]
    out = []
    for sid, directory, title, model_json, tin, tout, tcreated, worktree in rows:
        model = {}
        try:
            model = json.loads(model_json) if model_json else {}
        except json.JSONDecodeError:
            pass
        started = None
        if tcreated:
            from datetime import datetime, timezone

            started = datetime.fromtimestamp(tcreated / 1000, tz=timezone.utc).isoformat()
        out.append(
            {
                "harness": "opencode",
                "session_id": sid,
                "turns": None,
                "started": started,
                "cli_version": None,
                "cwd": directory or worktree,
                "source": str(DB_PATH),
                "title": (title or "")[:60],
                "model": f"{model.get('providerID')}/{model.get('id')}",
                "variant": model.get("variant"),
                "tokens_in": tin,
                "tokens_out": tout,
            }
        )
    return out


def _json(data: str | None) -> dict:
    try:
        return json.loads(data) if data else {}
    except json.JSONDecodeError:
        return {}


def _tool_errors(state: dict, output: str) -> list[str]:
    errs = []
    status = state.get("status")
    if status == "error":
        err = state.get("error")
        if isinstance(err, dict):
            err = err.get("message") or json.dumps(err)
        errs.append(f"status=error: {str(err or '')[:200]}")
    errs.extend(find_errors(output))
    return errs


def _read_spilled_output(output: str) -> str:
    if "tool-output/tool_" not in output:
        return output
    text = output
    for token in output.split():
        if "tool-output/tool_" in token:
            p = TOOL_OUTPUT_DIR / Path(token.strip()).name
            if p.is_file():
                try:
                    text += "\n" + p.read_text(errors="replace")
                except OSError:
                    pass
    return text


def audit(session_id: str) -> SessionAudit:
    db = connect()
    try:
        row = db.execute(
            "SELECT project_id, directory, title, model, agent, cost, "
            "tokens_input, tokens_output, tokens_reasoning, tokens_cache_read, "
            "time_created FROM session WHERE id = ?",
            (session_id,),
        ).fetchone()
        if not row:
            raise FileNotFoundError(f"session {session_id} not found")
        project_id, directory, title, model_json, agent, cost, tin, tout, treas, tcache, tcreated = row
        messages = db.execute(
            "SELECT id, data FROM message WHERE session_id = ? ORDER BY time_created, id",
            (session_id,),
        ).fetchall()
        parts = db.execute(
            "SELECT id, message_id, data FROM part WHERE session_id = ? ORDER BY time_created, id",
            (session_id,),
        ).fetchall()
    finally:
        db.close()

    session_model = _json(model_json)
    routing: list[RoutingEntry] = []
    skills: list[SkillEvent] = []
    tools: list[ToolCall] = []
    timeline: list[TimelineEvent] = []
    skills_advertised = False

    msg_meta = {}
    for mid, mdata in messages:
        d = _json(mdata)
        msg_meta[mid] = d
        if d.get("role") == "assistant":
            routing.append(
                RoutingEntry(
                    ts=None,
                    scope=mid[:8],
                    model=d.get("modelID"),
                    effort=session_model.get("variant"),
                    provider=d.get("providerID"),
                )
            )
        sys_text = d.get("system")
        if isinstance(sys_text, str) and "available_skills" in sys_text:
            skills_advertised = True

    for pid, mid, pdata in parts:
        d = _json(pdata)
        ptype = d.get("type")
        ts = None
        tinfo = d.get("time")
        if isinstance(tinfo, dict):
            ts = tinfo.get("created")
        if ptype == "tool":
            state = d.get("state") or {}
            inp = state.get("input") or {}
            output = str(state.get("output") or "")
            output = _read_spilled_output(output)
            name = d.get("tool", "?")
            cmd = inp.get("command") if name == "bash" else None
            preview = json.dumps(inp, ensure_ascii=False)[:200]
            errs = _tool_errors(state, output)
            t = ToolCall(
                ts=ts,
                name=name,
                cmd=cmd,
                input_preview=preview,
                output_len=len(output),
                errors=errs,
            )
            tools.append(t)
            if name == "skill":
                sname = inp.get("name", "?")
                skills.append(SkillEvent("invoked", sname, ts))
                timeline.append(TimelineEvent(ts, "skill-invoked", f"{sname} (skill tool)"))
            detail = f"{name}: {(cmd or preview)[:180]}"
            timeline.append(TimelineEvent(ts, "tool-call", detail))
            out_detail = f"{name} -> {t.output_len}B"
            if errs:
                out_detail += f"  ERRORS({len(errs)})"
                timeline.append(TimelineEvent(ts, "tool-error", errs[0][:200]))
            timeline.append(TimelineEvent(ts, "tool-out", out_detail))
        elif ptype == "text":
            text = (d.get("text") or "").strip()
            mrole = (msg_meta.get(mid) or {}).get("role")
            if mrole == "assistant" and text:
                timeline.append(TimelineEvent(ts, "assistant", text[:300]))

    meta = SessionMeta(
        harness="opencode",
        session_id=session_id,
        source=str(DB_PATH),
        cwd=directory,
        cli_version=None,
        originator=agent,
        provider=session_model.get("providerID"),
        started=str(tcreated) if tcreated else None,
    )
    tokens = {
        "input_tokens": tin,
        "cached_input_tokens": tcache,
        "output_tokens": tout,
        "reasoning_output_tokens": treas,
    }
    return SessionAudit(
        meta=meta,
        routing=routing,
        skills_advertised=skills_advertised,
        skills=skills,
        tools=tools,
        timeline=timeline,
        tokens=tokens,
    )


def follow(session_id: str, interval: float = 0.5, from_start: bool = False):
    import time

    db = connect()
    seen_msgs = set()
    seen_parts = set()
    if not from_start:
        for (mid,) in db.execute("SELECT id FROM message WHERE session_id = ?", (session_id,)):
            seen_msgs.add(mid)
        for (pid,) in db.execute("SELECT id FROM part WHERE session_id = ?", (session_id,)):
            seen_parts.add(pid)
    print(f"following opencode session {session_id} (ctrl-c to stop)")
    try:
        while True:
            for mid, mdata in db.execute(
                "SELECT id, data FROM message WHERE session_id = ? ORDER BY time_created, id",
                (session_id,),
            ):
                if mid in seen_msgs:
                    continue
                seen_msgs.add(mid)
                d = _json(mdata)
                if d.get("role") == "assistant":
                    model = f"{d.get('providerID')}/{d.get('modelID')}"
                    print(f"MSG    assistant model={model}")
            for pid, mid, pdata in db.execute(
                "SELECT id, message_id, data FROM part WHERE session_id = ? ORDER BY time_created, id",
                (session_id,),
            ):
                if pid in seen_parts:
                    continue
                seen_parts.add(pid)
                d = _json(pdata)
                ptype = d.get("type")
                if ptype == "tool":
                    state = d.get("state") or {}
                    inp = state.get("input") or {}
                    name = d.get("tool", "?")
                    cmd = inp.get("command") if name == "bash" else json.dumps(inp)[:160]
                    status = state.get("status")
                    print(f"TOOL   {name} [{status}]: {str(cmd)[:160]}")
                    if status == "error":
                        err = state.get("error")
                        if isinstance(err, dict):
                            err = err.get("message")
                        print(f"       ERR {str(err)[:160]}")
                elif ptype == "text":
                    text = (d.get("text") or "").strip()
                    if text:
                        print(f"SAY    {text[:160]}")
            time.sleep(interval)
    except KeyboardInterrupt:
        db.close()
