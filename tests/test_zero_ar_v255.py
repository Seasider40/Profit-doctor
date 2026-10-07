"""Positive source-supported zero population; default empty-export refusal retained."""
from datetime import date
import unittest
from sqlalchemy import select,func
from tests import test_ar_semantics_v255 as fixture
from profit_doctor.reasoning.production_evidence.zero import ZeroAREvidence,ZeroARPopulationService
from profit_doctor.reasoning.production_evidence.ar_semantics import ARSemanticVerifier
from profit_doctor.persistence import production_history_schema as tables,production_evidence_schema
from profit_doctor.reasoning.domain.service import ScopeError,RevisionConflict


class ZeroARV255(unittest.TestCase):
    setUp=fixture.ARSemanticCheckpointV255.setUp

    def source(self, *, status='COMPLETED', control='0', authority='SOURCE_DATA', membership=(), count=0):
        scope=self.ar.scope.model_copy(update={'as_of':date(2026,3,31)})
        export=self.ar.export.model_copy(update={'scope':scope,'invoices':(),'reviews':()})
        ev=self.ar.fx.document(export,'ar-export')
        manifest=self.ar.manifest.model_copy(update={'scope':scope,'record_version_id':ev,
            'open_items':membership,'extraction_as_of':scope.as_of})
        mv=self.ar.fx.document(manifest,'ar-manifest')
        cv=self.ar.fx.document(self.ar.control.model_copy(update={'scope':scope,'amount':control}),'ar-control')
        evidence=ZeroAREvidence(scope=scope,system_id='system1',report_id='open-ar',export_version_id=ev,
            manifest_version_id=mv,control_version_id=cv,extraction_id='source-completed-extraction',
            extraction_status=status,source_reference='authenticated-zero-report-and-control',population_record_count=count)
        version=self.ar.fx.document(evidence,'ar-zero',authority)
        return version,evidence

    def test_complete_authenticated_zero_population_qualifies(self):
        version,evidence=self.source();service=ZeroARPopulationService(self.service);zero=service.capture(version)
        self.assertEqual(zero.status,'ZERO_AR_VERIFIED');self.assertEqual(zero.total,0)
        self.assertEqual(zero,service.get(zero.zero_id,current=True))
        self.assertEqual(zero.proof,evidence)

    def test_source_authoritative_zero_revision_preserves_history(self):
        version,proof=self.source();service=ZeroARPopulationService(self.service)
        first=service.capture(version)
        corrected=proof.model_copy(update={'revision':2,'predecessor_source_version_id':version,
            'change_kind':'RESTATEMENT','change_reference':'source-corrected-extraction-proof'})
        revised=self.ar.fx.document(corrected,'ar-zero')
        second=service.capture(revised)
        self.assertEqual((second.revision,second.supersedes),(2,first.zero_id))
        self.assertEqual(second.scope.as_of,first.scope.as_of)
        self.assertEqual(service.get(first.zero_id),first)
        self.assertEqual(service.get(second.zero_id,current=True),second)
        with self.assertRaises(RevisionConflict):service.get(first.zero_id,current=True)

    def test_zero_revision_requires_owned_predecessor(self):
        version,proof=self.source()
        corrected=proof.model_copy(update={'revision':2,'predecessor_source_version_id':version,
            'change_kind':'CORRECTION','change_reference':'source-correction'})
        with self.assertRaises(RevisionConflict):ZeroARPopulationService(self.service).capture(self.ar.fx.document(corrected,'ar-zero'))

    def test_later_zero_document_without_revision_authority_refuses(self):
        version,proof=self.source();service=ZeroARPopulationService(self.service);service.capture(version)
        changed=proof.model_copy(update={'source_reference':'later-document-only'})
        with self.assertRaises(RevisionConflict):service.capture(self.ar.fx.document(changed,'ar-zero'))

    def test_zero_owner_remains_distinct_from_verified_absence(self):
        version,proof=self.source()
        owner=self.service.assess_absence(proof.export_version_id,proof.manifest_version_id,proof.control_version_id,zero_version=version)
        self.assertEqual(owner.outcome,'ABSENT_VERIFIED');self.assertEqual(owner.qualifying,0)
        self.assertNotEqual(owner.assessment_id,owner.zero_population_id)
        self.assertEqual(owner,self.service.get_absence(owner.assessment_id,current=True))
        self.assertEqual(self.session.scalar(select(tables.zero_absence.c.zero_id)),owner.zero_population_id)

    def test_empty_source_without_positive_zero_proof_still_refuses(self):
        _,proof=self.source()
        owner=self.service.assess_absence(proof.export_version_id,proof.manifest_version_id,proof.control_version_id)
        self.assertEqual(owner.outcome,'NOT_ASSESSED')
        self.assertIn('EMPTY_EXPORT_IS_NOT_ABSENCE',owner.blockers)

    def test_missing_source_is_not_zero_evidence(self):
        with self.assertRaises(ScopeError):ZeroARPopulationService(self.service).capture('missing')

    def test_untrusted_zero_control_or_completeness_refuses(self):
        version,_=self.source(authority='MANAGEMENT_ASSERTION')
        with self.assertRaises(ScopeError):ZeroARPopulationService(self.service).capture(version)

    def test_failed_extraction_refuses_zero(self):
        version,_=self.source(status='FAILED')
        with self.assertRaises(ScopeError):ZeroARPopulationService(self.service).capture(version)

    def test_unknown_extraction_refuses_zero(self):
        version,_=self.source(status='UNKNOWN')
        with self.assertRaises(ScopeError):ZeroARPopulationService(self.service).capture(version)

    def test_nonzero_control_refuses_empty_population(self):
        version,_=self.source(control='1')
        with self.assertRaises(ScopeError):ZeroARPopulationService(self.service).capture(version)

    def test_unknown_manifest_membership_refuses_zero(self):
        version,_=self.source(membership=None)
        with self.assertRaises(ScopeError):ZeroARPopulationService(self.service).capture(version)

    def test_nonzero_declared_source_membership_refuses_zero(self):
        version,_=self.source(count=1)
        with self.assertRaises(ScopeError):ZeroARPopulationService(self.service).capture(version)

    def test_source_authority_revocation_invalidates_current_zero(self):
        version,_=self.source();service=ZeroARPopulationService(self.service);value=service.capture(version)
        self.ar.fx.grants.clear()
        with self.assertRaises(ScopeError):service.get(value.zero_id,current=True)

    def test_zero_replay_no_duplicate_owner(self):
        version,_=self.source();service=ZeroARPopulationService(self.service);value=service.capture(version)
        self.assertEqual(service.capture(version),value)
        self.assertEqual(self.session.scalar(select(func.count()).select_from(tables.zero)),1)

    def test_zero_and_absence_rollback_together_in_caller_transaction(self):
        version,proof=self.source()
        self.service.assess_absence(proof.export_version_id,proof.manifest_version_id,proof.control_version_id,zero_version=version)
        self.session.rollback()
        for table in (tables.zero,tables.zero_absence,tables.audit):
            self.assertEqual(self.session.scalar(select(func.count()).select_from(table)),0)

    def test_zero_population_can_bind_governed_ar_semantic_view(self):
        version,proof=self.source()
        owner=self.service.assess_absence(proof.export_version_id,proof.manifest_version_id,proof.control_version_id,zero_version=version)
        evidence=self.evidence.model_copy(update={'scope':proof.scope,'record_version_id':proof.export_version_id,
            'manifest_version_id':proof.manifest_version_id,'control_version_id':proof.control_version_id,'owner_id':owner.assessment_id})
        semantic_version=self.ar.fx.document(evidence,'ar-semantics')
        view=ARSemanticVerifier(self.service).verify(semantic_version)
        self.assertEqual(view.contract.observed_row_count,0)
        self.assertEqual(view.contract.coverage.verified_value['completeness'],'COMPLETE')
        self.assertTrue(any(ref.source_id==version for ref in view.lineage))
