# Quickstart: calling the PS-DC GraphQL API

PS-DC is a single GraphQL endpoint, **no auth**, **POST only**, and the request body **must include a
`variables` key**. It is a prototype that currently answers **study-level queries only**. This is the
helper the other examples build on.

## The helper

```python
import requests

URL = "https://populationsciences.datacommons.cancer.gov/v1/graphql/"   # trailing slash; POST only

def psdc(query, variables=None, tries=3):
    """POST a GraphQL query to PS-DC and return the `data` block. Raises on GraphQL errors."""
    for _ in range(tries):
        # NOTE: the "variables" key is REQUIRED even when empty — omitting it is a hard error.
        r = requests.post(URL, json={"query": query, "variables": variables or {}}, timeout=120)
        r.raise_for_status()                       # transport-level HTTP errors
        body = r.json()
        if body.get("errors"):                     # PS-DC returns HTTP 200 even on query errors!
            raise RuntimeError(body["errors"])
        if body.get("data") is not None:
            return body["data"]
    raise RuntimeError("PS-DC returned null data after retries")

print(psdc("{ globalStatsBar { study_short_name number_of_participants study_design } }"))
# [{'study_short_name': 'NLST', 'number_of_participants': 48860, 'study_design': 'Clinical Trial'},
#  {'study_short_name': 'PLCO', 'number_of_participants': 151383, 'study_design': 'Cohort Study - Prospective'},
#  {'study_short_name': 'PBCS', 'number_of_participants': 4886, 'study_design': 'Case-Control Study'}]
```

`globalStatsBar` (the home-page study cards) is the quickest live overview — there is no working
`numberOf*`/`nodeCounts` totals query (those are Neo4j-backed and currently error).

## Three ways a first call fails

```python
# 1) No "variables" key → hard error, not an empty result:
requests.post(URL, json={"query": "{ globalStatsBar { study_short_name } }"}).json()
# {'errors': [{'message': 'Cannot invoke "java.util.Map.keySet()" because "variables" is null'}], ...}

# 2) A GET → rejected:
requests.get(URL).json()      # {'errors': [{'message': 'API will only accept POST requests'}], ...}

# 3) A participant/node/file query → Neo4j backend is down on this prototype:
psdc("{ subjectInfo(first: 1) { subject_id } }")
# RuntimeError: [{'message': '... Unable to connect to localhost:7687 ...'}]
psdc("{ study { study_short_name } }")            # same — node queries error
```

## What works vs what doesn't (this prototype)

```python
WORKING = ["globalStatsBar", "searchStudies", "tabStudy", "studyDemographics",
           "primarySiteMorphology", "dataCollectionPage", "studyGeneral", "studyFiles", "minMaxBoundQuery"]
# Everything else (subjectList*, subjectCountBy*, subjectInfo, fileOverview, fileInfo, nodeCounts,
# schemaVersion, and all node queries like study/program/diagnosis/sample/file) currently returns
# "Unable to connect to localhost:7687". Treat that as "endpoint not live yet," not a query mistake.
```

If a user wants participant-level data (cohorts by ER status, recurrence score, etc.), explain those
queries exist in the schema but aren't functional on the prototype yet — don't fabricate results.

## Things to remember

- **POST + `variables` key; inspect `errors` (HTTP 200 on failure).**
- **Study-level only, for now.** See [explore_studies.md](explore_studies.md) and [search_studies.md](search_studies.md).
- **Facet/group bucket counts use `subjects`, not `count`** — and in study facets `subjects` = number
  of studies. Object-valued fields (e.g. `participant_sexes`) need a subselection `{ group subjects }`.
- **Re-probe** — this is an undocumented prototype; the working set can change.
