"""Read an unchanged workbook through registered providers in isolated local stores.

This reports evidence eligibility, not an alternative capture calculation. No
database URL, positive target, cohort scaling or production database is accepted.
"""
import argparse
from collections import Counter
from datetime import date
from decimal import Decimal
import gc
import hashlib
import json
from pathlib import Path
import sys
import unittest
import warnings

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from profit_doctor.intake.declared_accounting import capture_pack
from profit_doctor.intake.receivables import ReceivablesWorkbook
from profit_doctor.intake.collection import CollectionWorkbook, _date
from profit_doctor.reasoning.opportunity.service import OpportunityService
from profit_doctor.reasoning.opportunity.engine import age_band
from profit_doctor.reasoning.receivables.contracts import population
from scripts.run_full_estate import EstateResult
from tests import test_receivables_v249 as fixtures


def cohort_checks(invoice, review, rows, horizon):
    """All supplied cohorts inspected; no selected subset becomes capture input."""
    groups={}
    for row in rows:groups.setdefault(row['Cohort ID'],{}).setdefault(row['Pair ID'],[]).append(row)
    result={}
    for cohort,pairs in groups.items():
        failures=Counter();dimension_matches=0
        for cases in pairs.values():
            reasons=set()
            for c in cases:
                if c['Customer ID'] != invoice.customer_id:reasons.add('CUSTOMER')
                if Decimal(c['Opening GBP']) != invoice.outstanding:reasons.add('EXACT_EXPOSURE')
                if c['Currency'] != invoice.currency:reasons.add('CURRENCY')
                if invoice.terms is None or int(c['Terms days']) != invoice.terms.days:reasons.add('TERMS')
                if age_band(int(c['Age at opening'])) != age_band(invoice.days_overdue):reasons.add('AGE_BAND')
                mechanism={'SERVICE_LIAISON':'COMMERCIAL_INTERVENTION'}.get(c['Observed mechanism'],c['Observed mechanism'])
                if mechanism != review.addressability:reasons.add('INTERVENTION')
                if int(c['Window days']) != horizon or _date(c['Window end']) > invoice.as_of:reasons.add('WINDOW')
            failures.update(reasons)
            if not reasons:dimension_matches+=1
        result[cohort]={'pairs':len(pairs),'dimension_matching_pairs':dimension_matches,
            'pair_failure_counts':dict(sorted(failures.items())),
            'qualified':False,'additional_blockers':['NO_HISTORICAL_INVOICE_IDS','NO_COMPLETE_INCEPTION_MANIFEST',
                'NO_EXPLICIT_CURRENT_INVOICE_COHORT_MEMBERSHIP']}
    return result


class WorkbookQualification(unittest.TestCase):
    target_url=fixtures.ReceivablesV249.target_url
    prepare_target=fixtures.ReceivablesV249.prepare_target
    setUp=fixtures.ReceivablesV249.setUp
    assess=fixtures.ReceivablesV249.assess

    def runTest(self):
        before=hashlib.sha256(self.workbook.read_bytes()).hexdigest()
        ar=ReceivablesWorkbook();collection=CollectionWorkbook()
        pack,_=capture_pack(self.contexts,self.workbook,self.directory/'store',providers=(ar,collection))
        snapshot=ar.capture(self.provider,pack,self.workbook,self.directory/'store',origin='BLIND_QUALIFICATION',ledger_id='trade-ar')
        impact=self.assess(snapshot)
        self.assertIsNotNone(impact.impact)
        invoices=population(snapshot)['QUALIFYING_OVERDUE']
        self.assertEqual(sum(i.outstanding for i in invoices),impact.impact.amount.value)
        service=OpportunityService(self.impacts)
        data=pack['extensions'][collection.name]
        candidate=service.create_candidate(impact.impact.impact_id,data['as_of'],data['horizon_days'])
        evidence=collection.capture(service,pack,self.workbook,self.directory/'store',impact_id=impact.impact.impact_id)
        result=service.qualify(candidate.candidate_id,evidence.evidence_id)
        self.assertEqual(evidence,service.get_evidence(evidence.evidence_id))
        self.assertEqual(result,service.get(candidate.candidate_id,current=True))
        self.assertIsNone(result.opportunity_id)
        self.assertIsNone(result.low);self.assertIsNone(result.high);self.assertIsNone(result.central)
        self.assertEqual('EMPTY',service.aggregate([candidate.candidate_id],origin='BLIND_QUALIFICATION')['status'])
        self.session.rollback()
        reviews={(r.customer_id,r.invoice_id):r for r in evidence.reviews}
        self.report.update(workbook_sha256=before,ingestion='PASS',source_impact=str(impact.impact.amount.value),
            outcome=result.outcome,opportunity_id=result.opportunity_id,low=result.low,high=result.high,central=result.central,
            addressable=str(result.addressable),excluded=str(result.excluded),unresolved=str(result.unresolved),
            invoices=[{'invoice_id':i.invoice_id,'customer_id':i.customer_id,'amount':str(i.outstanding),'currency':i.currency,
                'terms_days':i.terms.days if i.terms else None,'days_overdue':i.days_overdue,
                'addressability_evidence':reviews[(i.customer_id,i.invoice_id)].addressability,
                'initiative':reviews[(i.customer_id,i.invoice_id)].initiative,
                'initiative_review_complete':reviews[(i.customer_id,i.invoice_id)].initiative_review_complete,
                'cohorts':cohort_checks(i,reviews[(i.customer_id,i.invoice_id)],data['tables']['Recovery History'],data['horizon_days'])}
                for i in invoices],portions=[p.model_dump(mode='json') for p in result.portions],
            limitations=data['history_limitations'])
        self.assertEqual(before,hashlib.sha256(self.workbook.read_bytes()).hexdigest())


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workbook',type=Path);parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args();report={};errors=[];previous=sys.unraisablehook
    try:
        sys.unraisablehook=lambda event:errors.append(f'{event.exc_type.__name__}: {event.exc_value}')
        with warnings.catch_warnings():
            warnings.simplefilter('error',DeprecationWarning);warnings.simplefilter('error',ResourceWarning)
            case=WorkbookQualification();case.workbook=args.workbook;case.report=report
            result=unittest.TextTestRunner(verbosity=2,failfast=True,
                resultclass=lambda *a,**kw:EstateResult(*a,unraisable=errors,**kw)).run(unittest.TestSuite([case]))
            gc.collect()
    finally:sys.unraisablehook=previous
    report.update(run=result.testsRun,passed=sum(v['status']=='passed' for v in result.outcomes.values()),
        failed=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),unraisable=errors)
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('invoices','portions')},indent=2))
    return 0 if result.wasSuccessful() and not errors else 1


if __name__=='__main__':raise SystemExit(main())
