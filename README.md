# Beaker Biomedical: an agent for the Cancer Research Data Commons data fabric

An agent powered by [Beaker](https://github.com/jataware/beaker-notebook), packaged as a container, that provides a natural-language interface to query and use data from the 
NCI **Cancer Research Data Commons (CRDC)** data fabric. Beaker is an AI-enabled computational notebook with a built-in,
code-running AI assistant, and equipped with a set of **Agent Skills**, one per CRDC repository,
that teach the agent how each commons' API works. It also provides a top-level skill for the [Cancer Data Aggregator (CDA)](https://cda.readthedocs.io/) API and Python Library.

> Note: This is a preliminary implementation for the Cancer Genomics Cloud (CGC) developer
> team to evaluate the *approach*: skills-driven agentic access to CRDC. The skills are very much a work in progress
> and still improving; answer quality and user experience tracks with skill quality and is expected to climb as the skills are
> refined. See [Expected failure modes](#expected-failure-modes).

---

## Table of contents

- [About](#about)
- [Skills](#skills)
- [Testing](#testing)
- [Expected failure modes](#expected-failure-modes)
- [Build and run](#build-and-run)

---

## About

`beaker-biomedical` is a [Beaker](https://github.com/jataware/beaker-kernel) **context** (a domain
extension) plus a library of Agent Skills covering the CRDC data commons. Beaker gives the agent a
live Python subkernel; the skills give it the domain knowledge to write correct queries against each
commons' API. A user asks a question in plain language ("which proteomics studies cover clear cell
renal cell carcinoma, and how many cases each?"); the agent picks the relevant skill, writes and runs
the Python, and reports the verified answer, showing its code along the way.

The container bundles everything: the Beaker server/notebook, the `beaker-biomedical` context, the
Python client packages (`cdapython`, `idc-index`, `requests`, …), and the mounted skills. You provide
an LLM API key and `docker-compose up`.

**Covered repositories:**

| Commons | Skill | Interface |
|---|---|---|
| Cancer Data Aggregator (CDA) | `cancer-data-aggregator` | `cdapython` (cross-repository metadata) |
| Genomic Data Commons (GDC) | `genomics-data-commons` | REST API |
| Proteomic Data Commons (PDC) | `proteomic-data-commons` | GraphQL |
| Imaging Data Commons (IDC) | *fetched remotely* (see below) | `idc-index` |
| General Commons (GC, formerly CDS) | `general-commons` | GraphQL |
| Integrated Canine Data Commons (ICDC) | `integrated-canine-data-commons` | GraphQL |
| Clinical and Translational Data Commons (CTDC) | `clinical-translational-data-commons` | GraphQL |
| Population Sciences Data Commons (PS-DC) | `population-sciences-data-commons` | GraphQL (prototype) |


CDA is the cross-cutting entry point: it *locates* data across all the repositories (returning DRS
URIs), then hands off to the repository-specific skill for deep analysis or download.

---

## Skills

### Where the skills live

All skills live in the [`skills/`](skills/) directory and are mounted into the container at
`/beaker/.beaker/skills`. Each is a self-contained folder; the entry point is its `SKILL.md`.

- **[`skills/cancer-data-aggregator/SKILL.md`](skills/cancer-data-aggregator/SKILL.md)**: CDA, cross-repository metadata search and routing (`cdapython`).
- **[`skills/genomics-data-commons/SKILL.md`](skills/genomics-data-commons/SKILL.md)**: GDC genomics: cases/files, expression matrices, mutation frequency, survival, BAM slicing, GraphQL.
- **[`skills/proteomic-data-commons/SKILL.md`](skills/proteomic-data-commons/SKILL.md)**: PDC proteomics: studies, quantitation matrices, spectral counts, signed-URL downloads.
- **[`skills/general-commons/SKILL.md`](skills/general-commons/SKILL.md)**: GC / CDS: programs, studies, participants, clinical/biospecimen/file metadata (lower-priority fallback).
- **[`skills/integrated-canine-data-commons/SKILL.md`](skills/integrated-canine-data-commons/SKILL.md)**: ICDC comparative oncology: canine cancer studies, faceted cohort building (breed/diagnosis/…), clinical-trial data, DRS file manifests, GraphQL.
- **[`skills/clinical-translational-data-commons/SKILL.md`](skills/clinical-translational-data-commons/SKILL.md)**: CTDC clinical/translational trial data: participants with CTEP-coded diagnoses, targeted/non-targeted therapy, surgery, radiotherapy, biospecimens; faceted cohort building, per-study clinical node data, DRS files, GraphQL.
- **[`skills/population-sciences-data-commons/SKILL.md`](skills/population-sciences-data-commons/SKILL.md)**: PS-DC population-science screening cohorts (NLST, PLCO, PBCS): study metadata, demographics, cancer sites, data-collection scope, faceted study search, study-level DRS files, GraphQL. New prototype — study-level queries only (participant-level endpoints not yet live).

The **Imaging Data Commons (IDC)** skill is not vendored in this repo. It is referenced by URL in
[`skills.json`](skills.json) and pulled in at runtime from the upstream
[`ImagingDataCommons/idc-claude-skill`](https://github.com/ImagingDataCommons/idc-claude-skill)
repository. 

> **Note**: Externally hosted (e.g. via Github) skills such as the IDC skill can be managed via `skills.json`. Add or remove remote skills by editing `skills.json` (which mounts to the built container at `/beaker/.beaker/skills.json`).

---

### Anatomy of a skill

A **skill** is a folder of instructions and reference material that the agent loads on demand to gain
a specific capability: here, "how to query commons X." It follows the
[Agent Skills](https://agentskills.io) convention and uses **progressive disclosure** so the agent's
context stays lean:

```
skills/<name>/
├── SKILL.md        # entry point: YAML frontmatter (name + description) and core instructions
├── references/     # deep reference docs, read only when a task needs them
├── examples/       # worked, end-to-end query recipes
├── assets/         # API specs, OpenAPI/GraphQL schemas, man pages
└── auth.yaml       # the commons' auth model (most CRDC metadata is open-access)
```

The agent first reads only each skill's frontmatter `description` to decide which skill is relevant.
Once a skill is selected, it reads that skill's `SKILL.md`, and pulls in individual `references/`,
`examples/`, or `assets/` files **only as a given query requires**, so a single question never loads
the entire library. In effect, each skill is a compact, curated manual for one commons' API, written
for the agent rather than a human.

---

## Testing

> _This section is in progress and will be expanded with run results._

Testing to date is **behavioral evaluation in a live agent harness**: each skill has a suite of
natural-language prompts with verified ground-truth answers, run against the live CRDC APIs. The
prompts are deliberately chosen to use diseases, genes, columns, and IDs that appear **nowhere** in
the skill's own examples, so a pass demonstrates the skill *generalizes* rather than echoing its
worked examples. Each prompt embeds a known trap (e.g. value casing, wrong-commons routing, transient
null responses) and a gradeable outcome.

Test suites live in [`test_harness/tests/`](test_harness/tests/) — **one directory per external service**,
split into category folders, with one directory per test (`test.md` = prompt, `rationale.md` = verified
ground-truth rationale, `eval.yaml` = machine-gradeable checks: substring / number-with-tolerance /
set-membership / regex / behavioral assertions), so the corpus is authoritative for the code test suite:

- **[`test_harness/tests/cda/`](test_harness/tests/cda/)**: CDA (`cancer-data-aggregator`) — core query mechanics, file-modality → correct hand-off, full locate→analyze round-trips, and out-of-scope requests the agent should decline.
- **[`test_harness/tests/gdc/`](test_harness/tests/gdc/)**: GDC (`genomic-data-commons`) — project discovery (don't default to TCGA), the `case_filters` mutation-frequency denominator trap, "highly expressed" = most-variable, array-of-filters survival log-rank, and the facet-name (200-not-400) trap.
- **[`test_harness/tests/pdc/`](test_harness/tests/pdc/)**: PDC (`proteomic-data-commons`) — discovery, quantitation interpretation (relative vs absolute), and file download / version-resolution / robustness.
- **[`test_harness/tests/gc/`](test_harness/tests/gc/)**: GC (`general-commons`) — fallback-routing boundary, GC-only caNanoLab data + the non-`phs` key quirk, `phs_accession` resolution + String-cast, faceted search, and the DRS / no-direct-download model.
- **[`test_harness/tests/icdc/`](test_harness/tests/icdc/)**: ICDC (`integrated-canine-data-commons`) — faceted cohort building, controlled-vocabulary (empty ≠ absent), mapping one dog across studies, per-study clinical detail + the empty-node trap, and files → DRS → manifest.
- **[`test_harness/tests/ctdc/`](test_harness/tests/ctdc/)**: CTDC (`clinical-translational-data-commons`) — the required `variables`-key first-call quirk, `GroupCount.subjects`, a fresh disease cohort + its therapies, the carcinogen-exposure facet, the bracketed-string array quirk, and per-specimen-vs-per-participant counting.
- **[`test_harness/tests/psdc/`](test_harness/tests/psdc/)**: PS-DC (`population-sciences-data-commons`) — study-level demographics, the participant-level "not-live" boundary (no fabrication), `primarySiteMorphology`, the `subjects`-means-studies facet caveat, and the dbGaP handoff.

Each suite deliberately uses diseases, genes, studies, breeds, and IDs that appear **nowhere** in that
skill's own `examples/` (e.g. kidney/colorectal rather than GDC's breast; bladder cancer rather than
ICDC's osteosarcoma), so a pass demonstrates the skill *generalizes* rather than echoing its examples.
Ground-truth values were verified live on **2026-06-11** (GDC Data Release 45.0; the Bento/GraphQL
commons at their then-current loads) and **drift with each data release** — `number` checks grade the
right order of magnitude / tolerance, re-baselining against each commons' metrics endpoint when numbers
shift, while the graded *behaviors* (right endpoint, right filter slot, right interpretation) are stable.

The Imaging Data Commons (IDC) skill is fetched remotely (see [`skills.json`](skills.json)) and is not
yet covered here. _To be filled out: per-skill pass rates, the harness/runner used, and regression cadence._

---

## Expected failure modes

This is a **prototype**, and the agent is only as good as the skill backing a given query. We expect
quality to improve materially as the skills are refined. Known and anticipated failure modes:

- **Stale counts.** Verified numbers drift with each CRDC data release; an answer can be correct in
  approach but off on the exact integer.
- **Wrong-commons routing.** The agent may route a query to the wrong repository (e.g. proteomics →
  GDC), or over-rely on the lower-priority General Commons when a specialized commons fits better.
- **Free-text value mismatches.** Filtering on an un-verified value (wrong casing, or an exact term
  where a wildcard is needed) can silently return zero results instead of the intended cohort.
- **Hallucinated fields.** On a corner the skill doesn't cover, the agent may invent a column,
  endpoint, or capability rather than discovering the real one.
- **Boundary confusion.** CDA locates metadata only (returns DRS URIs); the agent can wrongly claim it
  downloads bytes, computes abundances, or runs analyses.
- **API flakiness.** Transient `null` payloads and signed-URL expiry (PDC) can derail a run unless the
  skill's retry guidance is followed.
- **Skill-discovery misses.** With several overlapping skills, the agent occasionally selects a
  suboptimal one for an ambiguous prompt.

Most of these are addressable by improving the relevant skill's instructions, examples, and reference
coverage, which is the intent of the prototype.

---

## Build and run

### Build

```console
docker-compose build
```

This builds the image from the [`Dockerfile`](Dockerfile) (Python 3.11, installs `beaker-biomedical`
and its client dependencies). No environment variables are needed to build.

---

### Run

1. Create your environment file from the sample and fill in at least one LLM API key:

```console
cp env.sample .env
```

Edit `.env`; see [`env.sample`](env.sample) for the full list. The key settings:

- `ANTHROPIC_API_KEY`: required for the default configuration.
- `LLM_PROVIDER_IMPORT_PATH`
- `LLM_SERVICE_MODEL`: default to Anthropic / `claude-sonnet-4-6`.
- `LANGSMITH_*`: optional tracing; leave blank to disable.

For example, for Bedrock;

# TODO: Add Bedrock Config

(`.env` is gitignored; your keys stay local.)

2. Start the stack:

```console
docker-compose up
```

3. Open the Beaker notebook at **http://localhost:8888**.

The [`docker-compose.yaml`](docker-compose.yaml) mounts [`skills/`](skills/) and
[`skills.json`](skills.json) into the container, so you can edit a skill and restart to pick up changes
without rebuilding the image. The `beaker-biomedical` context loads automatically
(`BEAKER_DEFAULT_CONTEXT=beaker-biomedical`).

