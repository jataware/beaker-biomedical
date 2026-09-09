# Facet field names

`facets=<field>` aggregates record counts by that field's distinct values. Pair with `size=0` when you
only need the counts, not the underlying records. The response carries
`data.aggregations.<field>.buckets[]` — each bucket is `{key, doc_count}`.

Facet field names are GDC field names, not free text. The most common reason a `facets=` call returns
nothing useful is that the field name was hallucinated. Use the procedure below before sending.

## Before you send a `facets=` call

1. **Check the per-endpoint table below.** If the field is listed, you can use it directly.
2. **If not, hit `/_mapping`.** `GET https://api.gdc.cancer.gov/<endpoint>/_mapping` and search the
   `fields` array (endpoint-specific names) or the top-level `_mapping` keys (endpoint-agnostic
   names) for the concept you want. Stage, gender, race, etc. all live under field-group prefixes
   (`diagnoses.*`, `demographic.*`, …) — there is no bare `stage`, `gender`, or `race` on `/cases`.
3. **Dry-run with `size=0`.** Send `GET <endpoint>?facets=<field>&size=0`. Read the response:
   - Success: `data.aggregations.<field>.buckets[]` is populated.
   - Failure: `aggregations` is **absent** and `warnings.facets` reads
     `"unrecognized values: [<field>]"`. The HTTP status is still 200 — there is no 400, so a
     non-checking client will silently report empty results. **Always inspect `warnings`.**

Captured: 2026-05-26 against GDC API v2.2.0. The GDC dictionary evolves; if a field below stops
working, fall back to `/_mapping`.

## Renamed / hallucinated fields to avoid

These are the field names agents most often invent. Replace before sending.

| Hallucination | Canonical field | Endpoint |
|---|---|---|
| `diagnoses.tumor_stage` | `diagnoses.ajcc_pathologic_stage` (or `ajcc_clinical_stage`, `figo_stage`, `ann_arbor_clinical_stage` — pick the staging system used by the disease) | `/cases` |
| `gender` | `demographic.sex_at_birth` (or `demographic.gender` — both exist, with different value enums) | `/cases` |
| `stage` | `diagnoses.ajcc_pathologic_stage` | `/cases` |
| `age` | `demographic.age_at_index` | `/cases` |
| `race` | `demographic.race` | `/cases` |
| `vital_status` | `demographic.vital_status` | `/cases` |
| `project_id` | `project.project_id` on `/cases`; `cases.project.project_id` on `/files` | `/cases`, `/files` |
| `experimental_strategy` | `files.experimental_strategy` | `/cases` |

The general rule on `/cases`: bare field names without their field-group prefix
(`demographic.*`, `diagnoses.*`, `samples.*`, `files.*`, `project.*`) are not valid facet fields. On
`/files` the situation is mirrored — case-side fields must be prefixed `cases.*`.

## `/cases`

| Facet field | Example bucket key |
|---|---|
| `primary_site` | `Lung` |
| `disease_type` | `Adenomas and Adenocarcinomas` |
| `project.project_id` | `TCGA-BRCA` |
| `project.program.name` | `TCGA` |
| `demographic.sex_at_birth` | `female` |
| `demographic.gender` | `female` |
| `demographic.race` | `white` |
| `demographic.ethnicity` | `not hispanic or latino` |
| `demographic.vital_status` | `Alive` |
| `diagnoses.primary_diagnosis` | `Infiltrating duct carcinoma, NOS` |
| `diagnoses.tissue_or_organ_of_origin` | `Breast, NOS` |
| `diagnoses.ajcc_pathologic_stage` | `Stage IIA` |
| `diagnoses.classification_of_tumor` | `primary` |
| `diagnoses.morphology` | `8500/3` |
| `samples.sample_type` | `Primary Tumor` |
| `samples.tissue_type` | `Tumor` |
| `samples.preservation_method` | `FFPE` |
| `files.experimental_strategy` | `RNA-Seq` |
| `files.data_category` | `Transcriptome Profiling` |
| `files.data_format` | `BAM` |
| `files.access` | `open` |

## `/files`

| Facet field | Example bucket key |
|---|---|
| `data_category` | `Transcriptome Profiling` |
| `data_type` | `Gene Expression Quantification` |
| `data_format` | `TSV` |
| `experimental_strategy` | `RNA-Seq` |
| `platform` | `Illumina` |
| `access` | `open` |
| `analysis.workflow_type` | `STAR - Counts` |
| `cases.project.project_id` | `TCGA-BRCA` |
| `cases.project.program.name` | `TCGA` |
| `cases.primary_site` | `Lung` |
| `cases.disease_type` | `Adenomas and Adenocarcinomas` |
| `cases.samples.sample_type` | `Primary Tumor` |
| `cases.demographic.sex_at_birth` | `female` |
| `cases.diagnoses.ajcc_pathologic_stage` | `Stage IIA` |

## `/projects`

| Facet field | Example bucket key |
|---|---|
| `program.name` | `TCGA` |
| `primary_site` | `Lung` |
| `disease_type` | `Adenomas and Adenocarcinomas` |

## `/ssms`

| Facet field | Example bucket key |
|---|---|
| `consequence.transcript.consequence_type` | `missense_variant` |
| `consequence.transcript.gene.symbol` | `TP53` |
| `consequence.transcript.is_canonical` | `true` |
| `chromosome` | `chr17` |
| `mutation_type` | `Simple Somatic Mutation` |
| `mutation_subtype` | `Single base substitution` |
| `occurrence.case.project.project_id` | `TCGA-BRCA` |

## `/cnvs`

| Facet field | Example bucket key |
|---|---|
| `consequence.gene.symbol` | `MYC` |
| `cnv_change` | `Gain` |
| `occurrence.case.project.project_id` | `TCGA-BRCA` |

## Discovering facet candidates from `/_mapping`

`id`-typed and short-string fields are the realistic facet candidates. Numeric and date fields are
also faceted but you usually want range filters, not buckets, against them.

```python
import requests
m = requests.get("https://api.gdc.cancer.gov/cases/_mapping").json()
candidates = [name for name, meta in m["_mapping"].items()
              if meta.get("type") == "id"]
print(candidates[:20])
```

## Combining `facets` with `filters`

When `facets` and `filters` are sent together, the filter scopes the aggregation — except that the
aggregation for a faceted field ignores any filter on that same field (so the facet stays available
even when "selected" on the GDC Portal). The top-level filter operator must be `and`, and internal
operators are restricted. See [FILTERS.md](FILTERS.md#facet--filter-interaction) for the full rules
and a worked payload.

## Reading the response

```python
import requests
r = requests.get(
    "https://api.gdc.cancer.gov/cases",
    params={"facets": "primary_site", "size": 0},
)
data = r.json()
# Always check warnings first — invalid facets return 200, not 400.
if "facets" in data.get("warnings", {}):
    raise RuntimeError(data["warnings"]["facets"])
for bucket in data["data"]["aggregations"]["primary_site"]["buckets"]:
    print(bucket["key"], bucket["doc_count"])
```

See [../examples/facet_aggregation.md](../examples/facet_aggregation.md) for a worked end-to-end
example.
