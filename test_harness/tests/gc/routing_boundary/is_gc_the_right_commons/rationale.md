# Intended Behavior

GC is a metadata fallback and mirror, not an analysis engine. The agent uses GC only to confirm a real Genomics prostate study exists (`searchSubjects(...)` → `phs001524`, `study_data_types = ["Genomics"]`, Controlled), then routes the mutation-frequency question to GDC via the `genomic-data-commons` skill. GC has no mutation-frequency capability — `ssms` and `mutationFrequency` both return `FieldUndefined`.

# Incorrect Behavior

The agent invents a `mutationFrequency`/`ssms`/`genes` query that does not exist in the GC schema, claims GC computes frequencies, or over-relies on GC because it happens to hold a prostate study instead of redirecting.
