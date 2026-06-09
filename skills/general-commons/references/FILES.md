# Files & data access

The single most important thing about GC files: **this API returns file *metadata*, not file *bytes*.**
The GC portal itself does not facilitate direct downloads, and neither does the GraphQL API. Data
access happens on the **Cancer Genomics Cloud (CGC) by Velsera** via an exported manifest. Never tell a
user you can download a GC file through this API.

## The `files` query

`files(phs_accession: "<phs>" …)` (`phs_accession` **required**) returns per-file metadata. Useful
filters: `file_types` ([String]), `file_names` ([String]), `file_ids` ([String]), `participant_ids`
([String]), and date windows `released_range_start` / `released_range_end` (`YYYY-MM-DD`).

```graphql
{ files(phs_accession: "phs001287" file_types: ["bam"] first: 100)
  { file_id file_name file_type file_size md5sum file_url_in_cds release_datetime is_supplementary_file } }
```

Fields: `file_id file_name file_type file_description file_size md5sum checksum_value checksum_algorithm
file_url_in_cds experimental_strategy_and_data_subtypes file_mapping_level release_datetime
is_supplementary_file submission_version crdc_id phs_accession participant_ids`.

## `file_id` is a CRDC DRS identifier, not a URL

`file_id` looks like `dg.4DFC/0359521d-648a-5337-b86b-9b62b8dd75f7` — a **GA4GH DRS** identifier in the
CRDC indexd namespace (`dg.4DFC`), **not** an HTTP link. `file_url_in_cds` is frequently empty (`""`).
You resolve the actual cloud object through the DRS/CRDC infrastructure or, in practice, by loading a
manifest into CGC — not by GET-ing a field from this API.

## Open vs controlled access

GC mixes **open** and **controlled (sensitive)** data:

- **Open-access data** is public — no authorization.
- **Controlled-access data** requires authorization through NCBI's **dbGaP**, granted per study. The
  study's access is on the Study node: `study_access` (`Open` / `Controlled`), `data_access_level`,
  `acl` (e.g. `['phs001287']`), and `authz`. dbGaP authorization is a property of the user's NIH account
  — there is nothing to pass to this API (all *metadata* is open regardless).

Searching metadata never requires login; that's deliberate, so users can confirm GC holds data of
interest before requesting dbGaP access.

## The download path (CGC manifest workflow)

The real workflow GC supports:

1. Build a cohort with the queries here (filter `files` / `samples` / `participants`).
2. Export a **manifest** (the portal's "shopping cart" → manifest; programmatically, the manifest is
   the set of `file_id` + metadata rows you assembled).
3. Load the manifest into a **CGC by Velsera** workspace, where (with dbGaP authorization for
   controlled data) the files are analyzed in-cloud with 200+ preinstalled tools — no local download.

Programs willing to fund egress for users with approved dbGaP access can contact the CRDC helpdesk;
that is outside this API. **When a user asks to "download" GC data, point them at the CGC manifest
workflow and the dbGaP authorization step — don't imply a direct fetch.**

## Tips

- Verify integrity with `md5sum` (or `checksum_value` + `checksum_algorithm`) once a file is in CGC.
- `is_supplementary_file` flags docs/READMEs vs primary data — filter it out for analysis sets.
- `file_size` is a String of bytes — cast before summing.
- To find which modality a file carries, join on `file_id` to `genomic_info` / `proteomics` / `images`
  / `multiplex_microscopies` / `non_dicom*` (see [DATA-TYPES.md](DATA-TYPES.md)).
</content>
