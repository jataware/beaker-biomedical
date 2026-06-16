# Expect

**Expected result (verified ground truth):**
- GC locates exactly one Genomics prostate study via faceted discovery:
  `searchSubjects(primary_diagnoses: ["Malignant Neoplasm Of Prostate"]) {
  filterSubjectCountByPhsAccession }` → **`phs001524`**. `studies(phs_accessions:["phs001524"])` →
  study_name *"The Genetic Basis of Aggressive Prostate Cancer, The Role of Rare Variation"*, acronym
  **CIDR Agg Prostate Cancer**, `study_data_types = ["Genomics"]`, `study_access = "Controlled"`,
  ~5,563 participants. Its `genomic_info` is submission-level sequencing metadata only (WXS / Illumina /
  GRCh37).
- GC has **no mutation-frequency capability**: `{ ssms { gene } }` and
  `{ mutationFrequency(gene:"TP53") }` both return `Validation error (FieldUndefined@...)`.
- Correct answer: **No — pull mutation frequencies from GDC (`genomic-data-commons`).** GC only tells
  you the study exists (and is Genomics), then you hand off; controlled access also needs dbGaP.
**Pass:** routes mutation frequencies to GDC; uses GC only to confirm `study_data_types = Genomics` for
a real prostate study (`phs001524`); does **not** fabricate a GC frequency query.

# Failure Cases

**Trap(s):**
1. Trying to answer the genomics question from GC (inventing a `mutationFrequency` / `ssms` / `genes`
   query — these do not exist in the GC schema).
2. Over-relying on GC because it *does* hold a prostate study, instead of routing to the specialized
   commons.
**Fail:** claims GC computes/returns mutation frequencies; invents a `mutationFrequency`/`ssms`/`genes`
query; stays in GC instead of redirecting.

# Automated Checks

```yaml
checks:
  - substring_all: ["genomic-data-commons", "GDC", "phs001524"]
  - substring_any: ["Genomics", "study_data_types"]
  - must_not_contain: ["mutationFrequency", "ssms("]
  - behavior: "redirected somatic-mutation-frequency analysis to GDC rather than computing it from GC (GC was used only to confirm the study is Genomics)"
  - behavior: "reported that GC returns metadata only and has no mutation-frequency field, rather than fabricating one"
```
