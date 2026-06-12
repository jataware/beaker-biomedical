# Skill evaluation harness

Runs the authoritative benchmark prompts in [`queries_md/`](queries_md/) through
an agent backend with the matching NCI CRDC skill loaded, then **grades the
agent's answer against the machine-gradeable `Checks` blocks** in those files.

It answers one question per query: *with this skill loaded, does the agent reach
the live-verified ground truth — using the right method, and avoiding the trap?*

Two backends, so you can compare harnesses on the same skills and answer key:

| backend    | what it is                                                                 |
|------------|----------------------------------------------------------------------------|
| `plain`    | a minimal ReAct loop driven directly against the **Anthropic Messages API**, with one `run_python` tool. No archytas. |
| `archytas` | the production `archytas` `ReActAgent` + `AnthropicModel` + `PythonTool` — the same wrapper the Beaker app uses (installed from PyPI). |

Both default to **`claude-sonnet-4-6`** (configurable). Both get the *identical*
skill text + task; the only variable is the agent loop.

---

## Layout

```
test_harness/
├── harness/                 # the package
│   ├── config.py            # paths, model, API-key resolution (.env aware)
│   ├── parsing.py           # *_test.md  ->  Query / Check objects
│   ├── checks.py            # parse + grade each Check  ->  CheckResult
│   ├── skills.py            # service -> skill dir; build system/user prompts
│   ├── judge.py             # LLM judge for semantic checks (behavior, count_at_least)
│   ├── runner.py            # select -> run -> grade
│   ├── report.py            # console + JSON rendering
│   ├── cli.py               # the CLI test runner  (python -m harness.cli)
│   └── backends/
│       ├── plain.py         # plain Anthropic backend
│       └── archytas_backend.py
├── tests/                   # pytest: unit (no API) + live (opt-in)
├── queries_md/              # the 7 authoritative *_test.md answer keys
├── run.py                   # == python -m harness.cli
└── pyproject.toml           # package + deps + pytest config
```

Each `<service>_test.md` maps to one skill under `../skills/`:

| service | skill dir |
|---------|-----------|
| `gdc`   | `genomics-data-commons` |
| `pdc`   | `proteomic-data-commons` |
| `cda`   | `cancer-data-aggregator` |
| `gc`    | `general-commons` |
| `icdc`  | `integrated-canine-data-commons` |
| `ctdc`  | `clinical-translational-data-commons` |
| `psdc`  | `population-sciences-data-commons` |

---

## Setup

You're in a `uv` venv at `test_harness/.venv`. Install the harness and its deps:

```bash
uv pip install -e ".[test]"
```

This pulls `archytas` (from PyPI; it brings `anthropic` + `langchain`), plus
`requests`/`cdapython` — the libraries the skills' own example code imports, so a
failure reflects the **skill**, not a missing dependency.

### API key

The harness reads `ANTHROPIC_API_KEY` from, in order: `--api-key`, the process
env, then the repo's `../.env`. Nothing else is needed for open-access CRDC APIs.

---

## CLI

```bash
# list parsed queries + their checks (no API calls)
python -m harness.cli list
python -m harness.cli list --service gdc --checks

# dry-run: assemble prompts, show the checks, call nothing
python -m harness.cli run --service pdc --dry-run
python -m harness.cli run --query gdc:Q1 --dry-run --show-prompt

# run a couple of queries on both backends, write a JSON report
python -m harness.cli run --query gdc:Q1,gdc:Q2 --backend both -o report.json

# run a whole skill suite on the archytas backend, with per-check detail
python -m harness.cli run --service icdc --backend archytas --detail

# run EVERYTHING in parallel (explicit opt-in — this is many live API calls)
python -m harness.cli run --all --backend both -j 8 -o full.json
```

