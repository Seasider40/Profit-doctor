"""Synthetic architecture fixtures only. No v2.50 blind workbook access."""
import csv
from datetime import date
from decimal import Decimal
import unittest
from sqlalchemy import select, func, update
from sqlalchemy.exc import IntegrityError
from tests import test_receivables_v249 as fixtures
from profit_doctor.reasoning.opportunity.service import OpportunityService
from profit_doctor.reasoning.opportunity.contracts import CollectionEvidence, Assessment
from profit_doctor.reasoning.domain.service import ScopeError, RevisionConflict
from profit_doctor.persistence import opportunity_schema as tables


class OpportunityV250(unittest.TestCase):
    target_url=fixtures.ReceivablesV249.target_url
    prepare_target=fixtures.ReceivablesV249.prepare_target
    data=fixtures.ReceivablesV249.data
    ingest=fixtures.ReceivablesV249.ingest
    assess=fixtures.ReceivablesV249.assess

    def setUp(self):
        fixtures.ReceivablesV249.setUp(self)
        data=self.data(outstanding='100',terms=dict(reference='synthetic-terms',days=30,effective_from='2026-01-01',effective_to='2026-12-31'))
        self.snapshot=self.ingest(data)
        self.impact=self.assess(self.snapshot)
        self.service=OpportunityService(self.impacts)
        self.candidate=self.service.create_candidate(self.impact.impact.impact_id,'2026-12-31',90)

    def evidence(self,**updates):
        source=dict(reference='synthetic-source-record',authority='SOURCE_RECORD',observed_on='2026-12-31')
        pairs=[]
        for n,amount in enumerate(('60','70','80')):
            base=dict(customer_id='customer-1',exposure='100',days_overdue_at_start=61,terms_days=30,
                status='ORDINARY_UNCONSTRAINED',started_on='2025-01-01',observed_through='2025-04-01',evidence=source)
            pairs.append(dict(treated={**base,'case_id':f't{n}','invoice_id':f'treated{n}','intervention':'ORDINARY_COLLECTION','cash_received':amount},
                comparison={**base,'case_id':f'c{n}','invoice_id':f'comparison{n}','intervention':'BUSINESS_AS_USUAL','cash_received':'20'},matching_evidence=source))
        review=dict(invoice_id='invoice-1',customer_id='customer-1',addressability='ORDINARY_COLLECTION',authority_evidence=source,
            initiative='NO_QUALIFYING_PRIOR_INITIATIVE_EVIDENCED',initiative_review=source,initiative_review_complete=True,
            cohort_pairs=pairs,cohort_coverage='COMPLETE_INCEPTION_COHORT',cohort_manifest=source,eligible_pair_count=3,
            comparability_basis='Synthetic complete inception cohort, matched customer, balance, ageing, terms and time window')
        value=dict(client_id='c1',run_id='r1',impact_id=self.impact.impact.impact_id,assessed_on='2026-12-31',horizon_days=90,
            origin='BLIND_QUALIFICATION',coverage='COMPLETE',source_version='synthetic-1',dataset_version_id='pending',reviews=[review])
        value.update(updates)
        return value

    def retain(self,data):
        value=CollectionEvidence.model_validate(data)
        path=self.directory/'collection.csv'
        with path.open('w',encoding='utf-8',newline='') as stream:
            w=csv.DictWriter(stream,fieldnames=['collection']);w.writeheader();w.writerow({'collection':value.to_json()})
        return self.service.ingest_evidence(path,self.directory/'store')

    def qualify(self,data=None,**kwargs):
        e=self.retain(data or self.evidence())
        return self.service.qualify(self.candidate.candidate_id,e.evidence_id,**kwargs)

    def test_impact_without_opportunity(self):
        q=self.service.qualify(self.candidate.candidate_id)
        self.assertIsNone(q.opportunity_id);self.assertEqual(Decimal('100'),q.unresolved)
        self.assertEqual('INSUFFICIENT_EVIDENCE',q.outcome)
        self.assertEqual(self.impact,self.impacts.get(self.impact.candidate_id,current=True))

    def test_candidate_gate_rejects_impact_candidate(self):
        with self.assertRaises(ScopeError):self.service.create_candidate(self.impact.candidate_id,'2026-12-31',90)

    def test_other_layer_identity_rejected(self):
        with self.assertRaises(ScopeError):self.service.create_candidate(self.candidate.candidate_id,'2026-12-31',90)

    def test_empirical_range_lower_than_impact(self):
        q=self.qualify();self.assertEqual('QUALIFIED',q.outcome)
        self.assertEqual((Decimal('40'),Decimal('60')),(q.low,q.high));self.assertIsNone(q.central)
        self.assertLess(q.high,q.candidate.source_amount);self.assertEqual(q,Assessment.from_json(q.to_json()))

    def test_central_cannot_be_invented(self):
        q=self.qualify();d=q.model_dump();d['central']='50'
        with self.assertRaises(ValueError):Assessment.model_validate(d)

    def test_strategic_constraint_preserves_impact(self):
        d=self.evidence();d['reviews'][0].update(addressability='STRATEGIC_CONSTRAINT',constraint_basis='Approved strategic flexibility')
        q=self.qualify(d);self.assertEqual('NOT_ADDRESSABLE',q.outcome);self.assertEqual(100,q.excluded)
        self.assertEqual(self.impact,self.impacts.get(self.impact.candidate_id,current=True))

    def test_existing_initiative_excluded(self):
        d=self.evidence();d['reviews'][0].update(initiative='ALREADY_UNDERWAY',initiative_id='existing-1',initiative_started_on='2026-12-01')
        q=self.qualify(d);self.assertEqual(100,q.excluded);self.assertIsNone(q.opportunity_id)
        self.assertEqual('EXCLUDED_PRIOR_INITIATIVE',q.portions[0].state)

    def test_missing_initiative_is_unknown(self):
        d=self.evidence();d['reviews'][0].update(initiative='UNKNOWN',initiative_review=None,initiative_review_complete=False)
        q=self.qualify(d);self.assertEqual(100,q.unresolved);self.assertIsNone(q.high)

    def test_incomplete_no_initiative_review_not_absence(self):
        d=self.evidence();d['reviews'][0]['initiative_review_complete']=False
        self.assertIsNone(self.qualify(d).opportunity_id)

    def test_management_constraint_can_exclude(self):
        d=self.evidence();r=d['reviews'][0];r['authority_evidence']['authority']='MANAGEMENT_ASSERTION'
        r.update(addressability='STRATEGIC_CONSTRAINT',constraint_basis='Management approval')
        self.assertEqual(100,self.qualify(d).excluded)

    def test_management_opinion_not_empirical_capture(self):
        d=self.evidence();d['reviews'][0]['cohort_pairs'][0]['treated']['evidence']['authority']='MANAGEMENT_ASSERTION'
        self.assertIsNone(self.qualify(d).high)

    def test_arbitrary_percentage_rejected(self):
        d=self.evidence();d['reviews'][0]['recovery_percentage']='90'
        with self.assertRaises(ValueError):self.retain(d)

    def test_insufficient_sample_unresolved_capture(self):
        d=self.evidence();d['reviews'][0]['cohort_pairs'].pop();d['reviews'][0]['eligible_pair_count']=2
        q=self.qualify(d);self.assertEqual('UNRESOLVED',q.outcome);self.assertEqual(100,q.addressable);self.assertIsNone(q.high)

    def test_different_exposure_not_scaled(self):
        d=self.evidence();d['reviews'][0]['cohort_pairs'][0]['treated']['exposure']='200'
        self.assertIsNone(self.qualify(d).high)

    def test_different_customer_not_universal_recovery(self):
        d=self.evidence();d['reviews'][0]['cohort_pairs'][0]['treated']['customer_id']='other'
        self.assertIsNone(self.qualify(d).high)

    def test_horizon_mismatch_refused(self):
        e=self.retain(self.evidence(horizon_days=30))
        with self.assertRaises(ScopeError):self.service.qualify(self.candidate.candidate_id,e.evidence_id)

    def test_historical_horizon_mismatch_unresolved(self):
        d=self.evidence();d['reviews'][0]['cohort_pairs'][0]['treated']['observed_through']='2025-05-01'
        self.assertIsNone(self.qualify(d).high)

    def test_selected_successful_cases_not_cohort(self):
        d=self.evidence();d['reviews'][0]['cohort_coverage']='SELECTED'
        self.assertIsNone(self.qualify(d).high)

    def test_duplicate_history_not_independent_sample(self):
        d=self.evidence();d['reviews'][0]['cohort_pairs'][1]=d['reviews'][0]['cohort_pairs'][0]
        self.assertIsNone(self.qualify(d).high)

    def test_contradictory_outcome_not_discarded(self):
        d=self.evidence();d['reviews'][0]['cohort_pairs'][0]['comparison']['cash_received']='90'
        self.assertIsNone(self.qualify(d).high)

    def test_zero_incremental_outcome_no_opportunity(self):
        d=self.evidence()
        for p in d['reviews'][0]['cohort_pairs']:p['treated']['cash_received']='20'
        self.assertIsNone(self.qualify(d).opportunity_id)

    def test_blind_source_cannot_enter_real_totals(self):
        q=self.qualify();a=self.service.aggregate([q.candidate.candidate_id])
        self.assertEqual('NOT_SAFELY_AGGREGATABLE',a['status']);self.assertIsNone(a['high'])

    def test_same_effect_duplicate_not_double_counted(self):
        q=self.qualify();a=self.service.aggregate([q.candidate.candidate_id]*2,origin='BLIND_QUALIFICATION')
        self.assertEqual(q.low,a['low']);self.assertEqual(q.high,a['high'])

    def test_cash_not_profit_or_benefit(self):
        q=self.qualify();self.assertEqual('CASH',q.dimension)
        with self.assertRaises(ValueError):self.service.aggregate([q.candidate.candidate_id],dimension='PROFIT_PNL')
        self.assertEqual('NOT_ASSESSED',q.confidence.benefit_attribution_confidence)

    def test_replay_and_revisions_preserve_history(self):
        q=self.qualify();self.assertEqual(q,self.qualify())
        d=self.evidence(source_version='synthetic-2');d['reviews'][0]['cohort_pairs'][0]['treated']['cash_received']='50'
        with self.assertRaises(RevisionConflict):self.qualify(d)
        r=self.qualify(d,expected_revision=1);self.assertEqual(2,r.revision)
        self.assertEqual(q,self.service.get(self.candidate.candidate_id,1))
        with self.assertRaises(RevisionConflict):self.service.get(self.candidate.candidate_id,1,current=True)

    def test_caller_owned_rollback(self):
        self.qualify();self.session.rollback()
        for t in (tables.evidence,tables.candidate,tables.assessment,tables.opportunity,tables.audit):
            self.assertEqual(0,self.session.scalar(select(func.count()).select_from(t)))

    def test_source_scope_and_fk(self):
        d=self.evidence(client_id='c2')
        with self.assertRaises(ScopeError):self.retain(d)
        q=self.qualify()
        with self.assertRaises(IntegrityError):
            with self.session.begin_nested():self.session.execute(update(tables.assessment).values(client_id='c2'))

    def test_source_tamper_rejected(self):
        e=self.retain(self.evidence());ds=self.contexts.source.dataset(e.dataset_version_id)
        from pathlib import Path
        import stat
        path=Path(ds['storage_location']);path.chmod(stat.S_IREAD|stat.S_IWRITE)
        path.write_text('changed',encoding='utf-8')
        with self.assertRaises(RevisionConflict):self.service.qualify(self.candidate.candidate_id,e.evidence_id)

    def test_complete_review_cannot_omit_population(self):
        e=self.retain(self.evidence(reviews=[]))
        with self.assertRaises(ValueError):self.service.qualify(self.candidate.candidate_id,e.evidence_id)

    def test_partial_missing_review_is_unresolved(self):
        q=self.qualify(self.evidence(coverage='PARTIAL',reviews=[]))
        self.assertEqual(100,q.unresolved);self.assertIsNone(q.opportunity_id)

    def test_future_evidence_rejected(self):
        d=self.evidence();d['reviews'][0]['authority_evidence']['observed_on']='2027-01-01'
        with self.assertRaises(ValueError):self.retain(d)

    def test_audit_and_effect_identity(self):
        q=self.qualify();obj=self.contexts.foundation.get_object(q.opportunity_id)
        self.assertEqual('VALIDATED_OPPORTUNITY',obj.object_type)
        self.assertEqual(self.impact.impact.effect_id,q.candidate.effect_id)
        self.assertEqual(2,self.session.scalar(select(func.count()).select_from(tables.audit)))

    def test_populated_downgrade_reupgrade(self):
        from alembic import command
        from tests.test_postgresql_live_qualification_v218 import alembic_config
        self.qualify();self.session.commit();self.session.close()
        url=('sqlite+pysqlite:///'+self.engine.url.database if self.engine.dialect.name=='sqlite' else self.engine.url.render_as_string(hide_password=False))
        cfg=alembic_config(url.replace('%','%%'));command.downgrade(cfg,'0012_receivables_snapshot');command.upgrade(cfg,'head')
        self.assertEqual(self.impact,self.impacts.get(self.impact.candidate_id,current=True))
        for t in (tables.evidence,tables.candidate,tables.assessment,tables.opportunity,tables.audit):
            self.assertEqual(0,self.session.scalar(select(func.count()).select_from(t)))

    def test_precision_survives_persistence(self):
        d=self.evidence();d['reviews'][0]['cohort_pairs'][0]['treated']['cash_received']='60.00000000000000000001'
        q=self.qualify(d);self.assertEqual(Decimal('40.00000000000000000001'),q.low)
        self.assertEqual(q,self.service.get(q.candidate.candidate_id,current=True))

    def test_synthetic_impact_cannot_enter(self):
        from tests import test_economic_impact_v249 as old
        from profit_doctor.reasoning.impact.contracts import Source, SyntheticBasis
        basis=SyntheticBasis.from_json(old.FIXTURE.read_text())
        self.impacts.synthetic_resolver=lambda key:basis
        q=self.impacts.assess(Source(kind='SYNTHETIC',source_id=basis.fixture_key),'CASH_TRAPPED')
        self.assertIsNotNone(q.impact)
        with self.assertRaises(ScopeError):self.service.create_candidate(q.impact.impact_id,'2026-12-31',90)

    def test_partitions_coexist_and_partial_qualification(self):
        import copy
        data=self.data(outstanding='100',terms=dict(reference='terms',days=30,effective_from='2026-01-01',effective_to='2026-12-31'))
        data['ledger_id']='mixed-ledger';data['control_amount']='400'
        data['invoices']=[{**data['invoices'][0],'invoice_id':f'invoice-{i}'} for i in range(1,5)]
        self.snapshot=self.ingest(data);self.impact=self.assess(self.snapshot)
        self.candidate=self.service.create_candidate(self.impact.impact.impact_id,'2026-12-31',90)
        d=self.evidence();template=d['reviews'][0];d['reviews']=[copy.deepcopy(template) for _ in range(4)]
        for i,r in enumerate(d['reviews'],1):r['invoice_id']=f'invoice-{i}'
        d['reviews'][1].update(addressability='STRATEGIC_CONSTRAINT',constraint_basis='Management approved flexibility')
        d['reviews'][2].update(initiative='ALREADY_UNDERWAY',initiative_id='existing',initiative_started_on='2026-01-01')
        d['reviews'][3].update(initiative='UNKNOWN')
        q=self.qualify(d);self.assertEqual('PARTIALLY_QUALIFIED',q.outcome)
        self.assertEqual((100,200,100),(q.addressable,q.excluded,q.unresolved))
        self.assertEqual((40,60),(q.low,q.high))

    def test_unknown_overlap_blocks_distinct_effects(self):
        a=self.qualify()
        d=self.data(outstanding='100',terms=dict(reference='terms',days=30,effective_from='2026-01-01',effective_to='2026-12-31'))
        d['ledger_id']='other-ledger';self.snapshot=self.ingest(d);self.impact=self.assess(self.snapshot)
        self.candidate=self.service.create_candidate(self.impact.impact.impact_id,'2026-12-31',90)
        b=self.qualify();result=self.service.aggregate([a.candidate.candidate_id,b.candidate.candidate_id],origin='BLIND_QUALIFICATION')
        self.assertEqual('NOT_SAFELY_AGGREGATABLE',result['status']);self.assertIsNone(result['high'])

    def test_stale_impact_blocks_opportunity(self):
        q=self.qualify();d=self.data(outstanding='90',terms=dict(reference='terms',days=30,effective_from='2026-01-01',effective_to='2026-12-31'))
        d['source_version']='2';self.ingest(d,self.snapshot.snapshot_id)
        with self.assertRaises(RevisionConflict):self.service.aggregate([q.candidate.candidate_id],origin='BLIND_QUALIFICATION')

    def test_unresolved_capture_separate_from_addressability(self):
        d=self.evidence();d['reviews'][0]['cohort_pairs']=[];d['reviews'][0]['eligible_pair_count']=0
        q=self.qualify(d);self.assertEqual((100,0,100),(q.addressable,q.unresolved,q.capture_unresolved))

    def test_governed_empirical_central_not_midpoint(self):
        d=self.evidence();r=d['reviews'][0];r['central_method']='EMPIRICAL_PAIR_MEAN'
        for pair,amount in zip(r['cohort_pairs'],('60','60','90')):pair['treated']['cash_received']=amount
        q=self.qualify(d);self.assertEqual((40,70,50),(q.low,q.high,q.central));self.assertNotEqual((q.low+q.high)/2,q.central)

    def test_nonterminating_mean_remains_unassessed(self):
        d=self.evidence();r=d['reviews'][0];r['central_method']='EMPIRICAL_PAIR_MEAN'
        r['cohort_pairs'][0]['treated']['cash_received']='61'
        q=self.qualify(d);self.assertIsNone(q.central);self.assertIsNotNone(q.high)

    def test_long_terminating_mean_preserves_every_digit(self):
        exact=Decimal('0.'+str(5**100).zfill(100))  # 1 / 2**100: 70 significant digits
        d=self.evidence();r=d['reviews'][0];r['central_method']='EMPIRICAL_PAIR_MEAN'
        for pair in r['cohort_pairs']:
            pair['treated']['cash_received']=str(exact)
            pair['comparison']['cash_received']='0'
        q=self.qualify(d)
        self.assertEqual((exact,exact,exact),(q.low,q.high,q.central))
        self.assertEqual(q,self.service.get(q.candidate.candidate_id,current=True))

    def test_days_to_pay_requires_governed_dates(self):
        d=self.evidence();d['reviews'][0]['cohort_pairs'][0]['treated']['days_to_pay']=30
        with self.assertRaises(ValueError):self.retain(d)
