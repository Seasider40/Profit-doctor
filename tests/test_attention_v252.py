"""Governed production service routes; no direct positive priority persistence."""
import json
import unittest
from sqlalchemy import select, update
from profit_doctor.persistence import priority_schema as tables
from profit_doctor.reasoning.attention.contracts import AttentionEvidence
from profit_doctor.reasoning.attention.service import AttentionPriorityService
from profit_doctor.reasoning.domain.contracts import ConfidenceProfile, ReasoningObject
from profit_doctor.reasoning.domain.service import ScopeError, RevisionConflict
from profit_doctor.reasoning.priority.service import PriorityService
from tests import test_hypothesis_engine_v246 as fixtures
from tests.test_priority_v251 import request


class AttentionV252(unittest.TestCase):
    target_url = fixtures.HypothesisEngineV246.target_url
    prepare_target = fixtures.HypothesisEngineV246.prepare_target
    signal = fixtures.HypothesisEngineV246.signal
    fact = fixtures.HypothesisEngineV246.fact
    margin = fixtures.HypothesisEngineV246.margin
    origin = fixtures.HypothesisEngineV246.origin

    def setUp(self):
        fixtures.HypothesisEngineV246.setUp(self)
        self.attention = AttentionPriorityService(self.service, 'r1')
        self.anchor, self.finding, self.group = self.origin()

    def qualify(self):
        h = self.h.get(self.group['INDEPENDENT_CORROBORATION'].object_id)
        return self.h.assess(h.object_id, expected_revision=h.revision)

    def assess(self, **kwargs):
        return self.attention.assess('FINDING', self.finding, **kwargs)

    def test_independent_supported_quality_is_strong_not_high_priority(self):
        self.margin('independent', ('b',))
        interpretation = self.qualify()
        value = self.assess()
        self.assertEqual('STRONG', value.result.basis.evidence_strength.state)
        self.assertEqual('INSUFFICIENT_EVIDENCE', value.result.classification)
        self.assertEqual(ConfidenceProfile(), value.result.basis.confidence)
        for name in ('materiality','urgency','controllability','persistence'):
            self.assertEqual('NOT_ASSESSED', getattr(value.result.basis, name).state)
        self.assertIn(interpretation.object_id, value.result.basis.evidence_strength.evidence)
        self.assertEqual(value, self.attention.get(value.subject_id, current=True))

    def test_five_shared_sources_do_not_uplift(self):
        for n in range(5):
            self.margin('shared'+str(n))
        self.qualify()
        self.assertEqual('NOT_ASSESSED', self.assess().result.basis.evidence_strength.state)

    def test_counter_evidence_preserved(self):
        self.margin('match', ('b',))
        counter = self.margin('counter', ('c',), observed='28', variance='-3')
        interpretation = self.qualify()
        value = self.assess()
        self.assertEqual('CONFLICTED', value.result.basis.evidence_strength.state)
        self.assertIn(counter.object_id, value.result.basis.evidence_strength.evidence)
        self.assertTrue(interpretation.supporting)
        self.assertEqual('INSUFFICIENT_EVIDENCE', value.result.classification)

    def test_management_challenge_is_not_verified_fact(self):
        self.margin('match', ('b',))
        obj = self.service.foundation.create_object(ReasoningObject(client_id='c1',run_id='r1',
            object_type='SIGNAL', source_authority='MANAGEMENT_ASSERTION'))
        self.graph.link(obj.object_id, self.anchor.object_id, 'CONTRADICTS', 'Management challenge')
        self.qualify()
        self.assertEqual('CONFLICTED', self.assess().result.basis.evidence_strength.state)
        self.assertEqual('MANAGEMENT_ASSERTION', self.service.foundation.get_object(obj.object_id).source_authority)

    def test_unassessed_interpretation_is_not_automatically_assessed(self):
        self.margin('match', ('b',))
        self.assertEqual('NOT_ASSESSED', self.assess().result.basis.evidence_strength.state)
        self.assertEqual((), self.h.history(self.group['INDEPENDENT_CORROBORATION'].object_id))

    def test_new_evidence_invalidates_current_but_preserves_history(self):
        self.margin('match', ('b',)); self.qualify()
        old = self.assess()
        self.margin('counter', ('c',), observed='28', variance='-3')
        with self.assertRaises(RevisionConflict):
            self.attention.get(old.subject_id, current=True)
        self.assertEqual(old, self.attention.get(old.subject_id))
        changed = self.assess(expected_revision=1)
        self.assertEqual('NOT_ASSESSED', changed.result.basis.evidence_strength.state)
        self.assertIn('reassessment', changed.result.basis.evidence_strength.reason)
        self.assertEqual(1, len(self.h.history(self.group['INDEPENDENT_CORROBORATION'].object_id)))

    def test_machine_revision_never_rewrites_adviser_decision(self):
        first = self.assess()
        decision = self.attention.decide(first.subject_id, 1, request())
        self.margin('match', ('b',)); self.qualify()
        second = self.assess(expected_revision=1)
        self.assertEqual('STRONG', second.result.basis.evidence_strength.state)
        self.assertEqual(decision, self.attention.get_decision(first.subject_id))
        self.assertEqual(((first,second),(decision,)), self.attention.history(first.subject_id))
        self.assertTrue(self.attention.holding('REJECT')[0]['reassessed_since_decision'])

    def test_replay_preserves_revision_and_audit(self):
        self.margin('match', ('b',)); self.qualify()
        value = self.assess()
        audits = self.session.execute(select(tables.audit)).all()
        self.assertEqual(value, self.assess())
        self.assertEqual(audits, self.session.execute(select(tables.audit)).all())

    def test_frozen_default_service_rejects_positive_extension(self):
        self.margin('match', ('b',)); self.qualify()
        value = self.assess()
        with self.assertRaises(ScopeError):
            PriorityService(self.service, 'r1').get(value.subject_id)

    def test_old_priority_history_remains_readable(self):
        old = PriorityService(self.service, 'r1').assess('FINDING', self.finding)
        self.assertEqual(old, self.attention.get(old.subject_id))
        new = self.assess(expected_revision=1)
        self.assertEqual(2, new.revision)

    def test_forged_positive_dimension_is_rejected(self):
        value = self.assess()
        for dimension, state in [('urgency','HIGH'),('controllability','DIRECT'),('persistence','RECURRING'),('materiality','HIGH'),('evidence_strength','STRONG')]:
            payload = json.loads(value.to_json())
            payload['result']['basis'][dimension] = dict(state=state, evidence=['invented'], reason='forged')
            self.session.execute(update(tables.assessment).values(document=json.dumps(payload)))
            with self.assertRaises(ScopeError):
                self.attention.get(value.subject_id)
        self.session.execute(update(tables.assessment).values(document=value.to_json()))

    def test_partial_evidence_cannot_become_strong(self):
        self.margin('partial', ('b',), eligibility='PARTIAL-A')
        self.qualify()
        self.assertEqual('NOT_ASSESSED', self.assess().result.basis.evidence_strength.state)

    def test_incomplete_lineage_cannot_become_strong(self):
        self.margin('match', ('b',))
        self.legacy.execute("UPDATE source_file SET immutable_flag=0 WHERE source_file_id='fb'")
        self.qualify()
        self.assertEqual('NOT_ASSESSED', self.assess().result.basis.evidence_strength.state)

    def test_temporal_refusal_retains_missing_population_prerequisite(self):
        for n in range(4):
            self.margin('observation'+str(n), ('b',), period_from=f'202{n+2}-01-01', period_to=f'202{n+2}-02-28')
        value = self.assess()
        self.assertEqual('NOT_ASSESSED', value.result.basis.persistence.state)
        self.assertIn('population coverage', value.result.basis.persistence.reason)
        self.assertIn('dataset versions', value.result.basis.persistence.reason)
        self.assertNotIn('RECURRING', value.to_json())

    def test_shared_support_is_not_independent_support(self):
        self.margin('shared')
        self.h.assess(self.group['SHARED_CORROBORATION'].object_id)
        self.assertEqual('NOT_ASSESSED', self.assess().result.basis.evidence_strength.state)

    def test_no_automatic_mechanism_assessment(self):
        self.margin('match', ('b',)); self.qualify(); self.assess()
        for key in ('MARGIN_PRICING','MARGIN_COST','MARGIN_MIX'):
            self.assertEqual((), self.h.history(self.group[key].object_id))

    def test_policy_roundtrip_and_unknown_version(self):
        self.margin('match', ('b',))
        value = AttentionEvidence(interpretation=self.qualify())
        self.assertEqual(value, AttentionEvidence.from_json(value.to_json()))
        with self.assertRaises(ValueError):
            AttentionEvidence(policy='UNKNOWN')

    def test_caller_rollback_removes_assessment(self):
        value = self.assess()
        self.session.rollback()
        self.assertIsNone(self.session.scalar(select(tables.assessment.c.subject_id).where(tables.assessment.c.subject_id==value.subject_id)))

    def test_changed_origin_ancestry_requires_reassessment(self):
        self.margin('match', ('b',)); self.qualify()
        old = self.assess()
        self.legacy.execute("UPDATE source_file SET immutable_flag=0 WHERE source_file_id='fa'")
        with self.assertRaises(RevisionConflict):
            self.attention.get(old.subject_id, current=True)
        self.assertEqual(old, self.attention.get(old.subject_id))

    def test_cross_client_and_run_refused(self):
        from profit_doctor.reasoning.canonical.service import CanonicalService
        from profit_doctor.reasoning.canonical.source import LegacySignalSource
        other = CanonicalService(self.session, 'c2', self.actor, LegacySignalSource(self.legacy, 'c2'))
        with self.assertRaises(ScopeError):
            AttentionPriorityService(other, 'r2').assess('FINDING', self.finding)
        with self.assertRaises(ScopeError):
            AttentionPriorityService(self.service, 'r3').assess('FINDING', self.finding)

    def test_combined_dates_do_not_populate_measurement_context(self):
        from profit_doctor.reasoning.measurement.service import MeasurementContextService
        contexts = MeasurementContextService(self.session,'c1','r1',self.actor,self.legacy)
        context = contexts.backfill_fact_slot(self.anchor.object_id, 'observed')
        self.assertIsNotNone(self.anchor.scope.period_from)
        self.assertIsNone(context.period.start)
        self.assertIsNone(context.period.end)
        self.assertEqual('UNKNOWN', context.coverage)
        self.assertEqual('UNKNOWN_UNBOUND', context.revision_state)
        self.assertEqual('NOT_ASSESSED', self.assess().result.basis.persistence.state)

    def test_dataset_version_change_is_not_temporal_evidence(self):
        self.legacy.execute("UPDATE dataset_version SET version_number=99 WHERE dataset_version_id='va'")
        value = self.assess()
        self.assertEqual('NOT_ASSESSED', value.result.basis.persistence.state)

    def test_unknown_period_blocks_strong_corroboration(self):
        self.margin('unknown', ('b',), period_from=None, period_to=None)
        self.qualify()
        self.assertEqual('NOT_ASSESSED', self.assess().result.basis.evidence_strength.state)


