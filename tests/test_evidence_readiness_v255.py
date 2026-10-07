"""Readiness derives capability from owned evidence, never business conclusions."""
import unittest
from sqlalchemy import select, func
from tests import test_production_temporal_v255 as fixture
from tests import test_ar_semantics_v255 as ar_fixture
from profit_doctor.persistence import production_history_schema as tables
from profit_doctor.reasoning.production_evidence.assessments import ProductionAssessmentService
from profit_doctor.reasoning.production_evidence.ar_admission import ARProductionAdmission
from profit_doctor.reasoning.production_evidence.readiness import (
    EvidenceReadinessService, EvidenceReadiness, ReadinessDomain as D, ReadinessReference as R)
from profit_doctor.reasoning.domain.service import ScopeError, RevisionConflict
from profit_doctor.reasoning.temporal.contracts import Window, ContractKey


class EvidenceReadinessV255(fixture.fixture.ComponentFixture,unittest.TestCase):
    revenue_series=fixture.ProductionTemporalV255.revenue_series
    margin_series=fixture.ProductionTemporalV255.margin_series

    def setUp(self):
        super().setUp()
        self.assessments=ProductionAssessmentService(self.service)
        self.ready=EvidenceReadinessService(self.assessments)
        self.window=Window(start='2026-01-01',end='2026-03-31',cadence='MONTHLY')

    def test_monthly_revenue_verified(self):
        value=self.ready.assess(D.REVENUE_MONTHLY_MEASUREMENT,(R(kind='MONTHLY',owner_id=self.revenue.measurement_id),))
        self.assertEqual(value.status,'VERIFIED')
        self.assertEqual(value.capabilities_unlocked,(D.REVENUE_MONTHLY_MEASUREMENT.value,))
        self.assertEqual(self.ready.get(value.readiness_id,current=True),value)
        self.assertEqual(EvidenceReadiness.from_json(value.to_json()),value)

    def test_monthly_c0_verified_independent_of_margin(self):
        value=self.ready.assess(D.CONTRIBUTION_0_MONTHLY_MEASUREMENT,(R(kind='MONTHLY',owner_id=self.contribution.measurement_id),))
        self.assertEqual(value.status,'VERIFIED')

    def test_two_months_do_not_unlock_revenue_temporal(self):
        ids=self.revenue_series()
        assessment=self.assessments.assess(fixture.REV,self.window,monthly_ids=ids[:2])
        value=self.ready.assess(D.REVENUE_TEMPORAL,(R(kind='TEMPORAL',owner_id=assessment.assessment_id),))
        self.assertEqual(value.status,'INSUFFICIENT')
        self.assertIn('SUFFICIENT_COMPLETE_COMPARABLE_OBSERVATIONS_REQUIRED',value.missing_prerequisites)

    def test_three_comparable_months_unlock_revenue_temporal(self):
        assessment=self.assessments.assess(fixture.REV,self.window,monthly_ids=self.revenue_series())
        value=self.ready.assess(D.REVENUE_TEMPORAL,(R(kind='TEMPORAL',owner_id=assessment.assessment_id),))
        self.assertEqual(value.status,'VERIFIED')
        self.assertNotIn('INCREASING',value.to_json())
        self.assertNotIn('amount',EvidenceReadiness.model_fields)
        self.assertNotIn('score',EvidenceReadiness.model_fields)

    def test_nonterminating_margin_is_insufficient(self):
        self.components('3','2')
        margin=self.margin_service.qualify(self.bind().binding_id)
        value=self.ready.assess(D.CONTRIBUTION_0_MARGIN_MEASUREMENT,(R(kind='MARGIN',owner_id=margin.margin_id),))
        self.assertEqual(value.status,'INSUFFICIENT')
        self.assertEqual(value.missing_prerequisites,margin.reasons)
        self.assertEqual(value.capabilities_unlocked,())

    def test_margin_refusal_cannot_unlock_temporal(self):
        self.components('3','2');margin=self.margin_service.qualify(self.bind().binding_id)
        assessment=self.assessments.assess(fixture.C0,self.window,margin_ids=(margin.margin_id,))
        value=self.ready.assess(D.CONTRIBUTION_0_TEMPORAL,(R(kind='TEMPORAL',owner_id=assessment.assessment_id),))
        self.assertEqual(value.status,'INSUFFICIENT')

    def test_missing_evidence_not_provided(self):
        value=self.ready.assess(D.REVENUE_MONTHLY_MEASUREMENT)
        self.assertEqual(value.status,'NOT_PROVIDED')
        self.assertEqual(value.missing_prerequisites,('REGISTERED_OWNED_EVIDENCE_NOT_PROVIDED',))

    def test_narrow_components_do_not_prove_full_finance_pack(self):
        value=self.ready.assess(D.CORE_ACCOUNTING_EVIDENCE,(R(kind='MONTHLY',owner_id=self.revenue.measurement_id),))
        self.assertEqual(value.status,'PARTIAL')
        self.assertIn('FULL_ACCOUNTING_PACK_SCOPE_NOT_ESTABLISHED',value.missing_prerequisites)

    def test_wrong_owner_family_refuses(self):
        with self.assertRaises(ScopeError):self.ready.assess(D.REVENUE_MONTHLY_MEASUREMENT,
            (R(kind='MONTHLY',owner_id=self.contribution.measurement_id),))

    def test_unknown_and_synthetic_ids_refuse(self):
        with self.assertRaises(ScopeError):self.ready.assess(D.REVENUE_MONTHLY_MEASUREMENT,
            (R(kind='MONTHLY',owner_id='synthetic-positive'),))

    def test_no_caller_status_flag(self):
        with self.assertRaises(TypeError):self.ready.assess(D.REVENUE_TEMPORAL,status='VERIFIED')

    def test_duplicate_references_refuse(self):
        ref=R(kind='MONTHLY',owner_id=self.revenue.measurement_id)
        with self.assertRaises(ValueError):self.ready.assess(D.REVENUE_MONTHLY_MEASUREMENT,(ref,ref))

    def test_replay_is_idempotent(self):
        refs=(R(kind='MONTHLY',owner_id=self.revenue.measurement_id),)
        first=self.ready.assess(D.REVENUE_MONTHLY_MEASUREMENT,refs)
        self.assertEqual(self.ready.assess(D.REVENUE_MONTHLY_MEASUREMENT,refs),first)
        self.assertEqual(self.session.scalar(select(func.count()).select_from(tables.readiness)),1)

    def test_new_evidence_appends_readiness_history(self):
        first=self.ready.assess(D.REVENUE_MONTHLY_MEASUREMENT)
        second=self.ready.assess(D.REVENUE_MONTHLY_MEASUREMENT,(R(kind='MONTHLY',owner_id=self.revenue.measurement_id),))
        self.assertEqual((first.status,second.status),('NOT_PROVIDED','VERIFIED'))
        self.assertEqual((second.revision,second.supersedes),(2,first.readiness_id))
        self.assertEqual(self.ready.get(first.readiness_id),first)
        with self.assertRaises(RevisionConflict):self.ready.get(first.readiness_id,current=True)

    def test_changed_source_authority_creates_conflict_not_positive(self):
        refs=(R(kind='MONTHLY',owner_id=self.revenue.measurement_id),)
        first=self.ready.assess(D.REVENUE_MONTHLY_MEASUREMENT,refs)
        self.fx.fx.grants.clear()
        second=self.ready.assess(D.REVENUE_MONTHLY_MEASUREMENT,refs)
        self.assertEqual(second.status,'CONFLICTED')
        self.assertEqual(second.supersedes,first.readiness_id)
        self.assertTrue(second.conflicts)
        self.assertEqual(second.capabilities_unlocked,())

    def test_caller_rollback_removes_readiness(self):
        self.ready.assess(D.REVENUE_MONTHLY_MEASUREMENT,(R(kind='MONTHLY',owner_id=self.revenue.measurement_id),))
        self.session.rollback()
        for table in (tables.readiness,tables.readiness_reference,tables.audit):
            self.assertEqual(self.session.scalar(select(func.count()).select_from(table)),0)


