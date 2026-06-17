"""In-process Python execution sandbox and tool-result formatting.

The agent's one tool is ``run_python``: it executes model-generated code in a
persistent namespace and feeds the captured stdout/stderr back. These pieces
don't depend on the model's wire protocol, so they live apart from the agent
loop. NOTE: :meth:`PyEnv.run` swaps the process-global ``sys.stdout`` /
``sys.stderr`` via ``redirect_*``, so two runs in one process would scramble
each other's captured output — which is exactly why the runner parallelises with
*processes* (one per query), never threads.
"""

from __future__ import annotations

import io
import traceback
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass


# Max chars of a loaded skill file kept in context (and in the trace). Reference
# docs are occasionally large; full text rarely adds signal past this and it
# keeps the conversation light. Truncation is flagged, never silent.
RESOURCE_CHAR_CAP = 20_000


@dataclass
class CodeStep:
    code: str
    stdout: str = ""
    stderr: str = ""
    error: str | None = None
    kind: str = "python"   # trace discriminator; see ResourceStep


@dataclass
class ResourceStep:
    """One ``read_skill_file`` load — a progressive-disclosure event in the trace.

    Sits in the same ordered :attr:`AgentRun.trace` as :class:`CodeStep`, so the
    transcript and dashboard show skill reads interleaved with code in execution
    order. ``path`` is the skill-relative posix path (matches the skill file
    listing keys); ``skill`` is the resolved skill name.
    """

    skill: str
    path: str
    ok: bool
    content: str = ""
    error: str | None = None
    truncated: bool = False
    n_chars: int = 0       # original length before any cap
    kind: str = "skill_file"


class PyEnv:
    """A persistent exec namespace with stdout/stderr capture."""

    def __init__(self) -> None:
        self.ns: dict[str, object] = {"__name__": "__main__"}

    def run(self, code: str) -> CodeStep:
        out, err = io.StringIO(), io.StringIO()
        error: str | None = None
        try:
            with redirect_stdout(out), redirect_stderr(err):
                exec(compile(code, "<agent>", "exec"), self.ns)
        except Exception:
            error = traceback.format_exc()
        return CodeStep(code=code, stdout=out.getvalue(), stderr=err.getvalue(), error=error)


def format_tool_result(step: CodeStep, limit: int = 20000) -> str:
    """Render a CodeStep into the text payload fed back to the model.

    stdout, then any stderr and exception traceback, stripped, clipped. Empty
    output becomes ``(no output)`` so the model never sees a blank tool result.
    """
    payload = step.stdout
    if step.stderr:
        payload += f"\n[stderr]\n{step.stderr}"
    if step.error:
        payload += f"\n[exception]\n{step.error}"
    return (payload.strip() or "(no output)")[:limit]


def format_resource_result(step: "ResourceStep") -> str:
    """Render a ResourceStep into the text payload fed back to the model: the file
    text on success, or a short error (which already lists the available files)."""
    if step.ok:
        return step.content or "(empty file)"
    return f"[read_skill_file] {step.error}"
