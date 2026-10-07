"""Registered AR semantic checkpoint; synthetic issuer authority is test-only."""
from datetime import date
import csv
import unittest

from tests import test_monthly_absence_v255 as ar_tests
from alembic import command
from tests.test_postgresql_live_qualification_v218 import alembic_config
from profit_doctor.persistence import Client, EngineRun, DatabaseConfig, build_engine, session_factory
from profit_doctor.reasoning.domain.contracts import Actor
from profit_doctor.reasoning.domain.service import ScopeError, RevisionConflict
from profit_doctor.reasoning.production_evidence.service import ProductionEvidenceService
from profit_doctor.reasoning.production_evidence.ar_semantics import (
    ARSemanticEvidence, ARSemanticProjection, ARSemanticVerifier, AR_FAMILY, PROJECTION_DOMAIN)
from profit_doctor.reasoning.dataset.comparability import assess_dataset_comparability
from profit_doctor.reasoning.dataset.contracts import DatasetContract


class ARSemanticCheckpointV255(unittest.TestCase):
    target_url=None
    def setUp(self):
        self.ar = ar_tests.ReceivablesAbsenceV255('runTest'); self.ar.setUp(); self.addCleanup(self.ar.doCleanups)
        url = getattr(self,'target_url',None) or ('sqlite+pysqlite:///'+(self.ar.fx.fx.root/'ar-canonical.db').as_posix())
        command.upgrade(alembic_config(url),'head')
        engine = build_engine(DatabaseConfig(url)); self.addCleanup(engine.dispose)
        factory = session_factory(engine)
        timestamp = '2026-10-01T00:00:00+00:00'
        with factory.begin() as session:
            session.add(Client(client_id='c1',client_name='Client',base_currency='GBP',created_at=timestamp))
            session.add(EngineRun(run_id='r1',client_id='c1',run_type='ADVISORY',started_at=timestamp,status='RUNNING',engine_version='2.55'))
        self.session = factory(); self.addCleanup(self.session.close)
        self.actor = Actor(actor_type='SYSTEM',actor_id='source-evidence-owner',source_authority='SYSTEM_DERIVED')
        self.service = ProductionEvidenceService(self.session, self.ar.fx.con, 'c1', 'r1', self.actor, self.ar.fx.authority)
        self.verifier = ARSemanticVerifier(self.service)
        self.mv = self.ar.fx.document(self.ar.manifest, 'ar-manifest')
        self.cv = self.ar.fx.document(self.ar.control, 'ar-control')
        self.owner = self.service.assess_absence(self.ar.ev, self.mv, self.cv)
        self.evidence = ARSemanticEvidence(scope=self.ar.scope, record_version_id=self.ar.ev,
            manifest_version_id=self.mv, control_version_id=self.cv, system_id='system1', report_id='open-ar',
            owner_kind='ABSENT_VERIFIED', owner_id=self.owner.assessment_id,
            population_definition='Complete entity e1 ledger l1 open receivables',
            inclusion_exclusion='All open invoice balances; no report exclusions', definition_reference='source-ar-policy-1',
            family='OPEN_RECEIVABLES', balance_basis='OUTSTANDING_BALANCE',
            contractual_basis='CONTRACTUAL_DUE_DATE', time_basis='POINT_IN_TIME_STOCK', unit='MONEY')

    def verify(self, evidence=None, authority='SOURCE_DATA'):
        version = self.ar.fx.document(evidence or self.evidence, 'ar-semantics', authority)
        return self.verifier.verify(version)

    def second(self, *, invoice_id='inv2', definition=None, entity='e1', ledger='l1', inclusion=None, month=2):
        from calendar import monthrange
        scope = self.ar.scope.model_copy(update={'as_of':date(2026,month,monthrange(2026,month)[1]),'entity_id':entity,'ledger_id':ledger})
        invoice = self.ar.invoice.model_copy(update={'invoice_id':invoice_id,'as_of':scope.as_of,
            'explicit_due':date(2026,month+1,1),'status':self.ar.invoice.status.model_copy(update={'reviewed_at':scope.as_of})})
        review = self.ar.review.model_copy(update={'invoice_id':invoice_id,'reviewed_at':scope.as_of})
        export = self.ar.export.model_copy(update={'scope':scope,'invoices':(invoice,),'reviews':(review,)})
        ev = self.ar.fx.document(export,'ar-export')
        manifest = self.ar.manifest.model_copy(update={'scope':scope,'record_version_id':ev,
            'open_items':(('customer1',invoice_id),),'extraction_as_of':scope.as_of})
        mv = self.ar.fx.document(manifest,'ar-manifest')
        cv = self.ar.fx.document(self.ar.control.model_copy(update={'scope':scope}),'ar-control')
        owner = self.service.assess_absence(ev,mv,cv)
        evidence = self.evidence.model_copy(update={'scope':scope,'record_version_id':ev,
            'manifest_version_id':mv,'control_version_id':cv,'owner_id':owner.assessment_id,
            'population_definition':definition or self.evidence.population_definition,
            'inclusion_exclusion':inclusion or self.evidence.inclusion_exclusion})
        return self.verify(evidence)

    def presence(self, *, origin='REAL_SOURCE', authority='SOURCE_DATA', month=2):
        from calendar import monthrange
        from profit_doctor.reasoning.receivables.contracts import Snapshot
        from profit_doctor.reasoning.receivables.service import ReceivablesService
        from profit_doctor.reasoning.impact.service import ImpactService
        from profit_doctor.reasoning.impact.contracts import Source
        provider = ReceivablesService(self.service.contexts)
        impacts = ImpactService(self.service.contexts.foundation,'r1',receivables=provider)
        scope = self.ar.scope.model_copy(update={'as_of':date(2026,month,monthrange(2026,month)[1])})
        invoice = self.ar.invoice.model_copy(update={'as_of':scope.as_of,'explicit_due':date(2026,month,1),
            'status':self.ar.invoice.status.model_copy(update={'reviewed_at':scope.as_of})})
        snapshot = Snapshot(client_id='c1',run_id='r1',ledger_id=scope.ledger_id,entity=scope.entity_id,
            as_of=scope.as_of,scope=scope.population,coverage='COMPLETE',coverage_basis='source-controlled-open-items',
            source_version='original1',origin=origin,invoices=(invoice,),control_amount=100,
            control_reference='independent-control',dataset_version_id='pending')
        path = self.ar.fx.fx.root/'presence.csv'
        with path.open('w',encoding='utf-8',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=['snapshot']);writer.writeheader();writer.writerow({'snapshot':snapshot.to_json()})
        snapshot = provider.ingest_csv(path,self.ar.fx.fx.root/'presence-store')
        q = impacts.assess(Source(kind='RECEIVABLES',source_id=snapshot.series_id),'CASH_TRAPPED')
        meta = self.service.contexts.source.dataset(snapshot.dataset_version_id)
        self.ar.fx.grants[snapshot.dataset_version_id]=(meta['logical_dataset_key'],meta['file_hash'],authority)
        manifest=self.ar.manifest.model_copy(update={'scope':scope,'extraction_as_of':scope.as_of,
            'record_version_id':snapshot.dataset_version_id})
        mv=self.ar.fx.document(manifest,'ar-manifest')
        cv=self.ar.fx.document(self.ar.control.model_copy(update={'scope':scope}),'ar-control')
        evidence=self.evidence.model_copy(update={'scope':scope,'record_version_id':snapshot.dataset_version_id,
            'manifest_version_id':mv,'control_version_id':cv,'owner_kind':'CASH_TRAPPED_IMPACT','owner_id':q.impact.impact_id})
        verifier=ARSemanticVerifier(self.service,impacts=impacts)
        version=self.ar.fx.document(evidence,'ar-semantics')
        return verifier,version,q

    def test_qualified_presence_binds_impact_without_recalculating_it(self):
        verifier,version,q=self.presence()
        projection=verifier.verify(version)
        self.assertEqual(projection.owner_id,q.impact.impact_id)
        self.assertEqual(q.impact.amount.value,100)
        self.assertEqual(projection.original_domain,'D04_AR_SNAPSHOT')
        self.assertEqual(projection.contract.family.verified_value,AR_FAMILY)

    def test_cross_route_views_compare_without_rewriting_raw_domains(self):
        absence=self.verify(); verifier,version,q=self.presence(); presence=verifier.verify(version)
        self.assertNotEqual(presence.original_domain,absence.original_domain)
        self.assertNotEqual(presence.original_refs,absence.original_refs)
        self.assertNotEqual(presence.owner_kind,absence.owner_kind)
        result=assess_dataset_comparability(absence.contract,presence.contract)
        self.assertEqual(result.outcome,'COMPARABLE')
        self.assertEqual(len(result.dimensions),11)

    def test_synthetic_presence_cannot_form_production_projection(self):
        verifier,version,_=self.presence(origin='BLIND_QUALIFICATION')
        with self.assertRaises(ScopeError):verifier.verify(version)

    def test_untrusted_snapshot_cannot_be_promoted_by_trusted_manifest(self):
        verifier,version,_=self.presence(authority='MANAGEMENT_ASSERTION')
        with self.assertRaises(ScopeError):verifier.verify(version)

    def test_changing_membership_does_not_change_population_definition(self):
        left, right = self.verify(), self.second()
        self.assertNotEqual(left.contract.source_version,right.contract.source_version)
        result = assess_dataset_comparability(left.contract,right.contract)
        self.assertEqual(result.outcome,'COMPARABLE')
        self.assertEqual(len(result.dimensions),11)
        self.assertEqual(result.temporal_evidence_role,'NEW_OBSERVATION')

    def test_identical_membership_cannot_override_different_population(self):
        left, right = self.verify(), self.second(invoice_id='inv1',definition='Different commercial population')
        result = assess_dataset_comparability(left.contract,right.contract)
        self.assertEqual(result.outcome,'NOT_COMPARABLE')
        self.assertEqual(result.dimensions['POPULATION'].state,'MISMATCH')

    def test_identical_totals_cannot_override_different_entity(self):
        left, right = self.verify(), self.second(invoice_id='inv1',entity='e2')
        result = assess_dataset_comparability(left.contract,right.contract)
        self.assertEqual(result.outcome,'NOT_COMPARABLE')
        self.assertEqual(result.dimensions['ORGANISATIONAL_SCOPE'].state,'MISMATCH')

    def test_different_ledger_does_not_compare(self):
        result = assess_dataset_comparability(self.verify().contract,self.second(ledger='l2').contract)
        self.assertEqual(result.outcome,'NOT_COMPARABLE')

    def test_inclusion_exclusion_difference_preserved_by_frozen_comparator(self):
        result = assess_dataset_comparability(self.verify().contract,self.second(inclusion='Different report selection').contract)
        self.assertEqual(result.outcome,'NOT_COMPARABLE')
        self.assertEqual(result.dimensions['INCLUSION_EXCLUSION'].state,'MISMATCH')

    def test_projection_provider_never_claims_same_physical_file(self):
        left, right = self.verify(), self.second()
        self.assertNotEqual(left.contract.source_file.source_id,right.contract.source_file.source_id)
        self.assertEqual(left.contract.source_provider.verified_value,
            {'semantic_view':'AR-SEMANTIC-PROJECTION-2.55.1','system':'system1'})

    def test_registered_complete_absence_population_qualifies_semantic_view(self):
        projection = self.verify()
        self.assertEqual(projection.contract.family.verified_value, AR_FAMILY)
        self.assertEqual(projection.contract.source_data_domain, PROJECTION_DOMAIN)
        self.assertEqual(projection.original_domain, 'PRODUCTION_ACCOUNTING_RECORDS_V255')
        self.assertEqual(projection.original_route, 'production-evidence:ar-export-1')
        self.assertEqual(projection.contract.observed_row_count, 1)
        self.assertEqual(self.owner.outcome, 'ABSENT_VERIFIED')
        self.assertEqual(self.owner.total, 100)
        self.assertEqual(self.owner.qualifying, 0)

    def test_original_source_ids_retained_and_not_replaced(self):
        projection = self.verify()
        self.assertEqual(projection.contract.source_version.source_id, self.ar.ev)
        self.assertNotEqual(projection.projection_id, self.ar.ev)
        self.assertTrue(all(r in projection.lineage for r in projection.original_refs))
        row = self.ar.fx.con.execute('SELECT data_domain FROM dataset WHERE dataset_id=?',
            (projection.contract.source_dataset.source_id,)).fetchone()
        self.assertEqual(row[0], projection.original_domain)

    def test_deterministic_replay_and_round_trip(self):
        version = self.ar.fx.document(self.evidence, 'ar-semantics')
        first = self.verifier.verify(version)
        self.assertEqual(first, self.verifier.verify(version))
        self.assertEqual(first, ARSemanticProjection.from_json(first.to_json()))

    def test_declaration_only_authority_cannot_qualify(self):
        with self.assertRaises(ScopeError): self.verify(authority='MANAGEMENT_ASSERTION')

    def test_missing_authority_cannot_qualify(self):
        version = self.ar.fx.document(self.evidence, 'ar-semantics')
        self.ar.fx.grants.clear()
        with self.assertRaises((ScopeError, RevisionConflict)): self.verifier.verify(version)

    def test_wrong_semantic_values_refuse(self):
        for field in ('family', 'balance_basis', 'contractual_basis', 'time_basis', 'unit'):
            with self.subTest(field=field), self.assertRaises(ScopeError):
                self.verify(self.evidence.model_copy(update={field:'UNKNOWN'}))

    def test_cross_client_refuses(self):
        evidence = self.evidence.model_copy(update={'scope':self.evidence.scope.model_copy(update={'client_id':'c2'})})
        with self.assertRaises(ScopeError): self.verify(evidence)

    def test_wrong_scope_refuses(self):
        for field, value in (('entity_id','other'), ('ledger_id','other'), ('population','subset')):
            with self.subTest(field=field), self.assertRaises(ScopeError):
                self.verify(self.evidence.model_copy(update={'scope':self.evidence.scope.model_copy(update={field:value})}))

    def test_wrong_reporting_date_refuses(self):
        with self.assertRaises(ScopeError):
            self.verify(self.evidence.model_copy(update={'scope':self.evidence.scope.model_copy(update={'as_of':date(2026,2,28)})}))

    def test_binding_requires_exact_source_evidence_versions(self):
        with self.assertRaises(ScopeError): self.verify(self.evidence.model_copy(update={'record_version_id':'wrong-source'}))

    def test_matching_client_and_date_do_not_bind_other_owner(self):
        with self.assertRaises(ScopeError): self.verify(self.evidence.model_copy(update={'owner_id':'other-owner'}))

    def test_source_system_mismatch_refuses(self):
        with self.assertRaises(ScopeError): self.verify(self.evidence.model_copy(update={'system_id':'other-source'}))

    def test_contradictory_declaration_fails_closed(self):
        with self.assertRaises(ScopeError): self.verify(self.evidence.model_copy(update={'declarations':{'population':'subset'}}))

    def test_unsupported_declaration_dimension_fails_closed(self):
        with self.assertRaises(ScopeError): self.verify(self.evidence.model_copy(update={'declarations':{'score':'100'}}))

    def test_ar_presence_requires_registered_impact_provider(self):
        with self.assertRaises(ScopeError): self.verify(self.evidence.model_copy(update={'owner_kind':'CASH_TRAPPED_IMPACT'}))

    def test_ar_source_route_cannot_be_ordinary_accounting_profile(self):
        version = self.ar.fx.document(self.evidence, 'manifest')
        with self.assertRaises(ScopeError): self.verifier.verify(version)

    def test_missing_registered_semantic_source_refuses(self):
        with self.assertRaises(ScopeError): self.verifier.verify('not-registered')

    def test_caller_cannot_inject_values_or_projection(self):
        with self.assertRaises(TypeError): self.verifier.verify('source', value=100)
        with self.assertRaises(TypeError): self.verifier.verify(self.evidence)

    def test_frozen_raw_domain_refusal_remains_unchanged(self):
        from tests.test_dataset_contract_v253 import contract, T
        left = contract('presence',month=1).model_copy(update={'source_data_domain':'D04_AR_SNAPSHOT'})
        right = contract('absence',month=2).model_copy(update={'source_data_domain':'PRODUCTION_ACCOUNTING_RECORDS_V255'})
        result = assess_dataset_comparability(DatasetContract.from_json(left.to_json()),
            DatasetContract.from_json(right.to_json()),assessed_at=T)
        self.assertEqual(result.outcome,'NOT_COMPARABLE')
        self.assertEqual(result.dimensions['SOURCE_LINEAGE'].reason,'SOURCE_DATA_DOMAIN_DIFFERS')
        self.assertEqual(len(result.dimensions),11)

    def test_incomplete_projection_lineage_rejects_deserialization(self):
        data = self.verify().model_dump(); data['lineage'] = ()
        with self.assertRaises(ValueError): ARSemanticProjection.model_validate(data)

    def test_original_domain_cannot_be_erased(self):
        data = self.verify().model_dump(); data['original_domain'] = PROJECTION_DOMAIN
        with self.assertRaises(ValueError): ARSemanticProjection.model_validate(data)

    def test_no_temporal_admission_or_impact_creation_by_verifier(self):
        projection = self.verify()
        self.assertNotEqual(projection.owner_id, projection.projection_id)
        self.assertEqual(self.service.get_absence(self.owner.assessment_id,current=True),self.owner)
        self.assertFalse(hasattr(self.verifier,'evaluate'))
        self.assertFalse(hasattr(self.verifier,'aggregate'))

    def window(self, start_month, end_month):
        from calendar import monthrange
        from profit_doctor.reasoning.temporal.contracts import Window
        return Window(start=date(2026,start_month,1),end=date(2026,end_month,monthrange(2026,end_month)[1]),cadence='MONTHLY')

    def test_typed_admission_reaches_shared_frozen_lifecycle(self):
        from profit_doctor.reasoning.production_evidence.ar_admission import ARProductionAdmission
        verifier, version, _ = self.presence()
        result = ARProductionAdmission(verifier).evaluate(self.window(1,2),
            (self.ar.fx.document(self.evidence,'ar-semantics'),version))
        self.assertEqual(result.sequence,'QUALIFIED')
        self.assertEqual(result.lifecycle,'NEW')
        self.assertEqual(result.basis.origin,'QUALIFIED_PRODUCTION_V255')
        self.assertEqual(result.basis.observations[0].dataset.family.verified_value,AR_FAMILY)

    def test_present_present_is_persistent(self):
        from profit_doctor.reasoning.production_evidence.ar_admission import ARProductionAdmission
        _, first, _ = self.presence(month=2)
        verifier, second, _ = self.presence(month=3)
        result=ARProductionAdmission(verifier).evaluate(self.window(2,3),(first,second))
        self.assertEqual(result.sequence,'QUALIFIED');self.assertEqual(result.lifecycle,'PERSISTENT')

    def test_present_verified_absence_is_resolved(self):
        from profit_doctor.reasoning.production_evidence.ar_admission import ARProductionAdmission
        verifier, first, _ = self.presence(month=2)
        absence=self.second(month=3)
        result=ARProductionAdmission(verifier).evaluate(self.window(2,3),(first,absence.semantic_version_id))
        self.assertEqual(result.sequence,'QUALIFIED');self.assertEqual(result.lifecycle,'RESOLVED')
        self.assertEqual(next(o for o in result.basis.observations if o.source_kind=='ABSENCE').absence.origin,'QUALIFIED_PRODUCTION_V255')

    def test_present_absent_present_is_recurrent(self):
        from profit_doctor.reasoning.production_evidence.ar_admission import ARProductionAdmission
        _, first, _ = self.presence(month=2)
        absence=self.second(month=3)
        verifier, last, _ = self.presence(month=4)
        result=ARProductionAdmission(verifier).evaluate(self.window(2,4),(first,absence.semantic_version_id,last))
        self.assertEqual(result.sequence,'QUALIFIED');self.assertEqual(result.lifecycle,'RECURRENT')

    def test_missing_month_cannot_establish_recurrence(self):
        from profit_doctor.reasoning.production_evidence.ar_admission import ARProductionAdmission
        _, first, _ = self.presence(month=2)
        verifier, last, _ = self.presence(month=4)
        result=ARProductionAdmission(verifier).evaluate(self.window(2,4),(first,last))
        self.assertEqual(result.lifecycle,'INDETERMINATE');self.assertIn('2026-03',result.gaps)

    def test_ar_labels_without_typed_admission_remain_ineligible(self):
        from profit_doctor.reasoning.production_evidence.ar_admission import ARProductionAdmission
        from profit_doctor.reasoning.temporal.engine import _evaluate_sequence
        from profit_doctor.reasoning.production_evidence.temporal import ProductionTemporalResult
        verifier,version,_=self.presence()
        result=ARProductionAdmission(verifier).evaluate(self.window(2,2),(version,))
        refused=_evaluate_sequence(result.basis,result_model=ProductionTemporalResult)
        self.assertEqual(refused.lifecycle,'NOT_ASSESSED')
        self.assertIn('DATASET_FAMILY_OUTSIDE_CONTRACT',refused.reasons)

    def test_arbitrary_text_cannot_enable_admission(self):
        from profit_doctor.reasoning.production_evidence.ar_admission import ARProductionAdmission
        from profit_doctor.reasoning.temporal.engine import _evaluate_sequence
        verifier,version,_=self.presence()
        result=ARProductionAdmission(verifier).evaluate(self.window(2,2),(version,))
        with self.assertRaises(ValueError):_evaluate_sequence(result.basis,ar_admission='AR')

    def test_forged_observation_amount_rejected_at_kernel_entry(self):
        from profit_doctor.reasoning.production_evidence.ar_admission import ARProductionAdmission
        from profit_doctor.reasoning.temporal.engine import _evaluate_sequence
        verifier,version,_=self.presence();admission=ARProductionAdmission(verifier)
        result=admission.evaluate(self.window(2,2),(version,))
        o=result.basis.observations[0].model_copy(update={'value':200})
        basis=result.basis.model_copy(update={'observations':(o,)})
        with self.assertRaises(RevisionConflict):_evaluate_sequence(basis,ar_admission=admission)

    def test_expired_authority_rejected_at_admission(self):
        from profit_doctor.reasoning.production_evidence.ar_admission import ARProductionAdmission
        verifier,version,_=self.presence();self.ar.fx.grants.clear()
        with self.assertRaises(ScopeError):ARProductionAdmission(verifier).evaluate(self.window(2,2),(version,))

    def test_duplicate_version_request_refuses(self):
        from profit_doctor.reasoning.production_evidence.ar_admission import ARProductionAdmission
        verifier,version,_=self.presence()
        with self.assertRaises(ValueError):ARProductionAdmission(verifier).evaluate(self.window(2,2),(version,version))
