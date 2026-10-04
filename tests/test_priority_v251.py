"""Production unknowns, isolated positive domain scenarios and human authority."""
from decimal import Decimal
import unittest
from sqlalchemy import select, func, update
from sqlalchemy.exc import IntegrityError
from profit_doctor.persistence import priority_schema as tables
from profit_doctor.reasoning.canonical.service import CanonicalService
from profit_doctor.reasoning.canonical.source import LegacySignalSource
from profit_doctor.reasoning.domain.contracts import Actor
from profit_doctor.reasoning.domain.service import ScopeError, RevisionConflict
from profit_doctor.reasoning.priority.contracts import (
    PriorityBasis, Dimension, EconomicBasis, AdviserRequest, Assessment,
)
from profit_doctor.reasoning.priority.engine import evaluate
from profit_doctor.reasoning.priority.service import PriorityService
from tests import test_canonical_facts_findings_v244 as canonical_fixtures
from tests import test_opportunity_v250 as opportunity_fixtures


def dimension(state):
    return Dimension(state=state, evidence=('SYNTHETIC:qualified-domain-evidence',), reason='Explicit synthetic domain premise')


def synthetic(**changes):
    data = dict(origin='SYNTHETIC_QUALIFICATION', source_snapshot='Synthetic only; no production evidence provider',
        materiality=dimension('HIGH'), evidence_strength=dimension('STRONG'), urgency=dimension('LOW'),
        controllability=dimension('DIRECT'), persistence=dimension('RECURRING'),
        economic=EconomicBasis(kind='RECURRING_LEAKAGE', amount='50000', currency='GBP', dimension='PROFIT_PNL',
            evidence=('SYNTHETIC:annual-leakage',)))
    data.update(changes)
    return PriorityBasis(**data)


def request(key='decision-1', choice='REJECT', **changes):
    data = dict(request_id=key, choice=choice, actor=Actor(actor_type='HUMAN', actor_id='adviser-1',
        source_authority='HUMAN_FD_JUDGEMENT'), rationale='Commercial context reviewed', provenance='Authenticated adviser command')
    data.update(changes)
    return AdviserRequest(**data)


