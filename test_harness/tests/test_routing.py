"""Unit tests for model→provider routing — no API calls, no litellm import.

``resolve_model`` is the contract the whole harness rests on: it decides which
provider every model id reaches and, critically, guarantees Claude is never
routed through OpenRouter.
"""

import pytest

from harness.llm.routing import (
    PROVIDER_KEY_ENV,
    Provider,
    resolve_model,
)


@pytest.mark.parametrize("model,litellm_model,provider", [
    # Frontier labs hosting their own → native provider.
    ("claude-sonnet-4-6", "anthropic/claude-sonnet-4-6", Provider.ANTHROPIC),
    ("claude-opus-4-8", "anthropic/claude-opus-4-8", Provider.ANTHROPIC),
    ("gpt-4o", "openai/gpt-4o", Provider.OPENAI),
    ("gpt-5", "openai/gpt-5", Provider.OPENAI),
    ("o3-mini", "openai/o3-mini", Provider.OPENAI),
    ("chatgpt-4o-latest", "openai/chatgpt-4o-latest", Provider.OPENAI),
    ("gemini-2.5-pro", "gemini/gemini-2.5-pro", Provider.GEMINI),
    # Everything else → OpenRouter fallback (open-weight slugs).
    ("qwen/qwen3-coder-next", "openrouter/qwen/qwen3-coder-next", Provider.OPENROUTER),
    ("google/gemma-4-31b-it", "openrouter/google/gemma-4-31b-it", Provider.OPENROUTER),
    ("meta-llama/llama-3.3-70b", "openrouter/meta-llama/llama-3.3-70b", Provider.OPENROUTER),
    ("deepseek/deepseek-chat", "openrouter/deepseek/deepseek-chat", Provider.OPENROUTER),
    ("mistralai/mistral-large", "openrouter/mistralai/mistral-large", Provider.OPENROUTER),
])
def test_bare_id_routing(model, litellm_model, provider):
    r = resolve_model(model)
    assert r.litellm_model == litellm_model
    assert r.provider is provider
    assert r.api_key_env == PROVIDER_KEY_ENV[provider]


@pytest.mark.parametrize("model,provider", [
    ("anthropic/claude-sonnet-4-6", Provider.ANTHROPIC),
    ("openai/gpt-4o", Provider.OPENAI),
    ("gemini/gemini-2.5-pro", Provider.GEMINI),
    ("vertex_ai/gemini-2.5-pro", Provider.GEMINI),       # the other Google route
    ("openrouter/qwen/qwen3-coder-next", Provider.OPENROUTER),
])
def test_explicit_prefix_honoured(model, provider):
    r = resolve_model(model)
    assert r.litellm_model == model     # passed through verbatim
    assert r.provider is provider


def test_claude_never_routes_through_openrouter():
    # The core guarantee: any plausible Claude spelling stays on Anthropic.
    for m in ["claude-sonnet-4-6", "claude-opus-4-8", "claude-3-5-haiku", "Claude-Sonnet-4-6"]:
        r = resolve_model(m)
        assert r.provider is Provider.ANTHROPIC
        assert r.litellm_model.startswith("anthropic/")
        assert "openrouter" not in r.litellm_model


def test_gemma_org_slug_is_openrouter_not_gemini():
    # `google/gemma-*` is an OpenRouter org/model slug, NOT native Gemini.
    r = resolve_model("google/gemma-4-31b-it")
    assert r.provider is Provider.OPENROUTER
    assert r.litellm_model == "openrouter/google/gemma-4-31b-it"


def test_key_env_mapping_complete():
    assert PROVIDER_KEY_ENV == {
        Provider.ANTHROPIC: "ANTHROPIC_API_KEY",
        Provider.OPENAI: "OPENAI_API_KEY",
        Provider.GEMINI: "GEMINI_API_KEY",
        Provider.OPENROUTER: "OPENROUTER_API_KEY",
    }


def test_empty_model_rejected():
    with pytest.raises(ValueError):
        resolve_model("   ")
