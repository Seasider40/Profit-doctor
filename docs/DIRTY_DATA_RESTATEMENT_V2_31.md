# v2.31 — Dirty Data, Restatement & Revision Qualification

Purpose: distinguish changes in source evidence from changes in the underlying business, while preserving historical advisory and benefit records.

Controls added:
- immutable logical-source revision history with hashes and version numbers;
- explicit restatement events and reasons;
- exact duplicate suppression, but refusal of conflicting duplicate keys;
- missing-period detection without interpolation;
- audit records for mapping changes, late journals, control restatements and source conflicts;
- baseline locks preserving both the original advisory baseline and the latest restated baseline;
- restatement events change future analysis, not historical realised-benefit claims;
- client isolation on baseline revisions.

Economic rule: a restatement can revise future expected/remaining economics, but it must not silently rewrite a benefit already claimed from evidence available at the time. Any correction to a prior benefit requires an explicit benefit adjustment/verification event, not a baseline overwrite.