class PriorityDomainV251(unittest.TestCase):
    def test_large_weak_evidence_is_not_critical(self):
        b=synthetic(evidence_strength=dimension('WEAK'), economic=EconomicBasis(kind='EXPOSURE', amount='500000',
            currency='GBP', dimension='EXPOSURE', evidence=('SYNTHETIC:exposure',)))
        q=evaluate(b);self.assertEqual('INSUFFICIENT_EVIDENCE',q.classification)
        self.assertEqual(500000,q.basis.economic.amount)

    def test_smaller_recurring_leakage_high(self):
        q=evaluate(synthetic());self.assertEqual('HIGH',q.classification)
        self.assertEqual('MATERIAL_CONTINUING_CONDITION',q.rule)

    def test_historical_cost_not_automatically_high(self):
        q=evaluate(synthetic(persistence=dimension('HISTORICAL_ONLY'),economic=EconomicBasis(kind='HISTORICAL_COST',
            amount='150000',currency='GBP',dimension='PROFIT_PNL',evidence=('SYNTHETIC:one-off',))))
        self.assertEqual('LOW',q.classification)

    def test_urgent_cash_and_recurring_have_distinct_reasons(self):
        urgent=evaluate(synthetic(urgency=dimension('HIGH'),persistence=dimension('ISOLATED'),
            economic=EconomicBasis(kind='EXPOSURE',amount='20000',currency='GBP',dimension='CASH',evidence=('SYNTHETIC:deadline',))))
        recurring=evaluate(synthetic())
        self.assertEqual(('HIGH','HIGH'),(urgent.classification,recurring.classification))
        self.assertNotEqual(urgent.rule,recurring.rule);self.assertNotEqual(urgent.reasons,recurring.reasons)

    def test_critical_requires_explicit_critical_timing(self):
        self.assertEqual('CRITICAL',evaluate(synthetic(urgency=dimension('CRITICAL'))).classification)
        self.assertEqual('INSUFFICIENT_EVIDENCE',evaluate(synthetic(urgency=dimension('CRITICAL'),evidence_strength=dimension('CONFLICTED'))).classification)

    def test_external_control_does_not_invent_action(self):
        q=evaluate(synthetic(controllability=dimension('EXTERNAL')))
        self.assertEqual('EXTERNAL',q.basis.controllability.state)
        self.assertNotIn('action',q.model_dump());self.assertNotIn('decision',q.model_dump())

    def test_missing_data_is_not_zero(self):
        q=evaluate(PriorityBasis(origin='SYNTHETIC_QUALIFICATION',source_snapshot='missing',economic=EconomicBasis(kind='UNQUANTIFIED')))
        self.assertEqual('INSUFFICIENT_EVIDENCE',q.classification);self.assertIsNone(q.basis.economic.amount)
        self.assertEqual(5,len(q.gaps))

    def test_medium_rule_and_no_universal_score(self):
        q=evaluate(synthetic(materiality=dimension('MEDIUM'),urgency=dimension('MEDIUM')))
        self.assertEqual('MEDIUM',q.classification);self.assertNotIn('score',q.to_json())

    def test_enum_and_empty_evidence_rejected(self):
        with self.assertRaises(ValueError):synthetic(urgency=dimension('NOW'))
        with self.assertRaises(ValueError):Dimension(state='HIGH',reason='Claim without evidence')

    def test_financial_precision_and_no_false_central(self):
        b=synthetic(economic=EconomicBasis(kind='INDICATIVE_CAPTURE_RANGE',low='0.00000000000000000001',
            high='1.00000000000000000001',currency='GBP',dimension='CASH',evidence=('SYNTHETIC:range',),horizon_days=90))
        self.assertEqual(b,PriorityBasis.from_json(b.to_json()));self.assertIsNone(evaluate(b).basis.economic.central)
        with self.assertRaises(ValueError):EconomicBasis(kind='UNQUANTIFIED',amount='1',currency='GBP',evidence=('x',))

    def test_human_required_not_system_or_management_assertion(self):
        for actor in (Actor(actor_type='SYSTEM',source_authority='SYSTEM_DERIVED'),
                      Actor(actor_type='MANAGEMENT',source_authority='MANAGEMENT_ASSERTION',actor_id='manager')):
            with self.assertRaises(ValueError):request(actor=actor)

    def test_investigate_requires_questions_and_evidence(self):
        with self.assertRaises(ValueError):request(choice='INVESTIGATE')
        r=request(choice='INVESTIGATE',questions=('What is the timing consequence?',),required_evidence=('Dated liquidity evidence',))
        self.assertEqual('INVESTIGATE',r.choice)

    def test_blank_rationale_rejected(self):
        with self.assertRaises(ValueError):request(rationale=' ')

    def test_human_can_reject_synthetic_high_without_changing_priority(self):
        from profit_doctor.reasoning.priority.contracts import Decision
        q=evaluate(synthetic())
        d=Decision(subject_id='synthetic-subject',client_id='synthetic-client',revision=1,
            assessment_revision=1,request=request())
        self.assertEqual('HIGH',q.classification);self.assertEqual('REJECT',d.request.choice)
        self.assertEqual(q,evaluate(q.basis))

    def test_human_can_investigate_synthetic_medium(self):
        from profit_doctor.reasoning.priority.contracts import Decision
        q=evaluate(synthetic(materiality=dimension('MEDIUM'),urgency=dimension('MEDIUM')))
        d=Decision(subject_id='synthetic-subject',client_id='synthetic-client',revision=1,
            assessment_revision=1,request=request(choice='INVESTIGATE',questions=('What changed?',),required_evidence=('Reconciliation',)))
        self.assertEqual('MEDIUM',q.classification);self.assertEqual('INVESTIGATE',d.request.choice)


