"""Unit tests for the harness internals — parser + deterministic grader.

These need no API key and run by default. They guard the machinery that turns
the ``tests/<service>/<category>/<test>/`` corpus into executable checks.
"""

import pytest

from harness.config import TESTS_DIR, SERVICE_TO_SKILL
from harness.parsing import Query, check_from_item, parse_all
from harness.checks import grade_check

ALL = parse_all(TESTS_DIR)


def _q():
    return Query(service="x", qid="cat/t", title="", prompt="")


def _grade(item, answer):
    """Build a Check from one YAML item ({type: value}) and grade it."""
    return grade_check(check_from_item(item), _q(), answer, answer)


# --------------------------------------------------------------------------- #
# parsing the corpus
# --------------------------------------------------------------------------- #
def test_all_seven_suites_present():
    assert set(ALL) == set(SERVICE_TO_SKILL)


def test_every_query_has_prompt_and_checks():
    for svc, qs in ALL.items():
        assert qs, f"{svc} parsed to zero queries"
        for q in qs:
            assert q.prompt.strip(), f"{q.ref} has empty prompt"
            assert q.checks, f"{q.ref} has zero checks"
            assert "/" in q.qid, f"{q.ref} qid is not <category>/<test>"


def test_known_query_counts():
    counts = {svc: len(qs) for svc, qs in ALL.items()}
    assert counts == {
        "cda": 16, "ctdc": 5, "gc": 5, "gdc": 6, "icdc": 5, "pdc": 3, "psdc": 5,
    }


def test_no_unknown_check_types():
    valid = {"substring", "substring_any", "substring_all", "must_not_contain",
             "regex", "number", "set_contains", "count_at_least", "behavior"}
    for qs in ALL.values():
        for q in qs:
            for c in q.checks:
                assert c.type in valid, f"{q.ref}: {c.type}"


def test_every_number_check_has_target_and_tolerance():
    for qs in ALL.values():
        for q in qs:
            for c in q.checks:
                if c.type == "number":
                    assert "target" in c.params and "tol_abs" in c.params, f"{q.ref}: {c.spec!r}"


def test_refs_unique():
    refs = [q.ref for qs in ALL.values() for q in qs]
    assert len(refs) == len(set(refs))


# --------------------------------------------------------------------------- #
# building a Check from a YAML item
# --------------------------------------------------------------------------- #
def test_check_from_item_number_tolerances():
    assert check_from_item({"number": {"name": "x", "target": 8556, "tolerance_percent": 15}}
                           ).params["tol_abs"] == pytest.approx(8556 * 0.15)
    assert check_from_item({"number": {"name": "x", "target": 72, "tolerance_pp": 8}}
                           ).params["tol_abs"] == 8.0
    assert check_from_item({"number": {"name": "x", "target": -1.65, "tolerance_absolute": 0.5}}
                           ).params["tol_abs"] == 0.5
    assert check_from_item({"number": {"name": "x", "target": 0, "exact": True}}
                           ).params["tol_abs"] == 0.0


def test_check_from_item_regex_scalar_and_named():
    assert check_from_item({"regex": "PDC\\d{6}"}).params == {"pattern": "PDC\\d{6}", "name": ""}
    named = check_from_item({"regex": {"name": "ids", "pattern": "phs\\d+"}})
    assert named.params["pattern"] == "phs\\d+"


def test_check_from_item_rejects_multikey():
    with pytest.raises(ValueError):
        check_from_item({"number": {}, "behavior": "x"})


# --------------------------------------------------------------------------- #
# deterministic grading
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("item,answer,expected", [
    ({"number": {"name": "APC_pct", "target": 72, "tolerance_pp": 8}}, "APC mutated in 71.7% of cases", True),
    ({"number": {"name": "kidney", "target": 2436, "tolerance_percent": 15}}, "2,436 kidney cases", True),
    ({"number": {"name": "r", "target": -1.65, "tolerance_absolute": 0.5}}, "normal median -1.7", True),
    ({"number": {"name": "bladder", "target": 0, "exact": True}}, "returns 0 cases", True),
    ({"number": {"name": "pValue", "target": 0.37, "tolerance_absolute": 0.10}}, "p was 0.85", False),
])
def test_number_checks(item, answer, expected):
    assert _grade(item, answer).passed is expected


def test_substring_any_all_mustnot():
    assert _grade({"substring_any": ["Proteome", "Glycoproteome"]}, "a Glycoproteome study").passed
    assert _grade({"substring_all": ["APC", "TP53", "KRAS"]}, "APC TP53").passed is False
    assert _grade({"must_not_contain": ["18289"]}, "denominator 18289").passed is False
    assert _grade({"must_not_contain": ["only TCGA"]}, "TARGET-WT largest").passed


def test_substring_single():
    assert _grade({"substring": "Cisplatin"}, "treated with Cisplatin").passed
    assert _grade({"substring": "Cisplatin"}, "no drug named").passed is False


def test_set_contains_with_spaces():
    r = _grade({"set_contains": {"name": "stages",
                                 "members": ["stage i", "stage ii", "stage iii", "stage iv"]}},
               "stage i 270, stage ii 60, stage iii 125, stage iv 83")
    assert r.passed


def test_regex_variants():
    assert _grade({"regex": "PDC\\d{6}"}, "study PDC000127").passed
    assert _grade({"regex": {"name": "phs", "pattern": "phs(001094|001286)"}}, "phs001094 cited").passed
    assert _grade({"regex": "dg\\.4DFC/[0-9a-f-]{36}"},
                  "dg.4DFC/0123abcd-4567-89ab-cdef-0123456789ab").passed


def test_semantic_unscored_without_judge():
    assert _grade({"behavior": "used case_filters"}, "x").passed is None
    assert _grade({"count_at_least": {"name": "projects", "min": 10}}, "x").passed is None
