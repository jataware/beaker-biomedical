# Submission API

The Submission API is **distinct** from search & retrieval. It writes data and metadata into the GDC
and reads submitted-but-unreleased data. Only registered submitters for the target project can write.

> Released data — what you see in the Portal — is **not** queryable through `/submission/...`. It's
> only available through the search endpoints and `/v0/graphql`.

## Base URLs

- `https://api.gdc.cancer.gov/submission/{Program}/{Project}` — current major version.
- `https://api.gdc.cancer.gov/v0/submission/{Program}/{Project}` — version-pinned.

The `Program.name` and `Project.code` map to the Portal URL
`https://portal.gdc.cancer.gov/submission/{Program}/{Project}/dashboard`.

Example: `https://api.gdc.cancer.gov/v0/submission/TCGA/ALCH`.

## Authentication

All write operations require an `X-Auth-Token`. The token-holder must be a registered submitter for
the project; otherwise the API returns 403.

## Metadata formats

- **JSON** (`Content-Type: application/json`) — default.
- **TSV** (`Content-Type: text/tsv`) — use `--data-binary` in curl to preserve newlines.

Both formats produce identical results. Use TSV for bulk uploads, JSON for single-entity edits.

## Request payload

Submission payloads follow this shape:

```json
{
  "type": "case",
  "id": "uuid-or-omit",
  "submitter_id": "custom-string",
  "<property>": "<value>",
  "<relationship_name>": [
    { "id": "neighbor-uuid", "submitter_id": "neighbor-submitter-id" }
  ]
}
```

- Either `id` or `submitter_id` is required.
- `<properties>` are entity fields from the GDC Data Dictionary.
- `<relationship_name>` arrays link to parent entities (e.g., a sample links to its case).

## Templates and schemas

Pre-built submission templates for each entity type:

```
GET https://api.gdc.cancer.gov/v0/submission/template/{entity}?format=json|tsv|csv
```

Entity types include: `case`, `sample`, `portion`, `analyte`, `aliquot`, `read_group`, `slide`,
`demographic`, `diagnosis`, `exposure`, `family_history`, `treatment`, `follow_up`, `molecular_test`,
`analysis_metadata`, `biospecimen_supplement`, `clinical_supplement`, `experiment_metadata`,
`pathology_report`, `run_metadata`, `slide_image`, `submitted_unaligned_reads`,
`submitted_aligned_reads`, `submitted_genomic_profile`.

Full JSON Schema for all entities:

```
GET https://api.gdc.cancer.gov/v0/submission/_dictionary/_all
GET https://api.gdc.cancer.gov/v0/submission/_dictionary/{entity}
```

## Transactions

Submissions are transactional — if one entity fails validation, the whole transaction aborts and
nothing is written.

### Dry run

Append `/_dry_run` to any submission URL to validate without writing:

```
POST /v0/submission/{Program}/{Project}/_dry_run
```

The response shape is the same as a real transaction (see "Response format" below). The transaction
will report `success: true` if it would have succeeded.

### Async transactions

Long-running uploads can be POSTed against `/_async` for background processing; status is then
polled.

## Response format

```json
{
  "code": 200,
  "success": true,
  "message": "Transaction successful.",
  "transaction_id": "...",
  "created_entity_count": 1,
  "updated_entity_count": 0,
  "entity_error_count": 0,
  "transactional_error_count": 0,
  "transactional_errors": [],
  "cases_related_to_created_entities_count": 1,
  "cases_related_to_updated_entities_count": 0,
  "entities": [
    {
      "action": "create",
      "id": "uuid",
      "type": "case",
      "valid": true,
      "errors": [],
      "warnings": [],
      "related_cases": [],
      "unique_keys": [{"project_id":"TCGA-ALCH","submitter_id":"GDC-INTERNAL-000093"}]
    }
  ]
}
```

### Entity status values

- `success` — entity was modified.
- `valid` — entity would have succeeded; another entity caused the transaction to abort.
- `error` — entity failed validation; this entity (and the whole transaction) was rolled back.

### Entity error types

- `EntityNotFoundError` — a referenced entity (in a relationship link) does not exist.
- `MissingPropertyError` — a required field is missing.
- `ValidationError` — a property failed a validation rule (regex, enum, range).

## Querying submitted data with GraphQL

`POST https://api.gdc.cancer.gov/v0/submission/graphql` — same shape as `/v0/graphql` (see
[GRAPHQL.md](GRAPHQL.md)). Use this to query in-flight, unreleased entities while debugging
submissions.

## Common workflow

1. `GET /v0/submission/_dictionary/case` — fetch the schema.
2. `GET /v0/submission/template/case?format=tsv` — get a starter TSV.
3. Fill in the TSV.
4. `POST /v0/submission/{Program}/{Project}/_dry_run` with the TSV body — validate.
5. If `success: true`: re-POST without `_dry_run`.
6. Repeat for child entities (sample → portion → analyte → aliquot → read_group → submitted files).

## When NOT to touch the submission API

If the user is asking to *download* or *search* released data, stay on search & retrieval. The
submission endpoints will return empty for any case that is in the Portal — by design.
