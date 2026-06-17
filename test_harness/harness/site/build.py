"""Build the static evaluation dashboard: N report JSONs -> one ``index.html``.

A pure ``inputs -> HTML`` function. Inputs are the report file(s) written by
``harness.cli run -o`` plus the on-disk ``skills/`` and ``tests/`` trees (read at
the current checkout, i.e. the captured SHA). The output is a single
self-contained file: the data, CSS and JS are all inlined, so it opens from
``file://`` with no server and uploads as one CI artifact.

Pipeline:
  load + normalize each report (tolerant of the legacy ``backend`` schema)
  -> flatten runs (one per test x model x rep) with globally-unique ids
  -> aggregate per-(test,model) pass-rate cells
  -> snapshot + render the skills/tests trees, with per-doc "reach" stats
  -> inline everything into the template.
"""

from __future__ import annotations

import hashlib
import html
import json
import posixpath
import re
from collections import defaultdict
from pathlib import Path
from typing import Iterable
from urllib.parse import quote

from markdown_it import MarkdownIt

from .. import meta as _meta
from ..config import SKILLS_DIR, TESTS_DIR, SERVICE_TO_SKILL
from ..parsing import parse_all, _split_frontmatter

_TEMPLATE_DIR = Path(__file__).resolve().parent / "template"

_md = MarkdownIt("commonmark", {"breaks": False}).enable("table").enable("strikethrough")


# --------------------------------------------------------------------------- #
# rendering helpers
# --------------------------------------------------------------------------- #
def _frontmatter_table(meta: dict) -> str:
    """YAML frontmatter (e.g. SKILL.md's name/description) -> a key/value table,
    instead of letting ``--- … ---`` render as a giant setext heading."""
    if not meta:
        return ""
    rows = []
    for k, v in meta.items():
        if isinstance(v, (list, tuple)):
            v = ", ".join(str(x) for x in v)
        rows.append(f"<tr><th>{html.escape(str(k))}</th>"
                    f"<td>{html.escape(str(v))}</td></tr>")
    return '<table class="frontmatter"><tbody>' + "".join(rows) + "</tbody></table>"


_HEADING_RE = re.compile(r"<(/?)h([1-6])>")


def _demote_headings(html_str: str, by: int) -> str:
    """Shift heading levels down by ``by`` (capped at h6) — used so rationale.md's
    ``# Intended Behavior`` renders as an h3, not a page-dominating h1."""
    return _HEADING_RE.sub(
        lambda m: f"<{m.group(1)}h{min(6, int(m.group(2)) + by)}>", html_str)


def render_markdown(text: str, *, heading_offset: int = 0) -> str:
    meta, body = _split_frontmatter(text or "")
    out = _md.render(body)
    if heading_offset:
        out = _demote_headings(out, heading_offset)
    return _frontmatter_table(meta) + out


def code_html(text: str, lang: str = "") -> str:
    cls = f" class=\"language-{lang}\"" if lang else ""
    return f'<pre class="codeblock"><code{cls}>{html.escape(text or "")}</code></pre>'


def _kind(path: str) -> str:
    suf = path.rsplit(".", 1)[-1].lower() if "." in path else ""
    if suf in ("md", "markdown"):
        return "md"
    if suf in ("yaml", "yml"):
        return "yaml"
    if suf == "json":
        return "json"
    return "text"


_HREF_RE = re.compile(r'href="([^"]*)"')


def _rewrite_links(html_str: str, svc: str, file_path: str, valid: set[str]) -> str:
    """Resolve a doc's relative markdown links against its own folder and point
    them at the in-page explorer (``#skills/<svc>/<path>``) when the target is a
    file in the same skill — so inter-file links actually navigate."""
    base = posixpath.dirname(file_path)

    def repl(m):
        href = m.group(1)
        if re.match(r"^[a-z][a-z0-9+.-]*:", href) or href[:1] in ("#", "/"):
            return m.group(0)                       # scheme, anchor, or absolute
        path_part = href.split("#", 1)[0].split("?", 1)[0]
        if not path_part:
            return m.group(0)
        target = posixpath.normpath(posixpath.join(base, path_part))
        if target in valid:
            return f'href="#skills/{svc}/{quote(target, safe="")}"'
        return m.group(0)

    return _HREF_RE.sub(repl, html_str)


