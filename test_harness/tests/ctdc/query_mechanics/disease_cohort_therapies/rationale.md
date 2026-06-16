# Intended Behavior

The agent discovers the exact controlled-vocabulary term `Colorectal Carcinoma` (50 participants) and reads `filterParticipantCountByTargetedTherapy` for that cohort, leading with Bevacizumab 33 and including Panitumumab 7, Regorafenib 4, and Cetuximab 3 — the anti-VEGF and anti-EGFR colorectal drugs, as expected.

# Incorrect Behavior

After a near-miss like `Colorectal Cancer` or wrong casing (which returns an empty cohort with no error), the agent reports 0 or "no colorectal data," or it returns the whole-study therapy ranking (Bortezomib/Lenalidomide/Pembrolizumab) instead of the colorectal-scoped one.
