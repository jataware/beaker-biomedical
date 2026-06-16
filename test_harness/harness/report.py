"""Render run results as a console summary and as JSON."""

from __future__ import annotations

from collections import defaultdict

from .checks import CheckResult
from .runner import RunResult, Suite

_TICK = {True: "PASS", False: "FAIL", None: "—"}


def _short(model: str) -> str:
    """Last path segment of a model id, for fixed-width console columns
    (``openrouter/qwen/qwen3-coder-next`` → ``qwen3-coder-next``)."""
    return model.split("/")[-1]


def _check_dict(r: CheckResult) -> dict:
    return {
        "type": r.check.type,
        "spec": r.check.spec,
        "passed": r.passed,
        "method": r.method,
        "detail": r.detail,
    }


def result_to_dict(res: RunResult) -> dict:
    return {
        "service": res.query.service,
        "qid": res.query.qid,
        "ref": res.query.ref,
        "title": res.query.title,
        "prompt": res.query.prompt,
        "model": res.model,
        "passed": res.passed,
        "score": round(res.grade.score, 3),
        "n_pass": res.grade.n_pass,
        "n_fail": res.grade.n_fail,
        "n_unscored": res.grade.n_unscored,
        "elapsed_s": round(res.elapsed, 1),
        "error": res.error,
        "steps": res.run.steps,
        "final_answer": res.run.final_answer,
        "checks": [_check_dict(r) for r in res.grade.results],
        # Full agent trace, for post-hoc inspection without re-running: each step's
        # code plus its captured output. `transcript` is the same flat rendering
        # the judge sees (answer + code + clipped stdout), easy to eyeball.
        "code_trace": [
            {"code": s.code, "stdout": s.stdout, "stderr": s.stderr, "error": s.error}
            for s in res.run.code_trace
        ],
        "transcript": res.run.transcript(),
    }


def suite_to_dict(suite: Suite) -> dict:
    # Keep top-level ``model`` (the configured default) so the per-file `compare`
    # subcommand still reads it; ``models`` lists every model actually run.
    return {
        "model": suite.config.model,
        "models": sorted({r.model for r in suite.results}),
        "judge_model": suite.config.judge_model,
        "judge": suite.config.use_judge,
        "results": [result_to_dict(r) for r in suite.results],
        "summary": summary_stats(suite),
    }


def summary_stats(suite: Suite) -> dict:
    by_model: dict[str, list[RunResult]] = defaultdict(list)
    for r in suite.results:
        by_model[r.model].append(r)
    out = {}
    for model, rs in by_model.items():
        passed = sum(1 for r in rs if r.passed)
        checks_pass = sum(r.grade.n_pass for r in rs)
        checks_fail = sum(r.grade.n_fail for r in rs)
        checks_unscored = sum(r.grade.n_unscored for r in rs)
        out[model] = {
            "queries": len(rs),
            "queries_passed": passed,
            "query_pass_rate": round(passed / len(rs), 3) if rs else 0.0,
            "checks_passed": checks_pass,
            "checks_failed": checks_fail,
            "checks_unscored": checks_unscored,
            "check_pass_rate": round(checks_pass / (checks_pass + checks_fail), 3)
            if (checks_pass + checks_fail) else 0.0,
        }
    return out


# --------------------------------------------------------------------------- #
# console rendering
# --------------------------------------------------------------------------- #
def render_run_line(res: RunResult) -> str:
    status = "PASS" if res.passed else "FAIL"
    err = f"  !{res.error}" if res.error else ""
    return (
        f"[{status}] {_short(res.model):16s} {res.ref:10s} "
        f"{res.grade.n_pass}/{res.grade.n_scored} checks "
        f"({res.grade.n_unscored} unscored)  {res.elapsed:5.1f}s{err}"
    )


def render_detail(res: RunResult) -> str:
    lines = [
        f"=== {res.ref} [{res.model}] — {res.query.title}",
        f"    prompt: {res.query.prompt}",
        f"    {'PASS' if res.passed else 'FAIL'}  "
        f"score={res.grade.score:.2f}  steps={res.run.steps}  {res.elapsed:.1f}s"
        + (f"  error={res.error}" if res.error else ""),
    ]
    for r in res.grade.results:
        mark = _TICK[r.passed]
        lines.append(f"      [{mark:4s}] {r.check.type}: {r.check.spec}")
        if r.detail:
            lines.append(f"             ↳ {r.detail}")
    return "\n".join(lines)


def render_summary(suite: Suite) -> str:
    stats = summary_stats(suite)
    lines = ["", "=" * 64,
             f"SUMMARY  (judge={suite.config.judge_model if suite.config.use_judge else 'off'})",
             "=" * 64]
    for model, s in stats.items():
        lines.append(
            f"  {_short(model):16s}  queries {s['queries_passed']}/{s['queries']} "
            f"({s['query_pass_rate']*100:.0f}%)   "
            f"checks {s['checks_passed']}/{s['checks_passed'] + s['checks_failed']} "
            f"({s['check_pass_rate']*100:.0f}%)   "
            f"unscored {s['checks_unscored']}"
        )
    return "\n".join(lines)


def render_failures(suite: Suite) -> str:
    fails = [r for r in suite.results if not r.passed]
    if not fails:
        return "All selected queries passed."
    lines = ["", f"FAILURES ({len(fails)}):"]
    for r in fails:
        bad = [cr for cr in r.grade.results if cr.passed is False]
        why = "; ".join(f"{c.check.type}:{c.detail}" for c in bad[:3]) or (r.error or "?")
        lines.append(f"  {_short(r.model):16s} {r.ref:10s} — {why}")
    return "\n".join(lines)
