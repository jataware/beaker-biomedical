"""Pytest wiring for the skill-evaluation harness.

Unit tests (parser + deterministic grader) run by default and need no API key.
The *live* tests — one per (query, backend) — are opt-in: pass ``--run-live``.
They are parametrized from the same ``queries_md`` selection the CLI uses.

    pytest                                   # unit tests only
    pytest --run-live --backend both         # full live suite, both harnesses
    pytest --run-live --service gdc          # just the GDC suite (plain backend)
    pytest --run-live --query gdc:Q1,pdc:Q2  # specific queries
"""

from __future__ import annotations

import os

import pytest

from harness.backends import BACKENDS
from harness.config import DEFAULT_MODEL, HarnessConfig
from harness.runner import run_query, select_queries


def pytest_addoption(parser):
    g = parser.getgroup("harness")
    g.addoption("--run-live", action="store_true", default=False,
                help="run the live skill-evaluation tests (calls APIs)")
    g.addoption("--backend", default="plain", help="plain | archytas | both")
    g.addoption("--model", default=os.environ.get("HARNESS_MODEL", DEFAULT_MODEL))
    g.addoption("--service", default=None, help="comma list of services")
    g.addoption("--query", default=None, help="comma list of refs/qids")
    g.addoption("--no-judge", action="store_true", default=False)
    g.addoption("--max-steps", type=int, default=25)
    g.addoption("--harness-timeout", type=int, default=600)


def _csv(val):
    return [v.strip() for v in val.split(",") if v.strip()] if val else None


def _backends(name):
    return list(BACKENDS) if name == "both" else [name]


@pytest.fixture(scope="session")
def harness_config(request) -> HarnessConfig:
    return HarnessConfig(
        model=request.config.getoption("--model"),
        use_judge=not request.config.getoption("--no-judge"),
        max_steps=request.config.getoption("--max-steps"),
        timeout=request.config.getoption("--harness-timeout"),
    )


@pytest.fixture(scope="session")
def judge(harness_config):
    if not harness_config.use_judge:
        return None
    from harness.judge import LLMJudge
    return LLMJudge(harness_config)


def pytest_generate_tests(metafunc):
    """Parametrize ``case`` over the selected (query, backend) pairs."""
    if "case" not in metafunc.fixturenames:
        return
    cfg = HarnessConfig()
    services = _csv(metafunc.config.getoption("--service"))
    qids = _csv(metafunc.config.getoption("--query"))
    queries = select_queries(cfg.queries_dir, services=services, qids=qids)
    backends = _backends(metafunc.config.getoption("--backend"))
    cases, ids = [], []
    for backend in backends:
        for q in queries:
            cases.append((q, backend))
            ids.append(f"{q.ref}|{backend}")
    metafunc.parametrize("case", cases, ids=ids)


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-live"):
        if not HarnessConfig().resolved_key():
            skip = pytest.mark.skip(reason="no ANTHROPIC_API_KEY for live tests")
            for item in items:
                if "live" in item.keywords:
                    item.add_marker(skip)
        return
    skip_live = pytest.mark.skip(reason="live test; pass --run-live to enable")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip_live)
