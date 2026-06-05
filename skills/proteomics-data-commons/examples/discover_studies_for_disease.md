# Discover the studies for a disease, then query them

When the user names a disease ("clear cell renal cell carcinoma") instead of a `pdc_study_id`, **don't
assume a single study.** A disease spans several studies across analytical fractions — CCRCC alone has
separate Proteome, Phosphoproteome, and Glycoproteome studies. Enumerate them first.

See [../references/DISCOVERY.md](../references/DISCOVERY.md) for all discovery entry points.

## Example

```python
import time, requests
URL = "https://proteomic.datacommons.cancer.gov/graphql"
def pdc(q, tries=5):                       # see quickstart.md — PDC emits transient null payloads
    for k in range(tries):
        b = requests.post(URL, json={"query": q}, timeout=180).json()
        if b.get("errors"): raise RuntimeError(b["errors"])
        data = b.get("data")
        if data and all(v is not None for v in data.values()): return data
        time.sleep(2 * (k + 1))
    raise RuntimeError("PDC returned null data after retries")

DISEASE = "Clear Cell Renal Cell Carcinoma"

# 1. DISCOVER — every study (program → project → study) that contains this disease.
q = '''{ programsProjectsStudies(disease_type: "%s") {
          name
          projects { name
            studies { pdc_study_id study_name analytical_fraction experiment_type } } } }''' % DISEASE
studies = []
for prog in pdc(q)["programsProjectsStudies"]:
    for proj in prog["projects"]:
        for s in proj["studies"]:
            studies.append((prog["name"], proj["name"], s["pdc_study_id"],
                            s["analytical_fraction"], s["study_name"]))

for prog, proj, sid, frac, name in studies:
    print(f"{sid}  {frac:16} {name}")
# PDC000127  Proteome         CPTAC CCRCC Discovery Study - Proteome
# PDC000128  Phosphoproteome  CPTAC CCRCC Discovery Study - Phosphoproteome
# PDC000413  Glycoproteome    ...
# ... several studies, NOT one

print(f"\n{len(studies)} studies contain {DISEASE!r}")

# 2. CONFIRM the disease values that exist (and case counts) if the user's wording is fuzzy:
for d in pdc('{ diseasesAvailable { disease_type project_submitter_id cases_count } }')["diseasesAvailable"]:
    if "Renal" in (d["disease_type"] or ""):
        print(d["disease_type"], "|", d["project_submitter_id"], "|", d["cases_count"])

# 3. QUERY — now run the real per-study work (quant matrix, clinical, files) over `studies`.
#    Pick the analytical fraction the user wants (Proteome for protein abundance,
#    Phosphoproteome for phospho-sites, etc.).
```

## Notes

- `programsProjectsStudies` also accepts `analytical_fraction`, `experiment_type`, and
  `instrument_model` to narrow the set in the query itself.
- For an anatomical site rather than a histology, use `tissueSitesAvailable` (axis is
  `tissue_or_organ_of_origin` / `primary_site`, e.g. *Kidney*). `diseasesAvailable` returns both axes
  and bridges them.
- `allPrograms` dumps the entire program→project→study tree (with diseases, sites, fractions) in one
  call — often enough to choose studies with no further query.
- The discovery results give you `pdc_study_id`. If a downstream query needs the version-specific
  `study_id`, resolve the latest version via `studyCatalog` — see
  [../references/ENTITIES.md](../references/ENTITIES.md).
