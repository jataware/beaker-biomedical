"""CLI test runner for the agent-skill evaluation harness.

Examples
--------
List every parsed query and its checks (no API calls)::

    python -m harness.cli list --checks

Dry-run a selection — assemble prompts and show the checks, but call nothing::

    python -m harness.cli run --service gdc --dry-run

Run two GDC queries comparing two models, write a JSON report::

    python -m harness.cli run --query gdc:project_discovery,gdc:survival_logrank \
        --model claude-sonnet-4-6,qwen/qwen3-coder-next -o report.json

Run the whole suite on a single model (explicit opt-in)::

    python -m harness.cli run --all --model claude-sonnet-4-6
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import report
from .config import DEFAULT_JUDGE_MODEL, DEFAULT_MODEL, HarnessConfig
from .llm.routing import PROVIDER_KEY_ENV, resolve_model
from .runner import run_suite, select_queries

# CLI key-override flags -> the *_API_KEY env var they populate.
_KEY_FLAGS = {
    "anthropic_api_key": "ANTHROPIC_API_KEY",
    "openai_api_key": "OPENAI_API_KEY",
    "gemini_api_key": "GEMINI_API_KEY",
    "openrouter_api_key": "OPENROUTER_API_KEY",
}


def _split_csv(val: str | None) -> list[str] | None:
    if not val:
        return None
    return [v.strip() for v in val.split(",") if v.strip()]


def cmd_list(args) -> int:
    config = HarnessConfig(tests_dir=Path(args.tests_dir))
    queries = select_queries(
        config.tests_dir,
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
            print(f"  {q.qid:42s} {nc:2d} checks  — {q.title}")
            if args.checks:
                for c in q.checks:
                    print(f"        · {c.type}: {c.spec}")
    print(f"\n{len(queries)} queries, {total_checks} checks total.")
    return 0


def cmd_run(args) -> int:
    services = _split_csv(args.service)
    qids = _split_csv(args.query)
    models = _split_csv(args.model) or [DEFAULT_MODEL]

    if not args.dry_run and not args.all and not services and not qids:
        raise SystemExit(
            "Refusing to run the full live suite implicitly. Pass --all to run "
            "everything, or narrow with --service / --query. (Use --dry-run to "
            "preview without calling the API.)"
        )

    # Explicit per-provider key overrides from the CLI (env/.env fill the rest).
    api_keys = {env: getattr(args, flag) for flag, env in _KEY_FLAGS.items()
                if getattr(args, flag)}

    config = HarnessConfig(
        model=models[0],
        judge_model=args.judge_model,
        api_keys=api_keys,
        max_steps=args.max_steps,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        use_judge=not args.no_judge,
        timeout=args.timeout,
        verbose=args.verbose,
        tests_dir=Path(args.tests_dir),
    )

    queries = select_queries(config.tests_dir, services=services, qids=qids)
    if not queries:
        raise SystemExit("No queries matched the selection.")

    if args.dry_run:
        return _dry_run(config, queries, models, args)

    # Resolve exactly the provider keys this run needs — one per distinct provider
    # across the test models plus (if grading) the judge model — and carry them on
    # config so the spawn-based workers don't depend on the parent's env/.env.
    needed = {resolve_model(m).api_key_env for m in models}
    if config.use_judge:
        needed.add(resolve_model(config.judge_model).api_key_env)
    for env_var in sorted(needed):
        key = config.key_for(env_var)
        if not key:
            providers = ", ".join(
                p.value for p, e in PROVIDER_KEY_ENV.items() if e == env_var)
            raise SystemExit(
                f"No {env_var} found (checked the matching --*-api-key flag, env, "
                f"and repo .env). Required to reach the selected {providers} model(s)"
                + (" / judge." if config.use_judge else ".")
            )
        config.api_keys[env_var] = key

    total_runs = len(queries) * len(models)
    concurrency = max(1, min(args.concurrency, total_runs))

    # Sequential mode streams a per-run "running…" line and builds the judge
    # in-process; parallel mode builds the judge inside each worker.
    judge = None
    if concurrency == 1 and config.use_judge:
        from .judge import LLMJudge
        judge = LLMJudge(config)

    print(
        f"Running {len(queries)} queries × {len(models)} model(s) "
        f"= {total_runs} runs | models={','.join(models)} "
        f"| judge={config.judge_model if config.use_judge else 'off'} "
        f"| concurrency={concurrency}"
    )

    def on_start(q, model, i, total):
        print(f"[{i}/{total}] {report._short(model):16s} {q.ref:12s} running…", flush=True)

    def on_done(res, i, total):
        print(f"[{i}/{total}] " + report.render_run_line(res), flush=True)

    suite = run_suite(
        config, models, services=services, qids=qids, judge=judge,
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


def _dry_run(config, queries, models, args) -> int:
    from . import skills
    print(f"DRY RUN — {len(queries)} queries × {len(models)} model(s), no API calls.\n")
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
    print("\nModel routing:")
    for m in models:
        r = resolve_model(m)
        print(f"  {m}  →  {r.litellm_model}  [{r.provider.value}, key {r.api_key_env}]")
    if config.use_judge:
        jr = resolve_model(config.judge_model)
        print(f"  judge: {config.judge_model}  →  {jr.litellm_model}  "
              f"[{jr.provider.value}, key {jr.api_key_env}]")
    return 0


def cmd_compare(args) -> int:
    from . import compare
    print(compare.render(args.reports))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="harness", description="Evaluate CRDC agent skills against the tests/ answer keys."
    )
    p.add_argument("--tests-dir", default=str(HarnessConfig().tests_dir),
                   help="root of the tests/<service>/<category>/<test>/ corpus")
    sub = p.add_subparsers(dest="command", required=True)

    pl = sub.add_parser("list", help="list parsed queries/checks (no API)")
    pl.add_argument("--service", help="comma list: gdc,pdc,cda,gc,icdc,ctdc,psdc")
    pl.add_argument("--query", help="comma list of refs/qids/slugs: "
                    "cda:core_query_mechanics/discovery, discovery")
    pl.add_argument("--checks", action="store_true", help="show each check")
    pl.set_defaults(func=cmd_list)

    pr = sub.add_parser("run", help="run queries through a model and grade")
    pr.add_argument("--model", default=os.environ.get("HARNESS_MODEL"),
                    help="comma list of test models, each routed through litellm by "
                         "harness.llm.routing: bare claude-*/gpt-*/o*/gemini-* hit the "
                         "native provider, everything else (e.g. qwen/qwen3-coder-next, "
                         "google/gemma-4-31b-it) falls back to OpenRouter; an explicit "
                         "provider/ prefix is honoured. Listing >1 model compares them "
                         f"in one report. Default: {DEFAULT_MODEL}.")
    pr.add_argument("--judge-model", default=DEFAULT_JUDGE_MODEL,
                    help=f"model for the LLM judge (default: {DEFAULT_JUDGE_MODEL}); "
                         "routed through litellm exactly like --model, independent of it")
    pr.add_argument("--service", help="comma list of services to run")
    pr.add_argument("--query", help="comma list of refs/qids to run")
    pr.add_argument("--all", action="store_true", help="run the entire suite")
    pr.add_argument("--max-steps", type=int, default=50)
    pr.add_argument("-j", "--concurrency", type=int, default=8,
                    help="parallel runs (separate processes); 1 = sequential "
                         "with live streaming. Higher risks provider rate limits.")
    pr.add_argument("--temperature", type=float, default=0.0)
    pr.add_argument("--max-tokens", type=int, default=4096)
    pr.add_argument("--timeout", type=int, default=600, help="seconds per query")
    pr.add_argument("--no-judge", action="store_true",
                    help="skip LLM grading of behavior/count_at_least checks")
    pr.add_argument("--anthropic-api-key", default="", help="override ANTHROPIC_API_KEY")
    pr.add_argument("--openai-api-key", default="", help="override OPENAI_API_KEY")
    pr.add_argument("--gemini-api-key", default="", help="override GEMINI_API_KEY")
    pr.add_argument("--openrouter-api-key", default="", help="override OPENROUTER_API_KEY")
    pr.add_argument("--dry-run", action="store_true", help="preview only, no API")
    pr.add_argument("--show-prompt", action="store_true",
                    help="(dry-run) print assembled prompts")
    pr.add_argument("--detail", action="store_true", help="print per-check detail")
    pr.add_argument("--verbose", action="store_true", help="verbose agent output")
    pr.add_argument("-o", "--output", help="write a JSON report to this path")
    pr.set_defaults(func=cmd_run)

    pc = sub.add_parser("compare", help="side-by-side comparison of report JSONs (no API)")
    pc.add_argument("reports", nargs="+", help="report JSON paths written by `run -o`")
    pc.set_defaults(func=cmd_compare)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
