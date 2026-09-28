# v2.44 Signal mapping coverage

All frozen static emission sites, including explicit closed dynamic expansions; not runtime occurrence coverage

| Signal | Classification | Reason |
|---|---|---|
| ABNORMAL_TRANSACTION_MARGIN | INSUFFICIENT_SEMANTICS | Transaction identity is omitted from Signal. |
| AP_LEDGER_OUTSTANDING | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| AP_OVERDUE_OUTSTANDING | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| AR_LEDGER_OUTSTANDING | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| AR_OVERDUE_OUTSTANDING | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| AVAILABLE_CASH_POSITION | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| BS_ACCOUNTS_PAYABLE | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| BS_ACCOUNTS_RECEIVABLE | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| BS_INVENTORY | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| CASH_OPTIMISATION_CANDIDATE | NOT_APPLICABLE_TO_FACT | Candidate/action semantics are not an established descriptive proposition. |
| COMMISSION_PLAN_STRUCTURE | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| COMPARABLE_PRICE_DISPERSION | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| COMPARABLE_REVENUE_CHANGE | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| CONTRIBUTION_0_PER_FTE | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| CONTRIBUTION_CHANGE | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| CONTRIBUTION_MARGIN_CHANGE | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| CONTROL_PROCESS_EXCEPTION | REQUIRES_TYPE_SPECIFIC_MAPPING | Exception kind and management/source authority need explicit resolution. |
| CUSTOMER_BRIDGE_LEG | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| CUSTOMER_CONTRIBUTION_AFTER_CTS | REQUIRES_TYPE_SPECIFIC_MAPPING | Upstream treats missing CTS as zero; require per-customer CTS coverage before asserting Contribution 1. |
| CUSTOMER_CONTRIBUTION_PARETO | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| CUSTOMER_DECLINE | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| CUSTOMER_GROWTH | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| CUSTOMER_HHI | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| CUSTOMER_MARGIN_VARIANCE | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| CUSTOMER_OVERDUE_AR | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| CUSTOMER_PRODUCT_WHITESPACE | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| CUSTOMER_PROFITABILITY | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| CUSTOMER_RETENTION_SUMMARY | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| DEPARTMENT_WORKFORCE_ECONOMICS | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| DEPENDENCY_EXPOSURE_SIGNAL | REQUIRES_TYPE_SPECIFIC_MAPPING | Resolve the heterogeneous originating Signal before mapping. |
| DUPLICATE_LOOKING_SPEND | INSUFFICIENT_SEMANTICS | The pair of transaction identities is omitted from Signal ancestry. |
| EVIDENCED_RECURRING_REVENUE_MIX | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| EXISTING_CUSTOMER_NET_CHANGE | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| FINANCIAL_EXPOSURE | REQUIRES_TYPE_SPECIFIC_MAPPING | Exposure type and source authority need explicit resolution. |
| FINANCIAL_INTEGRITY_WEAKNESS | REQUIRES_TYPE_SPECIFIC_MAPPING | Requires typed state proposition and trust-layer source resolver. |
| FORECAST_MAE | INSUFFICIENT_SEMANTICS | Signal omits forecast-vintage/target-period ancestry; percentage is not standard MAPE. |
| FORECAST_MEAN_ERROR | INSUFFICIENT_SEMANTICS | Signal omits forecast-vintage/target-period ancestry. |
| FORENSIC_EXCEPTION_SIGNAL | REQUIRES_TYPE_SPECIFIC_MAPPING | Resolve the heterogeneous originating Signal before mapping. |
| FORWARD_SCENARIO_RANGE | NOT_APPLICABLE_TO_FACT | Illustrative assumptions are not observed outcomes. |
| GOVERNANCE_ACTION_CANDIDATE | NOT_APPLICABLE_TO_FACT | Candidate/action semantics are not an established descriptive proposition. |
| INVENTORY_SNAPSHOT_VALUE | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| KPI_DRIVER_OBSERVATION | REQUIRES_TYPE_SPECIFIC_MAPPING | KPI-specific unit, authority and period contract required. |
| LOST_CUSTOMER_REVENUE | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| MARGIN_LEAKAGE_SIGNAL | INSUFFICIENT_SEMANTICS | Transaction identity is omitted; dataset ancestry alone cannot identify the transaction. |
| MARGIN_RATE_EFFECT | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| MIX_PORTFOLIO_RESIDUAL | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| MONTHLY_REVENUE_VOLATILITY | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| NEGATIVE_TRANSACTION_MARGIN | INSUFFICIENT_SEMANTICS | Transaction identity is omitted from Signal. |
| NEW_CUSTOMER_REVENUE | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| OVERHEAD_COST_DRIFT | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| PEOPLE_COST_PER_FTE | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| PLAN_VS_ACTUAL_REVENUE | INSUFFICIENT_SEMANTICS | Selected common periods and actual evidence are not retained in Signal ancestry. |
| PRICE_EFFECT | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| PRICE_LEAKAGE_SIGNAL | INSUFFICIENT_SEMANTICS | Transaction identity and unit basis are omitted from Signal. |
| PRICING_OPPORTUNITY_CANDIDATE_SET | NOT_APPLICABLE_TO_FACT | Candidate/action semantics are not an established descriptive proposition. |
| PRODUCT_COMPLEXITY_DISTRIBUTION | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| PRODUCT_ECONOMICS | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| PRODUCT_GROWTH_DECLINE | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| PRODUCT_MARGIN_VARIANCE | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| PRODUCT_MIX_SHIFT | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| PURCHASE_COST_INFLATION_RECOVERY | REQUIRES_TYPE_SPECIFIC_MAPPING | Mechanical recovery requires explicit quantity basis and comparability validation. |
| PURCHASE_PRICE_VARIANCE | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| PVM_RECONCILIATION | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| REACTIVATED_CUSTOMER_REVENUE | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| REALISED_PRICE_INCREASE_COVERAGE | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| REALISED_PRICE_MOVEMENT | INSUFFICIENT_SEMANTICS | Customer-product calculation drops product identity from the Signal. |
| RECONCILIATION_EXCEPTION | REQUIRES_TYPE_SPECIFIC_MAPPING | Multiple reconciliation kinds require signed residual and status semantics. |
| REVENUE_BRIDGE_TOTAL | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| REVENUE_PER_FTE | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| SEASONAL_INDEX_SPREAD | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| SEASONAL_PEAK_MONTH | INSUFFICIENT_SEMANTICS | Month identity exists only in prose; do not parse prose into truth. |
| SEASONAL_TROUGH_MONTH | INSUFFICIENT_SEMANTICS | Month identity exists only in prose; do not parse prose into truth. |
| SUPPLIER_DEPENDENCY | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| SUPPLIER_OVERHEAD_OPPORTUNITY_CANDIDATE | NOT_APPLICABLE_TO_FACT | Candidate/action semantics are not an established descriptive proposition. |
| SUPPLIER_SPEND | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| TOP5_CONCENTRATION | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| TOP_CUSTOMER_CONCENTRATION | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| TOTAL_PEOPLE_COST | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| VOLUME_EFFECT | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| WC_CCC | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| WC_DIO | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| WC_DPO | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| WC_DSO | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| WORKFORCE_CAPACITY_OPPORTUNITY_CANDIDATE | NOT_APPLICABLE_TO_FACT | Candidate/action semantics are not an established descriptive proposition. |
| WORKFORCE_UTILISATION | SAFE_TO_CANONICALISE | Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass |
| WORKING_CAPITAL_RELEASE_CANDIDATE | NOT_APPLICABLE_TO_FACT | Candidate/action semantics are not an established descriptive proposition. |
