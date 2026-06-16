# Intended Behavior

The agent runs `primarySiteMorphology(study_short_name: ["PLCO"])` and introspects the real return-type field names — `group` (site/morphology name), `group_code` (ICD-O code, e.g. `8140/3`), and `subjects` — rather than guessing `primary_site`/`count`. PLCO has 40 primary-site buckets and 335 morphology buckets:

- top sites (excluding `Not Applicable` 107,464): prostate gland 11,129, breast 6,987, lung 5,392, colorectum 3,323, …
- top morphologies: Adenocarcinoma `8140/3` 16,804, Infiltrating Duct Carcinoma, NOS `8500/3` 4,232, Squamous Cell Carcinoma `8070/3` 1,395

# Incorrect Behavior

The agent guesses `primary_site`/`count` (both `FieldUndefined`), reuses the skill's NLST example instead of PLCO, fabricates site/morphology names, or trips the `BadFaithIntrospection` guard by hammering full-`fields` introspection.
