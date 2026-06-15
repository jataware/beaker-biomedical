#!/usr/bin/env python
"""EXPERIMENTAL — OpenRouter trial runner for the CDA skill tests.

Drives `cda_test.md` prompts through any OpenRouter model using a `run_python`
ReAct loop — the same execution model as the harness's `plain` backend, but
talking OpenAI-style tool-calling via litellm so any OpenRouter model works.
Live `cdapython` runs in-process, so the A-series count checks grade against
real CDA numbers.

Grading reuses the harness's deterministic checks; the semantic `behavior` /
`count_at_least` checks are judged by Claude (also via OpenRouter, so one key).
Both the agent and the judge are keyed off OPENROUTER_API_KEY (from repo .env).

Models that don't honour the OpenAI tool schema and instead emit their native
tool-call format as text (e.g. gemma-4-31b-it) are handled by a text-format
fallback parser (see `parse_text_tool_calls`).

Usage (run from this directory, with ../../.venv):
    ../../.venv/bin/python run_openrouter.py                    # A2, A5, C1 on the default model
    ../../.venv/bin/python run_openrouter.py --query A2,A5      # pick queries
    ../../.venv/bin/python run_openrouter.py --model qwen/qwen3.5-397b-a17b --max-steps 40
    ../../.venv/bin/python run_openrouter.py --no-judge         # deterministic checks only
    ../../.venv/bin/python run_openrouter.py -o results/report_x.json
"""

from __future__ import annotations

import argparse
import io
import json
import logging
import os
import re
import sys
import traceback
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

# Import the harness modules directly (they're pure-python: no archytas/anthropic
# pulled in), without `pip install -e .`. This file lives at
# test_harness/experiments/openrouter/, so the harness package is two levels up.
HARNESS_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HARNESS_ROOT))

from harness import checks as checks_mod  # noqa: E402
from harness import config as cfg  # noqa: E402
from harness import skills  # noqa: E402
from harness.parsing import parse_query_file  # noqa: E402

import litellm  # noqa: E402

litellm.drop_params = True  # silently drop params a given model doesn't support
litellm.suppress_debug_info = True  # quiet the "Provider List:" stderr spam
logging.getLogger("LiteLLM").setLevel(logging.WARNING)

# Defaults
DEFAULT_MODEL = "google/gemma-4-31b-it"       # the model under test
JUDGE_MODEL = "anthropic/claude-sonnet-4.6"   # Claude judge, also via OpenRouter
DEFAULT_QUERIES = ["A2", "A5", "C1"]
MAX_STEPS = 40    # C1's multi-step CDA→GDC round-trip needs headroom; cap, only costs tokens if hit
MAX_TOKENS = 4096

OPENROUTER_BASE = "https://openrouter.ai/api/v1"


def setup_langsmith() -> str | None:
    """Enable litellm's LangSmith callback from the .env LANGSMITH_* vars.

    Returns the project name if tracing is on, else None. litellm's logger reads
    LANGSMITH_BASE_URL (the .env uses the langchain-standard LANGSMITH_ENDPOINT,
    so we map it). LANGSMITH_BATCH_SIZE=1 flushes each call immediately, which
    matters for a short-lived script that would otherwise exit mid-batch.
    """
    env = cfg._parse_env_file(cfg.ENV_FILE)
    for k, v in env.items():
        if k.startswith("LANGSMITH_") and not os.environ.get(k):
            os.environ[k] = v
    if os.environ.get("LANGSMITH_TRACING", "").lower() not in ("1", "true", "yes"):
        return None
    if not os.environ.get("LANGSMITH_API_KEY"):
        return None
    if os.environ.get("LANGSMITH_ENDPOINT") and not os.environ.get("LANGSMITH_BASE_URL"):
        os.environ["LANGSMITH_BASE_URL"] = os.environ["LANGSMITH_ENDPOINT"]
    os.environ.setdefault("LANGSMITH_BATCH_SIZE", "1")
    litellm.callbacks = ["langsmith"]
    return os.environ.get("LANGSMITH_PROJECT") or "default"

_RUN_PYTHON_TOOL = {
    "type": "function",
    "function": {
        "name": "run_python",
        "description": (
            "Execute Python 3 code in a persistent namespace and return its "
            "stdout/stderr. State persists across calls. `requests`/`json`/`urllib` "
            "are available and `cdapython` is importable. Anything you want to "
            "observe you MUST print(). Use this to query the live CDA APIs, parse "
            "responses, and compute results."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Python code to execute."}
            },
            "required": ["code"],
        },
    },
}


