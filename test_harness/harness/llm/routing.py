"""Model → provider routing.

One rule decides how every model id is reached through litellm:

* Frontier labs that host their own models use their **native** litellm provider
  — Anthropic (``claude*``), OpenAI (``gpt*`` / ``o1`` …), Google (``gemini*``).
* **Everything else falls back to OpenRouter** (open-weight slugs such as
  ``qwen/qwen3-coder-next`` or ``google/gemma-4-31b-it``).

An explicit ``provider/...`` prefix is always honoured verbatim. The upshot the
harness depends on: **Claude can never be routed through OpenRouter** — a bare
``claude-*`` id always resolves to the ``anthropic/`` provider, by construction.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class Provider(str, Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GEMINI = "gemini"
    OPENROUTER = "openrouter"


# Provider -> the environment variable litellm reads its key from.
PROVIDER_KEY_ENV: dict[Provider, str] = {
    Provider.ANTHROPIC: "ANTHROPIC_API_KEY",
    Provider.OPENAI: "OPENAI_API_KEY",
    Provider.GEMINI: "GEMINI_API_KEY",
    Provider.OPENROUTER: "OPENROUTER_API_KEY",
}

# litellm provider prefixes we accept verbatim (model id is already namespaced).
# ``vertex_ai`` is Google's other Gemini route, so it maps to the GEMINI key set.
_EXPLICIT_PREFIXES: dict[str, Provider] = {
    "anthropic": Provider.ANTHROPIC,
    "openai": Provider.OPENAI,
    "gemini": Provider.GEMINI,
    "vertex_ai": Provider.GEMINI,
    "openrouter": Provider.OPENROUTER,
}

# Bare-id heuristics for frontier-lab models. Anything that matches none of these
# is treated as an OpenRouter slug.
_OPENAI_BARE_RE = re.compile(r"^(?:gpt|chatgpt|o[1-9])", re.IGNORECASE)


@dataclass(frozen=True)
class ResolvedModel:
    """The fully-qualified model string handed to litellm, plus its provider."""

    litellm_model: str   # passed straight to litellm.completion(model=...)
    provider: Provider
    api_key_env: str     # which *_API_KEY env var holds this provider's key


def resolve_model(model: str) -> ResolvedModel:
    """Map a user-supplied model id to a ``ResolvedModel``.

    >>> resolve_model("claude-sonnet-4-6").litellm_model
    'anthropic/claude-sonnet-4-6'
    >>> resolve_model("qwen/qwen3-coder-next").provider
    <Provider.OPENROUTER: 'openrouter'>
    >>> resolve_model("google/gemma-4-31b-it").litellm_model   # org slug, not a provider
    'openrouter/google/gemma-4-31b-it'
    >>> resolve_model("gemini-2.5-pro").provider               # native, not gemma-on-OpenRouter
    <Provider.GEMINI: 'gemini'>
    """
    m = model.strip()
    if not m:
        raise ValueError("empty model id")

    prefix = m.split("/", 1)[0].lower()
    if prefix in _EXPLICIT_PREFIXES:
        provider = _EXPLICIT_PREFIXES[prefix]
        return ResolvedModel(m, provider, PROVIDER_KEY_ENV[provider])

    low = m.lower()
    if low.startswith("claude"):
        provider = Provider.ANTHROPIC
    elif _OPENAI_BARE_RE.match(low):
        provider = Provider.OPENAI
    elif low.startswith("gemini"):
        provider = Provider.GEMINI
    else:
        provider = Provider.OPENROUTER

    return ResolvedModel(f"{provider.value}/{m}", provider, PROVIDER_KEY_ENV[provider])
