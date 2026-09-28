"""Reviewed producer-specific slot semantics. No unknown-Signal fallback.

Units belong to slots, not rows. An optional slot may be absent but a populated
unmapped slot is always refused. Labels describe the frozen calculation, not an
inferred cause or a promised financial benefit.
"""
from dataclasses import dataclass
from enum import StrEnum


class MappingClass(StrEnum):
    SAFE_TO_CANONICALISE = 'SAFE_TO_CANONICALISE'
    REQUIRES_TYPE_SPECIFIC_MAPPING = 'REQUIRES_TYPE_SPECIFIC_MAPPING'
    INSUFFICIENT_SEMANTICS = 'INSUFFICIENT_SEMANTICS'
    LEGACY_ONLY = 'LEGACY_ONLY'
    NOT_APPLICABLE_TO_FACT = 'NOT_APPLICABLE_TO_FACT'


class Unit(StrEnum):
    CURRENCY = 'CURRENCY'
    PERCENTAGE = 'PERCENTAGE'
    PERCENTAGE_POINTS = 'PERCENTAGE_POINTS'
    DAYS = 'DAYS'
    COUNT = 'COUNT'
    INDEX = 'INDEX'
    INDEX_POINTS = 'INDEX_POINTS'
    HOURS = 'HOURS'
    FTE = 'FTE'
    CURRENCY_PER_FTE = 'CURRENCY_PER_FTE'
    CURRENCY_PER_UNIT = 'CURRENCY_PER_UNIT'


@dataclass(frozen=True)
class Slot:
    metric: str
    unit: Unit
    basis: str
    required: bool = True


@dataclass(frozen=True)
class Mapping:
    diagnostic: str
    signal_type: str
    source_unit: str
    family: str
    slots: tuple[Slot | None, Slot | None, Slot | None]
    entity_type: str | None
    period_basis: str
    version: str = 'SF-2.44.1'
    classification: MappingClass = MappingClass.SAFE_TO_CANONICALISE


REGISTRY: dict[tuple[str, str], Mapping] = {}


def register(test, typ, row_unit, family, slots, entity=None,
             period='Captured diagnostic scope; exact dates unavailable unless retained by Signal'):
    key = (test, typ)
    if key in REGISTRY:
        raise ValueError('Duplicate mapping')
    REGISTRY[key] = Mapping(test, typ, row_unit, family, tuple(slots), entity, period)


def s(metric, unit, basis, required=True):
    return Slot(metric, Unit(unit), basis, required)


# Current/prior are calculation roles; they are not invented calendar dates.
for test, typ, entity in [
    ('REV-01', 'COMPARABLE_REVENUE_CHANGE', None),
    ('REV-02', 'REVENUE_BRIDGE_TOTAL', None),
    ('REV-02', 'CUSTOMER_BRIDGE_LEG', 'CUSTOMER'),
    ('CUS-04', 'CUSTOMER_GROWTH', 'CUSTOMER'),
    ('CUS-04', 'CUSTOMER_DECLINE', 'CUSTOMER'),
    ('PROD-03', 'PRODUCT_GROWTH_DECLINE', 'PRODUCT'),
]:
    register(test, typ, 'GBP', 'COMPARATIVE', [
        s('revenue', 'CURRENCY', 'current comparable window'),
        s('revenue', 'CURRENCY', 'prior comparable window'),
        s('revenue_change', 'CURRENCY', 'current minus prior')], entity,
        'Diagnostic comparable sales windows; Signal dates, if present, span both windows')

register('GM-02', 'CONTRIBUTION_CHANGE', 'GBP', 'COMPARATIVE', [
    s('contribution_0', 'CURRENCY', 'current comparable window'),
    s('contribution_0', 'CURRENCY', 'prior comparable window'),
    s('contribution_0_change', 'CURRENCY', 'current minus prior')])

for test, typ, entity, metric in [
    ('GM-01', 'CONTRIBUTION_MARGIN_CHANGE', None, 'contribution_0_margin'),
    ('GM-03', 'CUSTOMER_MARGIN_VARIANCE', 'CUSTOMER', 'contribution_0_margin'),
    ('GM-04', 'PRODUCT_MARGIN_VARIANCE', 'PRODUCT', 'contribution_0_margin'),
    ('PROD-02', 'PRODUCT_MIX_SHIFT', 'PRODUCT', 'revenue_share'),
]:
    register(test, typ, 'PERCENTAGE_POINTS', 'COMPARATIVE', [
        s(metric, 'PERCENTAGE', 'current comparable window'),
        s(metric, 'PERCENTAGE', 'prior comparable window'),
        s(metric + '_change', 'PERCENTAGE_POINTS', 'current minus prior')], entity)

