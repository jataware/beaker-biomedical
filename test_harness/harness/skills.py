"""Load a CRDC skill and build the prompts handed to a backend.

The full ``SKILL.md`` is injected; its ``references/``, ``examples/`` and
``assets/`` files are listed by path so the agent can read them on demand from
its Python tool — mirroring the progressive-disclosure model the skills are
authored for.
"""

from __future__ import annotations

from pathlib import Path

from .config import HarnessConfig, SERVICE_TO_SKILL

_HARNESS_ROLE = (
    "You are an autonomous data-analysis agent with a Python execution tool. "
    "You are given an Agent Skill describing how to query a specific NCI Cancer "
    "Research Data Commons repository. Follow the skill precisely: use the "
    "endpoints, filter semantics, and interpretations it specifies, and read its "
    "reference files when you need detail. Execute real code against the live API "
    "to obtain real values — never fabricate numbers, IDs, or results. If the "
    "task is outside the repository's scope, say so and redirect rather than "
    "inventing a query. Finish with a clear final answer that states the key "
    "numbers, IDs, and conclusions explicitly."
)


def skill_dir_for(service: str, config: HarnessConfig | None = None) -> Path:
    from .config import SKILLS_DIR
    base = config.skills_dir if config else SKILLS_DIR
    name = SERVICE_TO_SKILL.get(service)
    if not name:
        raise KeyError(f"no skill mapping for service {service!r}")
    return Path(base) / name


def _list_skill_files(skill_dir: Path) -> list[str]:
    files = []
    for p in sorted(skill_dir.rglob("*")):
        if p.is_file() and p.name != "SKILL.md":
            files.append(str(p.relative_to(skill_dir)))
    return files


def load_skill_text(service: str, config: HarnessConfig | None = None) -> str:
    skill_dir = skill_dir_for(service, config)
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        raise FileNotFoundError(f"SKILL.md not found for {service!r} at {skill_md}")
    text = skill_md.read_text(encoding="utf-8")
    if config and config.skill_max_chars and len(text) > config.skill_max_chars:
        text = text[: config.skill_max_chars] + "\n…[SKILL.md truncated]"
    return text


def build_system_prompt(config: HarnessConfig | None = None) -> str:
    return _HARNESS_ROLE


def build_user_message(service: str, prompt: str, config: HarnessConfig | None = None) -> str:
    skill_dir = skill_dir_for(service, config)
    skill_name = SERVICE_TO_SKILL[service]
    skill_text = load_skill_text(service, config)
    ref_files = _list_skill_files(skill_dir)
    listing = "\n".join(f"  - {f}" for f in ref_files) or "  (none)"
    return (
        f"## Agent Skill: {skill_name}\n\n"
        f"<skill>\n{skill_text}\n</skill>\n\n"
        f"### Skill reference files (read on demand from your Python tool)\n"
        f"These live on disk under:\n  {skill_dir}\n"
        f"Read any with, e.g.: `print(open(r\"{skill_dir}/references/ENDPOINTS.md\").read())`\n"
        f"Available files:\n{listing}\n\n"
        f"---\n\n"
        f"## Task\n{prompt}\n"
    )
