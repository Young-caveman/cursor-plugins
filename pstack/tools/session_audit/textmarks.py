"""Text extraction helpers shared by harness backends."""

from __future__ import annotations

import re

ERROR_MARKERS = (
    "error:",
    "unexpected error",
    "os error",
    "permission denied",
    "command not found",
    "traceback (most recent call last)",
    "read-only file system",
)

SKILL_DOLLAR_RE = re.compile(r"^\$(?P<name>[A-Za-z0-9][A-Za-z0-9_-]*)\b")
SKILL_TAG_RE = re.compile(
    r"<skill>\s*<name>(?P<name>[^<]+)</name>\s*<path>(?P<path>[^<]+)</path>"
)
SKILL_LIST_RE = re.compile(r"<skills_instructions>")
CMD_RE = re.compile(
    r"cmd\s*:\s*(\"(?:[^\"\\]|\\.)*\"|'(?:[^'\\]|\\.)*'|`(?:[^`\\]|\\.)*`)"
)


def parse_js_string(raw: str) -> str:
    body = raw[1:-1]
    return bytes(body, "utf-8").decode("unicode_escape") if "\\" in body else body


def extract_exec_cmd(call_input: str) -> str | None:
    m = CMD_RE.search(call_input or "")
    return parse_js_string(m.group(1)) if m else None


def find_errors(text: str) -> list[str]:
    hits = []
    for i, ln in enumerate(text.splitlines(), 1):
        low = ln.lower()
        if any(m in low for m in ERROR_MARKERS):
            hits.append(f"L{i}: {ln.strip()[:200]}")
    return hits