for test, typ, entity in [('CUS-02', 'CUSTOMER_PROFITABILITY', 'CUSTOMER'),
                           ('PROD-01', 'PRODUCT_ECONOMICS', 'PRODUCT')]:
    register(test, typ, 'GBP', 'MEASUREMENT_SET', [
        s('contribution_0', 'CURRENCY', 'current comparable window'),
        s('revenue', 'CURRENCY', 'current comparable window'),
        s('contribution_0_margin', 'PERCENTAGE', 'contribution_0 / revenue * 100', False)], entity)

# Explicit mixed-unit mappings. No generic arithmetic is performed on these slots.
register('CUS-05', 'CUSTOMER_RETENTION_SUMMARY', 'GBP', 'MEASUREMENT_SET', [
    s('retained_customer_revenue', 'CURRENCY', 'current revenue of retained customers'),
    s('revenue', 'CURRENCY', 'prior comparable window'),
    s('observed_revenue_retention_ratio', 'PERCENTAGE', 'retained current revenue / prior revenue * 100; not contractual GRR', False)])
register('CUS-06', 'CUSTOMER_OVERDUE_AR', 'GBP', 'MEASUREMENT_SET', [
    s('overdue_receivables', 'CURRENCY', 'captured ledger'),
    s('outstanding_receivables', 'CURRENCY', 'captured ledger'),
    s('overdue_share', 'PERCENTAGE', 'overdue / outstanding * 100', False)], 'CUSTOMER')
register('CUS-07', 'CUSTOMER_CONTRIBUTION_PARETO', 'PERCENT', 'MEASUREMENT_SET', [
    s('top_customer_contribution_share', 'PERCENTAGE', 'top contribution-ranked 20% customer contribution / total contribution * 100', False),
    s('top_customer_count', 'COUNT', 'ceil(20% of customer count), minimum one'),
    s('customers_for_80_percent_contribution', 'PERCENTAGE', 'count to reach 80% positive total contribution / total count * 100; zero sentinel when total contribution is nonpositive', False)])
register('PROD-04', 'PRODUCT_COMPLEXITY_DISTRIBUTION', 'COUNT', 'MEASUREMENT_SET', [
    s('long_tail_product_count', 'COUNT', 'products with at most 1% revenue share; empty when total revenue is zero'),
    s('product_count', 'COUNT', 'current comparable window'),
    s('long_tail_contribution_0', 'CURRENCY', 'contribution of long-tail products')])
register('PROD-05', 'CUSTOMER_PRODUCT_WHITESPACE', 'COUNT', 'MEASUREMENT_SET', [
    s('unpurchased_peer_product_count', 'COUNT', 'peer-adopted products not purchased by customer'),
    s('peer_adopted_product_count', 'COUNT', 'products with at least max(2, floor(10% of active customers)) buyers'),
    s('observed_product_count_ratio', 'PERCENTAGE', 'all customer-owned products / peer-adopted universe * 100; numerator may include non-peer products')], 'CUSTOMER')
register('PRI-02', 'COMPARABLE_PRICE_DISPERSION', 'PERCENT', 'MEASUREMENT_SET', [
    s('highest_realised_unit_price', 'CURRENCY_PER_UNIT', 'current customer-product aggregates'),
    s('lowest_realised_unit_price', 'CURRENCY_PER_UNIT', 'current customer-product aggregates'),
    s('realised_price_dispersion', 'PERCENTAGE', '(highest - lowest) / unweighted mean * 100')], 'PRODUCT')
register('PRI-04', 'REALISED_PRICE_INCREASE_COVERAGE', 'PERCENT', 'MEASUREMENT_SET', [
    s('price_increase_coverage', 'PERCENTAGE', 'products with higher realised price / comparable products * 100'),
    s('comparable_product_count', 'COUNT', 'products comparable across windows'),
    s('mechanical_price_effect', 'CURRENCY', 'positive unit-price movement times current units; no attribution')])
register('PEO-01', 'COMMISSION_PLAN_STRUCTURE', 'COUNT', 'MEASUREMENT_SET', [
    s('active_commission_plan_count', 'COUNT', 'captured active plans'),
    s('variable_people_cost', 'CURRENCY', 'commission and bonus in latest workforce snapshot'), None])
