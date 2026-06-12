"""Archytas backend.

Drives the production agentic wrapper: an ``archytas.react.ReActAgent`` with an
``AnthropicModel`` and the built-in ``PythonTool``. The skill + task arrive as
the ReAct query; the harness role is injected as a leading ``SystemMessage``
(archytas folds system messages into its system prompt). The PythonTool's
executed scripts are captured as the code trace for ``behavior`` grading.
"""

from __future__ import annotations

import contextlib
import io
import sys

from ..config import HarnessConfig
from .base import AgentBackend, AgentRun, CodeStep


@contextlib.contextmanager
def _silence():
    """Swallow archytas's chatty stdout/stderr (PythonTool echoes, token logs).

    Its ``Python.run_script`` resets ``sys.__stdout__`` after each exec, so a
    plain ``redirect_stdout`` doesn't hold — we point the dunder streams at the
    sink too, and restore everything afterwards.
    """
    sink = io.StringIO()
    saved = (sys.stdout, sys.stderr, sys.__stdout__, sys.__stderr__)
    sys.stdout = sys.stderr = sink
    sys.__stdout__ = sys.__stderr__ = sink
    try:
        yield
    finally:
        sys.stdout, sys.stderr, sys.__stdout__, sys.__stderr__ = saved


class ArchytasBackend(AgentBackend):
    name = "archytas"

    def __init__(self, config: HarnessConfig):
        super().__init__(config)
        # Imported lazily so the plain backend never pulls archytas in.
        from archytas.models.anthropic import AnthropicModel
        self._AnthropicModel = AnthropicModel

    def run(self, user_message: str, system: str) -> AgentRun:
        from archytas.react import ReActAgent, FailedTaskError
        from archytas.tools import PythonTool
        from langchain_core.messages import SystemMessage

        model = self._AnthropicModel({
            "api_key": self.config.resolved_key(),
            "model_name": self.config.model,
            "max_tokens": self.config.max_tokens,
        })

        # Our own PythonTool instance, so we can read env.all_scripts afterward.
        pytool = PythonTool()

        agent = ReActAgent(
            model=model,
            tools=[pytool],
            allow_ask_user=False,
            verbose=self.config.verbose,
            temperature=self.config.temperature,
            max_react_steps=self.config.max_steps,
            messages=[SystemMessage(content=system)] if system else None,
            rich_print=False,
        )

        error = None
        final_answer = ""
        silencer = contextlib.nullcontext() if self.config.verbose else _silence()
        try:
            with silencer:
                final_answer = agent.react(user_message) or ""
        except FailedTaskError as e:
            error = f"FailedTaskError: {e}"
            final_answer = str(e)
        except Exception as e:
            error = f"{type(e).__name__}: {e}"

        # PythonTool stores each executed script's source in env.all_scripts.
        scripts = list(getattr(pytool.env, "all_scripts", []))
        trace = [CodeStep(code=s) for s in scripts]

        return AgentRun(
            backend=self.name,
            final_answer=final_answer.strip() if isinstance(final_answer, str) else str(final_answer),
            code_trace=trace,
            steps=len(scripts),
            error=error,
        )
