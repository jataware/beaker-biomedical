# Intended Behavior

Melanoma is recorded across many CRDC projects, so the agent must not settle on one. It filters
subjects with the free-text wildcard `diagnosis = *melanoma*` (≈1,444 subjects, verified 2026-06-18)
and then **facets them by `project_short_name`** — e.g. `column_values('project_short_name')` under
the diagnosis filter, or tabulating `get_subject_data(match_all=['diagnosis = *melanoma*'],
add_columns='project_short_name')`.

The distribution spans many projects/programs (verified live 2026-06-18 by value-counting
`project_short_name` over the 1,444 melanoma subjects):

- FM-AD ≈ 571
- TCGA-SKCM ≈ 470
- CPTAC (cptac_cm) ≈ 95
- TCGA-UVM ≈ 80
- CMB (cmb_mel) ≈ 54
- HCMI-CMDC ≈ 45
- PDMR ≈ 20, NCATS-COP01 ≈ 12, CTSMC/CCDI ≈ 14, …

Note `project_short_name` is multi-valued and **collapses program-, project-, and dbGaP-`phs`-level
ids together** (e.g. `TCGA` + `phs000178`, `FM`/`FM-AD`/`phs001179`, `tcga_skcm`/`TCGA-SKCM`), so the
same subject appears under several aliases. A strong answer reports several distinct projects with
per-project subject counts and notes this multi-granularity.

The two anchor projects (`set_contains`) are `TCGA-SKCM` and `FM-AD` — the two largest melanoma
project-level cohorts, which any correct breakdown must list. The prompt explicitly asks "which
projects have them", so the project ids are the requested return value; everything else about the
*method* (faceting, not tunnel-visioning) is left to the behavior judge.

# Incorrect Behavior

The agent reports only one project (commonly TCGA-SKCM), or gives a single ungrouped total, missing
that melanoma is distributed across many CRDC projects.
