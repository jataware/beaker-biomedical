"""Grade a parsed :class:`~harness.parsing.Check` against an agent's answer.

Two families of check:

* **deterministic** — graded mechanically, no LLM: ``substring`` / ``substring_any``
  / ``substring_all`` / ``must_not_contain`` / ``regex`` / ``number`` /
  ``set_contains``. These are string- and number-matching, exactly as the
  ``Automated grading`` sections describe.
* **semantic** — graded by an optional LLM judge over the agent's *code/tool
  trace* and answer: ``behavior`` (a method assertion) and ``count_at_least``
  (an enumeration-cardinality assertion). With no judge they are left
  ``unscored`` and excluded from pass/fail totals.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from typing import Callable, Optional

from .parsing import Check, Query

DETERMINISTIC_TYPES = {
    "substring", "substring_any", "substring_all",
    "must_not_contain", "regex", "number", "set_contains",
}
SEMANTIC_TYPES = {"behavior", "count_at_least"}

# A judge takes (check, query, answer, transcript) and returns (passed, reason).
# ``passed`` may be None if the judge itself could not decide.
Judge = Callable[[Check, Query, str, str], "tuple[Optional[bool], str]"]

_NUM_TOKEN_RE = re.compile(r"[-+]?\d[\d,]*(?:\.\d+)?")
_NUM_SPEC_RE = re.compile(
    r"^\s*(?P<name>.+?)\s*(?P<op>≈|==|=|~|≥|>=|≤|<=)\s*"
    r"(?P<val>[-+]?[\d,]*\.?\d+)\s*(?P<pct>%)?\s*"
    r"(?:\(\s*±\s*(?P<tol>[\d.]+)\s*(?P<tolunit>pp|%)?\s*\)\s*)?$"
)


@dataclass
class CheckResult:
    check: Check
    passed: Optional[bool]      # None == unscored
    method: str                 # "deterministic" | "judge" | "unscored" | "error"
    detail: str = ""

    @property
    def scored(self) -> bool:
        return self.passed is not None


# --------------------------------------------------------------------------- #
# spec helpers
# --------------------------------------------------------------------------- #
def _strip_explanation(spec: str) -> str:
    """Drop a trailing ``— explanation`` (only the structured types need this;
    harmless for the inside-backtick spellings, which never carry one)."""
    return re.split(r"\s+[—–]\s+", spec, maxsplit=1)[0].strip()


def _parse_list(spec: str) -> list[str]:
    spec = spec.strip()
    start, end = spec.find("["), spec.rfind("]")
    if start != -1 and end != -1:
        spec = spec[start:end + 1]
    try:
        val = ast.literal_eval(spec)
        if isinstance(val, (list, tuple)):
            return [str(x) for x in val]
    except (ValueError, SyntaxError):
        pass
    # Fallback: pull quoted strings.
    return [a or b for a, b in re.findall(r'"([^"]*)"|\'([^\']*)\'', spec)]


def _parse_set(spec: str) -> list[str]:
    m = re.search(r"\{(.*)\}", spec, re.DOTALL)
    body = m.group(1) if m else spec.split("⊇", 1)[-1]
    return [tok.strip() for tok in body.split(",") if tok.strip()]


def _parse_regex_pattern(spec: str) -> str:
    spec = _strip_explanation(spec).strip()
    m = re.search(r"\bmatch(?:es)?\b", spec)
    if m:
        spec = spec[m.end():].strip()
    return spec.strip().strip("`").strip()


def _numbers_in(text: str) -> list[float]:
    out = []
    for tok in _NUM_TOKEN_RE.findall(text):
        try:
            out.append(float(tok.replace(",", "")))
        except ValueError:
            continue
    return out


def parse_number_spec(spec: str) -> Optional[dict]:
    spec = _strip_explanation(spec)
    m = _NUM_SPEC_RE.match(spec)
    if not m:
        return None
    value = float(m.group("val").replace(",", ""))
    op = m.group("op")
    tol_raw, tolunit = m.group("tol"), m.group("tolunit")
    if tol_raw is None:
        tol_abs = 0.0
    else:
        tol = float(tol_raw)
        if tolunit == "%":
            tol_abs = abs(value) * tol / 100.0
        else:  # "pp" or bare ±N
            tol_abs = tol
    return {"name": m.group("name").strip(), "op": op, "value": value, "tol_abs": tol_abs}


# --------------------------------------------------------------------------- #
# deterministic grading
# --------------------------------------------------------------------------- #
def _grade_deterministic(check: Check, answer: str) -> CheckResult:
    t, spec = check.type, check.spec
    hay = answer.lower()

    if t == "substring":
        needle = _strip_explanation(spec).strip().strip('"').strip("'")
        ok = needle.lower() in hay
        return CheckResult(check, ok, "deterministic",
                           f"{'found' if ok else 'missing'}: {needle!r}")

    if t in ("substring_any", "substring_all", "must_not_contain"):
        items = _parse_list(spec)
        present = [s for s in items if s.lower() in hay]
        if t == "substring_any":
            ok = len(present) > 0
            return CheckResult(check, ok, "deterministic",
                               f"matched {present or 'none'} of {items}")
        if t == "substring_all":
            missing = [s for s in items if s.lower() not in hay]
            return CheckResult(check, not missing, "deterministic",
                               f"missing {missing}" if missing else "all present")
        # must_not_contain
        return CheckResult(check, not present, "deterministic",
                           f"forbidden present: {present}" if present else "clean")

    if t == "set_contains":
        members = _parse_set(spec)
        missing = [m for m in members if m.lower() not in hay]
        return CheckResult(check, not missing, "deterministic",
                           f"missing {missing}" if missing else f"all {len(members)} present")

    if t == "regex":
        pattern = _parse_regex_pattern(spec)
        try:
            ok = re.search(pattern, answer) is not None
        except re.error as e:
            return CheckResult(check, None, "error", f"bad regex {pattern!r}: {e}")
        return CheckResult(check, ok, "deterministic",
                           f"/{pattern}/ {'matched' if ok else 'no match'}")

    if t == "number":
        parsed = parse_number_spec(spec)
        if not parsed:
            return CheckResult(check, None, "error", f"unparseable number spec: {spec!r}")
        nums = _numbers_in(answer)
        hits = [n for n in nums if abs(n - parsed["value"]) <= parsed["tol_abs"] + 1e-9]
        ok = len(hits) > 0
        return CheckResult(
            check, ok, "deterministic",
            f"{parsed['name']}={parsed['value']}±{parsed['tol_abs']:g}: "
            f"{'matched ' + repr(hits[0]) if ok else 'no number in tolerance'}",
        )

    return CheckResult(check, None, "error", f"unknown deterministic type {t}")


def grade_check(check: Check, query: Query, answer: str, transcript: str,
                judge: Optional[Judge] = None) -> CheckResult:
    if check.type in DETERMINISTIC_TYPES:
        return _grade_deterministic(check, answer)
    if check.type in SEMANTIC_TYPES:
        if judge is None:
            return CheckResult(check, None, "unscored",
                               "semantic check (needs --judge)")
        try:
            passed, reason = judge(check, query, answer, transcript)
        except Exception as e:  # judge failures must not crash a run
            return CheckResult(check, None, "error", f"judge error: {e}")
        return CheckResult(check, passed, "judge" if passed is not None else "error", reason)
    return CheckResult(check, None, "error", f"unknown check type {check.type}")


@dataclass
class QueryGrade:
    query: Query
    results: list[CheckResult]

    @property
    def n_pass(self) -> int:
        return sum(1 for r in self.results if r.passed is True)

    @property
    def n_fail(self) -> int:
        return sum(1 for r in self.results if r.passed is False)

    @property
    def n_unscored(self) -> int:
        return sum(1 for r in self.results if r.passed is None)

    @property
    def n_scored(self) -> int:
        return self.n_pass + self.n_fail

    @property
    def score(self) -> float:
        return self.n_pass / self.n_scored if self.n_scored else 0.0

    @property
    def passed(self) -> bool:
        """A query passes when every *scored* check passes (and at least one was)."""
        return self.n_scored > 0 and self.n_fail == 0


def grade_query(query: Query, answer: str, transcript: str,
                judge: Optional[Judge] = None) -> QueryGrade:
    results = [grade_check(c, query, answer, transcript, judge=judge)
               for c in query.checks]
    return QueryGrade(query=query, results=results)
