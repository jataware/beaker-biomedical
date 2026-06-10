# beaker-biomedical: agent skills for the Cancer Research Data Commons

A prototype AI agent, packaged as a container, that answers natural-language questions against the
NCI **Cancer Research Data Commons (CRDC)** repositories. It is built on
[Beaker](https://github.com/jataware/beaker-kernel), a Jupyter-based notebook with a built-in,
code-running AI assistant, and equipped with a set of **Agent Skills**, one per CRDC repository,
that teach the agent how each commons' API works.

> **Status: prototype.** This is an early deliverable for the Cancer Genomics Cloud (CGC) developer
> team to evaluate the *approach*: skills-driven agentic access to CRDC. The skills are hand-authored
> and still improving; answer quality tracks skill quality and is expected to climb as the skills are
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
| Genomic Data Commons (GDC) | `genomics-data-commons` | REST API |
| Proteomic Data Commons (PDC) | `proteomic-data-commons` | GraphQL |
| Imaging Data Commons (IDC) | *fetched remotely* (see below) | `idc-index` |
| General Commons (GC, formerly CDS) | `general-commons` | GraphQL |
| Integrated Canine Data Commons (ICDC) | `integrated-canine-data-commons` | GraphQL |
| Clinical and Translational Data Commons (CTDC) | `clinical-translational-data-commons` | GraphQL |
| Population Sciences Data Commons (PS-DC) | `population-sciences-data-commons` | GraphQL (prototype) |
| Cancer Data Aggregator (CDA) | `cancer-data-aggregator` | `cdapython` (cross-repository metadata) |

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
repository. Add or remove remote skills by editing `skills.json` (mounted at
`/beaker/.beaker/skills.json`).

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

Test suites live in [`test_queries/`](test_queries/):

- **[`test_queries/TEST_QUERIES.md`](test_queries/TEST_QUERIES.md)**: CDA generalization suite: ~20 prompts across core query mechanics, file-modality → correct hand-off, full locate→analyze round-trips, and out-of-scope requests the agent should decline. Includes a scoring rubric.
- **[`test_queries/pdc_test.md`](test_queries/pdc_test.md)**: PDC live-harness suite: discovery, quantitation interpretation (relative vs absolute), and file download / version-resolution / robustness, with verified ground truth (PDC Data Release 6.1).

Ground-truth counts were verified live (≈ mid-2026) and **drift with each data release**; grading
targets the *approach* and the right order of magnitude, re-baselining against each commons' metrics
endpoint when numbers shift.

_To be filled out: per-skill pass rates, the harness/runner used, regression cadence, and coverage for
the GDC, GC, and IDC skills._

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

