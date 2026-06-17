"""Orchestration: select queries, run them through a model, grade the result.

Runs are independent, so the suite parallelizes across them. We use *processes*,
not threads: the agent mutates process-global ``sys.stdout`` while executing
model-generated code (the ``run_python`` sandbox's ``redirect_stdout``), so
concurrent runs in one process would scramble each agent's captured tool output.
One process per run keeps that state isolated.
"""

from __future__ import annotations

import multiprocessing as mp
import time
from concurrent.futures import (
    ProcessPoolExecutor,
    ThreadPoolExecutor,
    TimeoutError as FutureTimeout,
    as_completed,
)
from dataclasses import dataclass, field, replace
from typing import Callable, Optional

from . import skills
from .checks import QueryGrade, grade_query
from .config import HarnessConfig
from .llm import AgentRun, LiteLLMAgent
from .parsing import Query, parse_all


@dataclass
class RunResult:
    query: Query
    model: str
    run: AgentRun
    grade: QueryGrade
    elapsed: float
    error: Optional[str] = None

    @property
    def ref(self) -> str:
        return self.query.ref

    @property
    def passed(self) -> bool:
        return self.error is None and self.grade.passed


@dataclass
class Suite:
    config: HarnessConfig
    results: list[RunResult] = field(default_factory=list)


def _qid_matches(q: Query, qid_filter: set[str]) -> bool:
    """A filter token selects a query if it equals its full ref
    (``cda:core_query_mechanics/discovery``), its qid
    (``core_query_mechanics/discovery``), its leaf slug (``discovery``), or
    ``<service>:<leaf>`` (``cda:discovery``)."""
    candidates = {q.ref.lower(), q.qid.lower(), q.leaf.lower(),
                  f"{q.service}:{q.leaf}".lower()}
    return bool(candidates & qid_filter)


def select_queries(
    tests_dir,
    services: Optional[list[str]] = None,
    qids: Optional[list[str]] = None,
) -> list[Query]:
    """Flatten parsed queries, optionally filtered by service and/or qid.

    ``qids`` accepts full refs ("cda:core_query_mechanics/discovery"), bare qids
    ("core_query_mechanics/discovery"), or leaf slugs ("discovery").
    """
    allq = parse_all(tests_dir)
    selected: list[Query] = []
    qid_filter = {q.lower() for q in qids} if qids else None
    svc_filter = {s.lower() for s in services} if services else None
    for svc, qs in allq.items():
        if svc_filter and svc.lower() not in svc_filter:
            continue
        for q in qs:
            if qid_filter is not None and not _qid_matches(q, qid_filter):
                continue
            selected.append(q)
    return selected


def _run_with_timeout(fn: Callable[[], AgentRun], timeout: int) -> tuple[AgentRun, Optional[str]]:
    with ThreadPoolExecutor(max_workers=1) as ex:
        future = ex.submit(fn)
        try:
            return future.result(timeout=timeout), None
        except FutureTimeout:
            return (
                AgentRun(model="?", final_answer="", error="timeout"),
                f"timed out after {timeout}s",
            )
        except Exception as e:  # agent blew up
            return AgentRun(model="?", final_answer="", error=str(e)), str(e)


def run_query(
    query: Query,
    model: str,
    config: HarnessConfig,
    judge=None,
) -> RunResult:
    cfg = config if config.model == model else replace(config, model=model)
    agent = LiteLLMAgent(cfg)
    system = skills.build_system_prompt(cfg)
    user_message = skills.build_user_message(query.service, query.prompt, cfg)

    # The progressive-disclosure reader, bound to this run's skill. Confined to the
    # bound skill so a run can't read another commons' docs (see read_skill_resource).
    def read_resource(skill, path):
        return skills.read_skill_resource(query.service, path, cfg, skill=skill)

    t0 = time.monotonic()
    run, err = _run_with_timeout(
        lambda: agent.run(user_message, system, read_resource=read_resource), cfg.timeout
    )
    elapsed = time.monotonic() - t0
    run.model = model

    grade = grade_query(
        query, run.final_answer, run.transcript(),
        judge=judge if cfg.use_judge else None,
    )
    return RunResult(query=query, model=model, run=run,
                     grade=grade, elapsed=elapsed, error=err or run.error)


def _worker(payload: "tuple[Query, str, HarnessConfig]") -> RunResult:
    """Process-pool entrypoint: run one (query, model) pair and grade it.

    The judge is rebuilt here (it isn't carried across the process boundary);
    it's only constructed when ``config.use_judge`` is set.
    """
    query, model, config = payload
    judge = None
    if config.use_judge:
        from .judge import LLMJudge
        judge = LLMJudge(config)
    return run_query(query, model, config, judge=judge)


def _errored_result(query: Query, model: str, message: str) -> RunResult:
    return RunResult(
        query=query,
        model=model,
        run=AgentRun(model=model, final_answer="", error=message),
        grade=grade_query(query, "", "", judge=None),
        elapsed=0.0,
        error=message,
    )


def run_suite(
    config: HarnessConfig,
    models: list[str],
    services: Optional[list[str]] = None,
    qids: Optional[list[str]] = None,
    judge=None,
    concurrency: int = 1,
    on_start: Optional[Callable[[Query, str, int, int], None]] = None,
    on_done: Optional[Callable[[RunResult, int, int], None]] = None,
) -> Suite:
    queries = select_queries(config.tests_dir, services=services, qids=qids)
    pairs = [(query, model) for model in models for query in queries]
    suite = Suite(config=config)
    total = len(pairs)

    if concurrency <= 1 or total <= 1:
        for i, (query, model) in enumerate(pairs, 1):
            if on_start:
                on_start(query, model, i, total)
            result = run_query(query, model, config, judge=judge)
            suite.results.append(result)
            if on_done:
                on_done(result, i, total)
        return suite

    # Parallel: one process per run. Workers build their own judge from config.
    ctx = mp.get_context("spawn")
    payloads = [(query, model, config) for (query, model) in pairs]
    done = 0
    with ProcessPoolExecutor(max_workers=min(concurrency, total), mp_context=ctx) as ex:
        futures = {ex.submit(_worker, p): (p[0], p[1]) for p in payloads}
        for future in as_completed(futures):
            done += 1
            query, model = futures[future]
            try:
                result = future.result()
            except Exception as e:  # worker crash; keep the suite going
                result = _errored_result(query, model, f"worker error: {e}")
            suite.results.append(result)
            if on_done:
                on_done(result, done, total)

    # Stable report order regardless of completion order.
    order = {m: i for i, m in enumerate(models)}
    suite.results.sort(key=lambda r: (order.get(r.model, 0), r.query.service, r.query.qid))
    return suite
