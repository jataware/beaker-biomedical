"""Run-level metadata + skill/doc capture for machine-readable reports.

These enrich a report JSON so it is *self-describing* and *attributable*: when it
was produced, against which git revision and skill versions, with what config,
and — per run — which on-demand skill docs the agent actually opened.

Nothing here calls a model or the network beyond a couple of short, best-effort
``git`` invocations; every helper degrades to ``None`` rather than raising, so a
report still writes from a tarball with no ``.git`` or no ``git`` binary.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from . import skills
from .config import REPO_ROOT, SERVICE_TO_SKILL

SCHEMA_VERSION = "1"

# chars of stdout/stderr kept per code step in the JSON; full output rarely adds
# signal and the embedded dashboard stays light. Truncation is flagged, not silent.
STDOUT_CAP = 16_000


def now_iso() -> str:
    """Current UTC time as a stable ``YYYY-MM-DDTHH:MM:SSZ`` string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_uid(ref: str, model: str, rep: int = 1) -> str:
    """Stable short id for one (test × model × rep), used for deep links."""
    return hashlib.sha1(f"{ref}|{model}|{rep}".encode()).hexdigest()[:8]


# --------------------------------------------------------------------------- #
# git
# --------------------------------------------------------------------------- #
def _git(*args: str, cwd: Path) -> str | None:
    try:
        out = subprocess.run(
            ["git", *args], cwd=str(cwd),
            capture_output=True, text=True, timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def git_info(repo_root: Path = REPO_ROOT) -> dict:
    status = _git("status", "--porcelain", cwd=repo_root)
    return {
        "sha": _git("rev-parse", "--short", "HEAD", cwd=repo_root),
        "branch": _git("rev-parse", "--abbrev-ref", "HEAD", cwd=repo_root),
        "dirty": bool(status) if status is not None else None,
    }


def path_sha(path: Path, repo_root: Path = REPO_ROOT) -> str | None:
    """Short sha of the last commit that touched ``path`` — a skill-version pin."""
    return _git("log", "-1", "--format=%h", "--", str(path), cwd=repo_root)


def harness_version() -> str:
    try:
        from importlib.metadata import version
        return version("beaker-biomedical-test-harness")
    except Exception:
        return "0+unknown"


def ci_info() -> dict | None:
    """GitHub Actions context when running in CI, else ``None``."""
    if not os.environ.get("GITHUB_ACTIONS"):
        return None
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    return {
        "run_id": run_id or None,
        "run_url": f"{server}/{repo}/actions/runs/{run_id}" if repo and run_id else None,
        "actor": os.environ.get("GITHUB_ACTOR") or None,
    }


# --------------------------------------------------------------------------- #
# the report meta block + skill capture
# --------------------------------------------------------------------------- #
def build_meta(config, models: Iterable[str], *, rep: int = 1,
               elapsed_total_s: float | None = None,
               repo_root: Path = REPO_ROOT) -> dict:
    return {
        "generated_at": now_iso(),
        "git": git_info(repo_root),
        "harness_version": harness_version(),
        "rep": rep,
        "config": {
            "temperature": config.temperature,
            "max_steps": config.max_steps,
            "max_tokens": config.max_tokens,
            "timeout": config.timeout,
            "judge_model": config.judge_model,
            "use_judge": config.use_judge,
            "skill_max_chars": config.skill_max_chars,
        },
        "models": list(models),
        "elapsed_total_s": round(elapsed_total_s, 1) if elapsed_total_s is not None else None,
        "ci": ci_info(),
    }


def capture_skills(services: Iterable[str], config,
                   repo_root: Path = REPO_ROOT) -> dict:
    """Per service: the verbatim injected ``SKILL.md``, the offered file listing,
    and a skill-version sha — exactly the always-loaded context every run of that
    service saw (see :func:`harness.skills.build_user_message`)."""
    out: dict[str, dict] = {}
    for svc in sorted(set(services)):
        name = SERVICE_TO_SKILL.get(svc)
        if not name:
            continue
        try:
            skill_dir = skills.skill_dir_for(svc, config)
            out[svc] = {
                "name": name,
                "skill_sha": path_sha(skill_dir, repo_root),
                "skill_md": skills.load_skill_text(svc, config),
                "files": skills._list_skill_files(skill_dir),
            }
        except (KeyError, FileNotFoundError):
            continue
    return out


def detect_docs_opened(codes: Iterable[str], skill_files: Iterable[str]) -> list[str]:
    """Which offered skill docs the agent actually read this run.

    ``build_user_message`` hands the agent absolute paths and tells it to
    ``open(...).read()`` reference/example/asset files on demand; an opened file's
    relative path is therefore a substring of that absolute path in the executed
    code. We match conservatively on the relative path appearing in any code step.
    """
    blob = "\n".join(c or "" for c in codes)
    return [f for f in skill_files if f and f in blob]