register('PEO-03', 'DEPARTMENT_WORKFORCE_ECONOMICS', 'GBP', 'MEASUREMENT_SET', [
    s('annual_people_cost', 'CURRENCY', 'latest workforce snapshot'),
    s('full_time_equivalents', 'FTE', 'latest workforce snapshot'),
    s('utilisation', 'PERCENTAGE', 'captured utilised / practical capacity hours * 100', False)], 'DEPARTMENT')
register('PEO-04', 'WORKFORCE_UTILISATION', 'PERCENT', 'MEASUREMENT_SET', [
    s('utilisation', 'PERCENTAGE', 'utilised / practical capacity hours * 100'),
    s('practical_capacity', 'HOURS', 'records with both capacity and used hours'),
    s('unused_capacity', 'HOURS', 'max(capacity - used, 0); not a cash saving')])
register('SUP-01', 'SUPPLIER_SPEND', 'GBP', 'MEASUREMENT_SET', [
    s('supplier_spend', 'CURRENCY', 'captured purchase transactions'),
    s('supplier_spend_share', 'PERCENTAGE', 'supplier spend / total captured spend * 100'), None], 'SUPPLIER')
register('SUP-02', 'PURCHASE_PRICE_VARIANCE', 'GBP_PER_UNIT', 'MEASUREMENT_SET', [
    s('unit_cost_change', 'CURRENCY_PER_UNIT', 'latest minus earliest captured item cost'),
    s('mechanical_purchase_price_variance', 'CURRENCY', 'unit cost change times latest quantity'), None], 'SUPPLIER_ITEM')
register('SUP-03', 'SUPPLIER_DEPENDENCY', 'PERCENT', 'MEASUREMENT_SET', [
    s('supplier_spend_share', 'PERCENTAGE', 'supplier spend / total captured spend * 100'),
    s('supplier_spend', 'CURRENCY', 'captured purchase transactions'), None], 'SUPPLIER')
register('SUP-04', 'OVERHEAD_COST_DRIFT', 'GBP', 'COMPARATIVE', [
    s('overhead_spend', 'CURRENCY', 'later captured months'),
    s('overhead_spend', 'CURRENCY', 'earlier captured months'),
    s('overhead_spend_change', 'CURRENCY', 'later minus earlier; windows may differ in length')], 'OVERHEAD_CATEGORY')

for test, typ, metric, basis in [
    ('REV-03', 'NEW_CUSTOMER_REVENUE', 'new_customer_revenue', 'customers absent in prior comparable window'),
    ('REV-03', 'LOST_CUSTOMER_REVENUE', 'lost_customer_prior_revenue', 'prior revenue of customers absent in current window'),
    ('REV-03', 'EXISTING_CUSTOMER_NET_CHANGE', 'existing_customer_revenue_change', 'customers active in both windows'),
    ('CUS-05', 'NEW_CUSTOMER_REVENUE', 'new_customer_revenue', 'no prior or older captured customer revenue'),
    ('CUS-05', 'LOST_CUSTOMER_REVENUE', 'lost_customer_prior_revenue', 'prior revenue of customers absent in current window'),
    ('CUS-05', 'REACTIVATED_CUSTOMER_REVENUE', 'reactivated_customer_revenue', 'older history but no prior window revenue'),
    ('REV-04', 'PRICE_EFFECT', 'mechanical_price_effect', 'comparable products, current quantity weighting; not causal'),
    ('REV-04', 'VOLUME_EFFECT', 'mechanical_volume_effect', 'comparable products, prior unit-price weighting; not causal'),
    ('REV-04', 'MIX_PORTFOLIO_RESIDUAL', 'portfolio_residual', 'total revenue movement less mechanical price and volume effects'),
    ('GM-02', 'MARGIN_RATE_EFFECT', 'mechanical_margin_rate_effect', 'current revenue times margin-point movement / 100'),
    ('PEO-01', 'TOTAL_PEOPLE_COST', 'annual_people_cost', 'latest captured workforce snapshot'),
    ('WC-05', 'AVAILABLE_CASH_POSITION', 'captured_cash', 'available cash primitive or bank closing cash; no liquidity inference'),
]:
    register(test, typ, 'GBP', 'MEASUREMENT', [s(metric, 'CURRENCY', basis), None, None])

for test, typ, metric in [('PEO-01', 'PEOPLE_COST_PER_FTE', 'annual_people_cost_per_fte'),
                           ('PEO-02', 'REVENUE_PER_FTE', 'revenue_per_fte'),
                           ('PEO-02', 'CONTRIBUTION_0_PER_FTE', 'contribution_0_per_fte')]:
    register(test, typ, 'GBP_PER_FTE', 'MEASUREMENT', [s(metric, 'CURRENCY_PER_FTE', 'latest FTE; diagnostic output period'), None, None])

