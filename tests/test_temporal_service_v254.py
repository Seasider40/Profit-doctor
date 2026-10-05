"""Owning production source refusal, immutable history, scope and transactions."""
from datetime import date
import unittest

from sqlalchemy import func, insert, select, update
from sqlalchemy.exc import IntegrityError
from alembic import command

from tests import test_canonical_facts_findings_v244 as canonical_fixtures
from tests import test_receivables_v249 as receivables_fixtures
from tests.temporal_evidence_v254 import basis
from profit_doctor.persistence import Base, DatabaseConfig, build_engine, temporal_schema as tables
from profit_doctor.reasoning.canonical.service import CanonicalService
from profit_doctor.reasoning.canonical.source import LegacySignalSource
from profit_doctor.reasoning.dataset.service import DatasetContractService
from profit_doctor.reasoning.domain.service import ScopeError, RevisionConflict
from profit_doctor.reasoning.temporal.contracts import Assessment, Window
from profit_doctor.reasoning.temporal.engine import evaluate
from profit_doctor.reasoning.temporal.service import TemporalService
from tests.test_postgresql_live_qualification_v218 import alembic_config


KEY='REVENUE_DESCRIPTIVE_TRAJECTORY'


def prepare(fixture, target_url):
    if target_url:
        fixture.target_url=lambda directory: target_url
        def setup_target():
            command.upgrade(alembic_config(target_url),'head')
            engine=build_engine(DatabaseConfig(target_url))
            try:
                with engine.begin() as connection:
                    for table in reversed(Base.metadata.sorted_tables):
                        connection.execute(table.delete())
            finally:
                engine.dispose()
        fixture.prepare_target=setup_target


class TemporalServiceV254(unittest.TestCase):
    target_url=None

    def setUp(self):
        self.fixture=canonical_fixtures.CanonicalV244('runTest')
        prepare(self.fixture,self.target_url)
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.setUp()
        self.session=self.fixture.session
        self.canonical=self.fixture.service
        self.datasets=DatasetContractService(self.session,'c1','r1',self.fixture.actor,self.fixture.legacy)
        self.service=TemporalService(self.canonical,self.datasets)
        self.window=Window(start=date(2026,1,1),end=date(2026,3,31),cadence='MONTHLY')
        self.fact=self.add_fact('first')
        self.finding=self.canonical.assess(self.fact.object_id).finding_id

    def add_fact(self,name,run='r1'):
        return self.canonical.canonicalise(self.fixture.revenue(name,run=run)).fact

    def assess(self,**kwargs):
        return self.service.assess(self.finding,KEY,self.window,(self.fact.object_id,),**kwargs)

    def test_production_refuses_unverified_measurement_period_and_comparability(self):
        value=self.assess()
        self.assertEqual(('NOT_ASSESSED','NOT_ASSESSED','NOT_ASSESSED'),(
            value.result.sequence,value.result.trajectory,value.result.interpretation))
        self.assertIsNone(value.result.basis.observations[0].period.start)
        self.assertIsNone(value.result.basis.observations[0].dataset)

    def test_replay_is_idempotent_and_does_not_duplicate_audit(self):
        value=self.assess()
        self.assertEqual(value,self.assess())
        self.assertEqual(1,len(self.service.history(value.series_id)))
        self.assertEqual(1,len(self.service.audit_events(value.series_id)))

    def test_changed_evidence_requires_predecessor_and_preserves_history(self):
        first=self.assess()
        second_fact=self.add_fact('second','r3')
        self.canonical.assess(second_fact.object_id)
        sources=(self.fact.object_id,second_fact.object_id)
        with self.assertRaises(RevisionConflict):self.service.assess(self.finding,KEY,self.window,sources)
        second=self.service.assess(self.finding,KEY,self.window,sources,expected_revision=1)
        self.assertEqual((1,2),tuple(x.revision for x in self.service.history(first.series_id)))
        self.assertEqual(first.assessment_id,second.supersedes)
        self.assertEqual(first,self.service.get(first.series_id,1))
        self.assertEqual(second,self.service.assess(self.finding,KEY,self.window,tuple(reversed(sources))))
        self.assertEqual(2,len(self.service.audit_events(first.series_id)))

    def test_windows_have_distinct_identity_and_no_automatic_subwindow(self):
        first=self.assess()
        window=Window(start=date(2026,2,1),end=date(2026,3,31),cadence='MONTHLY')
        second=self.service.assess(self.finding,KEY,window,(self.fact.object_id,))
        self.assertNotEqual(first.series_id,second.series_id)
        self.assertEqual(window,second.result.basis.window)

    def test_caller_owned_rollback_removes_assessment_and_audit(self):
        self.session.commit()
        value=self.assess()
        self.session.rollback()
        self.assertIsNone(self.session.scalar(select(tables.assessment.c.assessment_id).where(
            tables.assessment.c.assessment_id==value.assessment_id)))
        self.assertEqual(0,self.session.scalar(select(func.count()).select_from(tables.audit)))

    def test_readback_preserves_decimal_lineage_and_requires_explicit_sources(self):
        value=self.assess()
        self.session.commit()
        with self.fixture.factory() as session:
            canonical=CanonicalService(session,'c1',self.fixture.actor,self.fixture.source)
            datasets=DatasetContractService(session,'c1','r1',self.fixture.actor,self.fixture.legacy)
            read=TemporalService(canonical,datasets).get(value.series_id)
            self.assertEqual(value,read)
            self.assertEqual(self.fact.lineage,read.result.basis.observations[0].lineage)
        with self.assertRaises(TypeError):self.service.assess(self.finding,KEY,self.window,observations=basis().observations)

    def test_foreign_client_and_run_owners_are_refused(self):
        value=self.assess()
        canonical=CanonicalService(self.session,'c2',self.fixture.actor,LegacySignalSource(self.fixture.legacy,'c2'))
        datasets=DatasetContractService(self.session,'c2','r2',self.fixture.actor,self.fixture.legacy)
        with self.assertRaises(ScopeError):TemporalService(canonical,datasets).get(value.series_id)
        with self.assertRaises(ScopeError):TemporalService(self.canonical,datasets)
        with self.assertRaises(ScopeError):DatasetContractService(self.session,'c1','r2',self.fixture.actor,self.fixture.legacy)

    def test_scoped_database_endpoint_and_uniqueness_constraints_are_enforced(self):
        value=self.assess()
        row=dict(self.session.execute(select(tables.assessment)).mappings().one())
        row.update(assessment_id='foreign-reference',series_id='other',client_id='c2')
        with self.assertRaises(IntegrityError),self.session.begin_nested():
            self.session.execute(insert(tables.assessment).values(**row))
        row.update(assessment_id='duplicate-revision',series_id=value.series_id,client_id='c1')
        with self.assertRaises(IntegrityError),self.session.begin_nested():
            self.session.execute(insert(tables.assessment).values(**row))

    def test_synthetic_result_cannot_be_read_as_production(self):
        value=self.assess()
        synthetic=basis().model_copy(update={'subject_id':self.finding})
        tampered=value.model_copy(update={'result':evaluate(synthetic)})
        self.session.execute(update(tables.assessment).where(tables.assessment.c.assessment_id==value.assessment_id).values(document=tampered.to_json()))
        with self.assertRaises(ScopeError):self.service.get(value.series_id)

    def test_source_changes_require_reassessment_without_erasing_history(self):
        value=self.assess()
        self.fixture.legacy.execute('UPDATE signal SET observed_value=? WHERE signal_id=?',('125',self.fact.source_signal_id))
        self.fixture.legacy.commit()
        with self.assertRaises(RevisionConflict):self.service.get(value.series_id,current=True)
        self.assertEqual(value,self.service.get(value.series_id))


