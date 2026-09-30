"""Generic workbook protocols and adversarial projection; no blind target fitting."""
import hashlib
import json
from datetime import date
from pathlib import Path
import unittest
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from profit_doctor.intake.collection import CollectionWorkbook, HEADERS
from profit_doctor.intake.declared_accounting import inspect_pack, read_cells
from profit_doctor.reasoning.opportunity.contracts import CollectionEvidence
from tests import test_opportunity_v250 as fixtures


def serial(day):
    return str((date.fromisoformat(day)-date(1899,12,30)).days)


def cells(headers, records):
    result = {chr(65+i)+'4':(key,'','inlineStr') for i,key in enumerate(headers)}
    for row, record in enumerate(records,5):
        for i,key in enumerate(headers):
            v = str(record.get(key,''))
            result[chr(65+i)+str(row)] = (v,'','n' if v.replace('.','',1).isdigit() else 'inlineStr')
    return result


def source_tables():
    tables = {}; contexts = []
    asof = serial('2026-12-31')
    def add(name, records):
        context = 'context-'+name
        common = {'Context ID':context,'Entity':'Example SME','As of':asof,'Currency':'GBP',
                  'Source ID':'source-'+name,'Dataset version':'source-1'}
        tables[name] = cells(HEADERS[name],[{**common,**r} for r in records])
        contexts.append({**common,'Measurement':name,'Coverage':'Named records only',
                         'Definition and limits':'Partial source extract','Provenance':'Source register'})
    add('Collection Evidence',[{'Evidence ID':'contact-1','Invoice ID':'invoice-1','Customer ID':'customer-1',
        'Last contact':serial('2026-12-20'),'Response date':serial('2026-12-21'),
        'Customer position':'ACKNOWLEDGED_PAYABLE','Processing context':'MATCHING_CLEARED',
        'Formal dispute':'NONE_RECORDED','Payment plan':'NONE_RECORDED','Credit-note case':'NONE_RECORDED',
        'Recorded promise':serial('2027-01-15'),'Recorded facts':'Dated correspondence'}])
    add('Collection Authority',[{'Authority ID':'authority-1','Invoice ID':'invoice-1','Recorded owner':'Credit control',
        'Ordinary contact':'PERMITTED','Commercial mandate':'APPROVED','Internal restriction':'NONE',
        'Effective from':serial('2026-12-01'),'Effective through':serial('2027-06-01'),
        'Approval reference':'delegation-1','Scope and reason':'Collection permission','Reviewed as of':asof}])
    add('Existing Recovery',[{'Evidence ID':'initiative-1','Invoice ID':'invoice-1','Customer ID':'customer-1',
        'Initiated date':serial('2026-12-20'),'Recorded owner':'Credit control','Observed status':'IN_PROGRESS',
        'Status date':serial('2026-12-21'),'Observed facts':'Existing contact sequence'}])
    history = []; receipts = []
    for n in range(6):
        episode = 'episode-'+str(n)
        amount = '75' if n%2 == 0 else '25'
        history.append({'Episode ID':episode,'Pair ID':'pair-'+str(n//2),'Cohort ID':'cohort-1',
            'Observed mechanism':'ORDINARY_COLLECTION','Arm':'ADDITIONAL_PROCESS' if n%2 == 0 else 'REFERENCE',
            'Customer ID':'customer-1','Opening date':serial('2026-04-01'),'Window days':'90',
            'Invoice date':serial('2025-12-31'),'Contractual due':serial('2026-01-30'),
            'Opening GBP':'100','Age at opening':'61','Window end':serial('2026-06-30'),
            'Matching review':'match-1','Terms days':'30','Cash inside window':amount,
            'Recorded date':serial('2026-07-01')})
        receipts.append({'Receipt ID':'receipt-'+str(n),'Episode ID':episode,'Receipt date':serial('2026-05-01'),
                         'Amount GBP':amount,'Posting status':'POSTED'})
    add('Recovery History',history);add('Historical Receipts',receipts)
    add('Collection Method',[{'Field':key,'Recorded method or value':val,'Unit':unit,'Scope':'Declared assessment',
                             'Approved date':serial('2026-12-01'),'Authority':'Finance Director'}
        for key,val,unit in [('Reporting date',asof,'date'),('Horizon days','90','calendar days'),
                            ('Proposed method','Unsupported percentages are not executed','text')]])
    tables['Recovery Context'] = cells(HEADERS['Recovery Context'],contexts)
    return tables


def write_protocol(path, sheets):
    """Minimal deterministic OOXML test transport, not a user workbook author."""
    ns = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    rel = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
    wb = ET.Element('{'+ns+'}workbook');catalogue=ET.SubElement(wb,'{'+ns+'}sheets')
    relationships = ET.Element('Relationships')
    with ZipFile(path,'w') as archive:
        for n,(name,table) in enumerate(sheets.items(),1):
            ET.SubElement(catalogue,'{'+ns+'}sheet',{'name':name,'sheetId':str(n),'{'+rel+'}id':str(n)})
            ET.SubElement(relationships,'Relationship',{'Id':str(n),'Target':f'worksheets/sheet{n}.xml'})
            sheet=ET.Element('{'+ns+'}worksheet');data=ET.SubElement(sheet,'{'+ns+'}sheetData');rows={}
            for address,(raw,formula,kind) in table.items():
                rownum=address.lstrip('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
                if rownum not in rows:rows[rownum]=ET.SubElement(data,'{'+ns+'}row',r=rownum)
                c=ET.SubElement(rows[rownum],'{'+ns+'}c',r=address,t=kind)
                if formula:ET.SubElement(c,'{'+ns+'}f').text=formula
                if kind=='inlineStr':ET.SubElement(ET.SubElement(c,'{'+ns+'}is'),'{'+ns+'}t').text=raw
                else:ET.SubElement(c,'{'+ns+'}v').text=raw
            archive.writestr(f'xl/worksheets/sheet{n}.xml',ET.tostring(sheet))
        archive.writestr('xl/workbook.xml',ET.tostring(wb))
        archive.writestr('xl/_rels/workbook.xml.rels',ET.tostring(relationships))


class CollectionWorkbookV250(unittest.TestCase):
    def setUp(self):
        self.tables=source_tables();self.adapter=CollectionWorkbook()

    def replace(self,sheet,cell,val):
        self.tables[sheet][cell]=(str(val),'','inlineStr')

    def test_generic_table_projection_retains_dates_promises_authority(self):
        data=self.adapter.inspect(self.tables);r=data['reviews'][0]
        self.assertEqual('ORDINARY_COLLECTION',r['addressability'])
        self.assertEqual('MANAGEMENT_ASSERTION',r['authority_evidence']['authority'])
        self.assertEqual('2027-01-15',r['contacts'][-1]['promised_on'])
        self.assertIsNone(r['contacts'][-1]['promised_amount'])
        self.assertEqual('ALREADY_UNDERWAY',r['initiative'])
        self.assertFalse(r['initiative_review_complete'])
        self.assertEqual('2026-12-20',r['initiative_started_on'])
        self.assertEqual([],r['cohort_pairs'])
        self.assertEqual(6,len(data['tables']['Recovery History']))

    def test_missing_authority_is_unknown(self):
        self.replace('Collection Authority','G5','')
        self.assertEqual('UNKNOWN',self.adapter.inspect(self.tables)['reviews'][0]['addressability'])

    def test_empty_initiative_extract_is_unknown_not_none(self):
        self.tables['Existing Recovery']=cells(HEADERS['Existing Recovery'],[])
        r=self.adapter.inspect(self.tables)['reviews'][0]
        self.assertEqual('UNKNOWN',r['initiative']);self.assertFalse(r['initiative_review_complete'])

    def test_empty_history_does_not_invent_pairs(self):
        for name in ('Recovery History','Historical Receipts'):
            self.tables[name]=cells(HEADERS[name],[])
        self.assertEqual([],self.adapter.inspect(self.tables)['reviews'][0]['cohort_pairs'])

    def test_conflicting_pair_rejected(self):
        self.replace('Recovery History','F6','different-customer')
        with self.assertRaises(ValueError):self.adapter.inspect(self.tables)

    def test_expired_authority_is_unknown(self):
        self.replace('Collection Authority','H5',serial('2026-12-30'))
        self.assertIsNone(self.adapter.inspect(self.tables)['reviews'][0]['authority_evidence'])

    def test_strategic_constraint_not_changed_payment_terms(self):
        self.replace('Collection Authority','F5','INTERNAL_ACCELERATION_HOLD')
        r=self.adapter.inspect(self.tables)['reviews'][0]
        self.assertEqual('STRATEGIC_CONSTRAINT',r['addressability']);self.assertEqual('Collection permission',r['constraint_basis'])

    def test_service_liaison_requires_commercial_mandate(self):
        self.replace('Collection Evidence','G5','SERVICE_LIAISON_PENDING')
        self.assertEqual('COMMERCIAL_INTERVENTION',self.adapter.inspect(self.tables)['reviews'][0]['addressability'])
        self.replace('Collection Authority','E5','UNVERIFIED')
        self.assertEqual('UNKNOWN',self.adapter.inspect(self.tables)['reviews'][0]['addressability'])

    def test_future_contact_rejected(self):
        self.replace('Collection Evidence','D5',serial('2027-01-01'))
        with self.assertRaises(ValueError):self.adapter.inspect(self.tables)

    def test_conflicting_customer_rejected(self):
        self.replace('Existing Recovery','C5','different-customer')
        with self.assertRaises(ValueError):self.adapter.inspect(self.tables)

    def test_unknown_initiative_status_not_promoted_to_underway(self):
        self.replace('Existing Recovery','F5','UNVERIFIED')
        with self.assertRaisesRegex(ValueError,'initiative status'):self.adapter.inspect(self.tables)

    def test_conflicting_scope_rejected(self):
        self.replace('Recovery History','R5','Other SME')
        with self.assertRaises(ValueError):self.adapter.inspect(self.tables)

    def test_unknown_vocab_rejected(self):
        self.replace('Collection Evidence','G5','GUARANTEED_RECOVERY')
        with self.assertRaises(ValueError):self.adapter.inspect(self.tables)

    def test_formula_in_authority_rejected(self):
        self.tables['Collection Authority']['D5']=('PERMITTED','A1','str')
        with self.assertRaises(ValueError):self.adapter.inspect(self.tables)

    def test_unknown_column_rejected(self):
        self.replace('Collection Authority','P4','Override')
        with self.assertRaises(ValueError):self.adapter.inspect(self.tables)

    def test_duplicate_identity_rejected(self):
        self.replace('Historical Receipts','A6','receipt-0')
        with self.assertRaises(ValueError):self.adapter.inspect(self.tables)

    def test_receipt_cache_mismatch_rejected(self):
        self.replace('Recovery History','U5','76')
        with self.assertRaises(ValueError):self.adapter.inspect(self.tables)

    def test_receipt_episode_mismatch_rejected(self):
        self.replace('Historical Receipts','B5','missing')
        with self.assertRaises(ValueError):self.adapter.inspect(self.tables)

    def test_historical_window_mismatch_rejected(self):
        self.replace('Recovery History','H5','91')
        with self.assertRaises(ValueError):self.adapter.inspect(self.tables)

    def test_unregistered_and_conflicting_sheets_fail_closed(self):
        from tests.test_receivables_v249 import WORKBOOK
        with self.assertRaisesRegex(ValueError,'sheet catalogue'):
            inspect_pack(WORKBOOK,providers=(self.adapter,))
        with self.assertRaisesRegex(ValueError,'Conflicting'):
            inspect_pack(WORKBOOK,providers=(self.adapter,self.adapter))

    def test_normalized_invalid_document_rejected(self):
        with self.assertRaises(ValueError):
            CollectionWorkbook(layout='NORMALIZED').inspect({'Collection Document':cells(('Collection document',),[{'Collection document':'{}'}])})

    def test_method_proposal_does_not_change_contract(self):
        before=self.adapter.inspect(self.tables)['reviews']
        self.replace('Collection Method','B7','Scale every opening balance by 100 percent')
        self.assertEqual(before,self.adapter.inspect(self.tables)['reviews'])


class CollectionWorkbookPersistenceV250(unittest.TestCase):
    target_url=fixtures.OpportunityV250.target_url
    prepare_target=fixtures.OpportunityV250.prepare_target
    data=fixtures.OpportunityV250.data
    ingest=fixtures.OpportunityV250.ingest
    assess=fixtures.OpportunityV250.assess
    evidence=fixtures.OpportunityV250.evidence
    setUp=fixtures.OpportunityV250.setUp

    def retain_workbook(self,data=None):
        adapter=CollectionWorkbook(layout='NORMALIZED')
        document=CollectionEvidence.model_validate(data or self.evidence())
        path=self.directory/'collection.xlsx'
        write_protocol(path,{'Collection Document':cells(('Collection document',),[{'Collection document':document.to_json()}])})
        pack={'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'entity':'Fixture company',
              'extensions':{adapter.name:adapter.inspect(read_cells(path))}}
        return adapter.capture(self.service,pack,path,self.directory/'store',impact_id=self.impact.impact.impact_id)

    def test_normalized_workbook_positive_preserves_existing_capture(self):
        e=self.retain_workbook();q=self.service.qualify(self.candidate.candidate_id,e.evidence_id)
        self.assertEqual((40,60,None),(q.low,q.high,q.central))
        self.assertEqual(e,self.service.get_evidence(e.evidence_id))
        reference=json.loads(e.reviews[0].cohort_pairs[0].treated.evidence.reference)
        self.assertIn('sha256',reference);self.assertIn('workbook_id',reference)
        self.assertEqual('synthetic-source-record',reference['reference'])

    def test_tabular_capture_preserves_full_source_and_excludes_existing_work(self):
        adapter=CollectionWorkbook();tables=source_tables()
        for table in tables.values():
            for address,(raw,formula,kind) in list(table.items()):
                if raw=='Example SME':table[address]=('Fixture company',formula,kind)
        path=self.directory/'tabular.xlsx';write_protocol(path,tables)
        pack={'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'entity':'Fixture company',
              'extensions':{adapter.name:adapter.inspect(read_cells(path))}}
        e=adapter.capture(self.service,pack,path,self.directory/'store',impact_id=self.impact.impact.impact_id)
        q=self.service.qualify(self.candidate.candidate_id,e.evidence_id)
        self.assertEqual('NOT_ADDRESSABLE',q.outcome);self.assertEqual(100,q.excluded)
        self.assertEqual('EXCLUDED_PRIOR_INITIATIVE',q.portions[0].state)
        root=json.loads(e.source_version)
        self.assertEqual(pack['sha256'],root['sha256']);self.assertTrue(root['workbook_id'])
        self.assertEqual(e,self.service.get_evidence(e.evidence_id))

    def test_normalized_workbook_preserves_missing_initiative(self):
        data=self.evidence();data['reviews'][0].update(initiative='UNKNOWN',initiative_review=None,initiative_review_complete=False)
        e=self.retain_workbook(data);q=self.service.qualify(self.candidate.candidate_id,e.evidence_id)
        self.assertEqual(100,q.unresolved);self.assertIsNone(q.opportunity_id)

    def test_normalized_workbook_never_scales_exposure(self):
        data=self.evidence();data['reviews'][0]['cohort_pairs'][0]['treated']['exposure']='200'
        e=self.retain_workbook(data);q=self.service.qualify(self.candidate.candidate_id,e.evidence_id)
        self.assertEqual(100,q.capture_unresolved);self.assertIsNone(q.opportunity_id)

    def test_normalized_workbook_rejects_foreign_scope(self):
        data=self.evidence();data['client_id']='foreign'
        with self.assertRaises(ValueError):self.retain_workbook(data)

    def test_table_source_missing_initiative_remains_unknown(self):
        tables=source_tables()
        # A second correspondence record has no row in the named initiative extract.
        for address,cell in list(tables['Collection Evidence'].items()):
            if address.endswith('5'):tables['Collection Evidence'][address[:-1]+'6']=cell
        tables['Collection Evidence']['A6']=('contact-2','','inlineStr')
        tables['Collection Evidence']['B6']=('other-invoice','','inlineStr')
        result=CollectionWorkbook().inspect(tables)
        self.assertEqual('UNKNOWN',result['reviews'][1]['initiative'])
        self.assertIsNone(result['reviews'][1]['initiative_review'])
        self.assertFalse(result['reviews'][1]['initiative_review_complete'])

    def test_changed_source_refused_before_capture(self):
        adapter=CollectionWorkbook(layout='NORMALIZED');path=self.directory/'changed.xlsx';path.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'changed after inspection'):
            adapter.capture(self.service,{'sha256':'old'},path,self.directory/'store',impact_id=self.impact.impact.impact_id)