# --------------------------------------------------------------------------- #
# in-process python execution sandbox (mirrors plain backend's _PyEnv)
# --------------------------------------------------------------------------- #
class PyEnv:
    def __init__(self) -> None:
        self.ns: dict = {"__name__": "__main__"}

    def run(self, code: str) -> dict:
        out, err = io.StringIO(), io.StringIO()
        error = None
        try:
            with redirect_stdout(out), redirect_stderr(err):
                exec(compile(code, "<agent>", "exec"), self.ns)
        except Exception:
            error = traceback.format_exc()
        return {"code": code, "stdout": out.getvalue(), "stderr": err.getvalue(), "error": error}


# Some models (notably gemma-4-31b-it on its OpenRouter route) ignore the
# OpenAI tool schema and emit their NATIVE tool-call format as plain text, e.g.
#   <|tool_call>call:run_python{code:<|"|> ...code... <|"|>}<tool_call|>
# or a ```tool_code fenced block. We detect and execute those as a fallback so
# the harness still works for models with no usable structured tool-calling.
_TEXT_TOOLCALL_RE = re.compile(
    r'call:\s*(?P<name>\w+)\s*\{\s*code\s*:\s*<\|"\|>(?P<code>.*?)<\|"\|>', re.DOTALL)
_TOOLCODE_FENCE_RE = re.compile(r'```tool_code\s*\n(?P<code>.*?)```', re.DOTALL)


def parse_text_tool_calls(text: str) -> list[tuple[str, str]]:
    """Extract (tool_name, code) pairs a model emitted as text instead of via
    structured tool_calls. Returns [] when none are present."""
    calls = [(m.group("name"), m.group("code")) for m in _TEXT_TOOLCALL_RE.finditer(text)]
    if calls:
        return calls
    # gemma's documented ```tool_code fence → implicit run_python
    return [("run_python", m.group("code")) for m in _TOOLCODE_FENCE_RE.finditer(text)]


def _exec_and_format(env: PyEnv, code: str, trace: list, verbose: bool, steps: int) -> str:
    step = env.run(code)
    trace.append(step)
    payload = step["stdout"]
    if step["stderr"]:
        payload += f"\n[stderr]\n{step['stderr']}"
    if step["error"]:
        payload += f"\n[exception]\n{step['error']}"
    payload = payload.strip() or "(no output)"
    if verbose:
        print(f"\n[step {steps}] run_python:\n{code}\n--- output ---\n{payload[:1500]}")
    return payload[:20000]


# --------------------------------------------------------------------------- #
# OpenRouter ReAct loop
# --------------------------------------------------------------------------- #
def run_agent(model: str, api_key: str, system: str, user_message: str,
              max_steps: int = MAX_STEPS, verbose: bool = False,
              trace_meta: dict | None = None) -> dict:
    trace_meta = trace_meta or {}
    env = PyEnv()
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_message},
    ]
    trace: list[dict] = []
    final_answer = ""
    error = None
    steps = 0

    for steps in range(1, max_steps + 1):
        try:
            resp = litellm.completion(
                model=f"openrouter/{model}",
                api_key=api_key,
                api_base=OPENROUTER_BASE,
                messages=messages,
                tools=[_RUN_PYTHON_TOOL],
                tool_choice="auto",
                temperature=0.0,
                max_tokens=MAX_TOKENS,
                metadata={"run_name": f"{trace_meta.get('model_tag', '?')}:{trace_meta.get('qid', '?')}:agent:step{steps}",
                          **trace_meta},
            )
        except Exception as e:
            error = f"api error on step {steps}: {e}"
            break

        msg = resp.choices[0].message
        text = msg.content or ""
        tool_calls = getattr(msg, "tool_calls", None) or []
        # Fallback for models that emit tool calls as text (e.g. gemma-4-31b-it).
        text_calls = parse_text_tool_calls(text) if not tool_calls else []

        # Echo the assistant turn back so the model sees its own tool calls.
        messages.append(msg.model_dump() if hasattr(msg, "model_dump") else dict(msg))

        if not tool_calls and not text_calls:
            final_answer = text.strip()
            if verbose:
                print(f"\n[step {steps}] final answer:\n{final_answer}\n")
            break

        if tool_calls:
            # Structured OpenAI-style tool calls → reply with role:tool results.
            for tc in tool_calls:
                if tc.function.name != "run_python":
                    payload = f"unknown tool {tc.function.name}"
                else:
                    try:
                        code = json.loads(tc.function.arguments or "{}").get("code", "")
                    except json.JSONDecodeError:
                        code = tc.function.arguments or ""
                    payload = _exec_and_format(env, code, trace, verbose, steps)
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": payload})
        else:
            # Text-format tool calls → execute and feed the output back as a
            # plain user turn (there's no tool_call_id to reply to).
            observations = []
            for name, code in text_calls:
                if name != "run_python":
                    observations.append(f"[unknown tool {name}]")
                    continue
                observations.append(_exec_and_format(env, code, trace, verbose, steps))
            obs = "\n\n".join(observations)
            messages.append({
                "role": "user",
                "content": f"[tool output from run_python]\n{obs}\n\n"
                           "Continue, or give your final answer in plain text.",
            })
    else:
        error = error or f"hit max_steps ({max_steps}) without a final answer"
        if not final_answer:
            final_answer = text

    return {"final_answer": final_answer, "trace": trace, "steps": steps, "error": error}


