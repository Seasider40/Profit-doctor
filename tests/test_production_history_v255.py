"""Scoped durable semantic evidence; no historical source/contract overwrite."""
import unittest
from sqlalchemy import select, func, insert, update, inspect
from sqlalchemy.exc import IntegrityError
from alembic import command
from alembic.migration import MigrationContext
from alembic.autogenerate import compare_metadata
from tests import test_ar_semantics_v255 as fixture
from tests.test_postgresql_live_qualification_v218 import alembic_config
from profit_doctor.persistence import Base, production_history_schema as tables, dataset_schema
from profit_doctor.reasoning.production_evidence.history import ARProjectionService, UnknownObservationService, UnknownObservation
from profit_doctor.reasoning.production_evidence.ar_semantics import ARSemanticProjection
from profit_doctor.reasoning.domain.service import ScopeError, RevisionConflict


class ProductionHistoryV255(unittest.TestCase):
    setUp=fixture.ARSemanticCheckpointV255.setUp
    verify=fixture.ARSemanticCheckpointV255.verify
    second=fixture.ARSemanticCheckpointV255.second
    presence=fixture.ARSemanticCheckpointV255.presence

    def capture(self, evidence=None):
        version=self.ar.fx.document(evidence or self.evidence,'ar-semantics')
        self.projections=ARProjectionService(self.verifier)
        return self.projections.capture(version)

    def revised(self, first, **changes):
        return self.evidence.model_copy(update={'revision':2,'predecessor_semantic_version_id':first.semantic_version_id,
            'change_kind':'CORRECTION','change_reference':'authenticated source semantic correction',**changes})

    def test_projection_persists_original_source_domain_and_refs(self):
        value=self.capture()
        self.assertEqual(self.projections.get(value.projection_id,current=True),value)
        self.assertEqual(value.original_domain,'PRODUCTION_ACCOUNTING_RECORDS_V255')
        self.assertEqual(value.contract.source_version.source_id,self.ar.ev)
        self.assertEqual(self.session.scalar(select(dataset_schema.dataset_contract.c.contract_role)),'AR_SEMANTIC_PROJECTION')

    def test_projection_replay_no_duplicate_owner_or_audit(self):
        value=self.capture();self.assertEqual(self.projections.capture(value.semantic_version_id),value)
        for table in (tables.projection,tables.audit,dataset_schema.dataset_contract):
            self.assertEqual(self.session.scalar(select(func.count()).select_from(table)),1)

    def test_semantic_revision_retains_previous_projection(self):
        first=self.capture();second=self.capture(self.revised(first))
        self.assertEqual(second.supersedes,first.projection_id)
        self.assertEqual(second.revision,2)
        self.assertEqual(second.contract.revision_relationship.verified_value,'CORRECTION')
        self.assertEqual(second.contract.coverage.verified_value['period'],first.contract.coverage.verified_value['period'])
        self.assertEqual(self.projections.get(first.projection_id),first)
        self.assertEqual(self.projections.get(second.projection_id,current=True),second)

    def test_source_restatement_retains_original_export_and_owner(self):
        first=self.capture()
        export=self.ar.export.model_copy(update={'invoices':(self.ar.invoice.model_copy(update={'outstanding':'80'}),)})
        ev=self.ar.fx.document(export,'ar-export')
        manifest=self.ar.manifest.model_copy(update={'record_version_id':ev,'predecessor_version_id':self.ar.ev,
            'change_kind':'RESTATEMENT','change_reference':'authenticated-restated-open-ar'})
        mv=self.ar.fx.document(manifest,'ar-manifest')
        cv=self.ar.fx.document(self.ar.control.model_copy(update={'amount':'80'}),'ar-control')
        owner=self.service.assess_absence(ev,mv,cv)
        second=self.capture(self.revised(first,record_version_id=ev,manifest_version_id=mv,control_version_id=cv,
            owner_id=owner.assessment_id,change_kind='RESTATEMENT',change_reference='authenticated-restated-open-ar'))
        self.assertEqual(second.supersedes,first.projection_id)
        self.assertNotEqual(second.original_refs,first.original_refs)
        self.assertEqual(self.service.get_absence(self.owner.assessment_id),self.owner)
        self.assertEqual(second.evidence.scope.as_of,first.evidence.scope.as_of)

    def test_same_date_restatement_is_not_new_temporal_observation(self):
        from profit_doctor.reasoning.dataset.comparability import assess_dataset_comparability
        first=self.capture();second=self.capture(self.revised(first,change_kind='RESTATEMENT'))
        comparison=assess_dataset_comparability(first.contract,second.contract)
        self.assertEqual(comparison.temporal_evidence_role,'REVISION_ONLY')
        self.assertEqual(comparison.dimensions['REVISION_RELATIONSHIP'].state,'LIMITED_MATCH')

    def test_later_registered_timestamp_is_not_revision_authority(self):
        self.capture()
        # Identical content is deduplicated by the registry. A separately
        # registered source document still has no replacement authority.
        with self.assertRaises(RevisionConflict):self.capture(self.evidence.model_copy(update={
            'declarations':{'family':'ELIGIBLE_OPEN_RECEIVABLES_V255'}}))

    def test_wrong_semantic_predecessor_refuses(self):
        first=self.capture()
        with self.assertRaises(RevisionConflict):self.capture(self.revised(first,predecessor_semantic_version_id='wrong'))

    def test_missing_change_authority_refuses(self):
        first=self.capture()
        with self.assertRaises(RevisionConflict):self.capture(self.revised(first,change_reference=None))

    def test_superseded_projection_not_current(self):
        first=self.capture();self.capture(self.revised(first))
        with self.assertRaises(RevisionConflict):self.projections.get(first.projection_id,current=True)

    def test_changed_source_authority_refuses_current_projection(self):
        value=self.capture();self.ar.fx.grants.clear()
        with self.assertRaises(ScopeError):self.projections.get(value.projection_id,current=True)

    def test_projection_indexed_relationship_tampering_refuses(self):
        value=self.capture()
        with self.assertRaises(IntegrityError), self.session.begin_nested():
            self.session.execute(update(tables.projection).values(contract_id='missing').where(tables.projection.c.projection_id==value.projection_id))

    def test_raw_contract_and_projection_coexist_without_overwrite(self):
        value=self.capture()
        raw=value.contract.model_copy(update={'contract_id':'raw-source-contract','source_data_domain':value.original_domain})
        self.session.execute(insert(dataset_schema.dataset_contract).values(contract_id=raw.contract_id,client_id='c1',run_id='r1',
            source_version_id=raw.source_version.source_id,revision=1,document=raw.to_json()))
        rows=self.session.execute(select(dataset_schema.dataset_contract.c.contract_role,dataset_schema.dataset_contract.c.document)).all()
        self.assertEqual({r[0] for r in rows},{'RAW','AR_SEMANTIC_PROJECTION'})
        self.assertIn(raw.to_json(),[r[1] for r in rows])
        self.assertEqual(self.projections.get(value.projection_id,current=True),value)

    def test_raw_dataset_writer_cannot_mutate_a_semantic_projection(self):
        from profit_doctor.reasoning.dataset.service import DatasetContractService
        value=self.capture()
        raw=DatasetContractService(self.session,'c1','r1',self.actor,self.ar.fx.con)
        with self.assertRaises(ScopeError):raw.get_contract(value.projection_id)

    def test_caller_owned_rollback_removes_projection_contract_and_audit(self):
        self.capture();self.session.rollback()
        for table in (tables.projection,tables.audit,dataset_schema.dataset_contract):
            self.assertEqual(self.session.scalar(select(func.count()).select_from(table)),0)

    def test_history_audit_retains_actor_predecessor_and_lineage(self):
        from profit_doctor.reasoning.domain.contracts import AuditEvent
        first=self.capture();second=self.capture(self.revised(first))
        document=self.session.scalar(select(tables.audit.c.document).where(tables.audit.c.projection_id==second.projection_id))
        event=AuditEvent.from_json(document)
        self.assertEqual(event.event_type,'OBJECT_SUPERSEDED')
        self.assertEqual(event.previous,{'predecessor':first.projection_id})
        self.assertEqual(event.lineage,second.lineage)

    def test_foreign_or_missing_projection_refuses(self):
        self.projections=ARProjectionService(self.verifier)
        with self.assertRaises(ScopeError):self.projections.get('not-owned')

    def test_owned_unknown_retains_refusal_and_no_amount(self):
        version=self.ar.fx.document(self.evidence.model_copy(update={'family':'UNKNOWN'}),'ar-semantics')
        unknowns=UnknownObservationService(ARProjectionService(self.verifier))
        value=unknowns.capture(version)
        self.assertIn('AR definition/family/time/unit insufficient',value.reasons)
        self.assertEqual(value.attempted_owner_id,self.owner.assessment_id)
        self.assertFalse(hasattr(value,'value'));self.assertFalse(hasattr(value,'absence'))
        self.assertEqual(UnknownObservation.from_json(value.to_json()),value)
        self.assertEqual(unknowns.get(value.unknown_id,current=True),value)

    def test_unknown_replay_is_idempotent(self):
        version=self.ar.fx.document(self.evidence.model_copy(update={'family':'UNKNOWN'}),'ar-semantics')
        unknowns=UnknownObservationService(ARProjectionService(self.verifier))
        first=unknowns.capture(version);self.assertEqual(first,unknowns.capture(version))
        self.assertEqual(self.session.scalar(select(func.count()).select_from(tables.unknown)),1)

    def test_unknown_requires_registered_refusal_not_caller_reasons(self):
        unknowns=UnknownObservationService(ARProjectionService(self.verifier))
        with self.assertRaises(TypeError):unknowns.capture('id',reasons=('unknown',))
        with self.assertRaises(ScopeError):unknowns.capture('not-registered')

    def test_qualified_projection_cannot_be_relabelled_unknown(self):
        version=self.ar.fx.document(self.evidence,'ar-semantics')
        unknowns=UnknownObservationService(ARProjectionService(self.verifier))
        with self.assertRaises(ValueError):unknowns.capture(version)
        self.assertEqual(self.session.scalar(select(func.count()).select_from(tables.unknown)),0)
        self.assertEqual(self.session.scalar(select(func.count()).select_from(tables.projection)),0)

    def test_unknown_changed_refusal_creates_history(self):
        unknowns=UnknownObservationService(ARProjectionService(self.verifier))
        a=unknowns.capture(self.ar.fx.document(self.evidence.model_copy(update={'family':'UNKNOWN'}),'ar-semantics'))
        b=unknowns.capture(self.ar.fx.document(self.evidence.model_copy(update={'unit':'UNKNOWN'}),'ar-semantics'))
        self.assertEqual(b.supersedes,a.unknown_id);self.assertEqual(b.revision,2)
        self.assertEqual(unknowns.get(a.unknown_id),a)

    def test_metadata_matches_clean_current_head(self):
        with self.session.get_bind().connect() as connection:
            ctx=MigrationContext.configure(connection,opts={'compare_type':True,'compare_server_default':True})
            self.assertEqual(ctx.get_current_heads(),('0020_engagement_workspace',))
            self.assertEqual(compare_metadata(ctx,Base.metadata),[])

    def test_downgrade_removes_only_derived_contracts_preserving_raw_source_rows(self):
        value=self.capture()
        raw=value.contract.model_copy(update={'contract_id':'raw-source-contract','source_data_domain':value.original_domain})
        self.session.execute(insert(dataset_schema.dataset_contract).values(contract_id=raw.contract_id,client_id='c1',run_id='r1',
            source_version_id=raw.source_version.source_id,revision=1,document=raw.to_json()))
        self.session.commit();self.session.close()
        engine_url=getattr(self,'target_url',None) or ('sqlite+pysqlite:///'+(self.ar.fx.fx.root/'ar-canonical.db').as_posix())
        engine_url=engine_url.replace('%','%%')
        command.downgrade(alembic_config(engine_url),'0018_production_qualification')
        command.upgrade(alembic_config(engine_url),'head')
        row=self.session.execute(select(dataset_schema.dataset_contract)).mappings().one()
        self.assertEqual(row['contract_id'],raw.contract_id)
        self.assertEqual(row['document'],raw.to_json())
        self.assertEqual(row['contract_role'],'RAW')
        self.assertEqual(self.session.scalar(select(func.count()).select_from(tables.projection)),0)
