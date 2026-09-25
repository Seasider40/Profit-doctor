# Profit Doctor Real SME Qualification Programme v1

## Purpose
Prove that Profit Doctor remains financially correct, appropriately cautious and genuinely useful when exposed to real SME data. Synthetic/adversarial cases prepare the harness; they do **not** count as real-company validation.

## Cohort design
Initial qualification cohort: 12 controlled archetypes across Product/Distribution, Professional Services, Subscription, Project/Contract, Hospitality/Transactional and Hybrid models, spanning Core, messy Core, Enhanced and Advanced data states. Turnover emphasis is approximately £0.5m–£10m, with the primary commercial target around £1m–£10m.

After harness qualification, use a minimum first wave of 5 anonymised real SMEs, then expand toward 10–20 businesses with deliberately different systems, accounting quality, business models and data maturity. A company must not be selected merely because its data is easy.

## Evidence pack per real SME
Preserve raw files unchanged; document source/system, extraction date, period coverage, currency, entity, transformations and known limitations. Capture the pre-analysis availability/quality/integrity/coverage assessment. Store the engine output before FD review so hindsight cannot alter the benchmark.

## Blind FD review
An experienced FD reviews the same evidence independently before seeing Profit Doctor's conclusions. Compare: issues detected; materiality; economics; missing-data refusals; management questions; prioritisation; and important issues missed by either side. Differences are adjudicated from evidence, not preference.

## Twelve gates
1 Source traceability. 2 Accounting reconciliation. 3 Eligibility/graceful degradation. 4 Business-model applicability. 5 Economic classification. 6 Anti-double-counting. 7 Numeric reproducibility. 8 Causal-language discipline. 9 Management usefulness. 10 FD-review agreement. 11 Client isolation. 12 Repeatability.

## Fail-closed blockers
Any material numeric error, unsupported opportunity value, cross-client contamination, double-counted benefit, unsupported causal claim presented as fact, silent material data repair, or omitted material limitation is a FAIL for that case and blocks qualification until corrected and rerun.

## Usefulness rubric
A finding is useful only if it is evidence-based, material enough to deserve management attention, understandable, non-duplicative, and changes or sharpens a management question/decision/action. More findings is not better. Primary monthly attention should remain deliberately scarce.

## Opportunity verification
For every £ opportunity independently reconstruct Theoretical → Addressable → Expected. Verify mechanism, recovery envelope, baseline, time basis, benefit type and overlap relationships. Cash release and recurring profit must never be aggregated as though equivalent.

## Required outputs
Per case: source manifest, data-quality report, diagnostic coverage, findings pack, FD benchmark, discrepancy log, opportunity reconciliation, client-facing summary and PASS/CONDITIONAL/FAIL decision. Programme level: defect register, false-positive/false-negative analysis, coverage matrix, recurring failure themes and release recommendation.

## Qualification boundary
Passing synthetic cases is harness readiness only. Real-SME qualification requires actual anonymised company data and independent FD judgement. Live PostgreSQL remains a separate release gate until executed against a real PostgreSQL service.