def transcript_of(run: dict) -> str:
    parts = ["=== FINAL ANSWER ===", run["final_answer"] or "(no answer)"]
    parts.append(f"\n=== CODE / TOOL TRACE ({len(run['trace'])} steps) ===")
    for i, step in enumerate(run["trace"], 1):
        parts.append(f"\n--- step {i} ---")
        parts.append(step["code"].strip())
        out = (step["stdout"] or "").strip()
        if out:
            clipped = out[:2500]
            if len(out) > 2500:
                clipped += f"\n…[+{len(out) - 2500} chars]"
            parts.append(f"[stdout]\n{clipped}")
        if step["error"]:
            parts.append(f"[error] {step['error']}")
    return "\n".join(parts)


# --------------------------------------------------------------------------- #
# Claude judge for behavior / count_at_least checks (via OpenRouter)
# --------------------------------------------------------------------------- #
_JUDGE_SYSTEM = (
    "You are a strict, literal grader for an automated test harness. You decide "
    "whether ONE assertion about an AI agent's run is satisfied, using only the "
    "agent's final answer and its code/tool trace as evidence. Be conservative: "
    "if the evidence does not clearly support the assertion, it FAILS. Judge only "
    "the stated assertion — not overall answer quality. Respond with a single "
    'JSON object: {"pass": true|false, "reason": "<= 30 words"}. No other text.'
)

_BEHAVIOR_TMPL = """\
ASSERTION (about the METHOD the agent used):
  {spec}

This is a `behavior` check: decide it from the agent's CODE / TOOL TRACE (the
endpoints called, request bodies, filter slots, fields read, interpretations
made). The final answer is secondary context.

TASK GIVEN TO THE AGENT:
{prompt}

AGENT RUN (final answer + code/tool trace):
{transcript}

Does the agent's run satisfy the assertion? Return the JSON verdict.
"""

_COUNT_TMPL = """\
ASSERTION (about enumeration cardinality):
  {spec}

This is a `count_at_least` check of the form `<name> >= N`. Decide whether the
agent's FINAL ANSWER actually enumerates/returns at least N distinct items of
the named kind.

TASK GIVEN TO THE AGENT:
{prompt}

AGENT FINAL ANSWER:
{answer}

Does the answer satisfy the assertion? Return the JSON verdict.
"""


