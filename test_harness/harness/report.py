"""Render run results as a console summary and as JSON."""

from __future__ import annotations

from collections import defaultdict

from . import meta as _meta
from .checks import CheckResult, DETERMINISTIC_TYPES
from .llm import CodeStep, ResourceStep
from .runner import RunResult, Suite

_TICK = {True: "PASS", False: "FAIL", None: "—"}


def _clip(text: str | None, cap: int = _meta.STDOUT_CAP) -> tuple[str, bool, int]:
    """(clipped_text, truncated, original_len) for a captured stream."""
    text = text or ""
    n = len(text)
    return (text, False, n) if n <= cap else (text[:cap], True, n)


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
        "family": "deterministic" if r.check.type in DETERMINISTIC_TYPES else "semantic",
    }


def _step_dict(i: int, s: CodeStep | ResourceStep) -> dict:
    if isinstance(s, ResourceStep):
        content, c_trunc, c_len = _clip(s.content)
        d = {"step": i, "kind": "skill_file", "skill": s.skill, "path": s.path,
             "ok": s.ok, "content": content, "error": s.error}
        if c_trunc:
            d["content_truncated"], d["content_len"] = True, c_len
        return d
    out, out_trunc, out_len = _clip(s.stdout)
    err, err_trunc, err_len = _clip(s.stderr)
    d = {"step": i, "kind": "python", "code": s.code,
         "stdout": out, "stderr": err, "error": s.error}
    if out_trunc:
        d["stdout_truncated"], d["stdout_len"] = True, out_len
    if err_trunc:
        d["stderr_truncated"], d["stderr_len"] = True, err_len
    return d


def _docs_opened(res: RunResult, skill_files: list[str]) -> list[str]:
    """Skill docs this run actually read, order-preserving and de-duplicated:
    files loaded via the ``read_skill_file`` tool (precise), unioned with any the
    agent opened from Python (matched heuristically against executed code)."""
    via_tool = [s.path for s in res.run.trace if isinstance(s, ResourceStep) and s.ok]
    via_code = _meta.detect_docs_opened(
        (s.code for s in res.run.trace if isinstance(s, CodeStep)), skill_files)
    return list(dict.fromkeys(via_tool + via_code))


def result_to_dict(res: RunResult, *, rep: int = 1,
                   skill_files: list[str] | None = None) -> dict:
    qid = res.query.qid
    return {
        "service": res.query.service,
        "category": qid.split("/", 1)[0] if "/" in qid else "",
        "qid": qid,
        "ref": res.query.ref,
        "run_uid": _meta.run_uid(res.query.ref, res.model, rep),
        "rep": rep,
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
        # On-demand skill docs that actually reached the agent this run — read via
        # the read_skill_file tool, or opened from Python (see _docs_opened).
        "docs_opened": _docs_opened(res, skill_files or []),
        "final_answer": res.run.final_answer,
        "checks": [_check_dict(r) for r in res.grade.results],
        # Full agent trace, for post-hoc inspection without re-running: code steps
        # (code + captured output) and skill-file loads (path + content), interleaved
        # in execution order, each tagged with ``kind``. Clipped, truncation flagged.
        # The flat judge-view transcript is reconstructed by the dashboard from this.
        "trace": [_step_dict(i, s) for i, s in enumerate(res.run.trace, 1)],
    }


def suite_to_dict(suite: Suite, *, rep: int = 1,
                  elapsed_total_s: float | None = None) -> dict:
    models = sorted({r.model for r in suite.results})
    services = {r.query.service for r in suite.results}
    skills_cap = _meta.capture_skills(services, suite.config)
    # Keep top-level ``model`` (the configured default) so the per-file `compare`
    # subcommand still reads it; ``models`` lists every model actually run.
    return {
        "schema_version": _meta.SCHEMA_VERSION,
        "meta": _meta.build_meta(suite.config, models, rep=rep,
                                 elapsed_total_s=elapsed_total_s),
        "model": suite.config.model,
        "models": models,
        "judge_model": suite.config.judge_model,
        "judge": suite.config.use_judge,
        "skills": skills_cap,
        "results": [
            result_to_dict(r, rep=rep,
                           skill_files=skills_cap.get(r.query.service, {}).get("files", []))
            for r in suite.results
        ],
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
