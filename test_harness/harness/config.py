"""Harness configuration: paths, model selection, and API-key loading."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

# test_harness/  (this package's parent)
HARNESS_DIR = Path(__file__).resolve().parent.parent
# repo root (test_harness/..)
REPO_ROOT = HARNESS_DIR.parent
QUERIES_DIR = HARNESS_DIR / "queries_md"
SKILLS_DIR = REPO_ROOT / "skills"
ENV_FILE = REPO_ROOT / ".env"

# Default test/agent model and judge model. Both are routed through litellm by
# harness.llm.routing.resolve_model — a bare ``claude-*`` id always resolves to
# the native ``anthropic/`` provider, never OpenRouter.
DEFAULT_MODEL = "claude-sonnet-4-6"
DEFAULT_JUDGE_MODEL = "claude-sonnet-4-6"

# service code (from `<service>_test.md`) -> skill directory name under skills/
SERVICE_TO_SKILL = {
    "gdc": "genomics-data-commons",
    "pdc": "proteomic-data-commons",
    "cda": "cancer-data-aggregator",
    "gc": "general-commons",
    "icdc": "integrated-canine-data-commons",
    "ctdc": "clinical-translational-data-commons",
    "psdc": "population-sciences-data-commons",
}


def _parse_env_file(path: Path) -> dict[str, str]:
    """Minimal .env reader. Strips quotes and resolves ``${VAR}`` references
    against values already parsed (and the process environment)."""
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")

        def _resolve(match: re.Match) -> str:
            name = match.group(1)
            return values.get(name) or os.environ.get(name, "")

        val = re.sub(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", _resolve, val)
        values[key] = val
    return values


def resolve_key(env_var: str, explicit: str | None = None) -> str:
    """Resolve any provider API key: explicit arg > process env > repo ``.env``.

    On a ``.env`` hit the value is also written back into ``os.environ`` (via
    ``setdefault``) so litellm — which reads keys from the environment — sees it
    too, in addition to the explicit ``api_key`` the harness passes per call.
    """
    if explicit:
        return explicit
    if os.environ.get(env_var):
        return os.environ[env_var]
    val = _parse_env_file(ENV_FILE).get(env_var, "")
    if val:
        os.environ.setdefault(env_var, val)
    return val


@dataclass
class HarnessConfig:
    """Everything a run needs. Sensible defaults so the CLI can override.

    ``model`` (the agent under test) and ``judge_model`` are both routed through
    litellm by :func:`harness.llm.routing.resolve_model`; either can name any
    provider. ``api_keys`` carries explicit per-provider key overrides
    (``env_var -> key``); it is a plain dict so it survives pickling to the
    spawn-based worker processes, which otherwise can't read the parent's env.
    """

    model: str = DEFAULT_MODEL
    judge_model: str = DEFAULT_JUDGE_MODEL
    api_keys: dict[str, str] = field(default_factory=dict)  # *_API_KEY env var -> key
    max_steps: int = 50          # ReAct step budget per query (cap; only costs tokens if hit)
    temperature: float = 0.0
    max_tokens: int = 4096       # per model turn
    num_retries: int = 2         # litellm transient-error retries per turn
    use_judge: bool = True       # LLM-grade `behavior` checks
    timeout: int = 600           # seconds per query (whole agent run)
    verbose: bool = False
    skill_max_chars: int = 0     # 0 = inject full SKILL.md; >0 truncates

    queries_dir: Path = field(default=QUERIES_DIR)
    skills_dir: Path = field(default=SKILLS_DIR)

    def key_for(self, env_var: str) -> str:
        """The resolved key for a provider's ``*_API_KEY`` env var."""
        return resolve_key(env_var, self.api_keys.get(env_var))
