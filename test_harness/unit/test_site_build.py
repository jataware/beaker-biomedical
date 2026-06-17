"""Unit tests for the static dashboard builder (``harness.site.build``).

No API key, no browser: writes synthetic report JSONs (two reps of one cda test,
one pass + one fail, with a reference doc loaded via read_skill_file in the
trace), builds the self-contained HTML, then asserts the aggregation (cells,
dense reps, reference reach), the snapshots (rendered SKILL.md, tests corpus),
and the inlining (placeholders gone, data round-trips through the <script>
escaping).
"""

import json
import re

import pytest

from harness import report
from harness.checks import CheckResult, QueryGrade
from harness.config import HarnessConfig
from harness.llm.agent import AgentRun
from harness.llm.sandbox import CodeStep, ResourceStep
from harness.parsing import Check, Query
from harness.runner import RunResult, Suite
from harness.site import build_site
from harness.site.build import aggregate, load_report

REF = "cda:core_query_mechanics/discovery"
DOC = "references/DISCOVERY.md"  # a real file in the cda skill


def _report_file(tmp_path, name, *, rep, passed):
    q = Query(service="cda", qid="core_query_mechanics/discovery",
              title="Discovery", prompt="what tables exist?",
              checks=[Check("substring", "subject", {"items": ["subject"]})])
    # the doc reaches the agent via the read_skill_file tool (precise reach), then
    # it runs a query — an interleaved trace, the real shape.
    trace = [
        ResourceStep(skill="cancer-data-aggregator", path=DOC, ok=True,
                     content="tables: subject, file", n_chars=21),
        CodeStep(code="from cdapython import tables; print(tables())",
                 stdout="subject\nfile", stderr="", error=None),
    ]
    run = AgentRun(model="claude-sonnet-4-6",
                   final_answer="subject" if passed else "nope",
                   trace=trace, steps=2)
    grade = QueryGrade(query=q, results=[
        CheckResult(q.checks[0], passed, "deterministic", "found" if passed else "missing")])
    suite = Suite(config=HarnessConfig(model="claude-sonnet-4-6"),
                  results=[RunResult(query=q, model="claude-sonnet-4-6", run=run,
                                     grade=grade, elapsed=3.0)])
    p = tmp_path / name
    p.write_text(json.dumps(report.suite_to_dict(suite, rep=rep)))
    return p


@pytest.fixture
def two_reps(tmp_path):
    return [_report_file(tmp_path, "rep1.json", rep=1, passed=True),
            _report_file(tmp_path, "rep2.json", rep=2, passed=False)]


def test_aggregate_cells_reps_and_reach(two_reps):
    data = aggregate([load_report(p) for p in two_reps])
    assert data["summary"]["runs"] == 2 and data["summary"]["runs_passed"] == 1
    cell = data["cells"][f"{REF}|claude-sonnet-4-6"]
    assert cell["pass"] == 1 and cell["total"] == 2 and len(cell["run_uids"]) == 2
    assert sorted(r["rep"] for r in data["runs"]) == [1, 2]          # dense
    assert len({r["run_uid"] for r in data["runs"]}) == 2            # unique ids
    doc = next(f for f in data["skills"]["cda"]["files"] if f["path"] == DOC)
    assert doc["reach"] == {"opened": 2, "total": 2}                 # reach lit up
    assert data["skills"]["cda"]["rendered"]["SKILL.md"].lstrip().startswith("<")
    # the read_skill_file load survives into each run's interleaved trace
    assert all(any(s["kind"] == "skill_file" and s["path"] == DOC for s in r["trace"])
               for r in data["runs"])


def test_tests_corpus_snapshot(two_reps):
    data = aggregate([load_report(p) for p in two_reps])
    t = next(t for t in data["tests"] if t["ref"] == REF)
    assert t["prompt_html"] and t["checks"]
    # whole corpus is browsable, not just the run test
    assert len(data["tests"]) > 1 and {x["service"] for x in data["tests"]} >= {"cda", "gdc"}


def test_build_inlines_one_file(two_reps, tmp_path):
    out = build_site([str(p) for p in two_reps], tmp_path / "index.html")
    html = out.read_text()
    for ph in ("/*__STYLE__*/", "/*__APP__*/", "__REPORT_DATA__"):
        assert ph not in html
    assert ".matrix" in html and "function render" in html
    blob = re.search(r'id="report-data">(.*?)</script>', html, re.S).group(1)
    data = json.loads(blob.replace("<\\/", "</"))     # reverse the script-escape
    assert data["summary"]["runs"] == 2
    assert any(s.get("kind") == "skill_file"          # skill loads inline too
               for r in data["runs"] for s in r.get("trace", []))


def test_load_report_tolerates_legacy_backend(tmp_path):
    legacy = tmp_path / "old.json"
    legacy.write_text(json.dumps({
        "model": "qwen/x",
        "results": [{"service": "cda", "qid": "a/b", "ref": "cda:a/b",
                     "backend": "qwen/x", "passed": True, "checks": []}],
    }))
    rep = load_report(legacy)
    assert rep["meta"]["rep"] == 1                     # filled default
    assert rep["results"][0]["model"] == "qwen/x"      # backend -> model
