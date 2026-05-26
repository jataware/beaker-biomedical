#!/usr/bin/env python3
"""Fetch the newest GitHub release of each remote skill and install into ./skills.

For each URL in REMOTE_SKILL_URLS, downloads the latest release archive,
extracts every directory containing a SKILL.md, and installs it under
./skills/<skill-name> (name taken from the SKILL.md frontmatter `name:` field,
falling back to the source directory name).

If a skill of the same name already exists, the old copy is moved to a temp
folder first, the new copy is installed, and the temp copy is deleted on
success (or restored on failure).
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

REMOTE_SKILL_URLS = [
    "https://github.com/ImagingDataCommons/idc-claude-skill",
]

USAGE = f"""Usage: {Path(__file__).name} <skills-dir>
Downloads the latest release of each URL in REMOTE_SKILL_URLS and
installs every SKILL.md-containing directory under <skills-dir>/<skill-name>."""


def parse_owner_repo(url: str) -> tuple[str, str]:
    path = url.rstrip("/").removeprefix("https://").removeprefix("http://")
    parts = path.split("/")
    if len(parts) < 3 or parts[0] != "github.com":
        raise ValueError(f"Not a GitHub URL: {url}")
    return parts[1], parts[2]


def _auth_headers() -> dict[str, str]:
    headers = {"User-Agent": "fetch-remote-skills"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def fetch_latest_release(owner: str, repo: str) -> dict:
    api_url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
    headers = {**_auth_headers(), "Accept": "application/vnd.github+json"}
    req = urllib.request.Request(api_url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def pick_archive_url(release: dict) -> str:
    for asset in release.get("assets", []):
        name = asset.get("name", "")
        if name.endswith(".zip"):
            return asset["browser_download_url"]
    return release["zipball_url"]


def download_to(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers=_auth_headers())
    with urllib.request.urlopen(req) as resp, open(dest, "wb") as f:
        shutil.copyfileobj(resp, f)


def read_skill_name(skill_md: Path) -> str | None:
    in_frontmatter = False
    with skill_md.open(encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped == "---":
                if in_frontmatter:
                    return None
                in_frontmatter = True
                continue
            if in_frontmatter and stripped.startswith("name:"):
                return stripped.split(":", 1)[1].strip().strip('"').strip("'")
    return None


def install_skill_dir(source_dir: Path, skills_dir: Path) -> None:
    name = read_skill_name(source_dir / "SKILL.md") or source_dir.name
    target = skills_dir / name
    backup_root: Path | None = None
    if target.exists():
        backup_root = Path(tempfile.mkdtemp(prefix=f"{name}-old-"))
        shutil.move(str(target), str(backup_root / name))
        print(f"\tbacked up existing {target} -> {backup_root / name}")
    try:
        shutil.move(str(source_dir), str(target))
        print(f"\tinstalled {target}")
    except Exception:
        if backup_root is not None:
            shutil.move(str(backup_root / name), str(target))
            print(f"\trestored backup to {target}")
        raise
    finally:
        if backup_root is not None and backup_root.exists():
            shutil.rmtree(backup_root, ignore_errors=True)


def process_release_archive(zip_path: Path, skills_dir: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(tmp_path)
        skill_md_files = sorted(tmp_path.rglob("SKILL.md"))
        if not skill_md_files:
            raise RuntimeError(f"No SKILL.md found in archive {zip_path}")
        for skill_md in skill_md_files:
            install_skill_dir(skill_md.parent, skills_dir)


def fetch_one(url: str, skills_dir: Path) -> None:
    owner, repo = parse_owner_repo(url)
    print(f"{owner}/{repo}:")
    release = fetch_latest_release(owner, repo)
    print(f"\tlatest release: {release.get('tag_name', '?')}")
    archive_url = pick_archive_url(release)
    with tempfile.TemporaryDirectory() as tmp:
        zip_path = Path(tmp) / "release.zip"
        print(f"\tdownloading {archive_url}")
        download_to(archive_url, zip_path)
        process_release_archive(zip_path, skills_dir)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(USAGE, file=sys.stderr)
        return 2
    skills_dir = Path(argv[1]).resolve()
    skills_dir.mkdir(parents=True, exist_ok=True)
    errors: list[tuple[str, Exception]] = []
    for url in REMOTE_SKILL_URLS:
        try:
            fetch_one(url, skills_dir)
        except (urllib.error.URLError, urllib.error.HTTPError, RuntimeError, ValueError) as e:
            print(f"  ERROR: {e}", file=sys.stderr)
            errors.append((url, e))
    if errors:
        print(f"\n{len(errors)} skill(s) failed", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
