"""The unified LiteLLM ReAct agent.

A single ReAct loop that drives *any* model through litellm: ask the model, run
whatever it asks for, feed the result back, repeat until it answers. The model
has two tools — ``run_python`` (execute code in a persistent namespace) and
``read_skill_file`` (load one of the skill's reference/example/asset files into
context by its relative path, the progressive-disclosure mechanism). Because
litellm normalises tool-calling to OpenAI format for every provider, this one
loop serves Anthropic, OpenAI, Gemini and OpenRouter-hosted models identically —
the provider is chosen entirely by :func:`~harness.llm.routing.resolve_model`. A
text-tool-call fallback covers models (e.g. gemma) that emit their native tool
format as plain text, for *both* tools.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable

from ..config import HarnessConfig
from .routing import resolve_model
from .sandbox import CodeStep, PyEnv, ResourceStep, format_resource_result, format_tool_result
from .tools import TOOLS, parse_text_tool_calls

_STDOUT_BUDGET = 2500  # chars of stdout kept per step in the transcript
_RESOURCE_BUDGET = 1500  # chars of a loaded skill file shown in the transcript

# Reader injected by the runner: ``(skill | None, path) -> ResourceStep``. Kept as
# a callable so the agent stays decoupled from ``harness.skills`` (avoids an import
# cycle, since skills.py imports this package's sandbox types).
ResourceReader = Callable[[str | None, str], ResourceStep]

# Steps in the trace are either code executions or skill-file loads.
Step = CodeStep | ResourceStep


@dataclass
class AgentRun:
    model: str
    final_answer: str
    trace: list[Step] = field(default_factory=list)
    steps: int = 0
    error: str | None = None
    raw: Any = None

    def transcript(self) -> str:
        """Answer + interleaved code/skill-load trace, for ``behavior`` judging and
        debugging — so the judge sees both what the agent ran and what skill docs
        it read."""
        parts = ["=== FINAL ANSWER ===", self.final_answer or "(no answer)"]
        parts.append(f"\n=== CODE / TOOL TRACE ({len(self.trace)} steps) ===")
        for i, step in enumerate(self.trace, 1):
            if isinstance(step, ResourceStep):
                head = f"read_skill_file {step.path!r}" + ("" if step.ok else " [error]")
                parts.append(f"\n--- step {i} ({head}) ---")
                body = step.content if step.ok else (step.error or "")
                clipped = (body or "").strip()[:_RESOURCE_BUDGET]
                if len(body or "") > _RESOURCE_BUDGET:
                    clipped += f"\n…[+{len(body) - _RESOURCE_BUDGET} chars]"
                parts.append(clipped)
                continue
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


def _args(raw: str | None) -> dict[str, Any]:
    """Parse a structured tool call's JSON argument string, tolerantly."""
    try:
        parsed = json.loads(raw or "{}")
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


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

    def _exec(self, env: PyEnv, code: str, trace: list[Step], step_no: int) -> str:
        step = env.run(code)
        trace.append(step)
        payload = format_tool_result(step)
        if self.config.verbose:
            print(f"\n[step {step_no}] run_python:\n{code}\n--- output ---\n{payload[:1500]}")
        return payload

    def _load(self, reader: ResourceReader | None, skill: str | None, path: str,
              trace: list[Step], step_no: int) -> str:
        """Load a skill file via the injected reader, record it in the trace, and
        return the text payload fed back to the model."""
        if reader is None:
            step = ResourceStep(skill=skill or "?", path=path or "", ok=False,
                                error="read_skill_file is unavailable in this run.")
        else:
            step = reader(skill, path)
        trace.append(step)
        payload = format_resource_result(step)
        if self.config.verbose:
            print(f"\n[step {step_no}] read_skill_file {path!r} -> "
                  f"{'ok' if step.ok else step.error}\n{payload[:800]}")
        return payload

    def run(self, user_message: str, system: str, *,
            read_resource: ResourceReader | None = None) -> AgentRun:
        # Imported here so importing the agent (e.g. for AgentRun) stays litellm-free;
        # litellm only loads when a run actually happens.
        from .completion import complete

        env = PyEnv()
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_message},
        ]
        trace: list[Step] = []
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
                    tools=TOOLS,
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
                    args = _args(tc.arguments)
                    if tc.name == "run_python":
                        payload = self._exec(env, args.get("code", ""), trace, steps)
                    elif tc.name == "read_skill_file":
                        payload = self._load(read_resource, args.get("skill"),
                                             args.get("path", ""), trace, steps)
                    else:
                        payload = f"unknown tool {tc.name}"
                    messages.append({"role": "tool", "tool_call_id": tc.id, "content": payload})
            else:
                # Text-format tool calls → execute and feed the output back as a
                # plain user turn (there's no tool_call_id to reply to).
                observations = []
                for tname, targs in text_calls:
                    if tname == "run_python":
                        observations.append(self._exec(env, targs.get("code", ""), trace, steps))
                    elif tname == "read_skill_file":
                        observations.append(self._load(read_resource, targs.get("skill"),
                                                       targs.get("path", ""), trace, steps))
                    else:
                        observations.append(f"[unknown tool {tname}]")
                obs = "\n\n".join(observations)
                messages.append({
                    "role": "user",
                    "content": f"[tool output]\n{obs}\n\n"
                               "Continue, or give your final answer in plain text.",
                })
        else:
            error = error or f"hit max_steps ({self.config.max_steps}) without final answer"
            if not final_answer:
                final_answer = text

        return AgentRun(
            model=self.config.model,
            final_answer=final_answer,
            trace=trace,
            steps=steps,
            error=error,
        )
