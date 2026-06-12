"""Parse the authoritative ``queries_md/*_test.md`` benchmark files.

Two layouts are supported with one code path:

* ``## Query N — title`` with a ``**Prompt:**`` line followed by ``>`` blockquote
  lines (gdc / pdc / gc / icdc / ctdc / psdc).
* ``### A1 — title`` with an inline ``> **Prompt:** "..."`` line (cda).

Each query carries a ``Checks (machine-gradeable):`` block of inline-code check
tokens (`` `type: spec` ``); a single bullet may hold more than one token.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

# Longest type names first so the alternation is unambiguous.
CHECK_TYPES = (
    "substring_all",
    "substring_any",
    "substring",
    "must_not_contain",
    "set_contains",
    "count_at_least",
    "behavior",
    "number",
    "regex",
)

_HEADING_RE = re.compile(r"^(#{2,4})\s+(.*?)\s*#*\s*$")
_PROMPT_RE = re.compile(r"\*\*Prompt:\*\*", re.IGNORECASE)
_CHECKS_MARKER_RE = re.compile(r"Checks\s*\(machine-gradeable\)\s*:", re.IGNORECASE)

_TYPE_ALT = "(?:" + "|".join(CHECK_TYPES) + r")"
# Two token spellings appear in the suites:
#   X-style (most files):  `type: spec`         — colon + spec INSIDE the backticks
#   Y-style (ctdc):        `type`: spec          — colon + spec AFTER the backticks
# A single bullet line may carry more than one token, joined by "and".
_CHECK_TOKEN_RE = re.compile(
    r"`\s*(?P<type>" + _TYPE_ALT + r")\b"
    r"(?:\s*:\s*(?P<inside>[^`\n]*))?"                 # X-style spec (inside)
    r"\s*`"
    r"(?:\s*:\s*(?P<outside>[^\n]*?)"                  # Y-style spec (outside)
    r"(?=\s*$|(?:\s+and\b)?\s+`\s*" + _TYPE_ALT + r"\b))?",
    re.MULTILINE,
)


@dataclass
class Check:
    """One backtick-wrapped, objectively decidable assertion."""

    type: str
    spec: str           # text after ``type:`` (inside the backticks)
    raw: str            # the full ``type: spec`` string

    def __str__(self) -> str:
        return f"{self.type}: {self.spec}"


@dataclass
class Query:
    """A single benchmark prompt with its expected-outcome checks."""

    service: str        # e.g. "gdc"
    qid: str            # e.g. "Q1" or "A1"
    title: str          # full heading text
    prompt: str         # the natural-language task
    checks: list[Check] = field(default_factory=list)
    source_file: Path | None = None
    lineno: int = 0

    @property
    def ref(self) -> str:
        return f"{self.service}:{self.qid}"


def _qid_from_heading(text: str) -> str:
    m = re.match(r"Query\s+(\d+)", text, re.IGNORECASE)
    if m:
        return f"Q{m.group(1)}"
    m = re.match(r"([A-Z]+\d+)\b", text)
    if m:
        return m.group(1)
    slug = re.sub(r"[^A-Za-z0-9]+", "-", text.strip()).strip("-")
    return slug[:24] or "Q?"


def _extract_prompt(section_lines: list[str]) -> str:
    """Pull the prompt out of a query section.

    Handles both the ``**Prompt:**`` / following-``>``-lines layout and the
    inline ``> **Prompt:** "..."`` layout.
    """
    for i, line in enumerate(section_lines):
        if not _PROMPT_RE.search(line):
            continue
        # Text after the marker on the same line (drop a leading ``>``).
        after = _PROMPT_RE.split(line, maxsplit=1)[1]
        after = after.lstrip(">").strip()
        parts = [after] if after else []
        # Consume following blockquote-continuation lines.
        for cont in section_lines[i + 1:]:
            stripped = cont.strip()
            if stripped.startswith(">"):
                parts.append(stripped.lstrip(">").strip())
            elif not parts:
                # Marker line was bare and the next line isn't a blockquote;
                # nothing to continue with.
                break
            else:
                break
        prompt = " ".join(p for p in parts if p).strip()
        return _strip_quotes(prompt)
    return ""


def _strip_quotes(text: str) -> str:
    text = text.strip()
    pairs = (('"', '"'), ("'", "'"), ("“", "”"), ("‘", "’"))
    for lo, hi in pairs:
        if len(text) >= 2 and text.startswith(lo) and text.endswith(hi):
            return text[1:-1].strip()
    return text


def _extract_checks(section_lines: list[str]) -> list[Check]:
    # Collect from the Checks marker to the end of the section.
    start = None
    for i, line in enumerate(section_lines):
        if _CHECKS_MARKER_RE.search(line):
            start = i
            break
    if start is None:
        return []
    blob = "\n".join(section_lines[start:])
    checks: list[Check] = []
    for m in _CHECK_TOKEN_RE.finditer(blob):
        ctype = m.group("type")
        inside, outside = m.group("inside"), m.group("outside")
        spec = (inside if inside not in (None, "") else (outside or "")).strip()
        # Drop a trailing "and" left by the multi-token-per-line lookahead.
        spec = re.sub(r"\s+and\s*$", "", spec).strip()
        checks.append(Check(type=ctype, spec=spec, raw=f"{ctype}: {spec}"))
    return checks


def service_from_filename(path: Path) -> str:
    name = path.stem  # e.g. "gdc_test"
    return name[:-5] if name.endswith("_test") else name


def parse_query_file(path: Path) -> list[Query]:
    path = Path(path)
    service = service_from_filename(path)
    lines = path.read_text(encoding="utf-8").splitlines()

    # Index heading positions.
    headings: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        m = _HEADING_RE.match(line)
        if m:
            headings.append((i, m.group(2).strip()))

    queries: list[Query] = []
    for idx, (lineno, text) in enumerate(headings):
        end = headings[idx + 1][0] if idx + 1 < len(headings) else len(lines)
        section = lines[lineno:end]
        if not any(_PROMPT_RE.search(s) for s in section):
            continue
        prompt = _extract_prompt(section)
        if not prompt:
            continue
        checks = _extract_checks(section)
        queries.append(
            Query(
                service=service,
                qid=_qid_from_heading(text),
                title=text,
                prompt=prompt,
                checks=checks,
                source_file=path,
                lineno=lineno + 1,
            )
        )
    return queries


def parse_all(queries_dir: Path) -> dict[str, list[Query]]:
    """service -> [Query], for every ``*_test.md`` under ``queries_dir``."""
    out: dict[str, list[Query]] = {}
    for path in sorted(Path(queries_dir).glob("*_test.md")):
        out[service_from_filename(path)] = parse_query_file(path)
    return out
