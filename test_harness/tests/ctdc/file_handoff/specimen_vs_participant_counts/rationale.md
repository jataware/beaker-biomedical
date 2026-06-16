# Intended Behavior

The agent reports specimen and file facet counts as specimens and files — explicitly distinct from the 248 participants — and explains that downloading happens via DRS resolution or the Cancer Genomics Cloud, not a direct API call.

- `specimenCountBySpecimenType` is per-specimen and sums to 1,140 (far above 248): Streck Blood to VARI 344, EDTA Blood 341 (drawn from 234 participants), FFPE Block 140, Formalin Fixed Tissue 65, Bone Marrow Aspirate 56, …
- `dataFileCountByDataFileType` is per-file and sums to 2,033: Radiology Imaging 1,864 (DICOM), Variant Call File 85 (vcf), Variant Report 84 (pdf).

A real file row carries a `dg.4DFC/<uuid>` DRS id and a `drs_uri`; bytes come from resolving that DRS id (e.g. a `ga4gh/drs` access call for a signed URL) or loading the uuid set into a CGC manifest.

# Incorrect Behavior

The agent reports a specimen-type or file count as a number of patients, claims the GraphQL endpoint downloads files directly, or invents a `signedUrl`/download field on the file record.
