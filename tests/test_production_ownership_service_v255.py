"""Durable monthly/absence ownership, caller transactions and scoped CMC."""
from datetime import date
from decimal import Decimal
import unittest

from alembic import command
from sqlalchemy import select, func, insert, update
from sqlalchemy.exc import IntegrityError

from tests import test_monthly_absence_v255 as domain
from tests.test_postgresql_live_qualification_v218 import alembic_config
from profit_doctor.persistence import (Client, EngineRun, DatabaseConfig, build_engine,
    session_factory, production_evidence_schema as tables, measurement_schema)
from profit_doctor.reasoning.domain.contracts import Actor
from profit_doctor.reasoning.domain.service import ScopeError, RevisionConflict
from profit_doctor.reasoning.measurement.contracts import MeasurementSlot
from profit_doctor.reasoning.production_evidence.service import ProductionEvidenceService


class OwnershipFixture:
    target_url=None
    def setUp(self):
        self.fx=domain.MonthlyOwnersV255('runTest');self.fx.setUp();self.addCleanup(self.fx.doCleanups)
        self.root=self.fx.fx.fx.root
        self.url=self.target_url or ('sqlite+pysqlite:///'+(self.root/'canonical.db').as_posix())
        command.upgrade(alembic_config(self.url),'head')
        self.engine=build_engine(DatabaseConfig(self.url));self.addCleanup(self.engine.dispose)
        self.factory=session_factory(self.engine)
        t='2026-10-01T00:00:00+00:00'
        with self.factory.begin() as session:
            for client,run in (('c1','r1'),('c2','r2')):
                session.add(Client(client_id=client,client_name='Client',base_currency='GBP',created_at=t))
                session.add(EngineRun(run_id=run,client_id=client,run_type='ADVISORY',started_at=t,status='RUNNING',engine_version='2.55'))
        self.session=self.factory();self.addCleanup(self.session.close)
        self.actor=Actor(actor_type='SYSTEM',actor_id='source-evidence-owner',source_authority='SYSTEM_DERIVED')
        self.service=ProductionEvidenceService(self.session,self.fx.fx.con,'c1','r1',self.actor,self.fx.fx.authority)

    def qualify(self):
        x=self.fx.fx
        return self.service.qualify_monthly(x.records,x.controls,x.document(x.manifest,'manifest'),
            mapping_version=x.document(x.mapping,'mapping','HUMAN_FD_JUDGEMENT'),family='REVENUE')


class ProductionOwnershipServiceV255(OwnershipFixture,unittest.TestCase):

    def test_create_read_exact_value_and_context(self):
        value=self.qualify().value
        self.assertEqual(self.service.get_monthly(value.measurement_id,current=True),value)
        binding=self.service.contexts.lookup(value.context.origin)
        self.assertEqual(self.service.contexts.resolve_binding(binding.binding_id)[1],value.context)

    def test_owned_history_replay_no_duplicates(self):
        first=self.qualify().value;self.assertEqual(self.qualify().value,first)
        self.assertEqual(self.session.scalar(select(func.count()).select_from(tables.monthly)),1)
        self.assertEqual(self.session.scalar(select(func.count()).select_from(tables.audit)),1)

    def test_caller_owned_rollback_removes_all_ownership_rows(self):
        self.qualify();self.session.rollback()
        for table in (tables.monthly,tables.audit,measurement_schema.measurement_context,measurement_schema.measurement_binding,measurement_schema.measurement_audit):
            self.assertEqual(self.session.scalar(select(func.count()).select_from(table)),0)

    def test_service_does_not_commit_legacy_store(self):
        x=self.fx.fx
        manifest=x.document(x.manifest,'manifest');mapping=x.document(x.mapping,'mapping','HUMAN_FD_JUDGEMENT')
        self.fx.fx.con.execute("UPDATE client SET client_name='uncommitted' WHERE client_id='c1'")
        self.service.qualify_monthly(x.records,x.controls,manifest,mapping_version=mapping,family='REVENUE')
        self.fx.fx.con.rollback()
        self.assertEqual(self.fx.fx.con.execute("SELECT client_name FROM client WHERE client_id='c1'").fetchone()[0],'Client')

    def test_cross_client_owner_read_refuses(self):
        value=self.qualify().value
        # Existing service refuses the foreign canonical owner before any source read.
        self.service.client_id='c2'
        with self.assertRaises(ScopeError):self.service.get_monthly(value.measurement_id)

    def test_cross_client_run_refuses(self):
        with self.assertRaises(ScopeError):ProductionEvidenceService(self.session,self.fx.fx.con,'c1','r2',self.actor)

    def test_untrusted_production_boundary_refuses(self):
        self.service=ProductionEvidenceService(self.session,self.fx.fx.con,'c1','r1',self.actor)
        self.assertEqual(self.qualify().outcome,'REFUSED')
        self.assertEqual(self.session.scalar(select(func.count()).select_from(tables.monthly)),0)

    def test_production_entry_rejects_caller_previous_document(self):
        with self.assertRaises(TypeError):self.service.qualify_monthly('r','c','m',mapping_version='map',family='REVENUE',previous={})

    def test_context_requires_registered_monthly_provider(self):
        value=self.qualify().value;self.service.contexts.monthly=None
        with self.assertRaises(ScopeError):self.service.contexts.get_context(value.context.context_id,current=True)

    def test_expired_source_authority_invalidates_current_owner(self):
        value=self.qualify().value;self.fx.fx.grants.clear()
        with self.assertRaises(RevisionConflict):self.service.get_monthly(value.measurement_id,current=True)

    def test_owned_monthly_cannot_propagate_into_diagnostic_consumers(self):
        value=self.qualify().value
        binding=self.service.contexts.lookup(value.context.origin)
        # No allowed retained one-to-one edge exists for monthly -> diagnostic.
        with self.assertRaises((ScopeError,ValueError)):
            self.service.contexts.propagate(binding.binding_id,MeasurementSlot(store='CANONICAL',resource='canonical_fact',source_id='REV-01',slot='observed'))

    def test_frozen_fact_tables_remain_empty(self):
        self.qualify()
        from profit_doctor.persistence import Base
        for name in ('canonical_fact','signal','finding_v2'):
            if name in Base.metadata.tables:
                self.assertEqual(self.session.scalar(select(func.count()).select_from(Base.metadata.tables[name])),0)

    def test_audit_preserves_actor_and_source_lineage(self):
        value=self.qualify().value
        document=self.session.scalar(select(tables.audit.c.document))
        self.assertIn('source-evidence-owner',document);self.assertIn('SOURCE_FILE',document)
        self.assertIn(value.measurement_id,document)

    def test_monthly_fk_rejects_foreign_context(self):
        value=self.qualify().value
        with self.assertRaises(IntegrityError),self.session.begin_nested():
            self.session.execute(insert(tables.monthly).values(measurement_id='foreign',series_id='other',
                client_id='c2',run_id='r2',revision=1,context_id=value.context.context_id,document='{}'))

    def test_missing_context_fk_rejected(self):
        with self.assertRaises(IntegrityError),self.session.begin_nested():
            self.session.execute(insert(tables.monthly).values(measurement_id='missing',series_id='other',client_id='c1',
                run_id='r1',revision=1,context_id='missing',document='{}'))

    def test_revision_uniqueness_rejected(self):
        value=self.qualify().value
        with self.assertRaises(IntegrityError),self.session.begin_nested():
            self.session.execute(insert(tables.monthly).values(measurement_id='duplicate',series_id=value.series_id,
                client_id='c1',run_id='r1',revision=1,context_id=value.context.context_id,document='{}'))

    def test_restatement_history_current_selection(self):
        old=self.qualify().value;x=self.fx.fx
        x.records=x.amounts('s1','101');x.controls=x.amounts('control1','101')
        x.manifest=x.manifest.model_copy(update={'record_version_id':x.records,'change_kind':'RESTATEMENT',
            'predecessor_version_id':old.semantic.contract.source_version.source_id})
        new=self.qualify().value
        self.assertEqual(self.service.get_monthly(new.measurement_id,current=True),new)
        self.assertEqual(self.service.get_monthly(old.measurement_id),old)
        with self.assertRaises(RevisionConflict):self.service.get_monthly(old.measurement_id,current=True)

    def test_no_update_method_or_temporal_evaluator(self):
        self.assertFalse(hasattr(self.service,'update'));self.assertFalse(hasattr(self.service,'assess_temporal'))


