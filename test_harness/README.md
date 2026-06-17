# Skill evaluation harness

Runs the authoritative benchmark prompts in [`tests/`](tests/) through a model
with the matching NCI CRDC skill loaded, then **grades the answer against the
machine-gradeable checks** in each test's `eval.yaml`.

It answers one question per query: *with this skill loaded, does the model reach
the live-verified ground truth — using the right method, and avoiding the trap?*

## One engine, any model

There is a **single execution engine**: a ReAct loop driven through
**[litellm](https://github.com/BerriAI/litellm)**, which normalises OpenAI-style
tool-calling across every provider. The agent gets two tools — `run_python`
(execute code in a persistent namespace) and `read_skill_file` (load one of the
skill's reference/example/asset files into context by its relative path, the
progressive-disclosure mechanism). The only variable is the **model** — list one
or several with `--model` and they all get the *identical* skill text + tools + task.

Which provider a model id reaches is decided by one rule
([`harness/llm/routing.py`](harness/llm/routing.py)):

| model id | routed to | why |
|----------|-----------|-----|
| `claude-*` | `anthropic/…` | Anthropic hosts its own — **never OpenRouter** |
| `gpt-*`, `o3-*`, `chatgpt-*` | `openai/…` | OpenAI hosts its own |
| `gemini-*` | `gemini/…` | Google hosts its own |
| everything else (`qwen/…`, `google/gemma-…`, `meta-llama/…`, …) | `openrouter/…` | **fallback** for open-weight / community models |
| explicit `provider/model` prefix | honoured verbatim | `anthropic/`, `openai/`, `gemini/`, `vertex_ai/`, `openrouter/` |

So `claude-sonnet-4-6` is *always* called natively on `ANTHROPIC_API_KEY`, and a
slug like `qwen/qwen3-coder-next` falls back to OpenRouter — by construction, not
by convention. A text-tool-call fallback keeps models that emit their native tool
format as plain text usable — for *both* tools (e.g. `google/gemma-4-31b-it`).

**The judge is just another routed model.** The semantic `behavior` /
`count_at_least` checks are graded by `--judge-model` (default `claude-sonnet-4-6`
→ Anthropic), routed through litellm exactly like the agent and fully selectable
(`--judge-model gemini-2.5-pro` works). A run needs the API key for every distinct
provider across its test models *plus* the judge's; `--no-judge` drops the judge.

---

## Layout

```
test_harness/
├── harness/                 # the package
│   ├── config.py            # paths, model/judge defaults, per-provider key resolution (.env aware)
│   ├── parsing.py           # tests/.../{test.md,eval.yaml}  ->  Query / Check objects
│   ├── checks.py            # grade each Check (reads check.params)  ->  CheckResult
│   ├── skills.py            # service -> skill dir; build prompts; read_skill_file resource loader
│   ├── judge.py             # LLM judge for semantic checks (litellm, any provider)
│   ├── runner.py            # select -> run -> grade  (one process per run)
│   ├── report.py            # console + JSON rendering (schema_version "1", full trace)
│   ├── meta.py              # run-level meta + skill capture + docs_opened detection
│   ├── compare.py           # side-by-side comparison of N report JSONs
│   ├── cli.py               # the CLI test runner  (python -m harness.cli)
│   ├── site/                # static dashboard builder (report JSON -> index.html)
│   │   ├── build.py         # pure JSON -> HTML: aggregate, snapshot, render, inline
│   │   └── template/        # index.html + style.css + app.js (vanilla, no deps)
│   └── llm/                 # the model-access layer (one litellm engine)
│       ├── routing.py       # model id -> provider (the heart of the design)
│       ├── completion.py    # the single typed litellm boundary
│       ├── agent.py         # the two-tool (run_python + read_skill_file) ReAct loop -> AgentRun
│       ├── tools.py         # run_python + read_skill_file tool schemas + text-tool-call fallback
│       └── sandbox.py       # in-process PyEnv exec sandbox + CodeStep/ResourceStep trace + formatters
├── tests/                   # the benchmark corpus: tests/<service>/<category>/<test>/
│   └── <service>/<category>/<test>/{test.md, rationale.md, eval.yaml}
├── unit/                    # pytest: unit (no API) + live (opt-in)
├── run.py                   # == python -m harness.cli
└── pyproject.toml           # package + deps + pytest + ty config
```

Each test lives in its own directory:

- **`test.md`** — optional YAML frontmatter (`name`, `description`); everything after
  the frontmatter is the prompt handed verbatim to the agent.
- **`rationale.md`** — `# Intended Behavior` and `# Incorrect Behavior` prose: **design
  rationale only**, never parsed, never sent to the agent or judge.
- **`eval.yaml`** — the machine-read answer key: a top-level `checks:` list.

A test's `ref` is `<service>:<category>/<test>` (e.g. `cda:core_query_mechanics/discovery`);
`--query` also accepts the bare `<category>/<test>` or just the leaf slug (`discovery`).

[`tests/README.md`](tests/) is the authoritative reference for the corpus format and for
**exactly what data reaches the agent and the judge at each step** — read it before authoring.

Each `tests/<service>/` directory maps to one skill under `../skills/`:

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

This pulls `litellm` (the single model-access layer), plus `requests`/`cdapython`
— the libraries the skills' own example code imports, so a failure reflects the
**skill**, not a missing dependency.

### API keys

The harness reads each provider's key from, in order: the matching `--*-api-key`
flag, the process env, then the repo's `../.env`:

| env var | provider | when it's needed |
|---------|----------|------------------|
| `ANTHROPIC_API_KEY` | Anthropic (`claude-*`) | default agent + default judge |
| `OPENAI_API_KEY` | OpenAI (`gpt-*`, `o*`) | a `gpt-*` / `o*` test or judge model |
| `GEMINI_API_KEY` | Google (`gemini-*`) | a `gemini-*` test or judge model |
| `OPENROUTER_API_KEY` | OpenRouter (everything else) | any open-weight slug |

The CLI resolves only the keys a given run actually needs and errors up front if
one is missing. Nothing else is needed for the open-access CRDC APIs.

### Type checking

```bash
ty check harness        # or: uvx ty check harness
```

---

## CLI

```bash
# list parsed queries + their checks (no API calls)
python -m harness.cli list
python -m harness.cli list --service gdc --checks

# dry-run: assemble prompts, show the checks + model routing, call nothing
python -m harness.cli run --service pdc --dry-run
python -m harness.cli run --query gdc:project_discovery --dry-run --show-prompt

# run a couple of queries comparing two models, write a JSON report
python -m harness.cli run --query gdc:project_discovery,gdc:survival_logrank \
    --model claude-sonnet-4-6,qwen/qwen3-coder-next -o report.json

# run a whole skill suite on one model, with per-check detail
python -m harness.cli run --service icdc --model claude-sonnet-4-6 --detail

# run EVERYTHING in parallel (explicit opt-in — this is many live API calls)
python -m harness.cli run --all --model claude-sonnet-4-6 -j 8 -o full.json

# run a non-Anthropic model via OpenRouter, judged by Gemini
python -m harness.cli run --model qwen/qwen3-coder-next --judge-model gemini-2.5-pro \
    --service cda -o qwen.json

# compare saved reports side-by-side (no API)
python -m harness.cli compare qwen.json gemma.json sonnet.json
```

Runs are independent and parallelize across processes (`-j/--concurrency`,
default 8). One process per run keeps each agent's `sys.stdout`/exec state
isolated; wall-clock collapses to roughly the slowest run × (runs ÷ workers).
`-j 1` forces sequential mode with live per-run streaming. Raising `-j` past a
provider's rate limit will cause `429`s, so push it up gradually.

Key `run` flags:

| flag | meaning |
|------|---------|
| `--model` | comma list of test models, each routed through litellm (see the table above). Listing >1 compares them in one report. Default `claude-sonnet-4-6`; or `$HARNESS_MODEL` |
| `--judge-model` | model for the judge (default `claude-sonnet-4-6`), routed like `--model`, independent of it |
| `--service` / `--query` | narrow the selection (`gdc` / `cda:core_query_mechanics/discovery,pdc:discovery`) |
| `--all` | run the full suite (required if no selection given) |
| `--max-steps` | per-query ReAct budget (default 50; a cap, only costs tokens if hit) |
| `-j/--concurrency` | parallel runs, one process each (default 8; `1` = sequential) |
| `--no-judge` | skip LLM grading of `behavior`/`count_at_least` (leaves them unscored) |
| `--anthropic-api-key` / `--openai-api-key` / `--gemini-api-key` / `--openrouter-api-key` | override the matching env var |
| `--dry-run` / `--show-prompt` | preview (incl. model routing) without calling the API |
| `--detail` | print every check result, not just failures |
| `-o/--output` | write a full JSON report (run-level `meta`, the verbatim injected `skills`, and per-run final answer, graded checks, the interleaved `trace` of code steps + `read_skill_file` loads, and detected `docs_opened`) |
| `--html` | also build the static dashboard (one self-contained `index.html`) from this run |
| `--rep` | repetition index stamped on the report; run with `--rep 1..N` to N files the dashboard aggregates into per-(test,model) pass-rates |

`run` exits non-zero if any selected run fails (CI-friendly).

A second subcommand, `compare <report.json> …`, prints a query × model grid plus
per-check detail across any number of saved reports — no API calls. (It reads a
report's top-level `model`, so write one report file per model for comparison.)

---

## Dashboard

`site` turns one or more report JSONs into a single **self-contained
`index.html`** — data, CSS and JS all inlined, so it opens straight from disk
(no server) and uploads as one CI artifact. It is a pure `JSON → HTML` build, so
it reruns cheaply after every harness run.

```bash
# build from a glob of reports (multiple files/reps aggregate into pass-rates)
python -m harness.cli site reports/*.json -o dashboard/index.html

# or build it inline with a run
python -m harness.cli run --all --model claude-sonnet-4-6 -o run.json --html dashboard/index.html
```

Three hash-routed views, all from the same embedded blob:

- **Results** — a pass-rate heatmap (rows = tests grouped by service/category,
  columns = models, *amber* = partial across reps), filters (search, fail-only,
  service/model), and a per-run detail panel: the prompt, the graded checks
  (deterministic vs judge), and the **trace** as step cards (the code the agent
  ran + its stdout/stderr, error steps auto-expanded).
- **Skills** — a *read-only* browser of the whole skill repo at the captured SHA,
  rendered markdown, with a **reference-reach** badge per doc (`opened in k/N
  runs`, greyed at `0/N`) computed from each run's `docs_opened`. A run's trace
  links here via *"View full skill →"*.
- **Tests** — the corpus / answer-key explorer: rendered `test.md` prompt and
  `rationale.md`, the pretty-printed `eval.yaml` checks, and links to the runs.

The report schema is the contract (`schema_version: "1"`): a `meta` block
(timestamp, git branch+SHA, config, CI context), a top-level `skills` capture
(the verbatim injected `SKILL.md` + offered file listing per service), and
per-run `category` / `rep` / `run_uid` / `docs_opened`. The builder tolerates the
legacy single-model `backend` schema, and snapshots the `skills/` + `tests/`
trees from the working copy at build time.

**CI:** [`.github/workflows/eval-dashboard.yml`](../.github/workflows/eval-dashboard.yml)
runs the suite (provider keys from repo Secrets) and publishes the dashboard as
an artifact (and optionally to Pages). It is manual + weekly, not per-push, since
each run spends API tokens; widen models/reps/services via the dispatch inputs.

---

## pytest

The same selection logic is exposed as parametrized tests — one per
`(query, model)`. Unit tests (parser, deterministic grader, routing, sandbox) run
by default and need no key; the **live** tests are opt-in.

```bash
pytest                                    # unit tests only (fast, no API)
pytest --run-live -n 8                    # full live suite, default model, 8-way parallel
pytest --run-live --service gdc           # one suite
pytest --run-live --model claude-sonnet-4-6,qwen/qwen3-coder-next   # compare models
pytest --run-live --query cda:discovery,pdc:discovery   # specific queries
pytest --run-live --no-judge
```

Live test ids look like `cda:core_query_mechanics/discovery|claude-sonnet-4-6`. A test passes when every
*scored* check for that query passes. Live tests skip automatically if a needed
provider key is absent. Parallelize with `-n <workers>` (pytest-xdist — each
worker is its own process, so the same isolation as the CLI's `-j`).

---

## How grading works

Each entry in a test's `# Automated Checks` block is one objectively decidable
assertion — a single-key YAML map keyed by the check type. Two families:

**Deterministic** — string/number matching against the final answer, no LLM:

- `substring` (scalar) / `substring_any` / `substring_all` (lists) — case-insensitive substring(s)
- `must_not_contain` (list) — substring(s) that must be absent (encodes the trap)
- `regex` — scalar pattern (or `{name, pattern}`) the answer/an ID must match
- `number` — `{name, target, tolerance_percent | tolerance_absolute | tolerance_pp | exact}`;
  passes if any number in the answer falls within `target ± tolerance`
- `set_contains` — `{name, members}`; every member appears in the answer

```yaml
checks:
  - number: {name: deceased_subjects, target: 8556, tolerance_percent: 15}
  - substring_any: [dead, deceased]
  - behavior: called column_values('vital_status') before filtering
  - set_contains: {name: top_genes, members: [TP53, CDKN2A]}
```

**Semantic** — graded by the LLM judge (`--judge-model`, default Sonnet, routed
through litellm regardless of which model the agent ran) over the answer **and the
code/tool trace**; left *unscored* under `--no-judge`:

- `behavior` — a claim about *method* (which endpoint, which filter slot, which
  interpretation, a decline/redirect) — read from the emitted code
- `count_at_least` — `{name, min}`; the answer enumerates ≥ N distinct items

A query passes when all of its *scored* checks pass.

---

## Notes & caveats

- **Live code execution.** The engine `exec()`s model-generated Python in-process
  to call the public CRDC APIs. Run it where you'd run those skills.
- **Drift.** Ground-truth numbers were live-verified (~June 2026) and move with
  data releases; `number` checks grade by tolerance, not exact equality. The
  graded *behaviors* are stable. Re-baseline a test if counts have shifted.
- **Cost / time.** A full `--all` run is 45 agent sessions per model plus judge
  calls. Runs are independent, so `-j` parallelizes them (one process per run); a
  single run is ~60–90s, so the full suite is roughly that × (runs ÷ `-j`). Narrow
  with `--service`/`--query` while iterating; use `--dry-run` to preview for free.
- **Step budget.** Multi-step suites (PDC, the CDA round-trips) need headroom; a
  query that exceeds `--max-steps` is recorded as an error. Default 50 is
  comfortable; raise it if a complex query truncates.
- **Run-to-run variance** is real even at temperature 0 (provider batching, MoE
  routing), amplified by the multi-step loop and threshold checks — repeat and
  average before ranking models.
