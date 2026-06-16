"""The single litellm boundary.

This is the *only* module that imports litellm or touches its dynamic response
objects. ``litellm.completion`` accepts OpenAI-style ``tools`` for every provider
and returns an OpenAI-shaped message (``.content`` + ``.tool_calls``), so one
call site serves Anthropic, OpenAI, Gemini and OpenRouter alike. We immediately
project that response into the typed :class:`Completion` below; everything
downstream of this module is fully typed and never sees a litellm object.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import litellm

# Silently drop params a given model doesn't support (e.g. ``temperature`` on the
# OpenAI o-series), and quiet litellm's stderr/debug chatter. litellm declares
# ``suppress_debug_info`` as ``Literal[False]`` (its default), so the type checker
# rejects assigning ``True`` — a stub quirk at this third-party boundary.
litellm.drop_params = True
litellm.suppress_debug_info = True  # ty: ignore[invalid-assignment]
logging.getLogger("LiteLLM").setLevel(logging.WARNING)


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: str   # raw JSON string as emitted by the model


@dataclass
class Completion:
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    # The assistant turn in OpenAI dict form, echoed back verbatim so the model
    # sees its own tool calls on the next step.
    assistant_message: dict[str, Any] = field(default_factory=dict)
    finish_reason: str | None = None


def complete(
    *,
    model: str,
    messages: list[dict[str, Any]],
    api_key: str,
    tools: list[dict[str, Any]] | None = None,
    temperature: float = 0.0,
    max_tokens: int = 4096,
    num_retries: int = 2,
    api_base: str | None = None,
) -> Completion:
    """One model turn through litellm, projected to a typed :class:`Completion`.

    ``model`` must be a fully-qualified litellm id (see
    :func:`harness.llm.routing.resolve_model`). litellm retries transient errors
    ``num_retries`` times before raising; the caller handles the terminal error.
    """
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "api_key": api_key,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "num_retries": num_retries,
    }
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"
    if api_base:
        kwargs["api_base"] = api_base

    # The one place litellm's untyped surface is touched; contained to `Any`.
    resp: Any = litellm.completion(**kwargs)
    choice = resp.choices[0]
    msg = choice.message

    raw: dict[str, Any] = msg.model_dump() if hasattr(msg, "model_dump") else dict(msg)
    tool_calls: list[ToolCall] = []
    for tc in (getattr(msg, "tool_calls", None) or []):
        tool_calls.append(
            ToolCall(id=tc.id, name=tc.function.name, arguments=tc.function.arguments or "")
        )

    return Completion(
        text=msg.content or "",
        tool_calls=tool_calls,
        assistant_message=raw,
        finish_reason=getattr(choice, "finish_reason", None),
    )