class AbsenceOwnershipServiceV255(OwnershipFixture,unittest.TestCase):
    def ar(self):
        from profit_doctor.reasoning.production_evidence.absence import ARScope,ARExport,ARManifest,ARControl,InvoiceReview
        from profit_doctor.reasoning.receivables.contracts import Invoice,StatusEvidence
        x=self.fx.fx
        scope=ARScope(client_id='c1',entity_id='e1',ledger_id='l1',as_of='2026-01-31',population='all-open-ar')
        export=ARExport(scope=scope,system_id='ar-system',report_id='ar-report',invoices=(Invoice(invoice_id='i1',customer_id='customer1',
            invoice_date='2026-01-01',explicit_due='2026-02-01',outstanding='100.00000000000000000001',as_of=scope.as_of,
            source_reference='invoice1',status=StatusEvidence(status='NONE_RECORDED',authority='SOURCE_RECORD',reviewed_at=scope.as_of,reference='review1')),),
            reviews=(InvoiceReview(customer_id='customer1',invoice_id='i1',reviewed_at=scope.as_of,source_reference='constraint-review1',
                dispute='NONE_RECORDED',payment_plan='NONE_RECORDED',pending_credit='NONE_RECORDED'),))
        ev=x.document(export,'ar-export')
        manifest=ARManifest(scope=scope,system_id='ar-system',report_id='ar-report',record_version_id=ev,
            open_items=(('customer1','i1'),),extraction_boundary=scope.population,extraction_query='all open items',
            extraction_as_of=scope.as_of,change_kind='ORIGINAL',change_reference='ar-source1')
        return ev,x.document(manifest,'ar-manifest'),x.document(ARControl(scope=scope,amount='100.00000000000000000001',source_reference='ar-gl1',basis='AR_OPEN_ITEM_CONTROL'),'ar-control')

    def test_ar_absence_owned_read_precision(self):
        a=self.service.assess_absence(*self.ar());self.assertEqual(a.outcome,'ABSENT_VERIFIED')
        self.assertEqual(self.service.get_absence(a.assessment_id,current=True),a)
        self.assertEqual(a.total,Decimal('100.00000000000000000001'))

    def test_ar_absence_rollback(self):
        self.service.assess_absence(*self.ar());self.session.rollback()
        self.assertEqual(self.session.scalar(select(func.count()).select_from(tables.absence)),0)
        self.assertEqual(self.session.scalar(select(func.count()).select_from(tables.audit)),0)

    def test_ar_absence_replay(self):
        versions=self.ar();old=self.service.assess_absence(*versions)
        self.assertEqual(self.service.assess_absence(*versions),old)
        self.assertEqual(self.session.scalar(select(func.count()).select_from(tables.absence)),1)

    def test_ar_absence_no_caller_document(self):
        with self.assertRaises(TypeError):self.service.assess_absence(snapshot={})