class AttentionOpportunityV252(unittest.TestCase):
    from tests.test_priority_v251 import PriorityOpportunityV251 as fixtures
    target_url = fixtures.target_url
    prepare_target = fixtures.prepare_target
    setup_source = fixtures.setUp
    data = fixtures.data
    ingest = fixtures.ingest
    assess = fixtures.assess
    retain = fixtures.retain
    evidence = fixtures.evidence
    qualify = fixtures.qualify

    def setUp(self):
        self.setup_source()
        self.priority = AttentionPriorityService(self.priority.canonical, 'r1', self.service)

    def test_qualified_economics_preserved_dimensions_unknown(self):
        source = self.qualify()
        value = self.priority.assess('OPPORTUNITY', self.candidate.candidate_id)
        self.assertEqual((source.low,source.high,source.central),
            (value.result.basis.economic.low,value.result.basis.economic.high,value.result.basis.economic.central))
        self.assertEqual(value,self.priority.get(value.subject_id,current=True))
        for name in ('materiality','urgency','controllability','persistence','evidence_strength'):
            self.assertEqual('NOT_ASSESSED', getattr(value.result.basis,name).state)

    def test_unqualified_opportunity_still_refused(self):
        self.service.qualify(self.candidate.candidate_id)
        with self.assertRaises(ScopeError):
            self.priority.assess('OPPORTUNITY', self.candidate.candidate_id)