for test, names in [('WC-01', ['WC_DSO', 'WC_DIO', 'WC_DPO', 'WC_CCC']),
                     ('WC-03', ['WC_DPO']), ('WC-04', ['WC_DIO'])]:
    for typ in names:
        register(test, typ, 'DAYS', 'MEASUREMENT', [s(typ.lower(), 'DAYS', 'captured trusted primitive; exact basis retained in lineage'), None, None])
for test, names in [('WC-02', ['BS_ACCOUNTS_RECEIVABLE', 'AR_LEDGER_OUTSTANDING', 'AR_OVERDUE_OUTSTANDING']),
                     ('WC-03', ['BS_ACCOUNTS_PAYABLE', 'AP_LEDGER_OUTSTANDING', 'AP_OVERDUE_OUTSTANDING']),
                     ('WC-04', ['BS_INVENTORY', 'INVENTORY_SNAPSHOT_VALUE'])]:
    for typ in names:
        register(test, typ, 'GBP', 'MEASUREMENT', [s(typ.lower(), 'CURRENCY', 'captured trusted primitive; no cash release inference'), None, None])
register('WC-02', 'CUSTOMER_OVERDUE_AR', 'GBP', 'MEASUREMENT', [
    s('overdue_receivables', 'CURRENCY', 'ledger overdue at diagnostic execution; upstream REAL aggregation precision retained'), None, None], 'CUSTOMER')
for typ, entity, metric in [('TOP_CUSTOMER_CONCENTRATION', 'CUSTOMER', 'largest_customer_revenue_share'),
                            ('TOP5_CONCENTRATION', None, 'top_five_customer_revenue_share')]:
    register('CUS-01', typ, 'PERCENT', 'MEASUREMENT', [s(metric, 'PERCENTAGE', 'current comparable revenue'), None, None], entity)
register('CUS-01', 'CUSTOMER_HHI', 'INDEX', 'MEASUREMENT', [
    s('customer_revenue_hhi', 'INDEX', 'sum squared fractional revenue shares * 10000'), None, None])
register('REV-06', 'MONTHLY_REVENUE_VOLATILITY', 'PERCENT_CV', 'MEASUREMENT', [
    s('monthly_revenue_coefficient_of_variation', 'PERCENTAGE', 'population standard deviation / mean * 100'), None, None])
register('REV-06', 'EVIDENCED_RECURRING_REVENUE_MIX', 'PERCENT', 'MEASUREMENT', [
    s('recurring_revenue_share', 'PERCENTAGE', 'mapped transaction revenue; not guaranteed future revenue'), None, None])
register('REV-05', 'SEASONAL_INDEX_SPREAD', 'INDEX_POINTS', 'MEASUREMENT', [
    s('seasonal_index_spread', 'INDEX_POINTS', 'peak minus trough month-of-year index; 100 = average month'), None, None])
register('REV-04', 'PVM_RECONCILIATION', 'GBP', 'RECONCILIATION', [
    s('mechanical_bridge_total', 'CURRENCY', 'price + volume + explicit portfolio residual'),
    s('revenue_change', 'CURRENCY', 'current minus prior'),
    s('reconciliation_residual', 'CURRENCY', 'bridge total minus revenue change')])

