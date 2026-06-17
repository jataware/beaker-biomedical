# auth.yaml

Every skill directory carries an `auth.yaml` declaring its credential requirements, so a caller
can run a pre-activation check. Load this when writing or auditing `auth.yaml`.

## Schema

```yaml
credentials:
  - name: API_KEY_NAME          # the env var / identifier
    check: env_var              # env_var | file | gcloud_adc | none
    required: true              # true = skill can't function without it; false = degraded/optional
    description: >-
      What the credential is and exactly which operations need it (vs what works without it).
    usage: "How it's passed — HTTP header `X-Auth-Token: <token>`, query param, body field, …"
    service: "https://service.example.com/"   # where the user obtains/uses it
    fallback: DEMO_KEY          # optional: default value when unset (free/demo tier)
```

`check` values: `env_var` (read from an environment variable), `file` (a token file path),
`gcloud_adc` (Google Cloud Application Default Credentials — any BigQuery/GCS service),
`none` (a non-secret identifier such as a required User-Agent string).

## The open-metadata pattern (most CRDC commons)

Open metadata/search APIs need no credential. Declare an **empty list** and use comments to record
the metadata-only nature and how real downloads actually work — because the agent will ask:

```yaml
credentials: []
# The X API is fully open-access for metadata/search. No key, token, cookie, or login for ANY query.
# IMPORTANT: returns METADATA ONLY. It does not download data; each file row carries a DRS id
# (`dg.4DFC/<uuid>` → `drs://…`). Resolve bytes in a cloud workspace (ISB-CGC / Velsera CGC / Terra).
# Controlled-access data still needs the user's own dbGaP authorization there — never passed to this API.
description: >-
  No credentials required. <one-line restatement for programmatic consumers.>
service: "https://x.datacommons.cancer.gov/"
```

## Rules

- No auth needs → `credentials: []` (plus the explanatory comment block). Never omit the file.
- A free/demo tier → `required: false` with a `fallback`.
- A non-secret required header (User-Agent) → `check: none`.
- Any Google Cloud service → `check: gcloud_adc`.
- In `description`, be precise about *which* operations need the credential and which don't —
  "open search works without it; only controlled-access downloads need it" is the useful sentence.
- For a metadata-only commons, always note the DRS / dbGaP / cloud-workspace download path, since
  the API itself never streams bytes.
