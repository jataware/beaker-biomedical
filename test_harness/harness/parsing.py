"""Parse the ``tests/`` benchmark corpus into :class:`Query` / :class:`Check` objects.

Layout (one directory per test)::

    tests/<service>/<category>/<test>/
        test.md      — YAML frontmatter (name, description) then the prompt (everything else)
        rationale.md — prose under ``# Intended Behavior`` / ``# Incorrect Behavior`` (NOT parsed)
        eval.yaml    — the machine-read checks: a top-level ``checks:`` list

Each check in that YAML block is a single-key map keyed by its check type::

    checks:
      - number: {name: deceased_subjects, target: 8556, tolerance_percent: 15}
      - behavior: called column_values('vital_status') before filtering
      - substring_any: [dead, deceased]
      - set_contains: {name: top_genes, members: [TP53, CDKN2A]}

A test's ``qid`` is its ``<category>/<test>`` path; its ``ref`` is ``<service>:<qid>``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

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


@dataclass
class Check:
    """One objectively decidable assertion, loaded from the eval YAML.

    ``params`` carries the structured fields the grader reads directly (no
    re-parsing): string types -> ``{"items": [...]}``; ``regex`` ->
    ``{"pattern", "name"}``; ``number`` -> ``{"name", "target", "tol_abs"}``;
    ``set_contains`` -> ``{"name", "members"}``; ``count_at_least`` ->
    ``{"name", "min"}``; ``behavior`` -> ``{}``. ``spec`` is a human-readable
    rendering (shown in reports; for ``behavior``/``count_at_least`` it is also
    what the LLM judge reads).
    """

    type: str
    spec: str
    params: dict = field(default_factory=dict)
    raw: str = ""

    def __str__(self) -> str:
        return f"{self.type}: {self.spec}"


@dataclass
class Query:
    """A single benchmark prompt with its expected-outcome checks."""

    service: str        # e.g. "gdc"
    qid: str            # e.g. "core_query_mechanics/discovery"
    title: str          # frontmatter `name`
    prompt: str         # the natural-language task
    checks: list[Check] = field(default_factory=list)
    description: str = ""
    source_file: Path | None = None
    lineno: int = 1

    @property
    def ref(self) -> str:
        return f"{self.service}:{self.qid}"

    @property
    def leaf(self) -> str:
        return self.qid.rsplit("/", 1)[-1]


# --------------------------------------------------------------------------- #
# building a Check from one YAML item
# --------------------------------------------------------------------------- #
def _as_list(val) -> list[str]:
    if isinstance(val, (list, tuple)):
        return [str(x) for x in val]
    return [str(val)]


def _tol_abs(target: float, val: dict) -> float:
    if val.get("exact"):
        return 0.0
    if "tolerance_percent" in val:
        return abs(target) * float(val["tolerance_percent"]) / 100.0
    if "tolerance_pp" in val:
        return float(val["tolerance_pp"])
    if "tolerance_absolute" in val:
        return float(val["tolerance_absolute"])
    return 0.0


def check_from_item(item: dict) -> Check:
    if not isinstance(item, dict) or len(item) != 1:
        raise ValueError(f"each check must be a single-key map, got: {item!r}")
    ctype, val = next(iter(item.items()))
    if ctype not in CHECK_TYPES:
        raise ValueError(f"unknown check type {ctype!r}")

    if ctype == "substring":
        items = [str(val)]
        return Check(ctype, str(val), {"items": items}, raw=f"{ctype}: {val}")

    if ctype in ("substring_any", "substring_all", "must_not_contain"):
        items = _as_list(val)
        return Check(ctype, ", ".join(items), {"items": items},
                     raw=f"{ctype}: {items}")

    if ctype == "regex":
        if isinstance(val, dict):
            pattern, name = str(val["pattern"]), str(val.get("name", ""))
        else:
            pattern, name = str(val), ""
        spec = f"{name} matches {pattern}".strip() if name else pattern
        return Check(ctype, spec, {"pattern": pattern, "name": name}, raw=spec)

    if ctype == "number":
        name = str(val["name"])
        target = float(val["target"])
        tol = _tol_abs(target, val)
        spec = f"{name} ≈ {target:g} (±{tol:g})" if tol else f"{name} == {target:g}"
        return Check(ctype, spec, {"name": name, "target": target, "tol_abs": tol},
                     raw=spec)

    if ctype == "set_contains":
        name, members = str(val["name"]), _as_list(val["members"])
        spec = f"{name} ⊇ {{{', '.join(members)}}}"
        return Check(ctype, spec, {"name": name, "members": members}, raw=spec)

    if ctype == "count_at_least":
        name, n = str(val["name"]), int(val["min"])
        spec = f"{name} ≥ {n}"
        return Check(ctype, spec, {"name": name, "min": n}, raw=spec)

    # behavior
    return Check(ctype, str(val), {}, raw=f"{ctype}: {val}")


# --------------------------------------------------------------------------- #
# reading test.md / eval.yaml
# --------------------------------------------------------------------------- #
def _split_frontmatter(text: str) -> tuple[dict, str]:
    """Return (frontmatter dict, body). Frontmatter is a leading ``---`` block."""
    if text.startswith("---"):
        m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.DOTALL)
        if m:
            meta = yaml.safe_load(m.group(1)) or {}
            return (meta if isinstance(meta, dict) else {}), m.group(2)
    return {}, text


def _checks_from_yaml(yaml_text: str) -> list[Check]:
    data = yaml.safe_load(yaml_text) or {}
    items = data.get("checks", []) if isinstance(data, dict) else []
    return [check_from_item(it) for it in items]


def parse_test(test_dir: Path, service: str, qid: str) -> Query:
    test_dir = Path(test_dir)
    meta, body = _split_frontmatter((test_dir / "test.md").read_text(encoding="utf-8"))
    eval_yaml = test_dir / "eval.yaml"
    checks = _checks_from_yaml(eval_yaml.read_text(encoding="utf-8")) if eval_yaml.exists() else []
    return Query(
        service=service,
        qid=qid,
        title=str(meta.get("name") or qid),
        prompt=body.strip(),
        checks=checks,
        description=str(meta.get("description") or ""),
        source_file=test_dir / "test.md",
    )


def parse_service(service_dir: Path) -> list[Query]:
    """Every test under ``tests/<service>/`` (any dir containing a ``test.md``)."""
    service_dir = Path(service_dir)
    service = service_dir.name
    queries: list[Query] = []
    for test_md in sorted(service_dir.rglob("test.md")):
        qid = test_md.parent.relative_to(service_dir).as_posix()
        queries.append(parse_test(test_md.parent, service, qid))
    return queries


def parse_all(tests_dir: Path) -> dict[str, list[Query]]:
    """service -> [Query], for every ``<service>/`` subdir of ``tests_dir``."""
    out: dict[str, list[Query]] = {}
    for service_dir in sorted(Path(tests_dir).iterdir()):
        if not service_dir.is_dir() or service_dir.name.startswith((".", "_")):
            continue
        qs = parse_service(service_dir)
        if qs:
            out[service_dir.name] = qs
    return out
