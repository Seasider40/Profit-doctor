"""Existing owned readiness/registry integration; no application trust uplift."""
import unittest
from pathlib import Path
from alembic import command
from tests.test_postgresql_live_qualification_v218 import alembic_config
from profit_doctor.persistence import Base
from sqlalchemy import select, func
from tests.test_component_margin_v255 import ComponentFixture
from profit_doctor.persistence import production_history_schema as tables
from profit_doctor.workspace.contracts import Scope, EngagementRevision, Operator
from profit_doctor.workspace.readers import OwnedEvidenceReader, production_reader
from profit_doctor.workspace.storage import EvidenceStore
from profit_doctor.workspace.service import WorkspaceService
from profit_doctor.reasoning.domain.service import ScopeError, RevisionConflict
from profit_doctor.reasoning.production_evidence.assessments import ProductionAssessmentService
from profit_doctor.reasoning.production_evidence.readiness import EvidenceReadinessService, ReadinessDomain, ReadinessReference


class WorkspaceReadersV256(ComponentFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.ready = EvidenceReadinessService(ProductionAssessmentService(self.service))
        self.result = self.ready.assess(ReadinessDomain.REVENUE_MONTHLY_MEASUREMENT,
            (ReadinessReference(kind='MONTHLY', owner_id=self.revenue.measurement_id),))
        source = self.revenue.semantic.manifest.scope
        self.scope = Scope(entity_id=source.entity_id, ledger_id=source.ledger_id,
            period_start=source.period.start, period_end=source.period.end)
        self.engagement = EngagementRevision(engagement_id='review-1', client_id='c1', revision=1,
            title='Evidence review', scope=self.scope, run_ids=('r1',))
        self.reader = OwnedEvidenceReader(self.fx.fx.con, readiness_factory=lambda client, runs: self.ready,
            scope_resolver=lambda value: self.scope)
        self.workspace = WorkspaceService(self.session, Operator('adviser', frozenset({'c1', 'c2'})),
            EvidenceStore(self.root / 'workspace-evidence'), reader=self.reader)
        self.workspace.save_engagement(self.engagement, expected_revision=0, key='engagement')

    def test_readiness_projection_uses_existing_writer_without_writes(self):
        before = self.session.scalar(select(func.count()).select_from(tables.readiness))
        selected = self.engagement.model_copy(update={'revision': 2, 'readiness_ids': (self.result.readiness_id,)})
        self.workspace.save_engagement(selected, expected_revision=1, key='select')
        value = self.workspace.readiness('c1', 'review-1')[0]
        self.assertEqual(value['assessment'], self.result.model_dump(mode='json'))
        self.assertEqual(value['view'], 'CURRENT')
        self.assertEqual(self.session.scalar(select(func.count()).select_from(tables.readiness)), before)

    def test_default_source_authority_cannot_promote_current_readiness(self):
        reader = production_reader(self.session, self.fx.fx.con, Operator('adviser', frozenset({'c1'})))
        with self.assertRaises((ScopeError, RevisionConflict, ValueError)):
            reader.readiness(self.engagement, self.result.readiness_id, current=True)
        historical = reader.readiness(self.engagement, self.result.readiness_id, current=False)
        self.assertEqual(historical['view'], 'HISTORICAL')
        self.assertEqual(historical['assessment']['readiness_id'], self.result.readiness_id)

    def test_historical_selection_available_without_current_source_authentication(self):
        self.workspace.reader = production_reader(self.session, self.fx.fx.con, self.workspace.operator)
        selected = self.engagement.model_copy(update={'revision': 2,
            'readiness_ids': (self.result.readiness_id,), 'readiness_view': 'HISTORICAL'})
        self.workspace.save_engagement(selected, expected_revision=1, key='historical-select')
        self.assertEqual(self.workspace.readiness('c1', 'review-1')[0]['view'], 'HISTORICAL')
        with self.assertRaises((ScopeError, RevisionConflict, ValueError)):
            self.workspace.readiness('c1', 'review-1', historical=False)

    def test_wrong_entity_period_and_client_fail_closed(self):
        for changes in ({'entity_id': 'other'}, {'period_end': '2026-12-31'}):
            changed = self.engagement.model_copy(update={'scope': self.scope.model_copy(update=changes)})
            with self.subTest(changes=changes), self.assertRaises(ScopeError):
                self.reader.readiness(changed, self.result.readiness_id, current=True)
        with self.assertRaises(ScopeError):
            self.reader.readiness(self.engagement.model_copy(update={'client_id': 'c2'}), self.result.readiness_id, current=True)

    def test_non_owner_reader_rejected(self):
        reader = OwnedEvidenceReader(self.fx.fx.con, readiness_factory=lambda *args: object(), scope_resolver=lambda value: self.scope)
        with self.assertRaises(ScopeError):
            reader.readiness(self.engagement, self.result.readiness_id, current=True)

    def registered_receipt(self):
        version = self.revenue.semantic.source_versions[0]
        row = self.fx.fx.con.execute('''SELECT f.storage_location FROM dataset_version v JOIN source_file f
            ON f.source_file_id=v.source_file_id WHERE v.dataset_version_id=?''', (version,)).fetchone()
        value = self.workspace.receive('c1', 'review-1', 'source.csv', Path(row['storage_location']).read_bytes(),
            role='REGISTERED_SOURCE', key='receipt')
        return version, value

    def test_exact_registered_bytes_link_no_authentication_uplift(self):
        version, receipt = self.registered_receipt()
        result = self.workspace.associate_registration('c1', 'review-1', receipt.receipt_id, version, key='link')
        self.assertEqual(result['registration']['relation'], 'EXACT_RECEIVED_BYTES')
        self.assertEqual(result['registration']['authority'], 'NOT_ESTABLISHED_BY_REGISTRATION')
        self.assertEqual(self.workspace.inventory('c1', 'review-1')[0]['authority'], 'NOT_ESTABLISHED_BY_RECEIPT')

    def test_different_bytes_cannot_claim_transformation(self):
        version, _ = self.registered_receipt()
        receipt = self.workspace.receive('c1', 'review-1', 'other.csv', b'other', role='SOURCE', key='other')
        with self.assertRaises(ScopeError):
            self.workspace.associate_registration('c1', 'review-1', receipt.receipt_id, version, key='bad-link')

    def test_foreign_registration_refused(self):
        version, receipt = self.registered_receipt()
        other = self.engagement.model_copy(update={'client_id': 'c2'})
        with self.assertRaises(ScopeError):
            self.reader.registration(other, receipt, version)

    def test_unknown_registration_is_not_missing_source_authentication_pass(self):
        _, receipt = self.registered_receipt()
        with self.assertRaises(ScopeError):
            self.reader.registration(self.engagement, receipt, 'unregistered')

    def test_superseded_readiness_is_historical_only(self):
        self.ready.assess(ReadinessDomain.REVENUE_MONTHLY_MEASUREMENT, ())
        with self.assertRaises(RevisionConflict):
            self.reader.readiness(self.engagement, self.result.readiness_id, current=True)
        self.assertEqual(self.reader.readiness(self.engagement, self.result.readiness_id, current=False)['view'], 'HISTORICAL')

    def test_all_legacy_owner_rows_survive_workspace_downgrade_reupgrade(self):
        self.session.commit()
        self.session.close()
        legacy = [table for name, table in Base.metadata.tables.items() if not name.startswith('workspace_')]
        def snapshot():
            with self.engine.connect() as connection:
                return {table.name: sorted([dict(row) for row in connection.execute(select(table)).mappings()], key=repr)
                    for table in legacy}
        before = snapshot()
        command.downgrade(alembic_config(self.url), '0019_production_history')
        self.assertEqual(snapshot(), before)
        command.upgrade(alembic_config(self.url), 'head')
        self.assertEqual(snapshot(), before)
