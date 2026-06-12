"""CLI test runner for the agent-skill evaluation harness.

Examples
--------
List every parsed query and its checks (no API calls)::

    python -m harness.cli list --checks

Dry-run a selection — assemble prompts and show the checks, but call nothing::

    python -m harness.cli run --service gdc --dry-run

Run two GDC queries on both backends and write a JSON report::

    python -m harness.cli run --query gdc:Q1,gdc:Q2 --backend both -o report.json

Run the whole suite on the archytas backend (explicit opt-in)::

    python -m harness.cli run --all --backend archytas
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import report
from .backends import BACKENDS
from .config import DEFAULT_MODEL, HarnessConfig
from .runner import run_suite, select_queries


def _split_csv(val: str | None) -> list[str] | None:
    if not val:
        return None
    return [v.strip() for v in val.split(",") if v.strip()]


def _resolve_backends(name: str) -> list[str]:
    if name == "both":
        return list(BACKENDS)
    if name in BACKENDS:
        return [name]
    raise SystemExit(f"--backend must be one of: plain, archytas, both (got {name!r})")


def cmd_list(args) -> int:
    config = HarnessConfig(queries_dir=Path(args.queries_dir))
    queries = select_queries(
        config.queries_dir,
        services=_split_csv(args.service),
        qids=_split_csv(args.query),
    )
    by_svc: dict[str, list] = {}
    for q in queries:
        by_svc.setdefault(q.service, []).append(q)
    total_checks = 0
    for svc, qs in by_svc.items():
        print(f"\n{svc}  ({len(qs)} queries)")
        for q in qs:
            nc = len(q.checks)
            total_checks += nc
            print(f"  {q.ref:12s} {nc:2d} checks  — {q.title}")
            if args.checks:
                for c in q.checks:
                    print(f"        · {c.type}: {c.spec}")
    print(f"\n{len(queries)} queries, {total_checks} checks total.")
    return 0


def cmd_run(args) -> int:
    backends = _resolve_backends(args.backend)
    services = _split_csv(args.service)
    qids = _split_csv(args.query)

    if not args.dry_run and not args.all and not services and not qids:
        raise SystemExit(
            "Refusing to run the full live suite implicitly. Pass --all to run "
            "everything, or narrow with --service / --query. (Use --dry-run to "
            "preview without calling the API.)"
        )

    config = HarnessConfig(
        model=args.model,
        backend=backends[0],
        api_key=args.api_key or "",
        max_steps=args.max_steps,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        use_judge=not args.no_judge,
        timeout=args.timeout,
        verbose=args.verbose,
        queries_dir=Path(args.queries_dir),
    )

    queries = select_queries(config.queries_dir, services=services, qids=qids)
    if not queries:
        raise SystemExit("No queries matched the selection.")

    if args.dry_run:
        return _dry_run(config, queries, backends, args)

    key = config.resolved_key()
    if not key:
        raise SystemExit(
            "No ANTHROPIC_API_KEY found (checked --api-key, env, and repo .env)."
        )
    # Carry the resolved key explicitly so spawned workers don't depend on env/.env.
    config.api_key = key

    total_runs = len(queries) * len(backends)
    concurrency = max(1, min(args.concurrency, total_runs))

    # Sequential mode streams a per-run "running…" line and builds the judge
    # in-process; parallel mode builds the judge inside each worker.
    judge = None
    if concurrency == 1 and config.use_judge:
        from .judge import LLMJudge
        judge = LLMJudge(config)

    print(
        f"Running {len(queries)} queries × {len(backends)} backend(s) "
        f"= {total_runs} runs | model={config.model} "
        f"| judge={'on' if config.use_judge else 'off'} "
        f"| concurrency={concurrency}"
    )

    def on_start(q, backend, i, total):
        print(f"[{i}/{total}] {backend:8s} {q.ref:12s} running…", flush=True)

    def on_done(res, i, total):
        print(f"[{i}/{total}] " + report.render_run_line(res), flush=True)

    suite = run_suite(
        config, backends, services=services, qids=qids, judge=judge,
        concurrency=concurrency,
        on_start=on_start if concurrency == 1 else None,
        on_done=on_done,
    )

    if args.detail:
        print()
        for res in suite.results:
            print(report.render_detail(res))
            print()
    print(report.render_failures(suite))
    print(report.render_summary(suite))

    if args.output:
        Path(args.output).write_text(json.dumps(report.suite_to_dict(suite), indent=2))
        print(f"\nWrote JSON report to {args.output}")

    # Exit non-zero if any run failed (CI-friendly).
    return 0 if all(r.passed for r in suite.results) else 1


def _dry_run(config, queries, backends, args) -> int:
    from . import skills
    print(f"DRY RUN — {len(queries)} queries × {len(backends)} backend(s), no API calls.\n")
    for q in queries:
        print(f"  {q.ref:12s} {len(q.checks):2d} checks — {q.title}")
        det = sum(1 for c in q.checks if c.type in
                  {"substring", "substring_any", "substring_all",
                   "must_not_contain", "regex", "number", "set_contains"})
        sem = len(q.checks) - det
        print(f"        deterministic={det}  semantic(judge)={sem}")
        if args.show_prompt:
            msg = skills.build_user_message(q.service, q.prompt, config)
            print("        --- assembled user message (first 400 chars) ---")
            print("        " + msg[:400].replace("\n", "\n        "))
    print(f"\nBackends: {', '.join(backends)} | model={config.model} | "
          f"judge={'on' if not args.no_judge else 'off'}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="harness", description="Evaluate CRDC agent skills against the queries_md answer keys."
    )
    p.add_argument("--queries-dir", default=str(HarnessConfig().queries_dir),
                   help="directory of *_test.md files")
    sub = p.add_subparsers(dest="command", required=True)

    pl = sub.add_parser("list", help="list parsed queries/checks (no API)")
    pl.add_argument("--service", help="comma list: gdc,pdc,cda,gc,icdc,ctdc,psdc")
    pl.add_argument("--query", help="comma list of refs/qids: gdc:Q1,A1")
    pl.add_argument("--checks", action="store_true", help="show each check")
    pl.set_defaults(func=cmd_list)

    pr = sub.add_parser("run", help="run queries through a backend and grade")
    pr.add_argument("--backend", default="plain", help="plain | archytas | both")
    pr.add_argument("--model", default=os.environ.get("HARNESS_MODEL", DEFAULT_MODEL))
    pr.add_argument("--service", help="comma list of services to run")
    pr.add_argument("--query", help="comma list of refs/qids to run")
    pr.add_argument("--all", action="store_true", help="run the entire suite")
    pr.add_argument("--max-steps", type=int, default=50)
    pr.add_argument("-j", "--concurrency", type=int, default=8,
                    help="parallel runs (separate processes); 1 = sequential "
                         "with live streaming. Higher risks Anthropic rate limits.")
    pr.add_argument("--temperature", type=float, default=0.0)
    pr.add_argument("--max-tokens", type=int, default=4096)
    pr.add_argument("--timeout", type=int, default=600, help="seconds per query")
    pr.add_argument("--no-judge", action="store_true",
                    help="skip LLM grading of behavior/count_at_least checks")
    pr.add_argument("--api-key", default="", help="override ANTHROPIC_API_KEY")
    pr.add_argument("--dry-run", action="store_true", help="preview only, no API")
    pr.add_argument("--show-prompt", action="store_true",
                    help="(dry-run) print assembled prompts")
    pr.add_argument("--detail", action="store_true", help="print per-check detail")
    pr.add_argument("--verbose", action="store_true", help="verbose agent output")
    pr.add_argument("-o", "--output", help="write a JSON report to this path")
    pr.set_defaults(func=cmd_run)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
