# OpenRouter model trials on the CDA skill tests

> **⚠️ EXPERIMENTAL.** This is an exploratory side-experiment, not part of the
> supported `test_harness` CLI. It reuses the harness's parsing/grading but ships
> its own minimal agent loop and dependencies. Expect rough edges. Findings here
> are a small-N snapshot (3 prompts), not a benchmark.

## What this is

A minimal runner that drives the [`cancer-data-aggregator` skill](../../../skills/cancer-data-aggregator)
test prompts (`queries_md/cda_test.md`) through **arbitrary OpenRouter models**, so
we can compare non-Anthropic models against the same answer key the production
harness uses.

It mirrors the harness's `plain` backend — a `run_python` ReAct loop with live
`cdapython` execution in-process — but talks **OpenAI-style tool-calling via
litellm**, so any OpenRouter model works off a single `OPENROUTER_API_KEY`:

- **Agent under test:** any OpenRouter model (`--model`), runs live CDA queries.
- **Judge:** Claude (`anthropic/claude-sonnet-4.6`) for the semantic `behavior` /
  `count_at_least` checks — also routed through OpenRouter, so one key for both.
- **Grading:** the harness's own deterministic checks (`harness.checks`) +
  the LLM judge, scored against `cda_test.md`'s machine-gradeable `Checks` blocks.
- **Tracing:** optional LangSmith (every agent step + judge call), enabled from
  the repo `.env` `LANGSMITH_*` vars.

## What we did

Ran three prompts chosen as the sharpest signals in the CDA suite:

| qid | prompt | what it probes |
|-----|--------|----------------|
| **A2** | "How many CDA subjects were treated with cisplatin?" | `treatment.therapeutic_agent` discover→filter; distinct-subject vs value-occurrence count |
| **A5** | "How many CDA subjects are diagnosed with melanoma?" | free-text diagnosis needs a `*wildcard*` (exact match returns 0) |
| **C1** | "Find the melanoma patients that also have genomic data, and tell me the most frequently mutated genes." | full CDA→GDC round-trip; *don't* rank from CDA's unreliable mutation table |

Across these models (each picked as the "best available" in its family):