Runs are independent and parallelize across processes (`-j/--concurrency`,
default 8). One process per run keeps each agent's `sys.stdout`/exec state
isolated; wall-clock collapses to roughly the slowest run × (runs ÷ workers).
`-j 1` forces sequential mode with live per-run streaming. Raising `-j` past
your Anthropic tier's rate limit will cause `429`s, so push it up gradually.

Key `run` flags:

| flag | meaning |
|------|---------|
| `--backend` | `plain` \| `archytas` \| `both` (default `plain`) |
| `--model` | model id (default `claude-sonnet-4-6`, or `$HARNESS_MODEL`) |
| `--service` / `--query` | narrow the selection (`gdc` / `gdc:Q1,pdc:Q2`) |
| `--all` | run the full suite (required if no selection given) |
| `--max-steps` | per-query ReAct budget (default 25; a cap, only costs tokens if hit) |
| `-j/--concurrency` | parallel runs, one process each (default 8; `1` = sequential) |
| `--no-judge` | skip LLM grading of `behavior`/`count_at_least` (leaves them unscored) |
| `--dry-run` / `--show-prompt` | preview without calling the API |
| `--detail` | print every check result, not just failures |
| `-o/--output` | write a full JSON report |

`run` exits non-zero if any selected run fails (CI-friendly).

---

## pytest

The same selection logic is exposed as parametrized tests — one per
`(query, backend)`. Unit tests (parser + deterministic grader) run by default
and need no key; the **live** tests are opt-in.

```bash
pytest                                    # unit tests only (fast, no API)
pytest --run-live --backend both -n 8     # full live suite, both backends, 8-way parallel
pytest --run-live --service gdc           # one suite
pytest --run-live --query gdc:Q1,pdc:Q1   # specific queries
pytest --run-live --no-judge --backend plain
```

Live test ids look like `gdc:Q1|plain`. A test passes when every *scored* check
for that query passes. Parallelize with `-n <workers>` (pytest-xdist — each
worker is its own process, so the same isolation as the CLI's `-j`).

---

## How grading works

Each `Checks (machine-gradeable)` bullet is one objectively decidable assertion.
Two families:

**Deterministic** — string/number matching against the final answer, no LLM:

- `substring` / `substring_any` / `substring_all` — case-insensitive substring(s)
- `must_not_contain` — substring(s) that must be absent (encodes the trap)
- `regex` — pattern the answer/an ID must match
- `number` — `name ≈ value (±tol)`; passes if any number in the answer falls in
  tolerance (`±N%` of counts, `±N` absolute, `±N pp` for percentages, `== v` exact)
- `set_contains` — every listed member appears in the answer

**Semantic** — graded by an LLM judge (Sonnet) over the answer **and the code/tool
trace**; left *unscored* under `--no-judge`:

- `behavior` — a claim about *method* (which endpoint, which filter slot, which
  interpretation, a decline/redirect) — read from the emitted code
- `count_at_least` — the answer enumerates ≥ N distinct items

A query passes when all of its *scored* checks pass.

---

## Notes & caveats

- **Live code execution.** Both backends `exec()` model-generated Python
  in-process to call the public CRDC APIs (the same model archytas's `PythonTool`
  uses). Run it where you'd run those skills.
- **Drift.** Ground-truth numbers were live-verified on the dates in each
  `*_test.md` header and move with data releases; `number` checks grade by
  tolerance, not exact equality. The graded *behaviors* are stable. Re-baseline a
  suite if counts have shifted.
- **Cost / time.** A full `--backend both --all` run is ~46×2 agent sessions plus
  judge calls. Runs are independent, so `-j` parallelizes them (one process per
  run); a single run is ~60–90s, so the full suite is roughly that × (runs ÷ `-j`).
  Narrow with `--service`/`--query` while iterating; use `--dry-run` to preview
  for free.
- **Step budget.** Multi-step suites (PDC, the CDA round-trips) need headroom;
  the archytas backend hard-fails a query if it exceeds `--max-steps`. Default 25
  is comfortable; raise it if a complex query truncates.
