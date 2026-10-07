"""Durable production assessments use the frozen evaluator and real owner IDs."""
import unittest
from sqlalchemy import select, func, update
from sqlalchemy.exc import IntegrityError
from tests import test_production_temporal_v255 as fixture
from tests import test_ar_semantics_v255 as ar_fixture
from profit_doctor.persistence import production_history_schema as tables
from profit_doctor.reasoning.production_evidence.assessments import ProductionAssessment, ProductionAssessmentService
from profit_doctor.reasoning.production_evidence.ar_admission import ARProductionAdmission
from profit_doctor.reasoning.domain.service import ScopeError, RevisionConflict
from profit_doctor.reasoning.temporal.contracts import Window, ContractKey


class ProductionAssessmentsV255(fixture.fixture.ComponentFixture, unittest.TestCase):
    revenue_series=fixture.ProductionTemporalV255.revenue_series
    margin_series=fixture.ProductionTemporalV255.margin_series

    def setUp(self):
        super().setUp()
        self.assessments=ProductionAssessmentService(self.service)
        self.window=Window(start='2026-01-01',end='2026-03-31',cadence='MONTHLY')

    def revenue_assessment(self):
        return self.assessments.assess(fixture.REV,self.window,monthly_ids=self.revenue_series())

    def test_revenue_result_persists_exact_frozen_basis(self):
        value=self.revenue_assessment()
        self.assertEqual(self.assessments.get(value.assessment_id,current=True),value)
        self.assertEqual(ProductionAssessment.from_json(value.to_json()),value)
        self.assertEqual(value.result.trajectory,'INCREASING')
        self.assertEqual(value.result.interpretation,'NOT_ASSESSED')
        self.assertEqual(value.result,self.assessments.monthly.evaluate(fixture.REV,self.window,
            monthly_ids=tuple(o.source_id for o in value.result.basis.observations)))

    def test_c0_result_persists_exact_percentage_points(self):
        value=self.assessments.assess(fixture.C0,self.window,margin_ids=self.margin_series())
        self.assertEqual(self.assessments.get(value.assessment_id,current=True),value)
        self.assertEqual(value.result.interpretation,'IMPROVING')
        self.assertEqual([m.delta for m in value.result.movements],[1,1])

    def test_unchanged_replay_is_idempotent(self):
        ids=self.revenue_series()
        a=self.assessments.assess(fixture.REV,self.window,monthly_ids=ids)
        self.assertEqual(self.assessments.assess(fixture.REV,self.window,monthly_ids=ids),a)
        self.assertEqual(self.session.scalar(select(func.count()).select_from(tables.temporal)),1)

    def test_changed_basis_appends_history(self):
        ids=self.revenue_series()
        first=self.assessments.assess(fixture.REV,self.window,monthly_ids=ids[:2])
        second=self.assessments.assess(fixture.REV,self.window,monthly_ids=ids)
        self.assertEqual((second.revision,second.supersedes),(2,first.assessment_id))
        self.assertEqual(self.assessments.get(first.assessment_id),first)
        with self.assertRaises(RevisionConflict):self.assessments.get(first.assessment_id,current=True)

    def test_window_identity_is_distinct(self):
        ids=self.revenue_series()
        a=self.assessments.assess(fixture.REV,self.window,monthly_ids=ids)
        window=Window(start='2026-01-01',end='2026-02-28',cadence='MONTHLY')
        b=self.assessments.assess(fixture.REV,window,monthly_ids=ids[:2])
        self.assertNotEqual(a.series_id,b.series_id)
        self.assertEqual(b.revision,1)
        self.assertEqual(b.result.basis.window,window)

    def test_unqualified_margin_remains_not_assessed(self):
        self.components('3','2')
        margin=self.margin_service.qualify(self.bind().binding_id)
        value=self.assessments.assess(fixture.C0,self.window,margin_ids=(margin.margin_id,))
        self.assertEqual(value.result,self.assessments.monthly.evaluate(fixture.C0,self.window,margin_ids=(margin.margin_id,)))
        self.assertEqual(value.result.sequence,'INDETERMINATE')
        self.assertEqual(value.result.gaps,('2026-01','2026-03'))
        self.assertEqual(self.assessments.get(value.assessment_id),value)

    def test_unknown_or_diagnostic_owner_refuses(self):
        with self.assertRaises(ScopeError):self.assessments.assess(fixture.REV,self.window,monthly_ids=('REV-01',))

    def test_wrong_family_owner_refuses(self):
        with self.assertRaises(ScopeError):self.assessments.assess(fixture.REV,self.window,monthly_ids=(self.contribution.measurement_id,))

    def test_missing_reference_fk_rejected(self):
        value=self.revenue_assessment()
        with self.assertRaises(IntegrityError),self.session.begin_nested():
            self.session.execute(update(tables.temporal_reference).values(monthly_id='missing').where(
                tables.temporal_reference.c.assessment_id==value.assessment_id))

    def test_caller_rollback_removes_history_and_references(self):
        self.revenue_assessment();self.session.rollback()
        for table in (tables.temporal,tables.temporal_reference,tables.audit):
            self.assertEqual(self.session.scalar(select(func.count()).select_from(table)),0)