| model | role | notes |
|-------|------|-------|
| `anthropic/claude-sonnet-4.6` | reference | also the judge (see caveat) |
| `qwen/qwen3.5-397b-a17b` | best **open-weight** Qwen | Apache; 397B MoE / 17B active. (`qwen3.7-max` is Alibaba's *proprietary* tier — excluded on purpose.) |
| `google/gemma-4-31b-it` | best Gemma | dense 31B; needs the text-tool-call fallback (below) |
| `google/gemma-4-26b-a4b-it` | first Gemma tried | sparse MoE (~4B active); tool-calls natively but lower capability |

## What we learned

### Headline (A2, A5, C1 — `--max-steps 40`)

| query | claude-sonnet-4.6 | qwen3.5-397b-a17b | gemma-4-31b-it |
|-------|:---:|:---:|:---:|
| A2 | PASS 4/4 | PASS 4/4 | PASS 4/4 |
| A5 | PASS 4/4 | PASS 4/4 | PASS 4/4 |
| C1 | FAIL 4/6 | FAIL 4/6 | FAIL 3/6 |
| **passed** | **2/3** | **2/3** | **2/3** |

All three tie at 2/3. The differentiator is **C1**, the hard multi-step task:

- **Sonnet & open-weight Qwen** both surfaced the real drivers (TP53, CDKN2A) and
  got the cohort size right (~1,229).
- **Gemma-4-31b** got the cohort size right but ranked genes from **CDA's raw
  mutation counts** → the gene-length-biased garbage list (TTN, MUC16, …), missing
  TP53/CDKN2A.
- **All three** failed the two strictest C1 checks: none explicitly stripped the
  `PROGRAM.` prefix to query GDC directly, and none named the specific project
  `TCGA-SKCM` (they used program-level "TCGA"). This is the genuine, shared
  weakness — the textbook CDA→GDC hand-off is hard.

### Findings worth keeping

1. **`gemma-4-31b-it` doesn't honour the OpenAI tool schema on its OpenRouter
   route** (even though the API advertises `tools=true`). It emits its *native*
   `<|tool_call>call:run_python{code:<|"|>…<|"|>}` format as plain text. We added
   a **text-format fallback parser** (`parse_text_tool_calls`) that detects and
   executes these. With the fallback, Gemma-4-31b goes from *unusable* (raw tokens
   as "answers") to a real 2/3. The smaller `gemma-4-26b-a4b-it` tool-calls
   natively and needs no fallback.

2. **Two `cda_test.md` checks are too literal** and produced false-positive
   failures during this experiment (the model was actually *right*):
   - **A2 `must_not_contain: ["1,270"]`** — Qwen correctly explained that 1,270 is
     the value-*occurrence* count while 1,168 is the distinct-*subject* count. The
     blunt substring guard failed it for *mentioning* the number.
   - **A5 `must_not_contain: ["0 subjects"]`** — tripped on an enumerated variant
     like "Epithelioid cell melanoma: **20 subjects**" (`0 subjects` ⊂ `20 subjects`).
   These should get word-boundary / headline-only matching. **Flag to the answer-key
   owner; don't silently edit `cda_test.md`.**

3. **Open-weight is competitive here.** `qwen3.5-397b-a17b` matched Sonnet on all
   three prompts including the C1 driver-gene result — a meaningful data point if
   open-weight / self-hostable models are a goal.

### Caveats

- **Small N (3 prompts).** Directional only. Run the full A–D suite before drawing
  conclusions.
- **Judge = one of the contestants.** The judge is `claude-sonnet-4.6`, which also
  graded the Sonnet row → mild self-grading bias on Sonnet's `behavior` checks.
- **Live-data drift.** Counts move with CDA releases; `number` checks grade by
  tolerance (see `cda_test.md` header).

## How to run

From this directory, using the harness venv at `test_harness/.venv`:

```bash
# one-time setup (creates test_harness/.venv with the two extra deps)
cd ../..                      # -> test_harness/
uv venv .venv
VIRTUAL_ENV="$PWD/.venv" uv pip install litellm cdapython
cd experiments/openrouter

# default run: A2, A5, C1 on the default model, with judge + LangSmith
../../.venv/bin/python run_openrouter.py

# pick model + queries, raise the step budget, save a report
../../.venv/bin/python run_openrouter.py \
    --model qwen/qwen3.5-397b-a17b --query A2,A5,C1 --max-steps 40 \
    -o results/report_qwen.json

# stream every tool call + output; skip the judge / tracing
../../.venv/bin/python run_openrouter.py --query A2 -v --no-judge --no-trace

# aggregate saved reports into the side-by-side table
../../.venv/bin/python compare_reports.py results/report_*.json
```

### Keys & config (repo `.env`)

- `OPENROUTER_API_KEY` — **required**; used for both the agent and the judge.
- `LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT`,
  `LANGSMITH_ENDPOINT` — optional tracing. The runner maps `LANGSMITH_ENDPOINT`
  → `LANGSMITH_BASE_URL` (litellm's name) and forces `LANGSMITH_BATCH_SIZE=1` so a
  short run flushes. Disable per-run with `--no-trace`.

### Flags

| flag | meaning |
|------|---------|
| `--model` | OpenRouter slug under test (default `google/gemma-4-31b-it`) |
| `--judge-model` | judge slug (default `anthropic/claude-sonnet-4.6`) |
| `--query` | comma-separated CDA qids (default `A2,A5,C1`) |
| `--max-steps` | ReAct budget per query (default 40; a cap) |
| `--no-judge` | skip the LLM judge (semantic checks left unscored) |
| `--no-trace` | disable LangSmith even if `LANGSMITH_TRACING=true` |
| `-v/--verbose` | stream each tool call + its output |
| `-o/--output` | write a JSON report |

## How it's organized

```
experiments/openrouter/
├── README.md            # this file
├── run_openrouter.py    # the runner: OpenRouter ReAct loop + grading + tracing
├── compare_reports.py   # aggregate N report JSONs into a side-by-side table
└── results/             # saved reports from the runs above (committed as evidence)
    ├── report_sonnet.json
    ├── report_qwen.json  # qwen3.5-397b-a17b
    └── report_gemma.json # gemma-4-31b-it (with text-tool-call fallback)
```

It deliberately **imports** the production harness (`harness.parsing`,
`harness.skills`, `harness.checks`, `harness.config`) rather than copying it, so
the prompts, skill injection, and grading stay identical to the `plain`/`archytas`
backends. The only new code is the litellm-based agent loop, the text-tool-call
fallback, and the OpenRouter-keyed judge.

## Possible next steps

- Run the **full A–D CDA suite** (and other `*_test.md` services) for real coverage.
- Add more models (DeepSeek, Llama, GLM) — the runner is model-agnostic.
- Promote to a first-class `openrouter` backend under `harness/backends/` if this
  proves useful (would need the text-tool-call fallback folded into `base`).
- Fix the two brittle `cda_test.md` checks upstream.