def make_judge(judge_model: str, api_key: str):
    def judge(check, query, answer: str, transcript: str):
        meta = {"run_name": f"{query.qid}:judge:{check.type}", "qid": query.qid, "role": "judge"}
        if check.type == "behavior":
            content = _BEHAVIOR_TMPL.format(
                spec=check.spec, prompt=query.prompt, transcript=transcript[:18000])
        elif check.type == "count_at_least":
            content = _COUNT_TMPL.format(
                spec=check.spec, prompt=query.prompt, answer=answer[:12000])
        else:
            return None, f"judge does not handle {check.type}"
        resp = litellm.completion(
            model=f"openrouter/{judge_model}",
            api_key=api_key,
            api_base=OPENROUTER_BASE,
            messages=[
                {"role": "system", "content": _JUDGE_SYSTEM},
                {"role": "user", "content": content},
            ],
            temperature=0.0,
            max_tokens=600,
            metadata=meta,
        )
        text = (resp.choices[0].message.content or "").strip()
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            return None, f"unparseable judge output: {text[:120]!r}"
        try:
            verdict = json.loads(m.group(0))
        except json.JSONDecodeError:
            return None, f"unparseable judge output: {text[:120]!r}"
        return bool(verdict.get("pass")), str(verdict.get("reason", ""))[:200]
    return judge


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def resolve_openrouter_key(explicit: str | None) -> str:
    if explicit:
        return explicit
    if os.environ.get("OPENROUTER_API_KEY"):
        return os.environ["OPENROUTER_API_KEY"]
    env = cfg._parse_env_file(cfg.ENV_FILE)
    return env.get("OPENROUTER_API_KEY", "")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default=DEFAULT_MODEL, help=f"OpenRouter model slug (default: {DEFAULT_MODEL})")
    ap.add_argument("--judge-model", default=JUDGE_MODEL, help=f"Judge model slug (default: {JUDGE_MODEL})")
    ap.add_argument("--query", default=",".join(DEFAULT_QUERIES),
                    help=f"comma-separated CDA qids (default: {','.join(DEFAULT_QUERIES)})")
    ap.add_argument("--max-steps", type=int, default=MAX_STEPS)
    ap.add_argument("--no-judge", action="store_true", help="skip the LLM judge (behavior checks left unscored)")
    ap.add_argument("--no-trace", action="store_true", help="disable LangSmith tracing even if LANGSMITH_TRACING=true")
    ap.add_argument("--verbose", "-v", action="store_true", help="stream each tool call + output")
    ap.add_argument("--api-key", default=None, help="OpenRouter API key (overrides env / .env)")
    ap.add_argument("-o", "--output", default=None, help="write a JSON report")
    args = ap.parse_args()

    api_key = resolve_openrouter_key(args.api_key)
    if not api_key:
        print("ERROR: no OPENROUTER_API_KEY (checked --api-key, env, ../.env)", file=sys.stderr)
        return 2

    wanted = {q.strip().upper() for q in args.query.split(",") if q.strip()}
    all_q = {q.qid: q for q in parse_query_file(cfg.QUERIES_DIR / "cda_test.md")}
    missing = wanted - set(all_q)
    if missing:
        print(f"ERROR: unknown qid(s): {sorted(missing)}. Available: {sorted(all_q)}", file=sys.stderr)
        return 2
    selected = [all_q[q] for q in sorted(wanted)]

    project = None if args.no_trace else setup_langsmith()

    judge = None if args.no_judge else make_judge(args.judge_model, api_key)
    system = skills.build_system_prompt()

    print(f"model:  {args.model}")
    print(f"judge:  {'(disabled)' if args.no_judge else args.judge_model}")
    print(f"trace:  {f'LangSmith → project {project!r}' if project else '(off)'}")
    print(f"queries: {', '.join(q.qid for q in selected)}\n")

    report = {"model": args.model, "judge_model": None if args.no_judge else args.judge_model, "queries": []}
    n_pass = 0

    for q in selected:
        print(f"{'='*70}\n{q.ref} — {q.title}\nPrompt: {q.prompt}\n{'-'*70}")
        user_message = skills.build_user_message("cda", q.prompt)
        run = run_agent(args.model, api_key, system, user_message,
                        max_steps=args.max_steps, verbose=args.verbose,
                        trace_meta={"qid": q.qid, "role": "agent",
                                    "model_tag": args.model.split("/")[-1][:18]})

        if run["error"]:
            print(f"  [run error] {run['error']}")
        print(f"\nFINAL ANSWER ({run['steps']} steps, {len(run['trace'])} code calls):")
        print("  " + (run["final_answer"] or "(none)").replace("\n", "\n  "))

        transcript = transcript_of(run)
        grade = checks_mod.grade_query(q, run["final_answer"], transcript, judge=judge)
        print("\nCHECKS:")
        for r in grade.results:
            mark = {True: "PASS", False: "FAIL", None: "----"}[r.passed]
            print(f"  [{mark}] {r.check.type}: {r.check.spec[:70]}")
            if r.detail:
                print(f"         ↳ {r.detail}")
        verdict = "PASS" if grade.passed else "FAIL"
        n_pass += grade.passed
        print(f"\n  => {verdict}  ({grade.n_pass} pass / {grade.n_fail} fail / {grade.n_unscored} unscored)\n")

        report["queries"].append({
            "qid": q.qid, "prompt": q.prompt, "passed": grade.passed,
            "final_answer": run["final_answer"], "error": run["error"],
            "steps": run["steps"],
            "checks": [{"type": r.check.type, "spec": r.check.spec,
                        "passed": r.passed, "method": r.method, "detail": r.detail}
                       for r in grade.results],
        })

    print(f"{'='*70}\nSUMMARY: {n_pass}/{len(selected)} queries passed")

    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=2))
        print(f"wrote {args.output}")

    if project:
        # LangSmith posts run on a background thread; give it a moment to flush
        # before the interpreter exits, or the last traces are lost.
        import time
        time.sleep(4)

    return 0 if n_pass == len(selected) else 1


if __name__ == "__main__":
    raise SystemExit(main())
