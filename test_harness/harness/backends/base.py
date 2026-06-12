"""Backend interface shared by the plain-Anthropic and archytas harnesses."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

from ..config import HarnessConfig

_STDOUT_BUDGET = 2500  # chars of stdout kept per step in the transcript


@dataclass
class CodeStep:
    code: str
    stdout: str = ""
    stderr: str = ""
    error: Optional[str] = None


@dataclass
class AgentRun:
    backend: str
    final_answer: str
    code_trace: list[CodeStep] = field(default_factory=list)
    steps: int = 0
    error: Optional[str] = None
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


class AgentBackend(ABC):
    name: str = "base"

    def __init__(self, config: HarnessConfig):
        self.config = config

    @abstractmethod
    def run(self, user_message: str, system: str) -> AgentRun:
        """Run one prompt to completion and return the answer + trace."""
        raise NotImplementedError


# Lazy registry so importing this module doesn't import anthropic/archytas.
def get_backend(name: str, config: HarnessConfig) -> AgentBackend:
    name = name.lower()
    if name == "plain":
        from .plain import PlainAnthropicBackend
        return PlainAnthropicBackend(config)
    if name == "archytas":
        from .archytas_backend import ArchytasBackend
        return ArchytasBackend(config)
    raise ValueError(f"unknown backend {name!r} (choose: {', '.join(BACKENDS)})")


BACKENDS = ("plain", "archytas")
