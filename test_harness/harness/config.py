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

DEFAULT_MODEL = "claude-sonnet-4-6"

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


def load_api_key(explicit: str | None = None) -> str:
    """Resolve the Anthropic API key: explicit arg > env var > repo ``.env``."""
    if explicit:
        return explicit
    if os.environ.get("ANTHROPIC_API_KEY"):
        return os.environ["ANTHROPIC_API_KEY"]
    env = _parse_env_file(ENV_FILE)
    key = env.get("ANTHROPIC_API_KEY", "")
    if key:
        # Make it visible to libraries (anthropic SDK, archytas) that read env.
        os.environ.setdefault("ANTHROPIC_API_KEY", key)
    return key


@dataclass
class HarnessConfig:
    """Everything a run needs. Sensible defaults so the CLI can override."""

    model: str = DEFAULT_MODEL
    backend: str = "plain"  # "plain" | "archytas"
    api_key: str = ""
    max_steps: int = 50          # ReAct step budget per query (cap; only costs tokens if hit)
    temperature: float = 0.0
    max_tokens: int = 4096       # per model turn
    use_judge: bool = True       # LLM-grade `behavior` checks
    timeout: int = 600           # seconds per query (whole agent run)
    verbose: bool = False
    skill_max_chars: int = 0     # 0 = inject full SKILL.md; >0 truncates

    queries_dir: Path = field(default=QUERIES_DIR)
    skills_dir: Path = field(default=SKILLS_DIR)

    def resolved_key(self) -> str:
        return load_api_key(self.api_key)
