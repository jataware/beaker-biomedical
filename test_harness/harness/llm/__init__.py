"""Model-access layer: one litellm-based engine for the agent and the judge.

Every model — Anthropic / OpenAI / Gemini natively, everything else via
OpenRouter — is reached through litellm with one OpenAI-style tool-calling loop.
:func:`resolve_model` decides the provider; :class:`LiteLLMAgent` is the ReAct
loop the runner drives. The single typed litellm boundary —
:func:`harness.llm.completion.complete` — is intentionally *not* re-exported here
so that importing this package stays litellm-free (litellm imports slowly);
import it from ``harness.llm.completion`` directly when you need it.
"""

from .agent import AgentRun, LiteLLMAgent
from .routing import PROVIDER_KEY_ENV, Provider, ResolvedModel, resolve_model
from .sandbox import CodeStep, PyEnv, format_tool_result
from .tools import RUN_PYTHON_TOOL, parse_text_tool_calls

__all__ = [
    "AgentRun", "LiteLLMAgent",
    "Provider", "ResolvedModel", "resolve_model", "PROVIDER_KEY_ENV",
    "CodeStep", "PyEnv", "format_tool_result",
    "RUN_PYTHON_TOOL", "parse_text_tool_calls",
]
