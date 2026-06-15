#!/usr/bin/env python
"""Aggregate openrouter_try.py report JSONs into a side-by-side comparison.

Usage: python compare_reports.py report_a.json report_b.json ...
"""
import json
import sys

MARK = {True: "PASS", False: "FAIL", None: "----"}


def main(paths):
    reports = [json.load(open(p)) for p in paths]
    models = [r["model"].split("/")[-1] for r in reports]
    w = max(len(m) for m in models) + 4

    qids = []
    for r in reports:
        for q in r["queries"]:
            if q["qid"] not in qids:
                qids.append(q["qid"])

    def get(r, qid):
        return next((x for x in r["queries"] if x["qid"] == qid), None)

    # ---- summary grid: query x model ----
    print(f"\n{'query':<8}" + "".join(f"{m:<{w}}" for m in models))
    print("-" * (8 + w * len(models)))
    for qid in qids:
        row = f"{qid:<8}"
        for r in reports:
            q = get(r, qid)
            if q is None:
                cell = "—"
            else:
                np = sum(1 for c in q["checks"] if c["passed"] is True)
                nf = sum(1 for c in q["checks"] if c["passed"] is False)
                nu = sum(1 for c in q["checks"] if c["passed"] is None)
                cell = f"{MARK[q['passed']]} {np}/{np + nf}" + (f"+{nu}u" if nu else "")
            row += f"{cell:<{w}}"
        print(row)
    print("-" * (8 + w * len(models)))
    totals = f"{'PASS':<8}"
    for r in reports:
        p = sum(1 for q in r["queries"] if q["passed"])
        totals += f"{p}/{len(r['queries'])}".ljust(w)
    print(totals)

    # ---- per-check detail ----
    for qid in qids:
        print(f"\n{'=' * 72}\n{qid}")
        base = next((get(r, qid) for r in reports if get(r, qid)), None)
        for idx, chk in enumerate(base["checks"]):
            print(f"  • {chk['type']}: {chk['spec']}"[:80])
            line = "      "
            for r in reports:
                q = get(r, qid)
                c = q["checks"][idx] if q and idx < len(q["checks"]) else None
                m = r["model"].split("/")[-1][:16]
                line += f"{m}={MARK[c['passed']] if c else '?'}  "
            print(line)


if __name__ == "__main__":
    main(sys.argv[1:])