# --------------------------------------------------------------------------- #
# load + normalize reports
# --------------------------------------------------------------------------- #
def load_report(path: Path) -> dict:
    """Read a report JSON, tolerating the legacy ``backend`` field and a missing
    ``meta`` block (older single-model experiment files)."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    data.setdefault("meta", {})
    data["meta"].setdefault("rep", 1)
    data["_source"] = Path(path).name
    for res in data.get("results", []):
        res.setdefault("model", res.get("backend") or data.get("model") or "?")
    return data


def _uid(ref: str, model: str, rep: int, file_idx: int) -> str:
    return hashlib.sha1(f"{ref}|{model}|{rep}|{file_idx}".encode()).hexdigest()[:8]


def _flatten_runs(reports: list[dict]) -> list[dict]:
    """One run per (test, model) per report file. ``rep`` is reassigned to a dense
    1..N index within each (ref, model) group so cells read ``k/N`` cleanly and
    ids stay unique even when several files share ``--rep 1``."""
    raw: list[dict] = []
    for fi, rep in enumerate(reports):
        rep_label = rep.get("meta", {}).get("rep", 1)
        for res in rep.get("results", []):
            qid = res.get("qid", "")
            raw.append({
                "file_idx": fi,
                "rep_label": rep_label,
                "run_uid": "",  # assigned below
                "ref": res.get("ref") or f'{res.get("service","?")}:{qid}',
                "service": res.get("service", "?"),
                "category": res.get("category") or (qid.split("/", 1)[0] if "/" in qid else ""),
                "leaf": qid.rsplit("/", 1)[-1] if qid else res.get("ref", "?"),
                "qid": qid,
                "title": res.get("title", ""),
                "model": res["model"],
                "passed": res.get("passed"),
                "score": res.get("score"),
                "n_pass": res.get("n_pass", 0),
                "n_fail": res.get("n_fail", 0),
                "n_unscored": res.get("n_unscored", 0),
                "elapsed_s": res.get("elapsed_s"),
                "steps": res.get("steps"),
                "error": res.get("error"),
                "prompt": res.get("prompt", ""),
                "final_answer": res.get("final_answer", ""),
                "checks": res.get("checks", []),
                "trace": res.get("trace", []),
                "docs_opened": res.get("docs_opened", []),
            })

    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in raw:
        groups[(r["ref"], r["model"])].append(r)
    for runs in groups.values():
        runs.sort(key=lambda r: (r["rep_label"], r["file_idx"]))
        for i, r in enumerate(runs, 1):
            r["rep"] = i
            r["run_uid"] = _uid(r["ref"], r["model"], i, r["file_idx"])
    for r in raw:
        r.pop("file_idx", None)
        r.pop("rep_label", None)
    return raw


def _cells(runs: list[dict]) -> dict:
    cells: dict[str, dict] = {}
    for r in runs:
        key = f'{r["ref"]}|{r["model"]}'
        c = cells.setdefault(key, {"pass": 0, "total": 0, "run_uids": []})
        c["total"] += 1
        if r["passed"]:
            c["pass"] += 1
        c["run_uids"].append(r["run_uid"])
    return cells


# --------------------------------------------------------------------------- #
# snapshot the skills/ and tests/ trees
# --------------------------------------------------------------------------- #
def _reach(runs: list[dict]) -> dict:
    """service -> {doc_path: {opened, total}} from each run's ``docs_opened``."""
    totals: dict[str, int] = defaultdict(int)
    opened: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in runs:
        totals[r["service"]] += 1
        for doc in r["docs_opened"]:
            opened[r["service"]][doc] += 1
    return {svc: {"total": totals[svc], "opened": dict(opened[svc])} for svc in totals}


def snapshot_skills(services: Iterable[str], skills_cap: dict, runs: list[dict],
                    skills_dir: Path = SKILLS_DIR) -> dict:
    reach = _reach(runs)
    out: dict[str, dict] = {}
    for svc in sorted(set(services)):
        name = SERVICE_TO_SKILL.get(svc)
        if not name:
            continue
        skill_dir = Path(skills_dir) / name
        if not skill_dir.is_dir():
            continue
        svc_reach = reach.get(svc, {"total": 0, "opened": {}})

        # Collect raw (path, text) first — SKILL.md (verbatim captured text when
        # available) pinned first — so link rewriting knows the full file set.
        entries: list[tuple[str, str]] = []
        skill_md = (skills_cap.get(svc) or {}).get("skill_md")
        if skill_md is None and (skill_dir / "SKILL.md").exists():
            skill_md = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        if skill_md is not None:
            entries.append(("SKILL.md", skill_md))
        for p in sorted(skill_dir.rglob("*")):
            if not p.is_file() or p.name == "SKILL.md":
                continue
            try:
                entries.append((p.relative_to(skill_dir).as_posix(),
                                p.read_text(encoding="utf-8")))
            except (UnicodeDecodeError, OSError):
                continue

        valid = {path for path, _ in entries}
        files, rendered = [], {}
        for path, text in entries:
            kind = _kind(path)
            if kind == "md":
                rendered[path] = _rewrite_links(render_markdown(text), svc, path, valid)
            else:
                rendered[path] = code_html(text, {"yaml": "yaml", "json": "json"}.get(kind, ""))
            files.append({"path": path, "kind": kind,
                          "reach": {"opened": svc_reach["opened"].get(path, 0),
                                    "total": svc_reach["total"]}})
        out[svc] = {"name": name,
                    "skill_sha": (skills_cap.get(svc) or {}).get("skill_sha"),
                    "files": files, "rendered": rendered}
    return out