class GoldenAttentionV252(unittest.TestCase):
    # Reuse the approved repository workbook, never a private qualification key.
    from tests import test_receivables_v249 as fixtures
    target_url=fixtures.ReceivablesV249.target_url
    prepare_target=fixtures.ReceivablesV249.prepare_target
    setUp=fixtures.ReceivablesV249.setUp
    assess=fixtures.ReceivablesV249.assess

    def test_golden_source_does_not_invent_opportunity_or_priority(self):
        from sqlalchemy import func
        from profit_doctor.reasoning.canonical.service import CanonicalService
        from profit_doctor.reasoning.canonical.source import LegacySignalSource
        from profit_doctor.intake.declared_accounting import capture_pack
        from profit_doctor.intake.receivables import ReceivablesWorkbook
        from profit_doctor.reasoning.opportunity.service import OpportunityService
        from tests.test_receivables_v249 import WORKBOOK
        import hashlib
        before=hashlib.sha256(WORKBOOK.read_bytes()).hexdigest()
        provider=ReceivablesWorkbook()
        pack,_=capture_pack(self.contexts,WORKBOOK,self.directory/'store',providers=(provider,))
        snapshot=provider.capture(self.provider,pack,WORKBOOK,self.directory/'store',origin='BLIND_QUALIFICATION',ledger_id='trade-ar')
        impact=self.assess(snapshot)
        self.assertEqual(340000,impact.impact.amount.value)
        opportunities=OpportunityService(self.impacts)
        candidate=opportunities.create_candidate(impact.impact.impact_id,snapshot.as_of,90)
        assessment=opportunities.qualify(candidate.candidate_id)
        self.assertEqual('INSUFFICIENT_EVIDENCE',assessment.outcome)
        self.assertIsNone(assessment.opportunity_id)
        canonical=CanonicalService(self.session,'c1',self.contexts.actor,LegacySignalSource(self.legacy,'c1'))
        priority=AttentionPriorityService(canonical,'r1',opportunities)
        with self.assertRaises(ScopeError):priority.assess('OPPORTUNITY',candidate.candidate_id)
        self.assertEqual(0,self.session.scalar(select(func.count()).select_from(tables.assessment)))
        self.assertEqual(impact,self.impacts.get(impact.candidate_id,current=True))
        self.assertEqual(before,hashlib.sha256(WORKBOOK.read_bytes()).hexdigest())
