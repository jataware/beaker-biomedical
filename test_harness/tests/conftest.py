"""Pytest wiring for the skill-evaluation harness.

Unit tests (parser + deterministic grader + routing + sandbox) run by default and
need no API key. The *live* tests — one per (query, model) — are opt-in: pass
``--run-live``. They are parametrized from the same ``queries_md`` selection the
CLI uses.

    pytest                                            # unit tests only
    pytest --run-live                                 # full live suite, default model
    pytest --run-live --service gdc                   # just the GDC suite
    pytest --run-live --model claude-sonnet-4-6,qwen/qwen3-coder-next  # compare models
    pytest --run-live --query gdc:Q1,pdc:Q2           # specific queries
"""

from __future__ import annotations

import os

import pytest

from harness.config import DEFAULT_JUDGE_MODEL, DEFAULT_MODEL, HarnessConfig
from harness.llm.routing import resolve_model
from harness.runner import select_queries


def pytest_addoption(parser):
    g = parser.getgroup("harness")
    g.addoption("--run-live", action="store_true", default=False,
                help="run the live skill-evaluation tests (calls model + CRDC APIs)")
    g.addoption("--model", default=os.environ.get("HARNESS_MODEL"),
                help="comma list of test models (routed through litellm)")
    g.addoption("--judge-model", default=DEFAULT_JUDGE_MODEL)
    g.addoption("--service", default=None, help="comma list of services")
    g.addoption("--query", default=None, help="comma list of refs/qids")
    g.addoption("--no-judge", action="store_true", default=False)
    g.addoption("--max-steps", type=int, default=25)
    g.addoption("--harness-timeout", type=int, default=600)


def _csv(val):
    return [v.strip() for v in val.split(",") if v.strip()] if val else None


def _models(config) -> list[str]:
    return _csv(config.getoption("--model")) or [DEFAULT_MODEL]


@pytest.fixture(scope="session")
def harness_config(request) -> HarnessConfig:
    return HarnessConfig(
        model=_models(request.config)[0],
        judge_model=request.config.getoption("--judge-model"),
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
    """Parametrize ``case`` over the selected (query, model) pairs."""
    if "case" not in metafunc.fixturenames:
        return
    cfg = HarnessConfig()
    services = _csv(metafunc.config.getoption("--service"))
    qids = _csv(metafunc.config.getoption("--query"))
    queries = select_queries(cfg.queries_dir, services=services, qids=qids)
    models = _models(metafunc.config)
    cases, ids = [], []
    for model in models:
        for q in queries:
            cases.append((q, model))
            ids.append(f"{q.ref}|{model}")
    metafunc.parametrize("case", cases, ids=ids)


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--run-live"):
        skip_live = pytest.mark.skip(reason="live test; pass --run-live to enable")
        for item in items:
            if "live" in item.keywords:
                item.add_marker(skip_live)
        return

    # Live run: skip if any provider key the selection needs is missing.
    cfg = HarnessConfig()
    needed = {resolve_model(m).api_key_env for m in _models(config)}
    if not config.getoption("--no-judge"):
        needed.add(resolve_model(config.getoption("--judge-model")).api_key_env)
    missing = sorted(env for env in needed if not cfg.key_for(env))
    if missing:
        skip = pytest.mark.skip(reason=f"missing API key(s) for live tests: {', '.join(missing)}")
        for item in items:
            if "live" in item.keywords:
                item.add_marker(skip)