class ARReadinessV255(unittest.TestCase):
    setUp=ar_fixture.ARSemanticCheckpointV255.setUp
    verify=ar_fixture.ARSemanticCheckpointV255.verify
    second=ar_fixture.ARSemanticCheckpointV255.second

    def readiness(self):
        return EvidenceReadinessService(ProductionAssessmentService(self.service,ar=ARProductionAdmission(self.verifier)))

    def test_complete_snapshot_and_absence_have_separate_domains(self):
        service=self.readiness();ref=R(kind='ABSENCE',owner_id=self.owner.assessment_id)
        snapshot=service.assess(D.RECEIVABLES_SNAPSHOT,(ref,))
        absence=service.assess(D.RECEIVABLES_ABSENCE,(ref,))
        self.assertEqual((snapshot.status,absence.status),('VERIFIED','VERIFIED'))
        self.assertNotEqual(snapshot.readiness_id,absence.readiness_id)
        self.assertEqual(service.get(absence.readiness_id,current=True),absence)

    def test_usable_lifecycle_unlocks_capability_not_conclusion(self):
        a=self.verify();b=self.second();service=self.readiness()
        assessment=service.assessments.assess(ContractKey.CASH_TRAPPED_RECEIVABLES_LIFECYCLE,
            Window(start='2026-01-01',end='2026-02-28',cadence='MONTHLY'),
            semantic_version_ids=(a.semantic_version_id,b.semantic_version_id))
        value=service.assess(D.RECEIVABLES_LIFECYCLE,(R(kind='TEMPORAL',owner_id=assessment.assessment_id),))
        self.assertEqual(value.status,'VERIFIED')
        self.assertNotIn('RECURRENT',value.to_json())

    def test_unresolved_status_does_not_invalidate_complete_snapshot(self):
        from datetime import date
        scope=self.ar.scope.model_copy(update={'as_of':date(2026,2,28)})
        invoice=self.ar.invoice.model_copy(update={'as_of':scope.as_of,
            'status':self.ar.invoice.status.model_copy(update={'status':'UNKNOWN','reviewed_at':scope.as_of})})
        review=self.ar.review.model_copy(update={'reviewed_at':scope.as_of})
        export=self.ar.export.model_copy(update={'scope':scope,'invoices':(invoice,),'reviews':(review,)})
        ev=self.ar.fx.document(export,'ar-export')
        manifest=self.ar.manifest.model_copy(update={'scope':scope,'record_version_id':ev,'extraction_as_of':scope.as_of})
        control=self.ar.fx.document(self.ar.control.model_copy(update={'scope':scope}),'ar-control')
        owner=self.service.assess_absence(ev,self.ar.fx.document(manifest,'ar-manifest'),control)
        self.assertIn('STATUS_REVIEW_INCOMPLETE:inv1',owner.blockers)
        service=self.readiness();ref=R(kind='ABSENCE',owner_id=owner.assessment_id)
        self.assertEqual(service.assess(D.RECEIVABLES_SNAPSHOT,(ref,)).status,'VERIFIED')
        self.assertEqual(service.assess(D.RECEIVABLES_ABSENCE,(ref,)).status,'INSUFFICIENT')
