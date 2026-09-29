"""Adversarial opt-in Story qualification through frozen canonical writers."""
import unittest
from decimal import Decimal
from sqlalchemy import insert, select, text
from sqlalchemy.exc import IntegrityError
from profit_doctor.persistence import story_schema as tables
from profit_doctor.reasoning.story.service import StoryService
from profit_doctor.reasoning.story.contracts import Story, project
from profit_doctor.reasoning.story.registry import REGISTRY, DEFERRED, Resolution
from profit_doctor.reasoning.hypothesis.service import HypothesisService
from profit_doctor.reasoning.hypothesis.contracts import Interpretation
from profit_doctor.reasoning.domain.contracts import ReasoningObject, EconomicEffect
from profit_doctor.reasoning.domain.service import ScopeError, RevisionConflict
from tests import test_hypothesis_engine_v246 as fixtures


class EconomicStoryV247(unittest.TestCase):
    target_url = fixtures.HypothesisEngineV246.target_url
    prepare_target = fixtures.HypothesisEngineV246.prepare_target
    signal = fixtures.HypothesisEngineV246.signal
    fact = fixtures.HypothesisEngineV246.fact
    margin = fixtures.HypothesisEngineV246.margin

    def setUp(self):
        fixtures.HypothesisEngineV246.setUp(self)
        self.stories = StoryService(self.session,'c1','r1',self.actor,self.source)

    def prepare(self, *, roots=('b',), family='MARGIN_COMPRESSION', suffix='', run='r1', **changes):
        if family == 'MARGIN_COMPRESSION':
            fact = self.margin('origin'+suffix,run=run,**changes)
            self.margin('copy'+suffix,roots,run=run,**changes)
        else:
            fields = dict(test='CUS-01',typ='TOP_CUSTOMER_CONCENTRATION',entity='CUSTOMER',entity_id='customer-a',
                observed='30',comparison=None,variance=None,unit='PERCENT',period_from='2026-01-01',period_to='2026-02-28',run=run)
            fields.update(changes)
            fact = self.fact('origin'+suffix,**fields)
            self.fact('copy'+suffix,roots,**fields)
        finding = self.service.assess(fact.object_id).finding_id
        h = HypothesisService(self.session,'c1',run,self.actor,self.source)
        if finding and self.service.get_finding(finding).assessment.outcome == 'FINDING_CREATED':
            for hypothesis in h.generate(finding): h.assess(hypothesis.object_id)
        return fact, finding

    def create(self, **kwargs):
        _, finding = self.prepare(**kwargs)
        return self.stories.synthesise(kwargs.get('family','MARGIN_COMPRESSION'),finding).story

    def test_condition_supported_mechanism_unresolved(self):
        value=self.create()
        self.assertEqual('SUPPORTED',value.status)
        self.assertEqual('CONDITION_STORY',value.resolution)
        self.assertEqual('UNRESOLVED',value.mechanism_state)
        self.assertEqual({'UNRESOLVED'},{i.outcome for i in value.interpretations if i.hypothesis_class=='ECONOMIC_MECHANISM'})
        self.assertTrue(value.gaps)
        self.assertIn('Contribution 0',project(value)['condition'])
        self.assertNotIn('gross',str(project(value)))

    def test_concentration_only(self):
        value=self.create(family='CUSTOMER_CONCENTRATION_DEPENDENCY')
        self.assertEqual('CUSTOMER',value.scope.entity_type)
        self.assertEqual('Customer revenue concentration',project(value)['title'])
        self.assertEqual('UNRESOLVED',value.mechanism_state)

    def test_reserved_resolution_is_not_available(self):
        self.assertIn('MECHANISM_RESOLVED_STORY',list(Resolution))
        value=self.create()
        with self.assertRaises(ValueError): Story.from_json(value.model_copy(update={'resolution':'MECHANISM_RESOLVED_STORY'}).to_json())

    def test_quality_support_never_resolves_mechanism(self):
        value=self.create()
        self.assertTrue(any(i.hypothesis_class=='EVIDENCE_QUALITY' and i.outcome=='SUPPORTED' for i in value.interpretations))
        self.assertEqual('CONDITION_STORY',value.resolution)

    def test_fabricated_mechanism_support_rejected(self):
        value=self.create()
        mechanism=next(i for i in value.interpretations if i.hypothesis_class=='ECONOMIC_MECHANISM')
        with self.assertRaises(ValueError):
            Interpretation.from_json(mechanism.model_copy(update={'outcome':'SUPPORTED','gaps':(),
                'checks':dict.fromkeys(mechanism.checks,'PASS'),'supporting':value.fact_ids}).to_json())

    def test_shared_ancestry_does_not_create_story(self):
        _,finding=self.prepare(roots=('a',))
        self.assertEqual('NO_STORY',self.stories.synthesise('MARGIN_COMPRESSION',finding).outcome)

    def test_partial_overlap_does_not_create_story(self):
        a=self.margin('a',('a','b'));self.margin('b',('b','c'))
        finding=self.service.assess(a.object_id).finding_id
        for h in self.h.generate(finding):self.h.assess(h.object_id)
        self.assertEqual('NO_STORY',self.stories.synthesise('MARGIN_COMPRESSION',finding).outcome)

    def test_unknown_lineage_does_not_create_story(self):
        _,finding=self.prepare()
        self.legacy.execute("UPDATE source_file SET immutable_flag=0 WHERE source_file_id='fa'")
        with self.assertRaises(RevisionConflict): self.stories.synthesise('MARGIN_COMPRESSION',finding)

    def test_healthy_margin_improvement_finding_creates_no_story(self):
        _,finding=self.prepare(observed='35',variance='4')
        self.assertIsNotNone(finding)
        self.assertEqual('NO_STORY',self.stories.synthesise('MARGIN_COMPRESSION',finding).outcome)
        self.assertEqual([],list(self.session.scalars(select(tables.story.c.object_id))))

    def test_unrelated_findings_do_not_create_story(self):
        _,finding=self.prepare(family='CUSTOMER_CONCENTRATION_DEPENDENCY')
        self.assertEqual('NO_STORY',self.stories.synthesise('MARGIN_COMPRESSION',finding).outcome)

    def test_insignificant_condition_has_no_finding_or_story(self):
        _,finding=self.prepare(observed='30.5',variance='-.5')
        self.assertIsNone(finding)
        self.assertEqual([],list(self.session.scalars(select(tables.story.c.object_id))))

    def test_unknown_periods_no_story(self):
        _,finding=self.prepare(period_from=None,period_to=None)
        self.assertEqual('NO_STORY',self.stories.synthesise('MARGIN_COMPRESSION',finding).outcome)

    def test_period_mismatch_cannot_corroborate(self):
        fact=self.margin('a');self.margin('b',('b',),period_from='2026-03-01',period_to='2026-04-28')
        finding=self.service.assess(fact.object_id).finding_id
        for h in self.h.generate(finding):self.h.assess(h.object_id)
        self.assertEqual('NO_STORY',self.stories.synthesise('MARGIN_COMPRESSION',finding).outcome)

    def test_entity_mismatch_cannot_corroborate(self):
        fact=self.fact('a',test='CUS-01',typ='TOP_CUSTOMER_CONCENTRATION',observed='30',comparison=None,variance=None,unit='PERCENT',period_from='2026-01-01',period_to='2026-02-28')
        self.fact('b',('b',),test='CUS-01',typ='TOP_CUSTOMER_CONCENTRATION',observed='30',comparison=None,variance=None,unit='PERCENT',entity_id='other',period_from='2026-01-01',period_to='2026-02-28')
        finding=self.service.assess(fact.object_id).finding_id
        for h in self.h.generate(finding):self.h.assess(h.object_id)
        self.assertEqual('NO_STORY',self.stories.synthesise('CUSTOMER_CONCENTRATION_DEPENDENCY',finding).outcome)

    def test_unlinked_counter_evidence_prevents_story(self):
        self.margin('counter',('c',),observed='28',variance='-3')
        _,finding=self.prepare()
        self.assertEqual('NO_STORY',self.stories.synthesise('MARGIN_COMPRESSION',finding).outcome)

    def test_management_mitigation_is_retained_and_holds_existing_story(self):
        value=self.create()
        context=self.service.foundation.create_object(ReasoningObject(client_id='c1',run_id='r1',object_type='SIGNAL',source_authority='MANAGEMENT_ASSERTION'))
        self.graph.link(context.object_id,value.fact_ids[0],'MITIGATES','Unverified management explanation')
        for h in self.h.generate(value.finding_id):self.h.assess(h.object_id,expected_revision=h.revision)
        revised=self.stories.synthesise(value.contract_key,value.finding_id,expected_revision=value.revision).story
        self.assertEqual('INVESTIGATING',revised.status)
        self.assertIn(context.object_id,revised.mitigating)

    def test_replay_no_duplicate_history_or_audits(self):
        value=self.create()
        audits=self.stories.foundation.audit_events(object_id=value.object_id)
        replay=self.stories.synthesise(value.contract_key,value.finding_id)
        self.assertEqual('REPLAYED',replay.outcome)
        self.assertEqual(value,replay.story)
        self.assertEqual((value,),self.stories.history(value.object_id))
        self.assertEqual(audits,self.stories.foundation.audit_events(object_id=value.object_id))

    def test_decimal_serialization_and_persistence(self):
        value=self.create(observed='27.00000000000000000001',variance='-3.99999999999999999999')
        self.assertEqual(Decimal('27.00000000000000000001'),value.measurements[0].value)
        self.assertEqual(value,Story.from_json(value.to_json()))
        self.session.commit()
        with self.factory() as session:
            read=StoryService(session,'c1','r1',self.actor,self.source).get(value.object_id)
            self.assertEqual(value,read)

    def test_caller_rollback_removes_story(self):
        value=self.create();self.session.rollback()
        with self.assertRaises(ScopeError):self.stories.get(value.object_id)

    def test_tenant_and_run_scope(self):
        value=self.create()
        with self.assertRaises(ScopeError):StoryService(self.session,'c1','r2',self.actor,self.source)
        with self.assertRaises(ScopeError):StoryService(self.session,'c2','r2',self.actor,self.source).get(value.object_id)

    def test_foreign_key_rejects_missing_endpoint(self):
        with self.assertRaises(IntegrityError),self.session.begin_nested():
            self.session.execute(insert(tables.story).values(object_id='missing',client_id='c1',finding_id='missing',revision=1,document='{}'))

    def test_deferred_and_unknown_families_rejected(self):
        self.assertEqual(2,len(REGISTRY));self.assertEqual(3,len(DEFERRED))
        for key in (*DEFERRED,'UNKNOWN'):
            with self.assertRaises(ValueError):self.stories.synthesise(key,'missing')

    def test_effect_reference_reused_without_amounts(self):
        _,finding=self.prepare()
        effect=self.stories.foundation.create_effect(EconomicEffect(client_id='c1',run_id='r1'))
        value=self.stories.synthesise('MARGIN_COMPRESSION',finding,effect_ids=(effect.effect_id,)).story
        self.assertEqual((effect.effect_id,),value.effect_ids)
        self.assertIsNone(value.materiality.absolute_economic_magnitude)

    def test_stale_interpretation_requires_explicit_reassessment(self):
        value=self.create();self.margin('new-counter',('c',),observed='28',variance='-3')
        with self.assertRaises(RevisionConflict):self.stories.synthesise(value.contract_key,value.finding_id,expected_revision=1)

    def test_healthy_estate_multiple_findings_still_no_story(self):
        _,margin=self.prepare(observed='35',variance='4')
        _,concentration=self.prepare(family='CUSTOMER_CONCENTRATION_DEPENDENCY',suffix='customer',roots=('a',))
        for family,finding in [('MARGIN_COMPRESSION',margin),('CUSTOMER_CONCENTRATION_DEPENDENCY',concentration)]:
            for h in self.h.generate(finding): self.h.assess(h.object_id,expected_revision=h.revision)
            self.assertEqual('NO_STORY',self.stories.synthesise(family,finding).outcome)
        self.assertEqual([],list(self.session.scalars(select(tables.story.c.object_id))))

    def test_partial_eligibility_does_not_create_story(self):
        _,finding=self.prepare(eligibility='PARTIAL-A')
        self.assertIsNone(finding)
        self.assertEqual([],list(self.session.scalars(select(tables.story.c.object_id))))

    def test_shared_and_independent_characteristics_remain_separate(self):
        self.margin('shared',('a',))
        value=self.create()
        self.assertEqual({'SAME_ANCESTRY','INDEPENDENT'},{c.independence for c in value.evidence_characteristics.values()})
        self.assertEqual(2,len(value.fact_ids))

    def test_missing_history_rejected(self):
        value=self.create()
        self.session.execute(tables.story_revision.delete())
        with self.assertRaises(ScopeError):self.stories.synthesise(value.contract_key,value.finding_id)

    def test_cross_client_effect_rejected(self):
        _,finding=self.prepare()
        from profit_doctor.reasoning.domain.service import FoundationService
        effect=FoundationService(self.session,'c2',self.actor).create_effect(EconomicEffect(client_id='c2',run_id='r2'))
        with self.assertRaises(ScopeError):self.stories.synthesise('MARGIN_COMPRESSION',finding,effect_ids=(effect.effect_id,))

    def test_story_payload_cannot_relabel_measurement(self):
        value=self.create()
        changed=value.measurements[0].model_copy(update={'metric':'gross_profit_margin'})
        with self.assertRaises(ValueError):Story.from_json(value.model_copy(update={'measurements':(changed,*value.measurements[1:])}).to_json())

    def test_story_revision_compare_and_swap(self):
        value=self.create()
        with self.assertRaises(RevisionConflict):self.stories.synthesise(value.contract_key,value.finding_id,expected_revision=2)

    def test_repeated_period_does_not_imply_persistence(self):
        first=self.create()
        self.legacy.execute("INSERT INTO engine_run VALUES ('r3','c1','BASELINE',?,NULL,'COMPLETED',NULL,NULL,'2.47')",('2026-10-28T00:00:00+00:00',))
        _,finding=self.prepare(suffix='r3',run='r3')
        value=StoryService(self.session,'c1','r3',self.actor,self.source).synthesise('MARGIN_COMPRESSION',finding,expected_revision=1).story
        self.assertEqual(first.object_id,value.object_id)
        self.assertEqual('NOT_COMPARABLE',value.transition)
        self.assertEqual('SUPPORTED',value.status)

    def test_longitudinal_improvement_resolution_and_reopening(self):
        first=self.create()
        previous=first
        for run,start,end,observed,variance,status in [
                ('r3','2026-03-01','2026-04-28','29','-2','IMPROVING'),
                ('r4','2026-05-01','2026-06-28','31','0','RESOLVED'),
                ('r5','2026-07-01','2026-08-28','27','-4','SUPPORTED'),
                ('r6','2026-09-01','2026-10-29','27','-4','PERSISTENT'),
                ('r7','2026-11-01','2026-12-29','25','-6','WORSENING')]:
            if run!='r3':
                self.session.execute(text("INSERT INTO engine_run (run_id,client_id,run_type,started_at,status,engine_version) VALUES (:r,'c1','BASELINE',:t,'COMPLETED','2.47')"),{'r':run,'t':f'2027-0{int(run[1:])-3}-28T00:00:00+00:00'})
            self.legacy.execute("INSERT INTO engine_run VALUES (?,'c1','BASELINE',?,NULL,'COMPLETED',NULL,NULL,'2.47')",(run,'2026-10-28T00:00:00+00:00'))
            _,finding=self.prepare(suffix=run,run=run,period_from=start,period_to=end,observed=observed,variance=variance)
            service=StoryService(self.session,'c1',run,self.actor,self.source)
            value=service.synthesise('MARGIN_COMPRESSION',finding,expected_revision=previous.revision).story
            self.assertEqual(first.object_id,value.object_id)
            self.assertEqual(status,value.status)
            if run=='r5': self.assertEqual('REOPENED',value.transition)
            if run=='r4': self.assertIn('absent',project(value)['condition'])
            previous=value
        self.assertEqual(6,len(service.history(value.object_id)))


if __name__=='__main__':unittest.main()