# Refusals are governed separately from numerical mappings.
REFUSALS = {
    'REALISED_PRICE_MOVEMENT': (MappingClass.INSUFFICIENT_SEMANTICS, 'Customer-product calculation drops product identity from the Signal.'),
    'SEASONAL_PEAK_MONTH': (MappingClass.INSUFFICIENT_SEMANTICS, 'Month identity exists only in prose; do not parse prose into truth.'),
    'SEASONAL_TROUGH_MONTH': (MappingClass.INSUFFICIENT_SEMANTICS, 'Month identity exists only in prose; do not parse prose into truth.'),
    'KPI_DRIVER_OBSERVATION': (MappingClass.REQUIRES_TYPE_SPECIFIC_MAPPING, 'KPI-specific unit, authority and period contract required.'),
    'FORENSIC_EXCEPTION_SIGNAL': (MappingClass.REQUIRES_TYPE_SPECIFIC_MAPPING, 'Resolve the heterogeneous originating Signal before mapping.'),
    'DEPENDENCY_EXPOSURE_SIGNAL': (MappingClass.REQUIRES_TYPE_SPECIFIC_MAPPING, 'Resolve the heterogeneous originating Signal before mapping.'),
    'FORWARD_SCENARIO_RANGE': (MappingClass.NOT_APPLICABLE_TO_FACT, 'Illustrative assumptions are not observed outcomes.'),
    'FINANCIAL_INTEGRITY_WEAKNESS': (MappingClass.REQUIRES_TYPE_SPECIFIC_MAPPING, 'Requires typed state proposition and trust-layer source resolver.'),
    'RECONCILIATION_EXCEPTION': (MappingClass.REQUIRES_TYPE_SPECIFIC_MAPPING, 'Multiple reconciliation kinds require signed residual and status semantics.'),
    'CONTROL_PROCESS_EXCEPTION': (MappingClass.REQUIRES_TYPE_SPECIFIC_MAPPING, 'Exception kind and management/source authority need explicit resolution.'),
    'FINANCIAL_EXPOSURE': (MappingClass.REQUIRES_TYPE_SPECIFIC_MAPPING, 'Exposure type and source authority need explicit resolution.'),
    'FORECAST_MEAN_ERROR': (MappingClass.INSUFFICIENT_SEMANTICS, 'Signal omits forecast-vintage/target-period ancestry.'),
    'FORECAST_MAE': (MappingClass.INSUFFICIENT_SEMANTICS, 'Signal omits forecast-vintage/target-period ancestry; percentage is not standard MAPE.'),
    'PLAN_VS_ACTUAL_REVENUE': (MappingClass.INSUFFICIENT_SEMANTICS, 'Selected common periods and actual evidence are not retained in Signal ancestry.'),
    'MARGIN_LEAKAGE_SIGNAL': (MappingClass.INSUFFICIENT_SEMANTICS, 'Transaction identity is omitted; dataset ancestry alone cannot identify the transaction.'),
    'NEGATIVE_TRANSACTION_MARGIN': (MappingClass.INSUFFICIENT_SEMANTICS, 'Transaction identity is omitted from Signal.'),
    'ABNORMAL_TRANSACTION_MARGIN': (MappingClass.INSUFFICIENT_SEMANTICS, 'Transaction identity is omitted from Signal.'),
    'PRICE_LEAKAGE_SIGNAL': (MappingClass.INSUFFICIENT_SEMANTICS, 'Transaction identity and unit basis are omitted from Signal.'),
    'DUPLICATE_LOOKING_SPEND': (MappingClass.INSUFFICIENT_SEMANTICS, 'The pair of transaction identities is omitted from Signal ancestry.'),
    'CUSTOMER_CONTRIBUTION_AFTER_CTS': (MappingClass.REQUIRES_TYPE_SPECIFIC_MAPPING, 'Upstream treats missing CTS as zero; require per-customer CTS coverage before asserting Contribution 1.'),
    'PURCHASE_COST_INFLATION_RECOVERY': (MappingClass.REQUIRES_TYPE_SPECIFIC_MAPPING, 'Mechanical recovery requires explicit quantity basis and comparability validation.'),
}
for name in ['PRICING_OPPORTUNITY_CANDIDATE_SET', 'WORKFORCE_CAPACITY_OPPORTUNITY_CANDIDATE',
             'SUPPLIER_OVERHEAD_OPPORTUNITY_CANDIDATE', 'WORKING_CAPITAL_RELEASE_CANDIDATE',
             'CASH_OPTIMISATION_CANDIDATE', 'GOVERNANCE_ACTION_CANDIDATE']:
    REFUSALS[name] = (MappingClass.NOT_APPLICABLE_TO_FACT, 'Candidate/action semantics are not an established descriptive proposition.')

# Future corrected mappings add a new entry and change REGISTRY's current pointer;
# historical versions must remain here for lossless historical reads.
MAPPING_VERSIONS = {(m.diagnostic, m.signal_type, m.version): m for m in REGISTRY.values()}

# The frozen producers substitute zero for an undefined denominator/selection.
# Zero can also be genuine for some of these rows; without the missing denominator
# the Signal alone cannot distinguish the two. Refuse the row, never guess.
ZERO_DENOMINATOR_GUARDS = {
    ('CUS-07', 'CUSTOMER_CONTRIBUTION_PARETO'): 'derived',
    ('PROD-02', 'PRODUCT_MIX_SHIFT'): 'comparison',
    ('SUP-01', 'SUPPLIER_SPEND'): 'comparison',
    ('SUP-03', 'SUPPLIER_DEPENDENCY'): 'observed',
    ('PROD-04', 'PRODUCT_COMPLEXITY_DISTRIBUTION'): 'observed',
}