class ARProductionAssessmentsV255(unittest.TestCase):
    setUp=ar_fixture.ARSemanticCheckpointV255.setUp
    second=ar_fixture.ARSemanticCheckpointV255.second
    verify=ar_fixture.ARSemanticCheckpointV255.verify

    def test_ar_lifecycle_persists_scoped_projection_references(self):
        first=self.verify();second=self.second()
        admission=ARProductionAdmission(self.verifier)
        service=ProductionAssessmentService(self.service,ar=admission)
        window=Window(start='2026-01-01',end='2026-02-28',cadence='MONTHLY')
        value=service.assess(ContractKey.CASH_TRAPPED_RECEIVABLES_LIFECYCLE,window,
            semantic_version_ids=(first.semantic_version_id,second.semantic_version_id))
        self.assertEqual(service.get(value.assessment_id,current=True),value)
        self.assertEqual(value.result.sequence,'QUALIFIED')
        self.assertEqual(self.session.scalar(select(func.count()).select_from(tables.temporal_reference)),2)

    def test_same_date_semantic_restatement_appends_assessment_without_new_period(self):
        a=self.verify();b=self.second();admission=ARProductionAdmission(self.verifier)
        service=ProductionAssessmentService(self.service,ar=admission)
        window=Window(start='2026-01-01',end='2026-02-28',cadence='MONTHLY')
        first=service.assess(ContractKey.CASH_TRAPPED_RECEIVABLES_LIFECYCLE,window,
            semantic_version_ids=(a.semantic_version_id,b.semantic_version_id))
        corrected=self.evidence.model_copy(update={'revision':2,'predecessor_semantic_version_id':a.semantic_version_id,
            'change_kind':'RESTATEMENT','change_reference':'authenticated source definition correction'})
        version=self.ar.fx.document(corrected,'ar-semantics')
        second=service.assess(ContractKey.CASH_TRAPPED_RECEIVABLES_LIFECYCLE,window,
            semantic_version_ids=(version,b.semantic_version_id))
        self.assertEqual((second.revision,second.supersedes),(2,first.assessment_id))
        self.assertEqual(len(second.result.included),2)
        self.assertEqual(service.get(first.assessment_id),first)
        self.assertEqual(service.get(second.assessment_id,current=True),second)

    def test_owned_unknown_remains_indeterminate_and_has_no_amount(self):
        a=self.verify();admission=ARProductionAdmission(self.verifier)
        refused=self.evidence.model_copy(update={'family':'UNKNOWN'})
        receipt=admission.unknowns.capture(self.ar.fx.document(refused,'ar-semantics'))
        service=ProductionAssessmentService(self.service,ar=admission)
        value=service.assess(ContractKey.CASH_TRAPPED_RECEIVABLES_LIFECYCLE,
            Window(start='2026-01-01',end='2026-02-28',cadence='MONTHLY'),
            semantic_version_ids=(),unknown_ids=(receipt.unknown_id,))
        self.assertEqual(value.result.lifecycle,'INDETERMINATE')
        observation=value.result.basis.observations[0]
        self.assertEqual(observation.presence,'UNKNOWN');self.assertIsNone(observation.value)
        self.assertIsNone(observation.absence)
        self.assertEqual(service.get(value.assessment_id,current=True),value)
