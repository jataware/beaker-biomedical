"""Unit tests for the harness internals — parser + deterministic grader.

These need no API key and run by default. They guard the machinery that turns
the authoritative ``*_test.md`` files into executable checks.
"""

import pytest

from harness.config import QUERIES_DIR, SERVICE_TO_SKILL
from harness.parsing import Check, Query, parse_all, parse_query_file
from harness.checks import grade_check, parse_number_spec

ALL = parse_all(QUERIES_DIR)


def _chk(t, s):
    return Check(type=t, spec=s, raw=f"{t}: {s}")


def _q():
    return Query(service="x", qid="1", title="", prompt="")


def _grade(t, s, answer):
    return grade_check(_chk(t, s), _q(), answer, answer)


# --------------------------------------------------------------------------- #
# parsing
# --------------------------------------------------------------------------- #
def test_all_seven_suites_present():
    assert set(ALL) == set(SERVICE_TO_SKILL)


def test_every_query_has_prompt_and_checks():
    for svc, qs in ALL.items():
        assert qs, f"{svc} parsed to zero queries"
        for q in qs:
            assert q.prompt.strip(), f"{q.ref} has empty prompt"
            assert q.checks, f"{q.ref} has zero checks"


def test_known_query_counts():
    counts = {svc: len(qs) for svc, qs in ALL.items()}
    assert counts == {
        "cda": 17, "ctdc": 5, "gc": 5, "gdc": 6, "icdc": 5, "pdc": 3, "psdc": 5,
    }


def test_ctdc_colon_outside_backticks_form():
    # ctdc writes `type`: spec  (colon outside) — must still parse, incl. a
    # nested backtick in the spec.
    q1 = ALL["ctdc"][0]
    types = {c.type for c in q1.checks}
    assert {"number", "substring_all", "behavior", "must_not_contain"} <= types
    behaviors = [c.spec for c in q1.checks if c.type == "behavior"]
    assert any("variables" in s for s in behaviors)


def test_multiple_checks_on_one_bullet():
    # gdc Q2 packs four `number:` tokens; some files put two per line.
    gdc_q2 = next(q for q in ALL["gdc"] if q.qid == "Q2")
    nums = [c for c in gdc_q2.checks if c.type == "number"]
    assert len(nums) >= 4


def test_no_unknown_check_types():
    valid = {"substring", "substring_any", "substring_all", "must_not_contain",
             "regex", "number", "set_contains", "count_at_least", "behavior"}
    for qs in ALL.values():
        for q in qs:
            for c in q.checks:
                assert c.type in valid


def test_every_number_spec_parses():
    for qs in ALL.values():
        for q in qs:
            for c in q.checks:
                if c.type == "number":
                    assert parse_number_spec(c.spec), f"{q.ref}: {c.spec!r}"


# --------------------------------------------------------------------------- #
# deterministic grading
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("spec,answer,expected", [
    ("APC_pct ≈ 72% (±8 pp)", "APC mutated in 71.7% of cases", True),
    ("total_kidney_cases ≈ 2436 (±15%)", "2,436 kidney cases", True),
    ("normal_median_log2_ratio ≈ -1.65 (±0.5)", "normal median -1.7", True),
    ("urinary_bladder_cases == 0", "returns 0 cases", True),
    ("pValue ≈ 0.37 (±0.10)", "p was 0.85", False),
])
def test_number_checks(spec, answer, expected):
    assert _grade("number", spec, answer).passed is expected


def test_substring_any_all_mustnot():
    assert _grade("substring_any", '["Proteome", "Glycoproteome"]', "a Glycoproteome study").passed
    assert _grade("substring_all", '["APC", "TP53", "KRAS"]', "APC TP53").passed is False
    assert _grade("must_not_contain", '["18289"]', "denominator 18289").passed is False
    assert _grade("must_not_contain", '["only TCGA"]', "TARGET-WT largest").passed


def test_set_contains_with_spaces():
    r = _grade("set_contains", "stages ⊇ {stage i, stage ii, stage iii, stage iv}",
               "stage i 270, stage ii 60, stage iii 125, stage iv 83")
    assert r.passed


def test_regex_variants():
    assert _grade("regex", r"ids match PDC\d{6}", "study PDC000127").passed
    assert _grade("regex", r"phs(001094|001286)", "phs001094 cited").passed
    assert _grade("regex", r"drs_id matches dg\.4DFC/[0-9a-f-]{36}",
                  "dg.4DFC/0123abcd-4567-89ab-cdef-0123456789ab").passed


def test_semantic_unscored_without_judge():
    assert _grade("behavior", "used case_filters", "x").passed is None
    assert _grade("count_at_least", "projects ≥ 10", "x").passed is None