class TemporalReceivablesV254(unittest.TestCase):
    target_url=None

    def setUp(self):
        self.fixture=receivables_fixtures.ReceivablesV249('runTest')
        prepare(self.fixture,self.target_url)
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.setUp()
        self.canonical=CanonicalService(self.fixture.session,'c1',self.fixture.actor,LegacySignalSource(self.fixture.legacy,'c1'))
        datasets=DatasetContractService(self.fixture.session,'c1','r1',self.fixture.actor,self.fixture.legacy)
        self.service=TemporalService(self.canonical,datasets,self.fixture.contexts,self.fixture.impacts)

    def test_owned_real_source_impact_can_establish_presence_but_not_temporal_lifecycle(self):
        data=self.fixture.data();data['origin']='REAL_SOURCE'
        q=self.fixture.assess(self.fixture.ingest(data))
        window=Window(start=date(2026,12,1),end=date(2026,12,31),cadence='MONTHLY')
        value=self.service.assess(q.impact.impact_id,'CASH_TRAPPED_RECEIVABLES_LIFECYCLE',window,(q.candidate_id,))
        observation=value.result.basis.observations[0]
        self.assertEqual('PRESENT',observation.presence)
        self.assertEqual(q.impact.amount.value,observation.value)
        self.assertEqual('NOT_ASSESSED',value.result.lifecycle)
        self.assertIsNone(observation.dataset)

    def test_blind_qualification_impact_cannot_enter_production_temporal_route(self):
        q=self.fixture.assess(self.fixture.ingest())
        window=Window(start=date(2026,12,1),end=date(2026,12,31),cadence='MONTHLY')
        with self.assertRaises(ScopeError):self.service.assess(q.impact.impact_id,
            'CASH_TRAPPED_RECEIVABLES_LIFECYCLE',window,(q.candidate_id,))
