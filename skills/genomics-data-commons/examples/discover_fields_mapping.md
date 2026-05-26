# Discover valid fields with `/_mapping`

Each search/retrieval endpoint exposes a sibling `_mapping` endpoint that lists every valid field,
the default return set, the available expand groups, and the nested-array fields. Hit it once and
filter the result locally instead of guessing field names.

## Example

```python
import requests

m = requests.get("https://api.gdc.cancer.gov/files/_mapping").json()

# Default fields returned when you don't pass `fields=`
print("defaults:", m["defaults"][:10])

# Available expand groups (use with the `expand=` parameter)
print("expand groups:", m["expand"][:10])

# Find every field with 'workflow' in it
workflow_fields = [f for f in m["fields"] if "workflow" in f]
print("workflow fields:", workflow_fields)

# Find every nested-array field — these are arrays and behave differently in filters
print("nested arrays:", m["nested"][:10])

# The endpoint-agnostic `_mapping` block (good for `filters`, sometimes good for `fields`)
sample = next(iter(m["_mapping"].items()))
print("sample _mapping entry:", sample)
```

Output snippet (truncated):

```text
defaults: ['file_id', 'file_name', 'access', 'acl', 'data_category', ...]
expand groups: ['cases', 'cases.samples', 'cases.samples.portions', ...]
workflow fields: ['analysis.workflow_type', 'analysis.workflow_link', ...]
nested arrays: ['cases', 'cases.samples', 'cases.samples.portions', 'annotations', ...]
sample _mapping entry: ('files.access',
  {'doc_type': 'files', 'field': 'access', 'type': 'id'})
```
