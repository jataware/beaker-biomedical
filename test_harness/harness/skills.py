"""Load a CRDC skill and build the prompts handed to a backend.

The full ``SKILL.md`` is injected; its ``references/``, ``examples/`` and
``assets/`` files are listed by path so the agent can read them on demand from
its Python tool — mirroring the progressive-disclosure model the skills are
authored for.
"""

from __future__ import annotations

from pathlib import Path

from .config import HarnessConfig, SERVICE_TO_SKILL
from .llm.sandbox import RESOURCE_CHAR_CAP, ResourceStep

_HARNESS_ROLE = (
    "You are an autonomous data-analysis agent with two tools: `run_python` to "
    "execute code, and `read_skill_file` to load one of the skill's reference, "
    "example, or asset files into the conversation by its relative path. "
    "You are given an Agent Skill describing how to query a specific NCI Cancer "
    "Research Data Commons repository. Follow the skill precisely: use the "
    "endpoints, filter semantics, and interpretations it specifies, and use "
    "`read_skill_file` to read its reference files whenever you need detail the "
    "SKILL.md summary doesn't give. Execute real code against the live API "
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


def read_skill_resource(service: str, rel_path: str,
                        config: HarnessConfig | None = None,
                        *, skill: str | None = None) -> ResourceStep:
    """Load a skill-relative file for the ``read_skill_file`` tool.

    The path is confined to the skill directory (``..`` / absolute escapes are
    rejected); content over :data:`RESOURCE_CHAR_CAP` is truncated with a flag.
    On any failure ``ok`` is False and ``error`` carries a recovery hint that
    lists the files actually on offer.
    """
    name = SERVICE_TO_SKILL.get(service, service)

    def fail(msg: str) -> ResourceStep:
        return ResourceStep(skill=name, path=(rel_path or "").strip(), ok=False, error=msg)

    try:
        skill_dir = skill_dir_for(service, config).resolve()
    except KeyError:
        return fail(f"unknown skill for service {service!r}")

    # The run is bound to one skill; honor an explicit `skill` arg only when it
    # matches, so a run can't read another commons' docs.
    if skill and skill.strip() and skill.strip() != name:
        return fail(f"this task is bound to skill {name!r}; cannot read from {skill.strip()!r}.")

    rel = (rel_path or "").strip()
    if not rel:
        return fail("no path given. Pass a skill-relative path, e.g. 'references/ENDPOINTS.md'.")

    target = (skill_dir / rel).resolve()
    if skill_dir not in target.parents:          # ../ traversal or absolute escape
        return fail(f"path {rel!r} is outside the skill directory.")
    if not target.is_file():
        avail = ", ".join(_list_skill_files(skill_dir)) or "(none)"
        return fail(f"no such file {rel!r}. Available files: {avail}")

    posix_rel = target.relative_to(skill_dir).as_posix()
    text = target.read_text(encoding="utf-8")
    n = len(text)
    if n > RESOURCE_CHAR_CAP:
        return ResourceStep(
            skill=name, path=posix_rel, ok=True, truncated=True, n_chars=n,
            content=text[:RESOURCE_CHAR_CAP] + f"\n…[{n - RESOURCE_CHAR_CAP} more chars truncated]",
        )
    return ResourceStep(skill=name, path=posix_rel, ok=True, content=text, n_chars=n)


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
        f"### Skill reference files (load on demand with the read_skill_file tool)\n"
        f"Read any of these by its relative path, e.g. "
        f"`read_skill_file(path=\"references/ENDPOINTS.md\")` — you do not need the "
        f"absolute path. (They also live on disk under {skill_dir}, so you can open "
        f"one in Python if you need to parse it programmatically.)\n"
        f"Available files:\n{listing}\n\n"
        f"---\n\n"
        f"## Task\n{prompt}\n"
    )
