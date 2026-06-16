"""The unified LiteLLM ReAct agent.

A single ``run_python`` ReAct loop that drives *any* model through litellm: ask
the model, run any code it emits in a persistent namespace, feed the output back,
repeat until it answers. Because litellm normalises tool-calling to OpenAI format
for every provider, this one loop serves Anthropic, OpenAI, Gemini and
OpenRouter-hosted models identically — the provider is chosen entirely by
:func:`~harness.llm.routing.resolve_model`. A text-tool-call fallback covers
models that emit their native tool format as plain text.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from ..config import HarnessConfig
from .routing import resolve_model
from .sandbox import CodeStep, PyEnv, format_tool_result
from .tools import RUN_PYTHON_TOOL, parse_text_tool_calls

_STDOUT_BUDGET = 2500  # chars of stdout kept per step in the transcript


@dataclass
class AgentRun:
    model: str
    final_answer: str
    code_trace: list[CodeStep] = field(default_factory=list)
    steps: int = 0
    error: str | None = None
    raw: Any = None

    def transcript(self) -> str:
        """Answer + code/tool trace, for ``behavior`` judging and debugging."""
        parts = ["=== FINAL ANSWER ===", self.final_answer or "(no answer)"]
        parts.append(f"\n=== CODE / TOOL TRACE ({len(self.code_trace)} steps) ===")
        for i, step in enumerate(self.code_trace, 1):
            parts.append(f"\n--- step {i} ---")
            parts.append(step.code.strip())
            out = (step.stdout or "").strip()
            if out:
                clipped = out[:_STDOUT_BUDGET]
                if len(out) > _STDOUT_BUDGET:
                    clipped += f"\n…[+{len(out) - _STDOUT_BUDGET} chars]"
                parts.append(f"[stdout]\n{clipped}")
            if step.error:
                parts.append(f"[error] {step.error}")
        return "\n".join(parts)


class LiteLLMAgent:
    """ReAct agent over a single litellm-routed model."""

    def __init__(self, config: HarnessConfig):
        self.config = config
        self.resolved = resolve_model(config.model)
        self.api_key = config.key_for(self.resolved.api_key_env)
        if not self.api_key:
            raise RuntimeError(
                f"no API key for provider {self.resolved.provider.value!r} "
                f"(model {config.model!r} needs {self.resolved.api_key_env})."
            )

    def _exec(self, env: PyEnv, code: str, trace: list[CodeStep], step_no: int) -> str:
        step = env.run(code)
        trace.append(step)
        payload = format_tool_result(step)
        if self.config.verbose:
            print(f"\n[step {step_no}] run_python:\n{code}\n--- output ---\n{payload[:1500]}")
        return payload

    def run(self, user_message: str, system: str) -> AgentRun:
        # Imported here so importing the agent (e.g. for AgentRun) stays litellm-free;
        # litellm only loads when a run actually happens.
        from .completion import complete

        env = PyEnv()
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_message},
        ]
        trace: list[CodeStep] = []
        final_answer = ""
        error: str | None = None
        steps = 0
        text = ""

        for steps in range(1, self.config.max_steps + 1):
            try:
                comp = complete(
                    model=self.resolved.litellm_model,
                    messages=messages,
                    api_key=self.api_key,
                    tools=[RUN_PYTHON_TOOL],
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                    num_retries=self.config.num_retries,
                )
            except Exception as e:
                error = f"api error on step {steps}: {e}"
                break

            text = comp.text
            tool_calls = comp.tool_calls
            # Fallback for models that emit tool calls as text (e.g. gemma-4-31b-it).
            text_calls = parse_text_tool_calls(text) if not tool_calls else []

            # Echo the assistant turn back so the model sees its own tool calls.
            messages.append(comp.assistant_message)

            if not tool_calls and not text_calls:
                final_answer = text.strip()
                if self.config.verbose:
                    print(f"\n[step {steps}] final answer:\n{final_answer}\n")
                break

            if tool_calls:
                # Structured OpenAI-style tool calls → reply with role:tool results.
                for tc in tool_calls:
                    if tc.name != "run_python":
                        payload = f"unknown tool {tc.name}"
                    else:
                        try:
                            code = json.loads(tc.arguments or "{}").get("code", "")
                        except json.JSONDecodeError:
                            code = tc.arguments or ""
                        payload = self._exec(env, code, trace, steps)
                    messages.append({"role": "tool", "tool_call_id": tc.id, "content": payload})
            else:
                # Text-format tool calls → execute and feed the output back as a
                # plain user turn (there's no tool_call_id to reply to).
                observations = []
                for tname, code in text_calls:
                    if tname != "run_python":
                        observations.append(f"[unknown tool {tname}]")
                        continue
                    observations.append(self._exec(env, code, trace, steps))
                obs = "\n\n".join(observations)
                messages.append({
                    "role": "user",
                    "content": f"[tool output from run_python]\n{obs}\n\n"
                               "Continue, or give your final answer in plain text.",
                })
        else:
            error = error or f"hit max_steps ({self.config.max_steps}) without final answer"
            if not final_answer:
                final_answer = text

        return AgentRun(
            model=self.config.model,
            final_answer=final_answer,
            code_trace=trace,
            steps=steps,
            error=error,
        )
