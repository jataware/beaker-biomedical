# Handoff: locate with CDA → analyze in GDC

These are **tested, end-to-end query pairs** (verified live against both APIs, mid-2026 — counts drift
with releases). Each starts from a real researcher's goal, uses CDA for what only CDA can do — find a
cohort *across* repositories and emit GDC-resolvable handles — then crosses the **handoff point** into
`genomic-data-commons` for the genomic analysis or download CDA does not perform.

Why this split is real: CDA is harmonized **metadata only**. It has no gene-expression matrices, no
reliable mutation frequencies (its `mutation` table is GDC-derived with documented count problems), no
survival, no BAM slicing, and no download. GDC has all of those — but GDC alone can't tell you a
patient also has proteomics at PDC or imaging at IDC. So researchers use CDA to *scope and assemble*,
then hand the GDC-resident slice to GDC to *analyze*.

## The two handoff keys (verified)

CDA emits identifiers that resolve directly in the GDC API:

| CDA field | Transform | GDC identifier | Verified example |
|---|---|---|---|
| `subject_id` | strip the `PROGRAM.` prefix | `cases.submitter_id` | `CPTAC.C3L-03728` → `C3L-03728` → project `CPTAC-3` |
| `file_id` (= UUID in `drs://dg.4dfc:<uuid>`) | use as-is | GDC file UUID | `00000073-27e1-4dcd-bfdc-e458c31feec2` → `TCGA-BRCA` RNA-Seq BAM |

The robust, documented way to get the GDC id in `cdapython` is the crosswalk join
`add_columns='upstream_identifiers.*'` (yields `upstream_source='GDC'`, `upstream_id=<gdc id>`); the
`PROGRAM.<submitter_id>` convention above is the quick shortcut. See
[../references/CROSS-REPOSITORY.md](../references/CROSS-REPOSITORY.md).

---

## Scenario 1 — Proteogenomics: patients with BOTH GDC genomics and PDC proteomics

> *"CPTAC ran proteomics and genomics on the same tumors. I want the patients who have **both**, then
> their GDC expression data, so I can correlate protein and RNA. No single repository lists that
> overlap for me."*

**Only CDA can find the overlap.** Locate it (verified: 2,345 subjects at both GDC and PDC):

```python
from cdapython import *
set_api_url("https://cda.datacommons.cancer.gov/")

summarize_subjects(match_all=['subject_data_at_gdc = true', 'subject_data_at_pdc = true'])
#   number_of_matching_subjects: 2345

cohort = get_subject_data(match_all=['subject_data_at_gdc = true', 'subject_data_at_pdc = true'],
                          add_columns='upstream_identifiers.*')   # -> per-subject GDC ids
# subject_id values look like: CPTAC.C3L-03728, TCGA.TCGA-23-1123, APOLLO.AP-LU5F, ...
```

**↳ HANDOFF:** take each subject's GDC case id (`C3L-03728` = `CPTAC.C3L-03728` minus the prefix). It
resolves directly as a GDC `cases.submitter_id`:

```python
import requests
sub_ids = ["C3L-03728"]   # derived from CDA subject_ids
r = requests.post("https://api.gdc.cancer.gov/cases", json={
    "filters": {"op": "in", "content": {"field": "submitter_id", "value": sub_ids}},
    "fields": "submitter_id,case_id,project.project_id,primary_site", "size": 100})
# verified: C3L-03728 -> project CPTAC-3, primary_site Brain
case_ids = [h["case_id"] for h in r.json()["data"]["hits"]]
```

Now GDC does the analysis CDA can't — the FPKM-UQ expression matrix for those exact cases:

```python
requests.post("https://api.gdc.cancer.gov/gene_expression/availability", json={
    "case_filters": {"op": "in", "content": {"field": "cases.case_id", "value": case_ids}}})
# -> per-case has_gene_expression_values: true   (then /gene_expression/values for the matrix)
```

**Why it matters:** the cohort definition ("has both omics") is a cross-repository fact only CDA holds;
the expression matrix is a GDC product. → continue in the `genomic-data-commons` skill (its
`examples/get_gene_expression_matrix.md`).

---

## Scenario 2 — BAM slicing without downloading terabytes

> *"CDA found the tumor RNA-Seq BAMs for my cohort. I only need the reads over BRCA1 — I am not
> downloading whole BAMs to pull one gene."*

Locate the BAMs in CDA (verified: 197,324 BAM files are GDC-resident; they come back with a `file_id`
that **is** the GDC UUID, plus `access`):

