# Expect

**Expected result (verified ground truth):**
- `cases.project.project_id in ["TCGA-PAAD"]`, facet/filter on `files.access`:
  **open ≈ 4971**, **controlled ≈ 7882**, total **≈ 12853**. Open files (clinical, derived expression,
  masked SSM, …) download with no token; controlled files (BAMs/aligned reads under a dbGaP `acl`)
  need a token + project authorization.
**Pass:** reports both counts (open ~4971, controlled ~7882) with the right interpretation — open is
token-free, controlled needs auth.

# Failure Cases

**Trap(s):**
1. Claiming all GDC data is open (or all requires a token).
2. Reporting only the total file count without the open/controlled split.
**Fail:** says all files are open / all are controlled; or returns only the total.

# Automated Checks

```yaml
checks:
  - number:
      name: "open_files"
      target: 4971
      tolerance_percent: 15
  - number:
      name: "controlled_files"
      target: 7882
      tolerance_percent: 15
  - substring_all: ["open", "controlled"]
  - behavior: "filtered files by files.access (open vs controlled) for TCGA-PAAD"
  - must_not_contain: ["all files are open", "everything requires a token", "all data requires controlled access"]
```
