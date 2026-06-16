"""Side-by-side comparison of N harness report JSONs (one per model / run).

Reads reports written by ``harness.cli run -o report.json`` and prints a
query × model grid plus per-check detail — handy for comparing how different
models do on the same queries. Tolerant of both the harness schema (top-level
``results``) and the older experiment schema (top-level ``queries``).

    python -m harness.cli compare report_a.json report_b.json ...
"""

from __future__ import annotations

import json

_MARK = {True: "PASS", False: "FAIL", None: "----"}


def _rows(report: dict) -> list[dict]:
    return report.get("results") or report.get("queries") or []


def _key(row: dict) -> str:
    return row.get("ref") or row.get("qid") or "?"


def _model(report: dict) -> str:
    return str(report.get("model", "?")).split("/")[-1]


def render(paths: list[str]) -> str:
    reports = [json.load(open(p)) for p in paths]
    models = [_model(r) for r in reports]
    w = max((len(m) for m in models), default=8) + 4

    keys: list[str] = []
    for r in reports:
        for row in _rows(r):
            if _key(row) not in keys:
                keys.append(_key(row))

    def get(r: dict, k: str):
        return next((row for row in _rows(r) if _key(row) == k), None)

    out = [f"\n{'query':<10}" + "".join(f"{m:<{w}}" for m in models),
           "-" * (10 + w * len(models))]
    for k in keys:
        line = f"{k:<10}"
        for r in reports:
            row = get(r, k)
            if row is None:
                cell = "—"
            else:
                chks = row.get("checks", [])
                npv = sum(1 for c in chks if c["passed"] is True)
                nfv = sum(1 for c in chks if c["passed"] is False)
                nuv = sum(1 for c in chks if c["passed"] is None)
                cell = f"{_MARK[row.get('passed')]} {npv}/{npv + nfv}" + (f"+{nuv}u" if nuv else "")
            line += f"{cell:<{w}}"
        out.append(line)
    out.append("-" * (10 + w * len(models)))
    totals = f"{'PASS':<10}"
    for r in reports:
        rows = _rows(r)
        passed = sum(1 for row in rows if row.get("passed"))
        totals += f"{passed}/{len(rows)}".ljust(w)
    out.append(totals)

    for k in keys:
        base = next((get(r, k) for r in reports if get(r, k)), None)
        if not base:
            continue
        out.append(f"\n{'=' * 72}\n{k}")
        for idx, chk in enumerate(base.get("checks", [])):
            out.append(f"  • {chk['type']}: {chk['spec']}"[:80])
            line = "      "
            for r in reports:
                row = get(r, k)
                c = row["checks"][idx] if row and idx < len(row.get("checks", [])) else None
                line += f"{_model(r)[:16]}={_MARK[c['passed']] if c else '?'}  "
            out.append(line)
    return "\n".join(out)
