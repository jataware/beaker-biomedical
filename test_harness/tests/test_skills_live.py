"""Live skill-evaluation tests — one per (query, backend) pair.

Each runs a benchmark prompt through an agent backend (with the matching CRDC
skill loaded), then asserts every *scored* check from the query's
``Checks (machine-gradeable)`` block passes. Opt-in via ``--run-live``.
"""

import pytest

from harness import report
from harness.runner import run_query


@pytest.mark.live
def test_skill_query(case, harness_config, judge):
    query, backend = case
    result = run_query(query, backend, harness_config, judge=judge)

    assert result.error is None, f"agent run errored: {result.error}\n" + report.render_detail(result)
    assert result.grade.n_scored > 0, f"no gradeable checks for {query.ref}"

    failed = [r for r in result.grade.results if r.passed is False]
    assert not failed, (
        f"{len(failed)} check(s) failed for {result.ref} [{backend}]\n"
        + report.render_detail(result)
    )
