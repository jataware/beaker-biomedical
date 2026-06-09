# General Commons — upstream documentation (verbatim)

Preserved verbatim from the official General Commons documentation. The skill's reference and example
files distill and verify this; this asset is the source of record. (Note: the "schema version 3.1.0 /
data model version 8.0.1" header below is what the doc shipped with; the live `version` query currently
reports a newer data model — always trust the live `version` / `schemaVersion` / `schemaModelVersion`
queries over this header.)

## About GC

The General Commons (GC), formerly Cancer Data Service (CDS) is one of the Data Commons under the
Cancer Research Data Commons (CRDC) data ecosystem. GC continues to evolve as a data-type agnostic data
commons, to meet the data needs of various NCI-funded programs.

The GC provides secure storage and data sharing capabilities, on the cloud, for studies that fall under
the following categories:

- Studies with data that do not match the requirements of the existing CRDC Data Commons (Genomic Data
  Commons, Proteomic Data Commons, Imaging Data Commons etc.)
- Studies with data that do not fit current data type criteria and/or the required metadata for any
  CRDC data commons

The GC is home to a combination of open and controlled access (sensitive) data. The GC portal is
accessible to all users for searching data across all studies which have submitted data to GC. This
requires no login and so allows any users to check if the GC has the data of their interest before
going through the process of requesting access. To access sensitive data (controlled access data) in
the GC, users must obtain authorization through the NCBI's dbGaP system. Open access data is publicly
accessible; it does not require any authorization.

General Commons is a cloud repository and makes data available on the NCI's Cloud resource, the Cancer
Genomics Cloud by Velsera. The GC portal does not facilitate direct downloads of data from the cloud.
However, programs/initiatives willing to fund the download costs for their users with approved dbGaP
access to the data can reach out to the CRDC helpdesk for further information.

### Accessing and Analyzing GC Data

The GC portal offers users a variety of ways to search the data. Users can create cohorts and download
a data manifest which has associated metadata. Researchers can explore the data hosted in GC using the
following different methods:

- Search by participant IDs: upload a list of known IDs to get the metadata associated with those
  participants
- Search using filters such as Study, Experimental Strategy, Tumor, Sex, and File Type etc.
- Search using a programmatic approach by querying the entire GC schema using the GraphQL endpoint

Once a researcher has filtered down to a cohort of interest (files, samples, Participants etc.), that
set can be added to the "shopping cart," from which a manifest can be exported/downloaded. The
exported/downloaded manifest will contain all the information needed to access the actual data files
for further analysis on the Cancer Genomics Cloud by Velsera, which is one of the NCI's Cloud Resources.

The GC portal also provides additional information and descriptions about the studies and programs that
have deposited data in the GC. These are linked to the search page making it easy to find all the data
from a specific study.

### About the NCI's Cloud Resources

The NCI Cloud Resources are cloud platforms for analyzing data hosted in CRDC. Data hosted in GC is made
accessible on the Cancer Genomics Cloud (CGC) by Velsera. This cloud-based platform eliminates the need
for researchers to download and store extremely large data sets by allowing them work in a secure cloud
environment that provides on-demand computational capacity. The NCI Cloud Resources, including CGC, make
it possible to use publicly available analytical tools applied to the selected data, or to bring custom
analytical tools to their secure environments. The NCI Cloud Resources also make it possible to upload
private data for secure comparative analysis.

Manifests generated on the GC portal can be exported and uploaded on to the CGC and the files accessed
in CGC's private workspaces. The Data can then be analyzed using more than 200 preinstalled, curated
bioinformatics tools and workflows. Researchers can also extend the functionality of the platform by
adding their own data and tools via an intuitive software development kit.

## General Commons API

- last updated: 27 June 2025
- schema version: 3.1.0
- data model version: 8.0.1

### Introduction

The General Commons GraphQL API includes a corresponding query for each of the data types in the
General Commons data model. This document refers to this set of queries as the **Data Type Queries**.
The Data Type Queries allow users to access untransformed data directly from the General Commons
Memgraph database. The other queries accessible through the General Commons GraphQL API involve data
transformations and are designed to retrieve data for the General Commons user interface; they are not
included in this document.

### Endpoint

The General Commons GraphQL API can be accessed at: `https://general.datacommons.cancer.gov/v1/graphql/`
A GET request to this endpoint returns a GraphQL schema for the Data Type Queries. GraphQL requests are
executed by sending a POST request to this endpoint.

### Pagination

Pagination is required for the Data Type Queries. There are two pagination variables: `offset` and
`first`.

- `offset` controls how many data records are skipped before starting the result set. Defaults to `0`.
- `first` controls how many data records are returned, starting from the offset, with a maximum of
  `10000`. Defaults to `10`.

### Node Count Queries

The Node Count Queries return the total number of nodes for each data type. With the exception of the
`programsCount`, `studiesCount`, and `versionsCount` queries, these require a `phs_accession` parameter
to specify the associated study.

