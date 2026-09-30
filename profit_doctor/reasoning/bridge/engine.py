"""Opt-in EB-2.48B.1 synthesis over current authoritative context bindings.

Only whole calendar-year revenue/C0 and December trade-working-capital stocks.
Selected-population movement is descriptive. No price/cost/mix attribution.
"""
from decimal import Decimal, localcontext
from pathlib import Path
from profit_doctor.intake.declared_accounting import inspect_pack, PL_BASIS, BS_BASIS
from profit_doctor.reasoning.domain.service import ScopeError
from .context_qualification import qualify_bridge_contexts
from .contracts import BridgeAssessment, EconomicBridge, Component
from .qualification import BridgeFamily


class BridgeEngine:
    def __init__(self, contexts):
        self.contexts=contexts

    def _resolve(self, ids):
        if len(ids)!=len(set(ids)):
            raise ValueError('Duplicate measurement bindings')
        results=[]
        for key in ids:
            binding,context=self.contexts.resolve_binding(key)
            row,amount,unit=self.contexts._owner(binding.owner)
            if binding.owner!=context.origin or binding.owner.resource!='financial_statement_line' or unit!='GBP':
                raise ValueError('This contract requires original accounting bindings')
            results.append((binding,context,amount))
        return results

    def _source_proof(self, records):
        """Recheck original pack membership, including partial subtotal arithmetic.

        Source label/locator alone cannot certify a forged derived CSV. Read the
        original immutable source and compare the records actually bound to it.
        """
        files=[]
        for _,ctx,_ in records:
            refs=[r for r in ctx.lineage if r.kind=='SOURCE_FILE']
            if len(refs)!=2:
                raise ValueError('Declared pack ancestry required')
            files.append(refs[-1].source_id)
        if len(set(files))!=1:
            raise ValueError('Different source packs need a separate version contract')
        source=self.contexts.source.row('source_file',files[0])
        pack=inspect_pack(Path(source['storage_location']), providers=self.contexts.workbook_providers)
        if pack['sha256']!=source['file_hash']:
            raise ValueError('Original source changed')
        expected={}
        metrics={'REVENUE':'financial_revenue','CONTRIBUTION_0':'contribution_0','AR':'bs_accounts_receivable',
                 'INVENTORY':'bs_inventory','AP':'bs_accounts_payable'}
        with localcontext() as arithmetic:
            arithmetic.prec=60
            for r in pack['records']:
                scope='SELECTED_CUSTOMER_PRODUCT' if r['context']=='CTX-DETAIL' else 'LEGAL_ENTITY'
                key=(metrics[r['metric']],r['period'],scope)
                expected[key]=expected.get(key,Decimal(0))+Decimal(r['amount'])
        for _,ctx,amount in records:
            dataset=self.contexts.source.dataset(ctx.source_version.source_id)
            latest=self.contexts.source.connection.execute('SELECT revision_id FROM source_revision WHERE client_id=? AND logical_source_key=? ORDER BY revision_number DESC LIMIT 1',
                (ctx.client_id,dataset['logical_dataset_key'])).fetchone()
            if latest is None or latest[0]!=ctx.source_revision_id:
                raise ValueError('Source snapshot is superseded or unbound')
            key=(ctx.metric,ctx.period.start.isoformat(),ctx.segment_scope)
            detail=ctx.segment_scope=='SELECTED_CUSTOMER_PRODUCT'
            if expected.get(key)!=amount or ctx.economic_basis!=(BS_BASIS if ctx.period.nature=='STOCK' else PL_BASIS):
                raise ValueError('Measurement/context is not supported by declared source')
            if ctx.coverage!=('PARTIAL' if detail else 'COMPLETE') or ctx.coverage_basis!=('Nonrandom selected customer/product population' if detail else 'Complete legal entity'):
                raise ValueError('Coverage differs from source declaration')
            if ctx.entity_type!='CLIENT' or ctx.entity_id!=self.contexts.client_id:
                raise ScopeError('Unqualified entity binding')
        return pack

    def assess(self, family, opening_year, closing_year, opening_ids, closing_ids, detail_ids=()):
        family=BridgeFamily(family)
        if family in (BridgeFamily.PROFIT_TO_CASH_BRIDGE,BridgeFamily.COST_TO_OUTPUT_BRIDGE):
            reason='CLASSIFIED_OPERATING_CASH_AND_RECONCILIATION_MISSING' if family==BridgeFamily.PROFIT_TO_CASH_BRIDGE else 'COMPARABLE_COST_OUTPUT_SCOPE_AND_PERIODS_MISSING'
            return BridgeAssessment(family=family,status='REFUSED',gaps=(reason,))
        try:
            return self._assess(family,opening_year,closing_year,tuple(opening_ids),tuple(closing_ids),tuple(detail_ids))
        except (ValueError, KeyError) as error:
            return BridgeAssessment(family=family,status='REFUSED',gaps=(str(error),))

    def _assess(self,family,oy,cy,opening_ids,closing_ids,detail_ids):
        if cy!=oy+1:
            raise ValueError('Consecutive calendar years required')
        a,b,d=map(self._resolve,(opening_ids,closing_ids,detail_ids))
        if not a or not b:
            raise ValueError('Missing endpoint measurements')
        if len(set(opening_ids+closing_ids+detail_ids))!=len(opening_ids+closing_ids+detail_ids):
            raise ValueError('Endpoint/component bindings overlap')
        self._source_proof(a+b+d)
        # Source versions may not silently change inside an annual aggregate.
        for records in (a+b,d):
            signatures={(c.source_version.source_id,c.source_revision_id,c.economic_basis,c.currency,c.coverage,c.coverage_basis,c.entity_id,c.segment_scope) for _,c,_ in records}
            if len(signatures)>1:
                raise ValueError('Aggregate context/version is inconsistent')
        metric={'REVENUE_BRIDGE':'financial_revenue','MARGIN_OR_PROFIT_BRIDGE':'contribution_0',
                'WORKING_CAPITAL_BRIDGE':'net_trade_working_capital'}[family]
        qualifications=[]
        stock=family=='WORKING_CAPITAL_BRIDGE'
        def ordered(records,year,detail=False):
            if stock:
                if len(records)!=3 or {c.metric for _,c,_ in records}!={'bs_accounts_receivable','bs_inventory','bs_accounts_payable'}:
                    raise ValueError('Complete AR/inventory/AP bundle required')
                if any(c.period.start.isoformat()!=f'{year}-12-31' or c.period.nature!='STOCK' for _,c,_ in records):
                    raise ValueError('December year-end stocks required')
                return sorted(records,key=lambda x:x[1].metric)
            if len(records)!=12 or {c.period.start.month for _,c,_ in records}!=set(range(1,13)):
                raise ValueError('All twelve unique monthly flows required')
            if any(c.period.start.year!=year or c.metric!=metric or c.period.nature!='FLOW' for _,c,_ in records):
                raise ValueError('Metric/annual flow scope mismatch')
            return sorted(records,key=lambda x:x[1].period.start)
        a,b=ordered(a,oy),ordered(b,cy)
        for left,right in zip(a,b):
            q=qualify_bridge_contexts(self.contexts,family,left[0].binding_id,right[0].binding_id)
            if q.outcome!='QUALIFIED' or left[1].segment_scope!='LEGAL_ENTITY':
                raise ValueError('Endpoint BIQ refusal: '+','.join(q.gaps))
            qualifications.append(q.assessment_id)
        components=[]
        with localcontext() as arithmetic:
            arithmetic.prec=60
            if stock:
                if d:
                    raise ValueError('Unsupported working-capital detail decomposition')
                signs={'bs_accounts_receivable':Decimal(1),'bs_inventory':Decimal(1),'bs_accounts_payable':Decimal(-1)}
                names={'bs_accounts_receivable':'AR_MOVEMENT','bs_inventory':'INVENTORY_MOVEMENT','bs_accounts_payable':'AP_MOVEMENT'}
                opening=sum((v*signs[c.metric] for _,c,v in a),Decimal(0))
                closing=sum((v*signs[c.metric] for _,c,v in b),Decimal(0))
                for left,right in zip(a,b):
                    change=(right[2]-left[2])*signs[left[1].metric]
                    components.append(Component(kind=names[left[1].metric],amount=change,cash_direction_amount=-change,
                        input_bindings=(left[0].binding_id,right[0].binding_id),coverage='COMPLETE'))
                limitations=('Trade working-capital stocks only; cash direction is not operating cash flow.',)
            else:
                opening=sum((x[2] for x in a),Decimal(0));closing=sum((x[2] for x in b),Decimal(0))
                if d:
                    da=ordered([x for x in d if x[1].period.start.year==oy],oy,True)
                    db=ordered([x for x in d if x[1].period.start.year==cy],cy,True)
                    if len(da)+len(db)!=len(d):
                        raise ValueError('Extra component periods')
                    for left,right in zip(da,db):
                        q=qualify_bridge_contexts(self.contexts,family,left[0].binding_id,right[0].binding_id)
                        if q.outcome!='PARTIALLY_QUALIFIED' or q.gaps!=('PARTIAL_COVERAGE',) or left[1].segment_scope!='SELECTED_CUSTOMER_PRODUCT':
                            raise ValueError('Selected-population comparability unqualified')
                        qualifications.append(q.assessment_id)
                    amount=sum((x[2] for x in db),Decimal(0))-sum((x[2] for x in da),Decimal(0))
                    components.append(Component(kind='SELECTED_POPULATION_MOVEMENT',amount=amount,coverage='PARTIAL',
                        input_bindings=tuple(x[0].binding_id for x in da+db)))
                limitations=('Selected detail is nonrandom and partial; no extrapolation or causal price/cost/mix attribution.',
                    'Residual is unexplained at this contract boundary, not an allocated component.')
            residual=closing-opening-sum((c.amount for c in components),Decimal(0))
        bridge=EconomicBridge(client_id=self.contexts.client_id,run_id=self.contexts.run_id,family=family,metric=metric,
            opening_year=oy,closing_year=cy,opening=opening,closing=closing,components=tuple(components),residual=residual,
            opening_bindings=tuple(x[0].binding_id for x in a),closing_bindings=tuple(x[0].binding_id for x in b),
            qualification_ids=tuple(qualifications),limitations=limitations)
        return BridgeAssessment(family=family,status='QUALIFIED',bridge=bridge)


def pack_binding_groups(contexts, captured, family, years):
    """Select explicit contract inputs, never manufacture missing measurements."""
    metric={'REVENUE_BRIDGE':{'financial_revenue'},'MARGIN_OR_PROFIT_BRIDGE':{'contribution_0'},
            'WORKING_CAPITAL_BRIDGE':{'bs_accounts_receivable','bs_inventory','bs_accounts_payable'}}.get(family,set())
    groups=[[],[],[]]
    for c in captured:
        if c.metric not in metric or c.period.start is None:continue
        if family=='WORKING_CAPITAL_BRIDGE' and c.period.start.month!=12:continue
        if c.segment_scope=='LEGAL_ENTITY' and c.period.start.year in years:
            groups[years.index(c.period.start.year)].append(contexts.lookup(c.origin).binding_id)
        elif c.segment_scope=='SELECTED_CUSTOMER_PRODUCT':groups[2].append(contexts.lookup(c.origin).binding_id)
    return tuple(tuple(x) for x in groups)
