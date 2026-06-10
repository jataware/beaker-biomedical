# Discover programs & studies, then decide if GC is the right commons

When the user names a program, disease, or topic instead of a `phs_accession`, enumerate first — and
check whether the data would be better served by a specialized commons. See
[../references/DISCOVERY.md](../references/DISCOVERY.md).

## Example

```python
import requests
URL = "https://general.datacommons.cancer.gov/v1/graphql/"
def gc(q, tries=3):
    for _ in range(tries):
        b = requests.post(URL, json={"query": q}, timeout=120).json()
        if b.get("errors"): raise RuntimeError(b["errors"])
        if b.get("data") is not None: return b["data"]
    raise RuntimeError("GC returned null data")

# 1. Programs at a glance (UI helper — flat list with study counts).
for p in gc("{ programList { acronym name num_studies } }")["programList"]:
    print(f'{p["acronym"]:16} {p["num_studies"]:>3}  {p["name"]}')
# CCDI 16, TCIA-RADIOLOGY 35, DCCPS 20, Kids First 7, PDXNet 4, HTAN 2, CPTAC 1, MP2PRT 1, NCIcaNano 1

# 2. Browse studies and inspect what each actually holds. `studies` is the only query that searches by
#    name/acronym; there is NO disease filter argument, so scan + inspect study_data_types.
studies = gc('{ studies(first: 200) { phs_accession study_name study_acronym study_data_types '
             'study_access number_of_participants } }')["studies"]
print(len(studies), "studies")
for s in studies[:5]:
    print(f'{s["phs_accession"]:14} {s["study_access"]:11} {s["study_data_types"]!s:28} {s["study_name"][:50]}')

# 3. Or resolve a known acronym/name straight to its phs_accession.
hit = gc('{ studies(study_acronyms: ["KF-ESGR"]) { phs_accession study_name study_data_types } }')["studies"]
print(hit)   # -> phs001228, Gabriella Miller Kids First ... Ewing Sarcoma

# 4. Free-text search across everything (UI/transform query) — fastest "is X in GC?" check.
g = gc('{ globalSearch(input: "Ewing sarcoma" first: 10 offset: 0) '
       '{ study_count studies { phs_accession } subject_count file_count } }')["globalSearch"]
print(g)   # {'study_count': 1, 'studies': [{'phs_accession': 'phs001228'}], 'subject_count': 1287, ...}
```

## Decide: GC, or a specialized commons?

Look at `study_data_types` and route accordingly — GC largely *mirrors* the specialized commons:

```python
def route(study):
    types = (study.get("study_data_types") or "").lower()
    if "proteom" in types:  return "→ prefer proteomic-data-commons"
    if "genom" in types:    return "→ prefer genomic-data-commons"
    if "imag" in types:     return "→ prefer imaging-data-commons"
    return "stay in GC (GC-specific or not in a specialized commons)"
```

Only stay in GC when the data is GC-specific (e.g. NCIcaNano nanomaterials), the user explicitly asked
for General Commons / CDS, or the specialized commons doesn't have it.

## Notes

- `studies` has **no** `disease`/`tissue` filter. For disease-level selection, scan studies and read
  `study_description`, use `globalSearch`, or pull `diagnoses` per study and filter client-side
  ([study_clinical.md](study_clinical.md)).
- `study_data_types` and `acl` come back as JSON-ish **strings** (e.g. `'["Genomics", "Proteomics"]'`,
  `"['phs001287']"`), not parsed arrays — `json.loads`/`ast.literal_eval` if you need the list.
- A handful of studies use a non-`phs` key (e.g. caNanoLab → `phs_accession: "10.17917"`). Read the real
  value; don't assume a `phs` prefix.