def snapshot_tests(tests_dir: Path = TESTS_DIR) -> list[dict]:
    out: list[dict] = []
    for svc, queries in parse_all(tests_dir).items():
        for q in queries:
            test_dir = Path(tests_dir) / svc / q.qid
            rationale = test_dir / "rationale.md"
            eval_yaml = test_dir / "eval.yaml"
            out.append({
                "ref": q.ref, "service": svc, "category": q.qid.split("/", 1)[0],
                "leaf": q.leaf, "qid": q.qid, "title": q.title,
                "description": q.description,
                "prompt_html": render_markdown(q.prompt),
                # demote rationale headings: `# Intended Behavior` -> h3, not h1
                "rationale_html": render_markdown(rationale.read_text(encoding="utf-8"),
                                                  heading_offset=2)
                if rationale.exists() else "",
                "eval_yaml": eval_yaml.read_text(encoding="utf-8") if eval_yaml.exists() else "",
                "checks": [{"type": c.type, "spec": c.spec,
                            "family": "deterministic"
                            if c.type in {"substring", "substring_any", "substring_all",
                                          "must_not_contain", "regex", "number", "set_contains"}
                            else "semantic"} for c in q.checks],
            })
    return out


# --------------------------------------------------------------------------- #
# aggregate + assemble the data blob
# --------------------------------------------------------------------------- #
def aggregate(reports: list[dict], *, skills_dir: Path = SKILLS_DIR,
              tests_dir: Path = TESTS_DIR) -> dict:
    runs = _flatten_runs(reports)
    services = sorted({r["service"] for r in runs})
    models = sorted({r["model"] for r in runs})
    skills_cap: dict = {}
    for rep in reports:
        for svc, cap in (rep.get("skills") or {}).items():
            skills_cap.setdefault(svc, cap)

    n_runs = len(runs)
    n_pass = sum(1 for r in runs if r["passed"])
    checks_pass = sum(r["n_pass"] for r in runs)
    checks_fail = sum(r["n_fail"] for r in runs)
    base_meta = next((rep["meta"] for rep in reports if rep.get("meta", {}).get("git")),
                     reports[0]["meta"] if reports else {})

    return {
        "generated_at": _meta.now_iso(),
        "git": base_meta.get("git") or _meta.git_info(),
        "config": base_meta.get("config", {}),
        "judge_model": next((rep.get("judge_model") for rep in reports
                             if rep.get("judge_model")), None),
        "meta_runs": [{"source": rep.get("_source"), "rep": rep.get("meta", {}).get("rep", 1),
                       "models": rep.get("models", []),
                       "generated_at": rep.get("meta", {}).get("generated_at"),
                       "git": rep.get("meta", {}).get("git", {})} for rep in reports],
        "models": models,
        "services": services,
        "summary": {
            "runs": n_runs, "runs_passed": n_pass,
            "run_pass_rate": round(n_pass / n_runs, 3) if n_runs else 0.0,
            "checks_passed": checks_pass, "checks_failed": checks_fail,
            "check_pass_rate": round(checks_pass / (checks_pass + checks_fail), 3)
            if (checks_pass + checks_fail) else 0.0,
            "n_tests": len({r["ref"] for r in runs}),
        },
        "runs": runs,
        "cells": _cells(runs),
        "tests": snapshot_tests(tests_dir),
        "skills": snapshot_skills(services, skills_cap, runs, skills_dir),
    }


# --------------------------------------------------------------------------- #
# inline into the template
# --------------------------------------------------------------------------- #
def _inline(data: dict) -> str:
    shell = (_TEMPLATE_DIR / "index.html").read_text(encoding="utf-8")
    css = (_TEMPLATE_DIR / "style.css").read_text(encoding="utf-8")
    app = (_TEMPLATE_DIR / "app.js").read_text(encoding="utf-8")
    # `</` is the only sequence that can break out of a <script> context; escaping
    # it keeps the JSON valid (\/ is a legal JSON escape).
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return (shell
            .replace("/*__STYLE__*/", css)
            .replace("/*__APP__*/", app)
            .replace("__REPORT_DATA__", payload))


def build_site(report_paths: list[str | Path], out_path: str | Path, *,
               skills_dir: Path = SKILLS_DIR, tests_dir: Path = TESTS_DIR) -> Path:
    if not report_paths:
        raise ValueError("no report JSONs given")
    reports = [load_report(Path(p)) for p in report_paths]
    data = aggregate(reports, skills_dir=Path(skills_dir), tests_dir=Path(tests_dir))
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(_inline(data), encoding="utf-8")
    return out
