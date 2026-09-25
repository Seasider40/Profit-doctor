# v2.38 — Upload Readiness & Coverage Explanation

Adds a deterministic, owner-facing preflight layer between workbook upload and the finished Profit Doctor Review.

It explains: detected sheets/domains, semantic mapping confidence, controls/reconciliations, diagnostic coverage, and which additional datasets would unlock deeper analysis. It deliberately does **not** create a universal quality score or convert failed controls into economic opportunities.

Scenario 2 remains analysable despite control failures; the failures are surfaced as limitations. Missing Level-3 evidence such as CRM/pipeline and detailed pricing becomes an explicit data request rather than invented precision.
