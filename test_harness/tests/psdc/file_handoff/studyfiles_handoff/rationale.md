# Intended Behavior

The agent lists the PBCS data-dictionary file from `studyFiles(study_short_name: ["PBCS"])` — `PBCS_Data_Dictionary_PSDC_Core_Variables.xls`, type Data Dictionary, Open Access — gives the full CRDC DRS id (`drs://nci-crdc.datacommons.io/dg.4DFC/6b9c5c3c-…`) as the way to fetch that study-level artifact, explains the API serves only study-level metadata (not participant-level bytes), and reports PBCS's `dbgap_accession_id` honestly as `Not Applicable`.

# Incorrect Behavior

The agent claims the API serves the participant-level dataset itself, fabricates a dbGaP accession for PBCS (it is `Not Applicable`), or presents the bare `data_file_uuid` as the DRS id — it lacks the `dg.4DFC/` prefix that `drs_uri` carries.
