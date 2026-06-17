#!/usr/bin/env python3
"""Lint an Agent Skill directory against the structural rules in this skill.

Usage:
    python validate_skill.py <skill-dir> [<skill-dir> ...]

Checks, per skill directory:
  - SKILL.md exists and has a parseable YAML frontmatter block
  - frontmatter `name` is present, valid (lowercase a-z/0-9/-, no edge/double hyphens, 1-64), and
    equals the directory name
  - `description` is present and <= 1024 chars
  - SKILL.md body is within budget (warns past ~250 non-blank lines)
  - every relative markdown link / inline path in SKILL.md resolves on disk
  - auth.yaml exists and parses (a `credentials` list, or the open-API description form)
  - no empty references/ examples/ assets/ scripts/ subdirectories

Exit code is non-zero if any ERROR was found (warnings don't fail). Needs pyyaml.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("pyyaml is required: pip install pyyaml")

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
# relative links: [text](path)  and bare inline paths like references/FOO.md or scripts/x.py
LINK_RE = re.compile(r"\]\(([^)]+)\)")
INLINE_PATH_RE = re.compile(r"(?<![\w./])((?:references|examples|assets|scripts)/[\w./-]+)")
SUBDIRS = ("references", "examples", "assets", "scripts")
LINE_BUDGET = 250


def split_frontmatter(text: str) -> tuple[dict | None, str]:
    if not text.startswith("---"):
        return None, text
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.DOTALL)
    if not m:
        return None, text
    try:
        meta = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        return None, m.group(2)
    return (meta if isinstance(meta, dict) else {}), m.group(2)


def validate(skill_dir: Path) -> tuple[list[str], list[str]]:
    errs: list[str] = []
    warns: list[str] = []

    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return [f"{skill_dir}: no SKILL.md"], warns

    meta, body = split_frontmatter(skill_md.read_text(encoding="utf-8"))
    if meta is None:
        errs.append("SKILL.md: missing or unparseable YAML frontmatter")
        meta = {}

    name = str(meta.get("name", ""))
    if not name:
        errs.append("frontmatter: `name` is missing")
    else:
        if not NAME_RE.match(name) or not (1 <= len(name) <= 64):
            errs.append(f"frontmatter: `name` {name!r} is not a valid skill name")
        if name != skill_dir.name:
            errs.append(f"frontmatter: `name` {name!r} != directory name {skill_dir.name!r}")

    desc = str(meta.get("description", ""))
    if not desc:
        errs.append("frontmatter: `description` is missing")
    elif len(desc) > 1024:
        errs.append(f"frontmatter: `description` is {len(desc)} chars (max 1024)")

    nonblank = [ln for ln in body.splitlines() if ln.strip()]
    if len(nonblank) > LINE_BUDGET:
        warns.append(f"SKILL.md body is {len(nonblank)} non-blank lines (> {LINE_BUDGET}); "
                     "consider moving detail to references/ or examples/")

    # link / path resolution
    targets = set(LINK_RE.findall(body)) | set(INLINE_PATH_RE.findall(body))
    for t in sorted(targets):
        if t.startswith(("http://", "https://", "#", "mailto:")):
            continue
        rel = t.split("#", 1)[0].strip()
        if not rel:
            continue
        if not (skill_dir / rel).exists():
            errs.append(f"SKILL.md: broken link/path -> {rel}")

    # auth.yaml
    auth = skill_dir / "auth.yaml"
    if not auth.exists():
        errs.append("no auth.yaml (use `credentials: []` for an open API)")
    else:
        try:
            data = yaml.safe_load(auth.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            errs.append(f"auth.yaml: does not parse ({e})")
        else:
            if not (isinstance(data, dict) and "credentials" in data):
                errs.append("auth.yaml: missing top-level `credentials` key")
            elif not isinstance(data["credentials"], list):
                errs.append("auth.yaml: `credentials` must be a list")

    # no empty convention dirs
    for sub in SUBDIRS:
        d = skill_dir / sub
        if d.is_dir() and not any(p.is_file() for p in d.rglob("*")):
            warns.append(f"{sub}/ exists but is empty")

    return errs, warns


def main(argv: list[str]) -> int:
    if not argv:
        sys.exit(__doc__)
    failed = False
    for arg in argv:
        d = Path(arg)
        errs, warns = validate(d)
        status = "FAIL" if errs else "ok"
        print(f"[{status}] {d}")
        for w in warns:
            print(f"  warn: {w}")
        for e in errs:
            print(f"  ERROR: {e}")
        failed = failed or bool(errs)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