class PriorityFindingsV251(unittest.TestCase):
    target_url=canonical_fixtures.CanonicalV244.target_url
    prepare_target=canonical_fixtures.CanonicalV244.prepare_target
    signal=canonical_fixtures.CanonicalV244.signal
    revenue=canonical_fixtures.CanonicalV244.revenue

    def setUp(self):
        canonical_fixtures.CanonicalV244.setUp(self)
        self.fact=self.service.canonicalise(self.revenue()).fact
        self.finding_id=self.service.assess(self.fact.object_id).finding_id
        self.priority=PriorityService(self.service,'r1')

    def priority_assessment(self):return self.priority.assess('FINDING',self.finding_id)

    def test_canonical_measurements_not_loss_or_urgency(self):
        q=self.priority_assessment()
        self.assertEqual('INSUFFICIENT_EVIDENCE',q.result.classification)
        self.assertEqual('OBSERVED_MEASUREMENTS',q.result.basis.economic.kind)
        self.assertIsNone(q.result.basis.economic.amount);self.assertEqual(5,len(q.result.gaps))
        self.assertIn(self.fact.object_id,q.result.basis.source_snapshot)
        self.assertIsNone(self.priority.get_decision(q.subject_id))

    def test_replay_is_identical_and_audited_once(self):
        q=self.priority_assessment();self.assertEqual(q,self.priority_assessment())
        self.assertEqual(1,self.session.scalar(select(func.count()).select_from(tables.audit)))

    def test_reject_keeps_source_queryable(self):
        q=self.priority_assessment();original=self.service.get_finding(self.finding_id)
        d=self.priority.decide(q.subject_id,1,request())
        self.assertEqual(original,self.service.get_finding(self.finding_id));self.assertEqual(q,self.priority.get(q.subject_id))
        self.assertEqual(d,self.priority.holding('REJECT')[0]['decision'])

    def test_accept_does_not_promote_machine_evidence(self):
        q=self.priority_assessment();self.priority.decide(q.subject_id,1,request(choice='ACCEPT'))
        self.assertEqual(q,self.priority.get(q.subject_id));self.assertEqual(1,len(self.priority.holding('ACCEPT')))

    def test_investigate_persists_details(self):
        q=self.priority_assessment();r=request(choice='INVESTIGATE',questions=('Why?',),required_evidence=('Source evidence',))
        d=self.priority.decide(q.subject_id,1,r)
        self.assertEqual(r,self.priority.get_decision(q.subject_id).request)
        self.assertEqual(d,self.priority.holding('INVESTIGATE')[0]['decision'])

    def test_decision_replay_and_explicit_revision(self):
        q=self.priority_assessment();d=self.priority.decide(q.subject_id,1,request())
        self.assertEqual(d,self.priority.decide(q.subject_id,1,request()))
        with self.assertRaises(RevisionConflict):self.priority.decide(q.subject_id,1,request(choice='ACCEPT'))
        with self.assertRaises(RevisionConflict):self.priority.decide(q.subject_id,1,request('d2','ACCEPT'))
        changed=self.priority.decide(q.subject_id,1,request('d2','ACCEPT'),expected_revision=1)
        self.assertEqual(2,changed.revision);self.assertEqual(d,self.priority.get_decision(q.subject_id,1))
        self.assertEqual((),self.priority.holding('REJECT'))

    def test_reassessment_preserves_decision_and_old_evidence(self):
        q=self.priority_assessment();d=self.priority.decide(q.subject_id,1,request())
        other=self.service.canonicalise(self.revenue('other')).fact
        self.service.assess(self.fact.object_id,contradictory=(other.object_id,))
        with self.assertRaises(RevisionConflict):self.priority.get(q.subject_id,current=True)
        with self.assertRaises(RevisionConflict):self.priority_assessment()
        new=self.priority.assess('FINDING',self.finding_id,expected_revision=1)
        self.assertEqual('CONFLICTED',new.result.basis.evidence_strength.state)
        self.assertEqual(q,self.priority.get(q.subject_id,1));self.assertEqual(d,self.priority.get_decision(q.subject_id))
        self.assertTrue(self.priority.holding('REJECT')[0]['reassessed_since_decision'])
        self.assertEqual((2,1),tuple(map(len,self.priority.history(q.subject_id))))

    def test_stale_source_blocks_decision_but_not_history(self):
        q=self.priority_assessment();self.service.invalidate(self.fact.object_id,'Source correction')
        self.assertEqual(q,self.priority.get(q.subject_id))
        with self.assertRaises(RevisionConflict):self.priority.decide(q.subject_id,1,request())

    def test_unknown_source_kind_and_wrong_run_refused(self):
        with self.assertRaises(ScopeError):self.priority.assess('LEGACY',self.finding_id)
        with self.assertRaises(ScopeError):PriorityService(self.service,'r2')
        with self.assertRaises(ScopeError):PriorityService(self.service,'r3').assess('FINDING',self.finding_id)

    def test_scope_and_missing_endpoints_at_database(self):
        q=self.priority_assessment()
        with self.assertRaises(IntegrityError):
            with self.session.begin_nested():self.session.execute(update(tables.assessment).values(client_id='c2'))
        self.priority.decide(q.subject_id,1,request())
        with self.assertRaises(IntegrityError):
            with self.session.begin_nested():self.session.execute(update(tables.decision).values(assessment_revision=99))

    def test_caller_rollback(self):
        q=self.priority_assessment();self.priority.decide(q.subject_id,1,request());self.session.rollback()
        for table in (tables.subject,tables.assessment,tables.decision,tables.audit):
            self.assertEqual(0,self.session.scalar(select(func.count()).select_from(table)))

    def test_forged_synthetic_record_cannot_be_read(self):
        q=self.priority_assessment();forged=Assessment(**{**q.model_dump(),'result':evaluate(synthetic())})
        self.session.execute(update(tables.assessment).values(document=forged.to_json()))
        with self.assertRaises(ScopeError):self.priority.get(q.subject_id)

    def test_no_caller_basis_parameter(self):
        with self.assertRaises(TypeError):self.priority.assess('FINDING',self.finding_id,basis=synthetic())

    def test_held_item_retains_decision_and_flags_stale_source(self):
        q=self.priority_assessment();self.priority.decide(q.subject_id,1,request())
        self.service.invalidate(self.fact.object_id,'Correction')
        held=self.priority.holding('REJECT')[0]
        self.assertFalse(held['source_current']);self.assertEqual(q,held['assessment'])

    def test_cross_client_history_is_not_visible(self):
        q=self.priority_assessment()
        other=CanonicalService(self.session,'c2',self.actor,LegacySignalSource(self.legacy,'c2'))
        service=PriorityService(other,'r2')
        with self.assertRaises(ScopeError):service.get(q.subject_id)
        self.assertEqual((),service.holding('REJECT'))

    def test_database_revision_uniqueness(self):
        from sqlalchemy import insert
        q=self.priority_assessment();row=dict(self.session.execute(select(tables.assessment)).mappings().one())
        with self.assertRaises(IntegrityError):
            with self.session.begin_nested():self.session.execute(insert(tables.assessment).values(**row))

    def test_changed_signal_cannot_reuse_assessment(self):
        q=self.priority_assessment()
        self.legacy.execute("UPDATE signal SET observed_value='999' WHERE signal_id='s1'");self.legacy.commit()
        with self.assertRaises(RevisionConflict):self.priority.get(q.subject_id,current=True)
        self.assertEqual(q,self.priority.get(q.subject_id))

    def test_new_session_read_preserves_audit_and_decision(self):
        q=self.priority_assessment();d=self.priority.decide(q.subject_id,1,request());self.session.commit()
        with self.factory() as session:
            owner=CanonicalService(session,'c1',self.actor,self.source)
            service=PriorityService(owner,'r1')
            self.assertEqual(q,service.get(q.subject_id,current=True));self.assertEqual(d,service.get_decision(q.subject_id))
            self.assertEqual(2,session.scalar(select(func.count()).select_from(tables.audit)))

    def test_populated_downgrade_preserves_finding(self):
        from alembic import command
        from tests.test_postgresql_live_qualification_v218 import alembic_config
        q=self.priority_assessment();self.priority.decide(q.subject_id,1,request())
        self.session.commit();self.session.close()
        cfg=alembic_config(self.url.replace('%','%%'))
        command.downgrade(cfg,'0013_opportunity');command.upgrade(cfg,'head')
        self.assertEqual(self.finding_id,self.service.get_finding(self.finding_id).object_id)
        for table in (tables.subject,tables.assessment,tables.decision,tables.audit):
            self.assertEqual(0,self.session.scalar(select(func.count()).select_from(table)))


