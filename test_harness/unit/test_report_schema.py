"""Unit tests for the enriched report schema (``harness.report.suite_to_dict``).

No API key: builds a Suite from synthetic RunResults and asserts the dict the
dashboard consumes — schema_version, meta, skills capture, per-result run_uid /
category / docs_opened, check family, the interleaved+capped ``trace`` (code
steps and read_skill_file loads), and that the redundant ``transcript`` field is
gone. ``capture_skills`` reads the real ``skills/`` tree, so this also guards
that the cda skill stays loadable.
"""

import json

from harness import report
from harness.checks import CheckResult, QueryGrade
from harness.config import HarnessConfig
from harness.llm.agent import AgentRun
from harness.llm.sandbox import CodeStep, ResourceStep
from harness.parsing import Check, Query
from harness.runner import RunResult, Suite

OPENED = "examples/handoff_to_gdc.md"   # read via open() in Python (heuristic match)
LOADED = "references/DISCOVERY.md"      # read via the read_skill_file tool (precise)


def _run_result(model="claude-sonnet-4-6"):
    q = Query(service="cda", qid="round_trips/melanoma_mutation_landscape",
              title="T", prompt="do the thing",
              checks=[Check("substring", "TCGA-SKCM", {"items": ["TCGA-SKCM"]}),
                      Check("behavior", "did the handoff", {})])
    trace = [
        CodeStep(code=f'print(open(r"/x/skills/cancer-data-aggregator/{OPENED}").read())',
                 stdout="ok", stderr="", error=None),
        ResourceStep(skill="cancer-data-aggregator", path=LOADED, ok=True,
                     content="discovery doc", n_chars=13),
        CodeStep(code="print(1)", stdout="x" * 40_000, stderr="", error="Boom"),
    ]
    run = AgentRun(model=model, final_answer="answer TCGA-SKCM", trace=trace, steps=3)
    grade = QueryGrade(query=q, results=[
        CheckResult(q.checks[0], True, "deterministic", "found"),
        CheckResult(q.checks[1], None, "unscored", "needs judge"),
    ])
    return RunResult(query=q, model=model, run=run, grade=grade, elapsed=12.3)


def _suite():
    return Suite(config=HarnessConfig(model="claude-sonnet-4-6"), results=[_run_result()])


def test_top_level_and_meta():
    d = report.suite_to_dict(_suite(), rep=2, elapsed_total_s=99.0)
    assert d["schema_version"] == "1"
    assert d["model"] == "claude-sonnet-4-6"           # kept for compare.py
    assert d["models"] == ["claude-sonnet-4-6"]
    assert d["meta"]["rep"] == 2
    assert d["meta"]["elapsed_total_s"] == 99.0
    assert d["meta"]["config"]["max_steps"] == 50
    assert "git" in d["meta"] and "generated_at" in d["meta"]
    json.dumps(d)  # must be JSON-serializable end to end


def test_skills_capture():
    d = report.suite_to_dict(_suite())
    cda = d["skills"]["cda"]
    assert cda["name"] == "cancer-data-aggregator"
    assert cda["skill_md"].strip()                     # verbatim injected SKILL.md
    assert OPENED in cda["files"]                       # offered file listing


def test_per_result_fields():
    r = report.suite_to_dict(_suite(), rep=3)["results"][0]
    assert r["category"] == "round_trips"
    assert r["rep"] == 3
    assert len(r["run_uid"]) == 8
    # union of tool loads (precise, first) and open(...) heuristic, order-preserving
    assert r["docs_opened"] == [LOADED, OPENED]
    assert "transcript" not in r                        # dropped (reconstructed in UI)
    assert r["checks"][0]["family"] == "deterministic"
    assert r["checks"][1]["family"] == "semantic"


def test_trace_interleaves_code_and_skill_loads():
    trace = report.suite_to_dict(_suite())["results"][0]["trace"]
    assert [s["kind"] for s in trace] == ["python", "skill_file", "python"]
    load = trace[1]
    assert load["step"] == 2 and load["path"] == LOADED and load["ok"] is True
    assert load["content"] == "discovery doc"


def test_trace_capped():
    trace = report.suite_to_dict(_suite())["results"][0]["trace"]
    step = next(s for s in trace if s.get("error") == "Boom")
    assert step["kind"] == "python" and step["step"] == 3
    assert step["stdout_truncated"] is True
    assert step["stdout_len"] == 40_000
    assert len(step["stdout"]) == report._meta.STDOUT_CAP
