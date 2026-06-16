# Intended Behavior

The agent resolves `studies(study_acronyms:["KF-MMC"])` → `phs002187` (Genomics, Controlled), then uses `participantsCount` and `filesCount` (≈60 participants, ≈3,342 files) rather than the study node's null `number_of_participants`. Paginating all file rows and summing `int(file_size)` gives ≈5.90 TB, with the largest single file ~68 GB.

# Incorrect Behavior

The agent omits `phs_accession` on per-study queries (a hard `MissingFieldArgument` error), calls `files` with no `first` and gets only 10 of 3,342, sums or compares `file_size` as a string (lexically — wrongly returning ~9.99 GB as the largest), or trusts the null `number_of_participants` field.