class PriorityOpportunityV251(unittest.TestCase):
    target_url=opportunity_fixtures.OpportunityV250.target_url
    prepare_target=opportunity_fixtures.OpportunityV250.prepare_target
    data=opportunity_fixtures.OpportunityV250.data
    ingest=opportunity_fixtures.OpportunityV250.ingest
    assess=opportunity_fixtures.OpportunityV250.assess
    evidence=opportunity_fixtures.OpportunityV250.evidence
    retain=opportunity_fixtures.OpportunityV250.retain
    qualify=opportunity_fixtures.OpportunityV250.qualify

    def setUp(self):
        opportunity_fixtures.OpportunityV250.setUp(self)
        canonical=CanonicalService(self.session,'c1',self.contexts.actor,LegacySignalSource(self.contexts.source.connection,'c1'))
        self.priority=PriorityService(canonical,'r1',self.service)

    def test_qualified_range_preserved_without_confidence_uplift(self):
        source=self.qualify();q=self.priority.assess('OPPORTUNITY',self.candidate.candidate_id)
        self.assertEqual((source.low,source.high,source.central),(q.result.basis.economic.low,q.result.basis.economic.high,q.result.basis.economic.central))
        self.assertEqual(source.confidence,q.result.basis.confidence)
        self.assertEqual('INSUFFICIENT_EVIDENCE',q.result.classification)
        self.assertEqual(90,q.result.basis.economic.horizon_days)

    def test_unqualified_candidate_refused(self):
        self.service.qualify(self.candidate.candidate_id)
        with self.assertRaises(ScopeError):self.priority.assess('OPPORTUNITY',self.candidate.candidate_id)

    def test_changed_opportunity_requires_reassessment(self):
        self.qualify();q=self.priority.assess('OPPORTUNITY',self.candidate.candidate_id)
        d=self.priority.decide(q.subject_id,1,request())
        data=self.evidence(source_version='2');data['reviews'][0]['cohort_pairs'][0]['treated']['cash_received']='50'
        self.qualify(data,expected_revision=1)
        with self.assertRaises(RevisionConflict):self.priority.get(q.subject_id,current=True)
        updated=self.priority.assess('OPPORTUNITY',self.candidate.candidate_id,expected_revision=1)
        self.assertEqual(30,updated.result.basis.economic.low);self.assertEqual(d,self.priority.get_decision(q.subject_id))

    def test_source_effect_preserved_and_no_aggregation_api(self):
        source=self.qualify();q=self.priority.assess('OPPORTUNITY',self.candidate.candidate_id)
        self.assertIn(source.candidate.effect_id,q.result.basis.source_snapshot)
        self.assertFalse(hasattr(self.priority,'aggregate'))

    def test_decimal_persistence(self):
        data=self.evidence();data['reviews'][0]['cohort_pairs'][0]['treated']['cash_received']='60.00000000000000000001'
        self.qualify(data);q=self.priority.assess('OPPORTUNITY',self.candidate.candidate_id)
        self.assertEqual(Decimal('40.00000000000000000001'),self.priority.get(q.subject_id,current=True).result.basis.economic.low)


class GoldenPriorityV251(unittest.TestCase):
    # Reuse the approved repository workbook, never a private qualification key.
    from tests import test_receivables_v249 as fixtures
    target_url=fixtures.ReceivablesV249.target_url
    prepare_target=fixtures.ReceivablesV249.prepare_target
    setUp=fixtures.ReceivablesV249.setUp
    assess=fixtures.ReceivablesV249.assess

    def test_golden_source_does_not_invent_opportunity_or_priority(self):
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
        priority=PriorityService(canonical,'r1',opportunities)
        with self.assertRaises(ScopeError):priority.assess('OPPORTUNITY',candidate.candidate_id)
        self.assertEqual(0,self.session.scalar(select(func.count()).select_from(tables.assessment)))
        self.assertEqual(impact,self.impacts.get(impact.candidate_id,current=True))
        self.assertEqual(before,hashlib.sha256(WORKBOOK.read_bytes()).hexdigest())
