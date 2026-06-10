# Quickstart: calling the CTDC GraphQL API

CTDC is a single GraphQL endpoint, **no auth**, **POST only**, and — unusually — the request body
**must include a `variables` key**. This is the helper the other examples build on.

## The helper

```python
import requests

URL = "https://clinical.datacommons.cancer.gov/v1/graphql/"   # trailing slash; POST only

def ctdc(query, variables=None, tries=3):
    """POST a GraphQL query to CTDC and return the `data` block. Raises on GraphQL errors."""
    for _ in range(tries):
        # NOTE: the "variables" key is REQUIRED even when empty — omitting it is a hard error.
        r = requests.post(URL, json={"query": query, "variables": variables or {}}, timeout=120)
        r.raise_for_status()                       # transport-level HTTP errors
        body = r.json()
        if body.get("errors"):                     # CTDC returns HTTP 200 even on query errors!
            raise RuntimeError(body["errors"])
        if body.get("data") is not None:
            return body["data"]
    raise RuntimeError("CTDC returned null data after retries")

print(ctdc("{ searchParticipants { numberOfStudies numberOfParticipants numberOfSpecimens "
           "numberOfFiles numberOfTargetedTherapies } }"))
# {'numberOfStudies': 1, 'numberOfParticipants': 248, 'numberOfSpecimens': 1140,
#  'numberOfFiles': 2033, 'numberOfTargetedTherapies': 42}
```

`searchParticipants` with no filter is the live "totals" call (there is no separate `numberOf*` query).

## Three ways a first call fails

```python
# 1) No "variables" key → hard error, not an empty result:
requests.post(URL, json={"query": "{ getAllStudies { study_short_name } }"}).json()
# {'errors': [{'message': 'Cannot invoke "java.util.Map.keySet()" because "variables" is null'}], ...}

# 2) A GET → rejected:
requests.get(URL).json()
# {'errors': [{'message': 'API will only accept POST requests'}], 'data': None}

# 3) schemaVersion → currently errors (it's the lone neo4j-backed query; the store is unreachable):
ctdc("{ schemaVersion }")   # RuntimeError: ... Unable to connect to ... 7687 ...
```

Use the **Elasticsearch-backed** queries (everything except `schemaVersion`).

## Error handling

CTDC answers query errors with **HTTP 200** and an `errors` array — `raise_for_status()` alone won't
catch them; always inspect `errors` (the helper does). Common messages:

- `Validation error (FieldUndefined@...)` — you invented a field or asked for it on the wrong type
  (e.g. `count` instead of `subjects` in a facet bucket; `specimen_type` on `ParticipantOverview`).
  Introspect: `ctdc('{ __type(name:"ParticipantOverview"){ fields { name } } }')`.
- An **empty list with no error** usually means a filter *value* didn't match the controlled vocabulary
  — discover valid values from `searchParticipants` facet counts ([faceted_search.md](faceted_search.md)).

## Things to remember

- **POST + `variables` key; inspect `errors` (HTTP 200 on failure).**
- **Facet bucket counts use `subjects`, not `count`** (`GroupCount { group subjects }`).
- **Multi-valued `*Overview` fields are bracketed strings** (`targeted_therapy: "[Lenalidomide, Bortezomib]"`).
- **Portal `*Overview` queries default to `first: 10`** — set it. See the other examples.
