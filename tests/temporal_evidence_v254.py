"""Explicitly synthetic temporal premises; never registered production providers."""
from calendar import monthrange
from datetime import date
from decimal import Decimal

from tests import test_dataset_contract_v253 as datasets
from profit_doctor.reasoning.bridge.qualification import Period
from profit_doctor.reasoning.dataset.contracts import DatasetContract
from profit_doctor.reasoning.temporal.contracts import (
    AbsenceEvidence, ContractKey, Observation, TemporalInput, Window,
)


def observation(month, value='30', *, key=ContractKey.CONTRIBUTION_0_MARGIN_TRAJECTORY,
                name=None, presence='UNKNOWN', dataset_changes=None):
    name = name or f'synthetic-{month}'
    cash = key == ContractKey.CASH_TRAPPED_RECEIVABLES_LIFECYCLE
    margin = key == ContractKey.CONTRIBUTION_0_MARGIN_TRAJECTORY
    ds = datasets.contract(name, month=month, family='GENERAL_LEDGER' if cash else 'SALES_TRANSACTIONS',
        unit='PERCENTAGE' if margin else 'MONEY', currency='N/A' if margin else 'GBP')
    end = date(2026, month, monthrange(2026, month)[1])
    period = Period(start=end if cash else date(2026, month, 1), end=end,
        basis='POINT_IN_TIME' if cash else 'MONTHLY', nature='STOCK' if cash else 'RATE' if margin else 'FLOW')
    if cash:
        coverage = ds.coverage.verified_value.copy()
        coverage['period'] = period.model_dump(mode='json')
        ds = ds.model_copy(update={'coverage':datasets.verified(coverage, ds.source_version),
            'source_data_domain':'SYNTHETIC_RECEIVABLES_SNAPSHOT'})
    if dataset_changes:
        ds = ds.model_copy(update={key:datasets.verified(value, ds.source_version)
            for key, value in dataset_changes.items()})
    ds = DatasetContract.from_json(ds.to_json())
    absence = None
    if presence == 'ABSENT_VERIFIED':
        absence = AbsenceEvidence(origin='SYNTHETIC_QUALIFICATION', client_id='c1', as_of=end,
            scope_key='synthetic-controlled-population', population=ds.population.verified_value,
            complete_population_verified=True, control_reconciled=True,
            contractual_and_status_review_complete=True, no_unresolved_classifications=True,
            condition_absence_verified=True, evidence=(ds.source_version,))
    metric = 'cash_trapped_receivables' if cash else 'contribution_0_margin' if margin else 'revenue'
    return Observation(observation_id=name, client_id='c1', run_id='synthetic-run',
        source_kind='ABSENCE' if absence else 'IMPACT' if presence == 'PRESENT' else 'UNKNOWN' if cash else 'FACT',
        source_id='source-'+name, scope_key='synthetic-controlled-population', period=period,
        dataset=ds, metric=metric, unit='PERCENTAGE' if margin else 'CURRENCY',
        currency=None if margin else 'GBP', value=Decimal(value) if value is not None else None,
        presence=presence, absence=absence, lineage=(ds.source_version,),
        source_snapshot='SYNTHETIC QUALIFICATION: '+name)


def basis(values=('30','32','34'), *, key=ContractKey.CONTRIBUTION_0_MARGIN_TRAJECTORY,
          observations=None, start=1, end=3, origin='SYNTHETIC_QUALIFICATION'):
    rows = observations if observations is not None else tuple(observation(i+1, value, key=key) for i, value in enumerate(values))
    return TemporalInput(origin=origin, contract_key=key, client_id='c1', subject_id='synthetic-subject',
        window=Window(start=date(2026,start,1),end=date(2026,end,monthrange(2026,end)[1]),cadence='MONTHLY'),
        observations=rows)