```python
bams = get_file_data(match_all=['file_data_at_gdc = true', 'format = BAM'],
                     data_source='GDC')
# rows: file_id=00000073-27e1-4dcd-bfdc-e458c31feec2,
#       drs_uri=drs://dg.4dfc:00000073-...,  access=controlled,  file_type=Aligned Reads
```

**↳ HANDOFF:** the CDA `file_id` is the GDC file UUID. Confirm and slice in GDC:

```python
uuid = "00000073-27e1-4dcd-bfdc-e458c31feec2"
requests.get(f"https://api.gdc.cancer.gov/files/{uuid}",
             params={"fields": "file_name,experimental_strategy,cases.project.project_id,access"}).json()
# verified -> TCGA-BRCA, RNA-Seq, Aligned Reads, access=controlled

# Remote BAM slice by gene — a GDC capability CDA has no equivalent for:
import os
headers = {"X-Auth-Token": os.environ["GDC_TOKEN"]}   # controlled file -> dbGaP-backed token required
sl = requests.get(f"https://api.gdc.cancer.gov/slicing/view/{uuid}",
                  params={"gencode": "BRCA1"}, headers=headers)   # returns BAM bytes
```

**Why it matters:** CDA is metadata-only and never moves bytes; remote slicing lives in GDC. Note CDA's
`access=controlled` flag warns you up front that this file needs the user's dbGaP authorization and a
`GDC_TOKEN`. → the `genomic-data-commons` skill (its `examples/bam_slice_by_gene.md`).

---

## Scenario 3 — "Don't default to TCGA": disease breadth in CDA → project-scoped mutation frequency in GDC

> *"I study breast cancer and everyone just grabs TCGA-BRCA. Where does the data actually live, and what
> are the most-mutated genes across the right projects — with trustworthy frequencies?"*

CDA gives the cross-repository reality check (how many breast subjects exist, and where):

```python
summarize_subjects('breast', data_source='GDC')   # GDC-resident breast subjects + the cross-DC Venn
```

**↳ HANDOFF:** hand the disease to GDC, which is project-aware. Faceting cases by project shows breast
spans **20 GDC projects**, and TCGA-BRCA is not even the largest (verified):

```python
r = requests.post("https://api.gdc.cancer.gov/cases", json={
    "filters": {"op": "in", "content": {"field": "primary_site", "value": ["Breast"]}},
    "facets": "project.project_id", "size": 0})
# verified buckets: FM-AD 2583, TCGA-BRCA 1098, CMI-MBC 200, CPTAC-2 134, HCMI-CMDC 69, ... (20 projects)

requests.get("https://api.gdc.cancer.gov/analysis/top_mutated_genes_by_project",
             params={"project_id": "TCGA-BRCA", "size": 5}).json()
# verified top genes: TP53, CSMD3, CSMD1, TTN, CDKN2A
```

**Why it matters:** CDA stops the TCGA tunnel-vision (it shows the disease's spread across repos), but
**mutation frequency must come from GDC** — CDA's own `mutation` table has documented unreliable counts,
and GDC's cohort-correct denominators (cohort in `case_filters`, Cancer Gene Census in `filters`) are
the authoritative recipe. → the `genomic-data-commons` skill (its `examples/top_mutated_genes.md` and
`examples/discover_projects_for_disease.md`).

---

## Other handoffs (same pattern)

| Researcher goal | CDA locates | ↳ Handoff key | GDC analyzes |
|---|---|---|---|
| Survival by expression | cohort across repos, GDC-resident subset | case ids | `/analysis/survival` (log-rank) + `/gene_expression/values` |
| CNV landscape of a located cohort | subjects/files at GDC | case ids | `/cnvs`, `/cnv_occurrences` |
| Download a located open file set | file rows + `drs_uri` | GDC UUID / drs_uri | `/data/{uuid}` or DTT manifest (controlled → token) |
| scRNA-Seq for a sample | the file at GDC | file UUID | `/scrna_seq/gene_expression` |

## Notes

- **Counts drift** with releases — re-run; cite CDA `release_metadata` and GDC `/status` for provenance.
- **`cdapython` for the CDA side, GDC REST for the GDC side.** The CDA-locate snippets use the client
  (it gives `*` wildcards and the `upstream_identifiers.*` crosswalk); the GDC-analyze snippets follow
  `genomic-data-commons` conventions.
- **Controlled access never leaves CDA's purview clean:** CDA's `access` column tells you *before* the
  handoff whether GDC retrieval will need a `GDC_TOKEN` + dbGaP authorization. Open files need neither.
- The reverse is just as useful: a GDC-only researcher can use CDA to discover their GDC cases *also*
  have PDC/IDC data worth integrating (Scenario 1, run from the GDC side).