| Query | Returns | Parameters |
|---|---|---|
| `programsCount` | total Program nodes | none |
| `studiesCount` | total Study nodes | none |
| `versionsCount` | total Version nodes | none |
| `participantsCount` | Participant nodes for a study | `phs_accession` (String, required) |
| `samplesCount` | Sample nodes for a study | `phs_accession` (required) |
| `filesCount` | File nodes for a study | `phs_accession` (required) |
| `diagnosesCount` | Diagnosis nodes for a study | `phs_accession` (required) |
| `treatmentsCount` | Treatment nodes for a study | `phs_accession` (required) |
| `imagesCount` | Image nodes for a study | `phs_accession` (required) |
| `genomicInfoCount` | Genomic Info nodes for a study | `phs_accession` (required) |
| `proteomicsCount` | Proteomic nodes for a study | `phs_accession` (required) |
| `pdxCount` | PDX nodes for a study | `phs_accession` (required) |
| `multiplexMicroscopiesCount` | Multiplex Microscopy nodes for a study | `phs_accession` (required) |
| `nonDICOMCTimagesCount` | Non-DICOM CT Images nodes for a study | `phs_accession` (required) |
| `nonDICOMMRimagesCount` | Non-DICOM MR Images nodes for a study | `phs_accession` (required) |
| `nonDICOMPETimagesCount` | Non-DICOM PET Images nodes for a study | `phs_accession` (required) |
| `nonDICOMpathologyImagesCount` | Non-DICOM Pathology Images nodes for a study | `phs_accession` (required) |
| `nonDICOMradiologyAllModalitiesCount` | Non-DICOM Radiology All-Modalities nodes for a study | `phs_accession` (required) |

### Data Type Queries

Refer to the GraphQL schema for the list of properties that can be included in these requests.

- **`programs`** — list of Program records. Params: `program_names` ([String], optional), `first`,
  `offset`.
- **`studies`** — list of Study records. Params: `phs_accessions` ([String]), `study_names` ([String]),
  `study_acronyms` ([String]), `first`, `offset` (all optional).
- **`participants`** — list of Participant records. Params: `participant_ids` ([String], optional),
  `phs_accession` (String, **required**), `first`, `offset`.
- **`diagnoses`** — list of Diagnosis records. Params: `diagnosis_ids` ([String]), `phs_accession`
  (**required**), `participant_ids` ([String]), `first`, `offset`.
- **`treatments`** — list of Treatment records. Params: `treatment_ids` ([String]), `phs_accession`
  (**required**), `participant_ids` ([String]), `first`, `offset`.
- **`samples`** — list of Sample records. Params: `sample_ids` ([String]), `phs_accession`
  (**required**), `participant_ids` ([String]), `first`, `offset`.
- **`files`** — list of File records. Params: `file_ids` ([String]), `file_names` ([String]),
  `file_types` ([String]), `released_range_start` (String, `YYYY-MM-DD`), `released_range_end` (String,
  `YYYY-MM-DD`), `phs_accession` (**required**), `participant_ids` ([String]), `first`, `offset`.
- **`genomic_info`** — list of Genomic_Info records. Params: `genomic_info_ids` ([String]),
  `phs_accession` (**required**), `file_ids` ([String]), `first`, `offset`.
- **`images`** — list of Image records. Params: `study_link_ids` ([String]), `phs_accession`
  (**required**), `file_ids` ([String]), `first`, `offset`.
- **`multiplex_microscopies`** — MultiplexMicroscopy records. Params: `multiplex_microscopy_ids`
  ([String]), `phs_accession` (**required**), `file_ids` ([String]), `first`, `offset`.
- **`non_dicomct_images`** — NonDICOMCTimages records. Params: `non_dicomct_images_ids` ([String]),
  `phs_accession` (**required**), `file_ids` ([String]), `first`, `offset`.
- **`non_dicommr_images`** — NonDICOMMRimages records. Params: `non_dicommr_images_ids` ([String]),
  `phs_accession` (**required**), `file_ids` ([String]), `first`, `offset`.
- **`non_dicom_pathology_images`** — NonDICOMpathologyImages records. Params:
  `non_dicom_pathology_images_ids` ([String]), `phs_accession` (**required**), `file_ids` ([String]),
  `first`, `offset`.
- **`non_dicompet_images`** — NonDICOMPETimages records. Params: `non_dicompet_images_ids` ([String]),
  `phs_accession` (**required**), `file_ids` ([String]), `first`, `offset`.
- **`non_dicom_radiology_all_modalities`** — NonDICOMradiologyAllModalities records. Params:
  `non_dicom_radiology_all_modalities_ids` ([String]), `phs_accession` (**required**), `file_ids`
  ([String]), `first`, `offset`.
- **`proteomics`** — list of Proteomic records. Params: `proteomic_info_ids` ([String]), `phs_accession`
  (**required**), `file_ids` ([String]), `first`, `offset`.
- **`pdx`** — list of PDX records. Params: `pdx_ids` ([String]), `phs_accession` (**required**),
  `sample_ids` ([String]), `first`, `offset`.

### Version Queries

- **`version`** — version information for the General Commons data (Version type).
- **`schemaVersion`** — the General Commons GraphQL API schema version (String).
- **`schemaModelVersion`** — the data model version used by the GraphQL API schema (String).
</content>
</invoke>
