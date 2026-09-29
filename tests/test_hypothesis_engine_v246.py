"""Adversarial class-scoped reasoning using unchanged canonical/graph writers."""
import unittest
from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError
from profit_doctor.persistence import hypothesis_schema as tables
from profit_doctor.reasoning.hypothesis.service import HypothesisService
from profit_doctor.reasoning.hypothesis.contracts import Hypothesis, Interpretation
from profit_doctor.reasoning.hypothesis.registry import REGISTRY
from profit_doctor.reasoning.domain.contracts import ReasoningObject
from profit_doctor.reasoning.domain.service import ScopeError, RevisionConflict
from tests import test_evidence_graph_v245 as fixtures


class HypothesisEngineV246(unittest.TestCase):
    target_url = fixtures.EvidenceGraphV245.target_url
    prepare_target = fixtures.EvidenceGraphV245.prepare_target
    signal = fixtures.EvidenceGraphV245.signal
    fact = fixtures.EvidenceGraphV245.fact

    def setUp(self):
        fixtures.EvidenceGraphV245.setUp(self)
        self.h = HypothesisService(self.session, 'c1', 'r1', self.actor, self.source)

    def margin(self, sid, roots=('a',), **changes):
        fields = dict(test='GM-01', typ='CONTRIBUTION_MARGIN_CHANGE', entity=None, entity_id=None,
            observed='27', comparison='31', variance='-4', unit='PERCENTAGE_POINTS',
            period_from='2026-01-01', period_to='2026-02-28')
        fields.update(changes)
        return self.fact(sid, roots, **fields)

    def origin(self):
        fact = self.margin('origin')
        finding_id = self.service.assess(fact.object_id).finding_id
        hypotheses = {h.contract_key: h for h in self.h.generate(finding_id)}
        return fact, finding_id, hypotheses

    def test_classes_roles_and_round_trip(self):
        fact, finding, group = self.origin()
        self.assertEqual(6,len(group))
        self.assertEqual({'EVIDENCE_QUALITY','ECONOMIC_MECHANISM','NULL_OR_ALTERNATIVE'}, {h.hypothesis_class for h in group.values()})
        self.assertEqual({'PRIMARY','ALTERNATIVE','NULL'}, {h.role for h in group.values()})
        self.assertEqual(6,len({h.object_id for h in group.values()}))
        for h in group.values():
            self.assertEqual(h,Hypothesis.from_json(h.to_json()))
            self.assertEqual('r1',h.run_id)
            self.assertEqual(fact.scope,h.scope)

    def test_generation_is_idempotent(self):
        _,finding,group=self.origin()
        self.assertEqual(set(h.object_id for h in group.values()),set(h.object_id for h in self.h.generate(finding)))
        self.assertEqual(6,len(list(self.session.scalars(select(tables.hypothesis.c.object_id)))))

    def test_independent_quality_supported_mechanisms_unresolved_same_finding(self):
        _,_,group=self.origin()
        self.margin('independent',('b',))
        quality=self.h.assess(group['INDEPENDENT_CORROBORATION'].object_id)
        self.assertEqual('SUPPORTED',quality.outcome)
        self.assertEqual('EVIDENCE_QUALITY',quality.hypothesis_class)
        self.assertEqual(set(REGISTRY['INDEPENDENT_CORROBORATION'].disconfirmation),set(quality.checks))
        self.assertEqual({'PASS'},set(quality.checks.values()))
        for key in ('MARGIN_PRICING','MARGIN_COST','MARGIN_MIX'):
            value=self.h.assess(group[key].object_id)
            self.assertEqual('UNRESOLVED',value.outcome)
            self.assertEqual('ECONOMIC_MECHANISM',value.hypothesis_class)
            self.assertTrue(value.gaps)
            self.assertTrue(all(g.blocks=='BOTH' for g in value.gaps))
        self.assertEqual('SUPPORTED',self.h.get(quality.hypothesis_id).status)

    def test_shared_ancestry_is_not_independent_confirmation(self):
        _,_,group=self.origin()
        self.margin('same1'); self.margin('same2')
        self.assertEqual('PLAUSIBLE',self.h.assess(group['INDEPENDENT_CORROBORATION'].object_id).outcome)
        self.assertEqual('SUPPORTED',self.h.assess(group['SHARED_CORROBORATION'].object_id).outcome)

    def test_independent_reproduction_disconfirms_all_shared_proposition(self):
        _,_,group=self.origin(); self.margin('other',('b',))
        value=self.h.assess(group['SHARED_CORROBORATION'].object_id)
        self.assertEqual('CONTRADICTED',value.outcome)
        self.assertTrue(value.contradictory)

    def test_unlinked_counter_evidence_prevents_cherry_picked_support(self):
        _,_,group=self.origin()
        self.margin('match',('b',)); dissent=self.margin('dissent',('c',),observed='28',variance='-3')
        value=self.h.assess(group['INDEPENDENT_CORROBORATION'].object_id)
        self.assertEqual('CONTRADICTED',value.outcome)
        self.assertIn(dissent.object_id,value.contradictory)
        self.assertTrue(value.supporting)

    def test_reassessment_overturns_plausible_and_preserves_history(self):
        _,_,group=self.origin(); self.margin('same')
        h=group['INDEPENDENT_CORROBORATION']
        first=self.h.assess(h.object_id)
        self.assertEqual('PLAUSIBLE',first.outcome)
        self.margin('counter',('b',),observed='28',variance='-3')
        with self.assertRaises(RevisionConflict): self.h.assess(h.object_id)
        second=self.h.assess(h.object_id,expected_revision=2)
        self.assertEqual('CONTRADICTED',second.outcome)
        self.assertEqual((first,second),self.h.history(h.object_id))
        with self.assertRaises(RevisionConflict): self.h.assess(h.object_id,expected_revision=2)

    def test_replay_adds_no_audits_or_revisions(self):
        _,_,group=self.origin(); self.margin('other',('b',))
        first=self.h.assess(group['INDEPENDENT_CORROBORATION'].object_id)
        audits=self.h.foundation.audit_events(object_id=first.object_id)
        self.assertEqual(first,self.h.assess(first.hypothesis_id))
        self.assertEqual(audits,self.h.foundation.audit_events(object_id=first.object_id))
        self.assertEqual(1,len(self.h.history(first.hypothesis_id)))

    def test_management_assertion_only_never_verifies_mechanism(self):
        fact,_,group=self.origin()
        context=self.service.foundation.create_object(ReasoningObject(client_id='c1',run_id='r1',object_type='SIGNAL',source_authority='MANAGEMENT_ASSERTION'))
        self.graph.link(context.object_id,fact.object_id,'CONTEXTUALISES','Management claims competitor discounting')
        value=self.h.assess(group['MARGIN_PRICING'].object_id)
        self.assertEqual('UNRESOLVED',value.outcome)
        self.assertIn(context.object_id,value.contextual)
        self.assertEqual('MANAGEMENT_ASSERTION',self.service.foundation.get_object(context.object_id).source_authority)

    def test_management_challenge_is_searched_even_with_matching_sources(self):
        fact,_,group=self.origin(); self.margin('other',('b',))
        context=self.service.foundation.create_object(ReasoningObject(client_id='c1',run_id='r1',object_type='SIGNAL',source_authority='MANAGEMENT_ASSERTION'))
        self.graph.link(context.object_id,fact.object_id,'CONTRADICTS','Management contests captured period')
        value=self.h.assess(group['INDEPENDENT_CORROBORATION'].object_id)
        self.assertEqual('UNRESOLVED',value.outcome)
        self.assertEqual('GAP',value.checks['COUNTER_EVIDENCE'])

    def test_unknown_dates_do_not_establish_temporal_null(self):
        fact,_,group=self.origin()
        other=self.margin('other',('b',),period_from=None,period_to=None)
        self.graph.link(other.object_id,fact.object_id,'SUPPORTS','Explicit comparison claim')
        value=self.h.assess(group['TEMPORAL_NULL'].object_id)
        self.assertEqual('UNRESOLVED',value.outcome)
        self.assertTrue(any(g.kind=='INCOMPARABLE_PERIODS' for g in value.gaps))

    def test_later_evidence_supports_temporal_null_not_causal_direction(self):
        fact,_,group=self.origin()
        other=self.margin('later',('b',),period_from='2026-03-01',period_to='2026-04-30')
        self.graph.link(other.object_id,fact.object_id,'SUPPORTS','Claimed reproduction with different periods')
        value=self.h.assess(group['TEMPORAL_NULL'].object_id)
        self.assertEqual('SUPPORTED',value.outcome)
        self.assertEqual('NULL_OR_ALTERNATIVE',value.hypothesis_class)
        self.assertEqual('UNRESOLVED',self.h.assess(group['MARGIN_PRICING'].object_id).outcome)

    def test_same_period_disconfirms_temporal_null(self):
        fact,_,group=self.origin(); other=self.margin('other',('b',))
        self.graph.link(other.object_id,fact.object_id,'SUPPORTS','Same exact captured period')
        self.assertEqual('CONTRADICTED',self.h.assess(group['TEMPORAL_NULL'].object_id).outcome)

    def test_missing_evidence_does_not_invalidate_condition(self):
        _,finding,group=self.origin()
        for h in group.values(): self.assertEqual('UNRESOLVED',self.h.assess(h.object_id).outcome)
        self.assertEqual('FINDING_CREATED',self.service.get_finding(finding).assessment.outcome)

    def test_partial_and_unknown_ancestry_block_support(self):
        _,_,group=self.origin(); self.margin('good',('b',)); self.margin('partial',('c',),eligibility='PARTIAL-A')
        value=self.h.assess(group['INDEPENDENT_CORROBORATION'].object_id)
        self.assertEqual('UNRESOLVED',value.outcome)
        self.assertEqual('GAP',value.checks['LINEAGE'])

    def test_invalidated_origin_does_not_remain_supported(self):
        fact,_,group=self.origin(); self.margin('other',('b',))
        h=group['INDEPENDENT_CORROBORATION']; self.h.assess(h.object_id)
        self.service.invalidate(fact.object_id,'Corrected evidence')
        self.assertEqual('UNRESOLVED',self.h.assess(h.object_id,expected_revision=2).outcome)

    def test_scope_is_not_broadened_by_other_customer_product_evidence(self):
        _,_,group=self.origin()
        self.fact('product',('b',),test='GM-04',typ='PRODUCT_MARGIN_VARIANCE',entity='PRODUCT',entity_id='p1',
            observed='27',comparison='31',variance='-4',unit='PERCENTAGE_POINTS',period_from='2026-01-01',period_to='2026-02-28')
        self.assertEqual('UNRESOLVED',self.h.assess(group['INDEPENDENT_CORROBORATION'].object_id).outcome)

    def test_foreign_client_and_run_rejected(self):
        _,finding,group=self.origin()
        with self.assertRaises(ScopeError): HypothesisService(self.session,'c1','r2',self.actor,self.source)
        other=HypothesisService(self.session,'c1','r3',self.actor,self.source)
        with self.assertRaises(ScopeError): other.get(group['MARGIN_MIX'].object_id)
        with self.assertRaises(ScopeError): other.generate(finding)

    def test_contract_and_class_cannot_be_rewritten(self):
        _,_,group=self.origin()
        h=group['INDEPENDENT_CORROBORATION']
        for changes in ({'hypothesis_class':'ECONOMIC_MECHANISM'},{'contract_key':'UNKNOWN'},{'proposition':'ROOT_CAUSE_ESTABLISHED'}):
            with self.assertRaises(ValueError): Hypothesis.from_json(h.model_copy(update=changes).to_json())

    def test_support_requires_disconfirmation_and_class_preservation(self):
        _,_,group=self.origin(); self.margin('other',('b',))
        value=self.h.assess(group['INDEPENDENT_CORROBORATION'].object_id)
        for changes in ({'checks':{}},{'hypothesis_class':'ECONOMIC_MECHANISM'},{'supporting':()}):
            with self.assertRaises(ValueError): Interpretation.from_json(value.model_copy(update=changes).to_json())

    def test_caller_transaction_rollback_and_read(self):
        _,_,group=self.origin(); self.margin('other',('b',))
        self.session.commit()
        value=self.h.assess(group['INDEPENDENT_CORROBORATION'].object_id)
        self.session.rollback()
        self.assertEqual((),self.h.history(value.hypothesis_id))
        value=self.h.assess(value.hypothesis_id); self.session.commit()
        with self.factory() as session:
            other=HypothesisService(session,'c1','r1',self.actor,self.source)
            self.assertEqual((value,),other.history(value.hypothesis_id))

    def test_database_fk_and_revision_uniqueness(self):
        _,_,group=self.origin(); value=self.h.assess(group['MARGIN_MIX'].object_id)
        row=dict(object_id=value.object_id,revision=1,client_id='c1',hypothesis_id=value.hypothesis_id,document=value.to_json())
        with self.assertRaises(IntegrityError),self.session.begin_nested(): self.session.execute(insert(tables.interpretation).values(**row))
        row.update(revision=2,hypothesis_id='missing')
        with self.assertRaises(IntegrityError),self.session.begin_nested(): self.session.execute(insert(tables.interpretation).values(**row))

    def test_payload_loss_is_not_silently_reconstructed(self):
        _,finding,group=self.origin()
        self.session.execute(tables.hypothesis.delete())
        with self.assertRaises(IntegrityError),self.session.begin_nested(): self.h.generate(finding)

    def test_revenue_and_concentration_findings_are_covered(self):
        for test,typ,unit,entity,eid,obs,comp,var in (
            ('REV-01','COMPARABLE_REVENUE_CHANGE','GBP',None,None,'120','100','20'),
            ('CUS-01','TOP_CUSTOMER_CONCENTRATION','PERCENT','CUSTOMER','c','25',None,None)):
            fact=self.fact(test,test=test,typ=typ,unit=unit,entity=entity,entity_id=eid,observed=obs,comparison=comp,variance=var)
            finding=self.service.assess(fact.object_id).finding_id
            self.assertEqual(3,len(self.h.generate(finding)))

    def test_pricing_cost_false_positive_remains_explicit_evidence_gap(self):
        _,_,group=self.origin()
        self.fact('price',test='REV-04',typ='PRICE_EFFECT',entity=None,entity_id=None,
            observed='-40',comparison=None,variance=None)
        self.fact('cost',('b',),test='SUP-02',typ='PURCHASE_PRICE_VARIANCE',unit='GBP_PER_UNIT',
            entity='SUPPLIER_ITEM',entity_id='supplier|item',observed='2',comparison='40',variance=None)
        for key in ('MARGIN_PRICING','MARGIN_COST'):
            value=self.h.assess(group[key].object_id)
            self.assertEqual('UNRESOLVED',value.outcome)
            self.assertTrue(any('comparab' in g.missing_evidence.lower() for g in value.gaps))

    def test_mix_and_stable_segment_margin_do_not_repair_segmentation(self):
        _,_,group=self.origin()
        self.fact('mix',test='PROD-02',typ='PRODUCT_MIX_SHIFT',unit='PERCENTAGE_POINTS',entity='PRODUCT',entity_id='p',
            observed='40',comparison='20',variance='20')
        self.fact('stable',test='GM-04',typ='PRODUCT_MARGIN_VARIANCE',unit='PERCENTAGE_POINTS',entity='PRODUCT',entity_id='p',
            observed='30',comparison='30',variance='0')
        for key in ('MARGIN_PRICING','MARGIN_MIX'):
            value=self.h.assess(group[key].object_id)
            self.assertEqual('UNRESOLVED',value.outcome)
            self.assertTrue(any('segment' in g.missing_evidence.lower() for g in value.gaps))

    def test_supported_primary_does_not_eliminate_plausible_alternative(self):
        origin=self.margin('origin',('a','b'))
        finding=self.service.assess(origin.object_id).finding_id
        group={h.contract_key:h for h in self.h.generate(finding)}
        self.margin('partial',('b','c')); self.margin('independent',('d',))
        self.assertEqual('SUPPORTED',self.h.assess(group['INDEPENDENT_CORROBORATION'].object_id).outcome)
        alt=self.h.assess(group['SHARED_CORROBORATION'].object_id)
        self.assertEqual('PLAUSIBLE',alt.outcome)
        self.assertIn(group['INDEPENDENT_CORROBORATION'].object_id,alt.alternatives)

    def test_incomplete_origin_ancestry_blocks_temporal_support(self):
        fact,_,group=self.origin()
        other=self.margin('later',('b',),period_from='2026-03-01',period_to='2026-04-30')
        self.graph.link(other.object_id,fact.object_id,'SUPPORTS','Claimed temporal comparison')
        self.legacy.execute("UPDATE source_file SET immutable_flag=0 WHERE source_file_id='fa'")
        value=self.h.assess(group['TEMPORAL_NULL'].object_id)
        self.assertEqual('UNRESOLVED',value.outcome)
        self.assertEqual('GAP',value.checks['LINEAGE'])

    def test_corrupted_snapshot_rejected_on_read(self):
        import json
        _,_,group=self.origin()
        value=self.h.assess(group['MARGIN_MIX'].object_id)
        data=json.loads(value.to_json()); data['evidence_snapshot']['facts']=[]
        self.session.execute(tables.interpretation.update().where(tables.interpretation.c.object_id==value.object_id).values(document=json.dumps(data)))
        with self.assertRaises(ScopeError): self.h.history(value.hypothesis_id)

    def test_decimal_equality_and_snapshot_precision_are_both_preserved(self):
        original=self.margin('origin',observed='27.00000000000000000001',comparison='31.00',variance='-3.99999999999999999999')
        finding=self.service.assess(original.object_id).finding_id
        group={h.contract_key:h for h in self.h.generate(finding)}
        self.margin('other',('b',),observed='27.0000000000000000000100',comparison='31',variance='-3.9999999999999999999900')
        value=self.h.assess(group['INDEPENDENT_CORROBORATION'].object_id)
        self.assertEqual('SUPPORTED',value.outcome)
        self.session.commit()
        retained=self.h.history(value.hypothesis_id)[0]
        self.assertEqual('27.00000000000000000001',retained.evidence_snapshot['origin_fact']['observed']['value'])
        self.assertEqual(value,retained)


if __name__ == '__main__': unittest.main()
