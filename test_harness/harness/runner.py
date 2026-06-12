"""Orchestration: select queries, run them through a backend, grade the result.

Runs are independent, so the suite parallelizes across them. We use *processes*,
not threads: both backends mutate process-global ``sys.stdout`` while executing
model-generated code (the plain backend's ``redirect_stdout``; archytas's
``PythonTool``), so concurrent runs in one process would scramble each agent's
captured tool output. One process per run keeps that state isolated.
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
from dataclasses import dataclass, field
from typing import Callable, Optional

from . import skills
from .backends import AgentRun, get_backend
from .checks import QueryGrade, grade_query
from .config import HarnessConfig
from .parsing import Query, parse_all


@dataclass
class RunResult:
    query: Query
    backend: str
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


def select_queries(
    queries_dir,
    services: Optional[list[str]] = None,
    qids: Optional[list[str]] = None,
) -> list[Query]:
    """Flatten parsed queries, optionally filtered by service and/or qid.

    ``qids`` accepts bare ids ("Q1", "A1") or "service:qid" refs ("gdc:Q1").
    """
    allq = parse_all(queries_dir)
    selected: list[Query] = []
    qid_filter = {q.lower() for q in qids} if qids else None
    svc_filter = {s.lower() for s in services} if services else None
    for svc, qs in allq.items():
        if svc_filter and svc.lower() not in svc_filter:
            continue
        for q in qs:
            if qid_filter is not None:
                if (q.qid.lower() not in qid_filter
                        and q.ref.lower() not in qid_filter):
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
                AgentRun(backend="?", final_answer="", error="timeout"),
                f"timed out after {timeout}s",
            )
        except Exception as e:  # backend blew up
            return AgentRun(backend="?", final_answer="", error=str(e)), str(e)


def run_query(
    query: Query,
    backend_name: str,
    config: HarnessConfig,
    judge=None,
) -> RunResult:
    backend = get_backend(backend_name, config)
    system = skills.build_system_prompt(config)
    user_message = skills.build_user_message(query.service, query.prompt, config)

    t0 = time.monotonic()
    run, err = _run_with_timeout(
        lambda: backend.run(user_message, system), config.timeout
    )
    elapsed = time.monotonic() - t0
    run.backend = backend_name

    grade = grade_query(
        query, run.final_answer, run.transcript(),
        judge=judge if config.use_judge else None,
    )
    return RunResult(query=query, backend=backend_name, run=run,
                     grade=grade, elapsed=elapsed, error=err or run.error)


def _worker(payload: "tuple[Query, str, HarnessConfig]") -> RunResult:
    """Process-pool entrypoint: run one (query, backend) pair and grade it.

    The judge is rebuilt here (an Anthropic client isn't picklable, so it can't
    be passed in); it's only constructed when ``config.use_judge`` is set.
    """
    query, backend_name, config = payload
    judge = None
    if config.use_judge:
        from .judge import LLMJudge
        judge = LLMJudge(config)
    return run_query(query, backend_name, config, judge=judge)


def _errored_result(query: Query, backend_name: str, message: str) -> RunResult:
    return RunResult(
        query=query,
        backend=backend_name,
        run=AgentRun(backend=backend_name, final_answer="", error=message),
        grade=grade_query(query, "", "", judge=None),
        elapsed=0.0,
        error=message,
    )


def run_suite(
    config: HarnessConfig,
    backends: list[str],
    services: Optional[list[str]] = None,
    qids: Optional[list[str]] = None,
    judge=None,
    concurrency: int = 1,
    on_start: Optional[Callable[[Query, str, int, int], None]] = None,
    on_done: Optional[Callable[[RunResult, int, int], None]] = None,
) -> Suite:
    queries = select_queries(config.queries_dir, services=services, qids=qids)
    pairs = [(query, backend) for backend in backends for query in queries]
    suite = Suite(config=config)
    total = len(pairs)

    if concurrency <= 1 or total <= 1:
        for i, (query, backend_name) in enumerate(pairs, 1):
            if on_start:
                on_start(query, backend_name, i, total)
            result = run_query(query, backend_name, config, judge=judge)
            suite.results.append(result)
            if on_done:
                on_done(result, i, total)
        return suite

    # Parallel: one process per run. Workers build their own judge from config.
    ctx = mp.get_context("spawn")
    payloads = [(query, backend, config) for (query, backend) in pairs]
    done = 0
    with ProcessPoolExecutor(max_workers=min(concurrency, total), mp_context=ctx) as ex:
        futures = {ex.submit(_worker, p): (p[0], p[1]) for p in payloads}
        for future in as_completed(futures):
            done += 1
            query, backend_name = futures[future]
            try:
                result = future.result()
            except Exception as e:  # worker crash; keep the suite going
                result = _errored_result(query, backend_name, f"worker error: {e}")
            suite.results.append(result)
            if on_done:
                on_done(result, done, total)

    # Stable report order regardless of completion order.
    order = {b: i for i, b in enumerate(backends)}
    suite.results.sort(key=lambda r: (order.get(r.backend, 0), r.query.service, r.query.qid))
    return suite
