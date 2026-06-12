"""Plain-Anthropic backend.

A minimal, self-contained ReAct loop driven directly against the Anthropic
Messages API. The model gets one tool — ``run_python`` — that executes code in
a persistent in-process namespace (the same execution model archytas's
``PythonTool`` uses), so the agent can call the live CRDC APIs the skills
describe. No archytas dependency: this is the "just the plain API" harness.
"""

from __future__ import annotations

import io
import traceback
from contextlib import redirect_stderr, redirect_stdout

import anthropic

from ..config import HarnessConfig
from .base import AgentBackend, AgentRun, CodeStep

_RUN_PYTHON_TOOL = {
    "name": "run_python",
    "description": (
        "Execute Python 3 code in a persistent namespace and return its "
        "stdout/stderr. State persists across calls. The environment has "
        "`urllib`/`requests`/`json` for HTTP and standard scientific libs may "
        "be importable. Anything you want to observe you MUST print(). Use this "
        "to query the live APIs, parse responses, and compute results."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "Python code to execute."}
        },
        "required": ["code"],
    },
}


class _PyEnv:
    """In-process exec sandbox with a persistent namespace + stdout capture."""

    def __init__(self) -> None:
        self.ns: dict = {"__name__": "__main__"}

    def run(self, code: str) -> CodeStep:
        out, err = io.StringIO(), io.StringIO()
        error = None
        try:
            with redirect_stdout(out), redirect_stderr(err):
                exec(compile(code, "<agent>", "exec"), self.ns)
        except Exception:
            error = traceback.format_exc()
        return CodeStep(code=code, stdout=out.getvalue(), stderr=err.getvalue(), error=error)


class PlainAnthropicBackend(AgentBackend):
    name = "plain"

    def __init__(self, config: HarnessConfig):
        super().__init__(config)
        self.client = anthropic.Anthropic(api_key=config.resolved_key())

    def run(self, user_message: str, system: str) -> AgentRun:
        env = _PyEnv()
        messages: list[dict] = [{"role": "user", "content": user_message}]
        trace: list[CodeStep] = []
        final_answer = ""
        error = None
        steps = 0
        text = ""

        for steps in range(1, self.config.max_steps + 1):
            try:
                resp = self.client.messages.create(
                    model=self.config.model,
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature,
                    system=system,
                    tools=[_RUN_PYTHON_TOOL],
                    messages=messages,
                )
            except Exception as e:
                error = f"api error on step {steps}: {e}"
                break

            text = "".join(b.text for b in resp.content if b.type == "text")
            tool_uses = [b for b in resp.content if b.type == "tool_use"]

            # Echo the assistant turn back verbatim (block models round-trip).
            messages.append({"role": "assistant", "content": resp.content})

            if not tool_uses:
                final_answer = text.strip()
                break

            results = []
            for tu in tool_uses:
                if tu.name == "run_python":
                    code = (tu.input or {}).get("code", "")
                    step = env.run(code)
                    trace.append(step)
                    payload = step.stdout
                    if step.stderr:
                        payload += f"\n[stderr]\n{step.stderr}"
                    if step.error:
                        payload += f"\n[exception]\n{step.error}"
                    payload = payload.strip() or "(no output)"
                    results.append({
                        "type": "tool_result",
                        "tool_use_id": tu.id,
                        "content": payload[:20000],
                        "is_error": step.error is not None,
                    })
                else:
                    results.append({
                        "type": "tool_result",
                        "tool_use_id": tu.id,
                        "content": f"unknown tool {tu.name}",
                        "is_error": True,
                    })
            messages.append({"role": "user", "content": results})
        else:
            # Loop exhausted without a tool-free turn.
            error = error or f"hit max_steps ({self.config.max_steps}) without final answer"
            if not final_answer:
                final_answer = text

        return AgentRun(
            backend=self.name,
            final_answer=final_answer,
            code_trace=trace,
            steps=steps,
            error=error,
        )
