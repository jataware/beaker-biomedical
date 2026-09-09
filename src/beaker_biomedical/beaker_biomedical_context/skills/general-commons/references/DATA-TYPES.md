# Per-modality data nodes

Because GC is **data-type agnostic**, the metadata hanging off a study's files and samples differs by
study. Each of these queries is per-study (**`phs_accession` required**) and joins to a file (via
`file_id`) or sample (via `sample_id`/`study_link_id`). They describe the data; the bytes live in the
cloud (see [FILES.md](FILES.md)). For deep analysis of these data types, the specialized commons are
usually the better tool — these nodes are GC's submission-level metadata.

## Sequencing — `genomic_info`
Library/sequencing metadata attached to files (`genomic_info(phs_accession, file_ids, genomic_info_ids)`).
Fields: `genomic_info_id library_id library_strategy library_layout library_selection
library_source_material library_source_molecule platform instrument_model design_description bases
number_of_reads avg_read_length coverage reference_genome_assembly
custom_assembly_fasta_file_for_alignment sequence_alignment_software methylation_platform reporter_label
file_id phs_accession crdc_id`. → For variants/expression analysis, use `genomic-data-commons`.

## Proteomics — `proteomics`
MS run metadata attached to files (`proteomics(phs_accession, file_ids, proteomic_info_ids)`).
Fields: `proteomic_info_id aliquot_id analytical_fractions instrument_make proteomic_instrument_model
proteomic_design_description manufacturer_model_name file_id phs_accession crdc_id`.
→ For quantitation matrices/spectral counts, use `proteomic-data-commons`.

## PDX — `pdx`
Patient-derived xenograft models attached to samples (`pdx(phs_accession, sample_ids, pdx_ids)`).
Fields: `pdx_id model_id implantation_type implantation_site mouse_strain sample_type_for_implantation
tumor_not_mus_or_ebv_origin sample_id phs_accession`.

## Imaging metadata
The bytes (pixels) belong in the imaging-data-commons; GC carries acquisition/equipment metadata.

- **`images`** (`study_link_ids`, `file_ids`) — `study_link_id image_modality
  imaging_equipment_manufacturer imaging_equipment_model imaging_software imaging_protocol
  organ_or_tissue species de_identification_method_type/_description/_software license citation_or_DOI
  performed_imaging_study_typeCode longitudinal_temporal_event_type/_offset file_id phs_accession`.
- **`multiplex_microscopies`** (`multiplex_microscopy_ids`, `file_ids`) — rich channel/antibody/
  fluorophore metadata: `MultiplexMicroscopy_id acquisition_method_type tumor_tissue_type
  tissue_fixative embedding_medium staining_method objective nominal_magnification immersion
  imaging_assay_type pyramid physical_size_x/y/z size_c/t/x/y/z channel_id channel_name cycle_number
  target_name antibody_name rrid_identifier fluorophore clone lot catalog_number
  excitation_wavelength emission_wavelength metal_isotope_element_abbreviation/_mass
  oligo_barcode_upper_strand/_lower_strand dilution concentration study_link_id phs_accession`.
- **Non-DICOM imaging** — `non_dicomct_images`, `non_dicommr_images`, `non_dicompet_images`,
  `non_dicom_pathology_images`, `non_dicom_radiology_all_modalities`. Each takes
  `<query>_ids` + `file_ids` and holds modality-specific image metadata for files not in DICOM form.

## caNanoLab / nanomaterials (NCIcaNano)
GC hosts the NCI Alliance for Nanotechnology's caNanoLab data, surfaced through study-extra queries
(live; not in the official Data Type Queries doc):

- **`characterizations`** (`characterization_ids`, `sample_ids`) — `Characterization_ID
  Characterization_Assay_Type Characterization_Name`.
- **`compositions`** (`composition_ids`, `sample_ids`) — `Composition_ID Nanomaterial_Entity_Type
  Functionalizing_Entity_Type Functionalizing_Entity_Inherent_Function_Type`.
- **`publications`** (`publication_ids`, `sample_ids`) — `DOI_or_Pub_ID Publication_Type
  Publication_Status Publication_Title`.
- **`protocols`** (`protocol_ids`, `file_ids`, `sample_ids`) — `protocol_pk_id protocol_name
  protocol_type doi`.

## Study-level extras
- **`investigators`** (`investigator_ids`) — PI/co-I contact and affiliation metadata.
- **`consent_groups`** (`consent_group_ids`) — dbGaP consent-group metadata for the study.

All of these have matching `*Count` queries (require `phs_accession`) for sizing — see
[QUERIES.md](QUERIES.md).
