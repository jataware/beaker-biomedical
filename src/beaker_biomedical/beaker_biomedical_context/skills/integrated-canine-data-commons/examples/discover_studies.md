# Discover programs & studies

Start here when the user names a cancer, breed, program, or topic rather than a study code. Resolve to
real `program_acronym` / `clinical_study_designation` values before any per-entity pull.

Uses the `icdc()` helper from [quickstart.md](quickstart.md).

## List every program and study with counts

`studiesByProgram` is the "show me everything" call — one row per study with its program, accession,
and per-study case/file/image/publication counts.

```python
studies = icdc("""
{ studiesByProgram {
    program_id
    clinical_study_designation
    clinical_study_name
    clinical_study_type
    accession_id
    numberOfCases
    numberOfCaseFiles
    numberOfStudyFiles
    study_disposition } }
""")["studiesByProgram"]

for s in studies:
    print(f"{s['program_id']:10} {s['clinical_study_designation']:14} "
          f"{s['numberOfCases']:4} cases  {s['clinical_study_name'][:50]}")
# COP        COTC007B        84 cases  Preclinical Comparison of Three Indenoisoquino...
# COP        COTC021        152 cases  Evaluation of Orally Administered mTOR inhibito...
# COP        COTC022        157 cases  A Contemporaneous Controlled Study of the Stand...
# CMCP       GLIOMA01        81 cases  Comparative Molecular Life History of Spontaneo...
# CSU FACC   OSA02          117 cases  Association of canine osteosarcoma outcomes ...
# ...
```

Just the programs:

```python
icdc('{ program { program_acronym program_name } }')["program"]
# [{'program_acronym': 'CMCP', 'program_name': 'Comparative Molecular Characterization Program'},
#  {'program_acronym': 'COP',  'program_name': 'Comparative Oncology Program'},
#  {'program_acronym': 'PCCR', 'program_name': 'Purdue Center for Cancer Research'},
#  {'program_acronym': 'PRECINCT', 'program_name': 'Pre-medical Cancer Immunotherapy Network ...'},
#  {'program_acronym': 'CSU FACC', 'program_name': 'Colorado State University Flint Animal Cancer Center'}]
```

## Free-text search when you only have a term

`globalSearch` spans programs, studies, cases, samples, files, help pages, and the data dictionary —
ideal when the user's word could be a disease, study, breed, or model property.

```python
gs = icdc('''
{ globalSearch(input: "osteosarcoma", first: 5) {
    study_count studies { clinical_study_designation clinical_study_name }
    case_count  cases   { case_id disease_term breed } } }
''')["globalSearch"]

print(gs["study_count"], "studies,", gs["case_count"], "cases mention osteosarcoma")
# 7 studies, 567 cases mention osteosarcoma
for s in gs["studies"]:
    print(s["clinical_study_designation"], "—", s["clinical_study_name"])
# OSA01 — A Multi-Platform Sequencing Analysis of Canine Appendicular Osteosarcoma.
# COTC022 — A Contemporaneous Controlled Study of the Standard of Care (SOC) in Dogs with ...
# PRECINCT01 — Inhaled IL-15 Immunotherapy for Treatment of Lung Metastases ...
```

## Per-study detail

Resolve a study code, then drill in:

```python
icdc('{ study(clinical_study_designation: "OSA01") { clinical_study_name accession_id clinical_study_type } }')
# 'A Multi-Platform Sequencing Analysis of Canine Appendicular Osteosarcoma.', accession 000006, type Genomics

icdc('{ caseCountOfStudy(study_code: "OSA01") sampleCountOfStudy(study_code: "OSA01") fileCountOfStudy(study_code: "OSA01") }')
```

`study_code` arguments accept the code (`OSA01`) **or** the numeric `accession_id` (`000006`).

## Next steps

- Build a cohort across studies by breed/diagnosis/etc. → [faceted_search.md](faceted_search.md).
- Pull one case's clinical record → [case_clinical.md](case_clinical.md).
- How a study maps to human cancer → `humanRelevanceNodeData` in [../references/CLINICAL.md](../references/CLINICAL.md).
