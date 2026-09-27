"""Pi backend: read ~/.pi/agent/sessions/<cwd>/<session>.jsonl into SessionAudit."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

from .schema import RoutingEntry, SessionAudit, SessionMeta, SkillEvent, TimelineEvent, ToolCall
from .textmarks import find_errors

SESSIONS = Path.home() / ".pi" / "agent" / "sessions"
SKILL_COMMAND_RE = re.compile(r"^/skill:(?P<name>[A-Za-z0-9][A-Za-z0-9_-]*)\b")


def _entries(path: Path) -> list[dict]:
    out = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _header(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        try:
            first = json.loads(f.readline() or "{}")
        except json.JSONDecodeError:
            return {}
    return first if first.get("type") == "session" else {}


def resolve_session(arg: str) -> Path:
    p = Path(arg).expanduser()
    if p.is_file():
        return p
    matches = [f for f in SESSIONS.glob("*/*.jsonl") if arg in f.name]
    if not matches:
        raise FileNotFoundError(f"no pi session matching {arg!r} in {SESSIONS}")
    if len(matches) > 1:
        raise ValueError(f"ambiguous id {arg!r}: " + ", ".join(f.name for f in matches))
    return matches[0]


def list_sessions(limit: int = 0) -> list[dict]:
    files = sorted(SESSIONS.glob("*/*.jsonl"), key=lambda f: f.stat().st_mtime)
    if limit:
        files = files[-limit:]
    rows = []
    for f in files:
        head = _header(f)
        rows.append(
            {
                "harness": "pi",
                "session_id": head.get("id") or f.stem,
                "turns": None,
                "started": head.get("timestamp"),
                "cli_version": None,
                "cwd": head.get("cwd"),
                "source": str(f),
            }
        )
    return rows


def _text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text")
    return ""


def audit(path: Path) -> SessionAudit:
    entries = _entries(path)
    head = entries[0] if entries and entries[0].get("type") == "session" else {}
    routing: list[RoutingEntry] = []
    skills: list[SkillEvent] = []
    tools: list[ToolCall] = []
    timeline: list[TimelineEvent] = []
    pending: dict[str, ToolCall] = {}
    tokens = {"input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0, "reasoning_output_tokens": 0}
    thinking = None
    advertised = False
    last_route = None

    for e in entries:
        ts = e.get("timestamp")
        etype = e.get("type")
        if etype == "thinking_level_change":
            thinking = e.get("thinkingLevel")
            timeline.append(TimelineEvent(ts, "thinking", str(thinking)))
        elif etype == "model_change":
            timeline.append(TimelineEvent(ts, "model", f"{e.get('provider')}/{e.get('modelId')}"))
        if etype != "message":
            continue
        m = e.get("message") or {}
        role = m.get("role")
        if role == "system":
            advertised = "<available_skills>" in ((m.get("sections") or {}).get("skills") or "")
        elif role == "user":
            text = _text(m.get("content")).strip()
            hit = SKILL_COMMAND_RE.match(text)
            if hit:
                skills.append(SkillEvent("invoked", hit.group("name"), ts))
                timeline.append(TimelineEvent(ts, "skill-invoked", f"/skill:{hit.group('name')}"))
        elif role == "assistant":
            route = (m.get("provider"), m.get("model"), thinking)
            if route != last_route:
                routing.append(RoutingEntry(ts, e.get("id", "")[:8], m.get("model"), thinking, m.get("provider")))
                last_route = route
            usage = m.get("usage") or {}
            tokens["input_tokens"] += usage.get("input") or 0
            tokens["cached_input_tokens"] += usage.get("cacheRead") or 0
            tokens["output_tokens"] += usage.get("output") or 0
            tokens["reasoning_output_tokens"] += usage.get("reasoning") or 0
            for c in m.get("content") or []:
                if c.get("type") == "toolCall":
                    args = c.get("arguments") or {}
                    name = c.get("name", "?")
                    cmd = args.get("command") if name == "bash" else None
                    call = ToolCall(ts, name, cmd, json.dumps(args, ensure_ascii=False)[:200])
                    tools.append(call)
                    pending[c.get("id")] = call
                    timeline.append(TimelineEvent(ts, "tool-call", f"{name}: {(cmd or call.input_preview)[:180]}"))
                    target = str(args.get("path") or args.get("file_path") or "")
                    if name == "read" and target.endswith("/SKILL.md"):
                        skills.append(SkillEvent("loaded", Path(target).parent.name, ts, target))
                        timeline.append(TimelineEvent(ts, "skill-loaded", target))
                elif c.get("type") == "text" and c.get("text", "").strip():
                    timeline.append(TimelineEvent(ts, "assistant", c["text"].strip()[:300]))
        elif role == "toolResult":
            call = pending.pop(m.get("toolCallId"), None)
            output = _text(m.get("content"))
            errs = (["isError=true"] if m.get("isError") else []) + find_errors(output)
            if call:
                call.output_len = len(output)
                call.errors = errs
            detail = f"{m.get('toolName', '?')} -> {len(output)}B" + (f"  ERRORS({len(errs)})" if errs else "")
            timeline.append(TimelineEvent(ts, "tool-out", detail))

    meta = SessionMeta(
        harness="pi",
        session_id=head.get("id") or path.stem,
        source=str(path),
        cwd=head.get("cwd"),
        provider=routing[0].provider if routing else None,
        started=head.get("timestamp"),
    )
    return SessionAudit(meta, routing, advertised, skills, tools, timeline, tokens)


def follow(path: Path, interval: float = 0.5, from_start: bool = False):
    print(f"following {path} (ctrl-c to stop)")
    pos = 0 if from_start else path.stat().st_size
    try:
        while True:
            with path.open(encoding="utf-8", errors="replace") as f:
                f.seek(pos)
                while line := f.readline():
                    pos = f.tell()
                    try:
                        e = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    ts = str(e.get("timestamp") or "")[11:19]
                    if e.get("type") == "model_change":
                        print(f"{ts} MODEL  {e.get('provider')}/{e.get('modelId')}")
                    elif e.get("type") == "thinking_level_change":
                        print(f"{ts} THINK  {e.get('thinkingLevel')}")
                    elif e.get("type") == "message":
                        m = e.get("message") or {}
                        if m.get("role") == "assistant":
                            for c in m.get("content") or []:
                                if c.get("type") == "toolCall":
                                    args = c.get("arguments") or {}
                                    print(f"{ts} TOOL   {c.get('name')}: {str(args.get('command') or args)[:160]}")
                                elif c.get("type") == "text" and c.get("text", "").strip():
                                    print(f"{ts} SAY    {c['text'].strip()[:160]}")
                        elif m.get("role") == "toolResult" and m.get("isError"):
                            print(f"{ts} ERR    {m.get('toolName')}: {_text(m.get('content'))[:160]}")
            time.sleep(interval)
    except KeyboardInterrupt:
        pass
