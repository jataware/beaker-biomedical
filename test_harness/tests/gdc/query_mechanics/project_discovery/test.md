---
name: "Project discovery for a site (don't default to TCGA)"
description: "This tests the discover-then-query workflow — faceting `/cases` by `project.project_id` under a `primary_site` filter rather than assuming a single TCGA project — plus the lowercase `disease_type` value casing."
---
Which GDC projects contain kidney cancer cases, and how many cases are in each?
