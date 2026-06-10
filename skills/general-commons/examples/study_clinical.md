# Pull a study's participants + clinical + biospecimen

Given a `phs_accession`, fetch participants and join their diagnoses, treatments, and samples. Every
per-study query **requires `phs_accession`** and **defaults to 10 rows** — set `first` or loop. See
[../references/ENTITIES.md](../references/ENTITIES.md) and [../references/PAGINATION.md](../references/PAGINATION.md).

## Example

```python
import requests
from collections import defaultdict
URL = "https://general.datacommons.cancer.gov/v1/graphql/"
def gc(q, tries=3):
    for _ in range(tries):
        b = requests.post(URL, json={"query": q}, timeout=120).json()
        if b.get("errors"): raise RuntimeError(b["errors"])
        if b.get("data") is not None: return b["data"]
    raise RuntimeError("GC returned null data")

PHS = "phs001287"   # CPTAC Pan-Cancer

# 0. Size the study first (counts are real ints; record fields are strings).
counts = gc('{ participantsCount(phs_accession:"%s") diagnosesCount(phs_accession:"%s") '
            'samplesCount(phs_accession:"%s") treatmentsCount(phs_accession:"%s") }'
            % (PHS, PHS, PHS, PHS))
print(counts)   # {'participantsCount': 1112, 'diagnosesCount': 3252, 'samplesCount': 9603, 'treatmentsCount': 0}

def paginate(field, selection, page=5000):
    """Page a per-study query that returns a list under `field`. Stops on a short page."""
    out, offset = [], 0
    while True:
        rows = gc('{ %s(phs_accession:"%s" first:%d offset:%d) { %s } }'
                  % (field, PHS, page, offset, selection))[field]
        out.extend(rows); offset += page
        if len(rows) < page:
            return out

participants = paginate("participants", "participant_id sex race ethnicity")
diagnoses    = paginate("diagnoses",    "participant_id primary_diagnosis disease_type primary_site "
                                        "tumor_grade age_at_diagnosis vital_status")
samples      = paginate("samples",      "sample_id participant_id sample_type sample_tumor_status "
                                        "sample_anatomic_site")

# Join on participant_id (one participant -> many diagnoses/samples).
dx_by_pt = defaultdict(list)
for d in diagnoses: dx_by_pt[d["participant_id"]].append(d)
sm_by_pt = defaultdict(list)
for s in samples:   sm_by_pt[s["participant_id"]].append(s)

for pt in participants[:5]:
    pid = pt["participant_id"]
    dx  = dx_by_pt.get(pid, [])
    primary = dx[0]["primary_diagnosis"] if dx else "?"
    print(f'{pid:10} {pt["sex"]:8} dx={len(dx)} samples={len(sm_by_pt.get(pid, []))}  {primary}')
```

## Filter to specific participants

`diagnoses`, `treatments`, and `samples` also accept `participant_ids` to scope to a known cohort:

```python
sub = gc('{ diagnoses(phs_accession:"%s" participant_ids:["01BR001","01BR008"] first:50) '
         '{ participant_id primary_diagnosis disease_type } }' % PHS)["diagnoses"]
```

## Notes

- **`phs_accession` is required** on all four queries — resolve it from `studies` first
  ([discover_studies.md](discover_studies.md)).
- **One-to-many.** A participant can have several diagnoses/samples/treatments — keep them as lists.
- **Empty strings are common.** Optional clinical fields come back as `""` (seen above: `disease_type`,
  `tumor_grade`) rather than null. Treat `""` as missing.
- **`treatmentsCount` can be 0** — not every GC study submits treatments (or diagnoses, or samples).
  Check the count before pulling.
- There is no single "all clinical for a study" query (unlike PDC's `clinicalPerStudy`) — assemble it
  from `participants` + `diagnoses` + `treatments` + `samples` as above.
