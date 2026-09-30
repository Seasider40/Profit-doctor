"""Economic Bridge contracts: deterministic movements, no impact/opportunity claim."""
from decimal import Decimal, localcontext
from typing import Literal
from pydantic import Field, model_validator
from profit_doctor.reasoning.domain.contracts import Contract, Identifier, FinancialDecimal
from profit_doctor.reasoning.canonical.service import identity
from .qualification import BridgeFamily


class Component(Contract):
    kind: Literal['SELECTED_POPULATION_MOVEMENT','AR_MOVEMENT','INVENTORY_MOVEMENT','AP_MOVEMENT']
    amount: FinancialDecimal
    input_bindings: tuple[Identifier, ...]
    coverage: Literal['COMPLETE','PARTIAL']
    # Cash direction is a stock-change projection, not operating cash flow.
    cash_direction_amount: FinancialDecimal | None = None


class EconomicBridge(Contract):
    contract_version: Literal['EB-2.48B.1'] = 'EB-2.48B.1'
    client_id: Identifier
    run_id: Identifier
    family: BridgeFamily
    metric: Literal['financial_revenue','contribution_0','net_trade_working_capital']
    currency: Literal['GBP'] = 'GBP'
    opening_year: int = Field(ge=1900, le=9998)
    closing_year: int = Field(ge=1901, le=9999)
    opening: FinancialDecimal
    closing: FinancialDecimal
    components: tuple[Component, ...] = ()
    residual: FinancialDecimal
    tolerance: Literal['0.01'] = '0.01'
    opening_bindings: tuple[Identifier, ...]
    closing_bindings: tuple[Identifier, ...]
    qualification_ids: tuple[Identifier, ...]
    limitations: tuple[str, ...]

    @property
    def series_id(self):
        return identity('bridge-series', self.client_id, self.family.value, self.metric, self.opening_year, self.closing_year, self.contract_version)

    @property
    def snapshot_id(self):
        return identity('economic-bridge', self.to_json())

    @model_validator(mode='after')
    def reconcile(self):
        metric = {'REVENUE_BRIDGE':'financial_revenue','MARGIN_OR_PROFIT_BRIDGE':'contribution_0',
                  'WORKING_CAPITAL_BRIDGE':'net_trade_working_capital'}.get(self.family)
        if metric != self.metric or self.closing_year != self.opening_year + 1:
            raise ValueError('Unqualified family/metric/period contract')
        bindings=self.opening_bindings+self.closing_bindings
        if not bindings or len(bindings)!=len(set(bindings)):
            raise ValueError('Missing or duplicate endpoints')
        kinds=[c.kind for c in self.components]
        if self.family=='WORKING_CAPITAL_BRIDGE':
            if set(kinds)!={'AR_MOVEMENT','INVENTORY_MOVEMENT','AP_MOVEMENT'} or len(kinds)!=3:
                raise ValueError('Working-capital component contract incomplete')
            if any(c.cash_direction_amount != -c.amount or c.coverage!='COMPLETE' for c in self.components):
                raise ValueError('Explicit inverse stock/cash direction required')
        elif kinds not in ([], ['SELECTED_POPULATION_MOVEMENT']) or any(c.cash_direction_amount is not None or c.coverage!='PARTIAL' for c in self.components):
            raise ValueError('Unsupported attribution component')
        with localcontext() as arithmetic:
            arithmetic.prec=60
            if abs(self.opening+sum((c.amount for c in self.components),Decimal(0))+self.residual-self.closing)>Decimal(self.tolerance):
                raise ValueError('Bridge does not reconcile')
        return self


class BridgeAssessment(Contract):
    family: BridgeFamily
    status: Literal['QUALIFIED','REFUSED']
    gaps: tuple[str, ...] = ()
    bridge: EconomicBridge | None = None

    @model_validator(mode='after')
    def valid_result(self):
        if (self.status=='QUALIFIED') != (self.bridge is not None) or (self.status=='REFUSED' and not self.gaps):
            raise ValueError('Assessment must contain a Bridge or explicit refusal')
        if self.bridge and (self.bridge.family!=self.family or self.gaps):
            raise ValueError('Assessment family/gaps disagree')
        return self
