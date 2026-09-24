"""Shared audit record types for harness session backends."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RoutingEntry:
    ts: str | None
    scope: str
    model: str | None
    effort: str | None
    provider: str | None = None


@dataclass
class SkillEvent:
    kind: str
    name: str
    ts: str | None = None
    path: str | None = None


@dataclass
class ToolCall:
    ts: str | None
    name: str
    cmd: str | None = None
    input_preview: str = ""
    output_len: int | None = None
    errors: list[str] = field(default_factory=list)


@dataclass
class TimelineEvent:
    ts: str | None
    kind: str
    detail: str


@dataclass
class SessionMeta:
    harness: str
    session_id: str
    source: str
    cwd: str | None = None
    cli_version: str | None = None
    originator: str | None = None
    provider: str | None = None
    started: str | None = None


@dataclass
class SessionAudit:
    meta: SessionMeta
    routing: list[RoutingEntry] = field(default_factory=list)
    skills_advertised: bool = False
    skills: list[SkillEvent] = field(default_factory=list)
    tools: list[ToolCall] = field(default_factory=list)
    timeline: list[TimelineEvent] = field(default_factory=list)
    tokens: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "meta": self.meta.__dict__,
            "routing": [r.__dict__ for r in self.routing],
            "skills_advertised": self.skills_advertised,
            "skills": [s.__dict__ for s in self.skills],
            "tools": [t.__dict__ for t in self.tools],
            "timeline": [e.__dict__ for e in self.timeline],
            "tokens": self.tokens,
        }
