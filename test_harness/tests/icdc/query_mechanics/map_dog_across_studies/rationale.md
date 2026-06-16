# Intended Behavior

The agent uses `searchCases(study_participation: ["Multiple Study"])` (18 caseIds) to find multi-study cases, then `multiStudyCases(case_id)` (or the `canine_individual` node) to pool one physical dog's data under a single `canine_individual_id`. For example, individual `0003` (a male Scottish Terrier with Bladder Cancer) ties `UBC02-776-675-63` and `UBC01-776-675-Vm20` across the UBC01 and UBC02 studies, with 3 samples and 6 files. Any dog tying ≥2 case_ids across ≥2 studies works, as long as it is a fresh one (not the skill's worked example, individual `0009`).

# Incorrect Behavior

The agent treats each `case_id` as a distinct animal (so one dog looks like two unrelated patients), fails to resolve the shared `canine_individual_id`, or reuses the example dog `0009` instead of finding a fresh one.
