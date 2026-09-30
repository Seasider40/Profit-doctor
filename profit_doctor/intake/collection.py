"""Opt-in collection workbook evidence, with no valuation or inferred completeness.

TABLES retains correspondence/register extracts and projects only their explicit
semantics. NORMALIZED accepts the existing CE-2.50.1 document, including explicit
inception-cohort and initiative reviews. Neither layout changes capture rules.
"""
import csv
import hashlib
import json
from datetime import date, timedelta
from decimal import Decimal, localcontext
from pathlib import Path
from tempfile import TemporaryDirectory

from profit_doctor.intake.declared_accounting import data_rows, value, number
from profit_doctor.ingestion.northstar import register_file
from profit_doctor.reasoning.opportunity.contracts import CollectionEvidence, CollectionReview, Evidence, Contact


HEADERS = {
    'Collection Evidence': ('Evidence ID','Invoice ID','Customer ID','Last contact','Response date','Customer position','Processing context','Recorded facts','Formal dispute','Payment plan','Credit-note case','Recorded promise','Posted settlement','As of','Source ID','Dataset version','Context ID','Entity','Currency'),
    'Collection Authority': ('Authority ID','Invoice ID','Recorded owner','Ordinary contact','Commercial mandate','Internal restriction','Effective from','Effective through','Approval reference','Scope and reason','Reviewed as of','Source ID','Dataset version','Context ID','Entity'),
    'Existing Recovery': ('Evidence ID','Invoice ID','Customer ID','Initiated date','Recorded owner','Observed status','Status date','Posted settlement','Observed facts','Source ID','Dataset version','Context ID','Entity','As of'),
    'Recovery History': ('Episode ID','Pair ID','Cohort ID','Observed mechanism','Arm','Customer ID','Opening date','Window days','Invoice date','Contractual due','Opening GBP','Age at opening','Window end','Matching review','Context ID','Source ID','Dataset version','Entity','Currency','Terms days','Cash inside window','Recorded date'),
    'Historical Receipts': ('Receipt ID','Episode ID','Receipt date','Amount GBP','Posting status','Source ID','Dataset version','Context ID','Entity','Currency'),
    'Collection Method': ('Field','Recorded method or value','Unit','Scope','Approved date','Authority','Source ID','Dataset version','Context ID','Entity'),
    'Recovery Context': ('Context ID','Entity','As of','Measurement','Coverage','Definition and limits','Source ID','Dataset version','Provenance'),
}


def _date(raw):
    n = Decimal(raw)
    if not n.is_finite() or n != int(n) or n < 61:
        raise ValueError('Expected an integral Excel date')
    return date(1899, 12, 30) + timedelta(days=int(n))


def _integer(raw):
    n = Decimal(raw)
    if not n.is_finite() or n != int(n) or n < 0:
        raise ValueError('Expected nonnegative integral evidence value')
    return int(n)


def _table(cells, headers, *, cached=(), allow_empty=False):
    # No unknown data columns or orphan rows may disappear during projection.
    if allow_empty and not any(value(cells,a) for a in cells if a.startswith('A') and a[1:].isdigit() and int(a[1:]) >= 5):
        if tuple(value(cells,chr(65+i)+'4') for i in range(len(headers))) != headers:
            raise ValueError('Unqualified source layout/header')
        rows = []
    else:
        rows = data_rows(cells, headers)
    for address, (raw, formula, kind) in cells.items():
        col = address.rstrip('0123456789')
        row = int(address[len(col):])
        if row >= 4 and (raw or formula) and (len(col) != 1 or ord(col)-65 >= len(headers)
                or row > 4 and row not in rows):
            raise ValueError('Unsupported collection column or orphan row')
    result = []
    for r in rows:
        record = {'_row': r}
        for i, header in enumerate(headers):
            address = chr(65+i)+str(r)
            record[header] = cells.get(address, ('','',''))[0] if header in cached else value(cells,address)
        result.append(record)
    ids = [r[headers[0]] for r in result]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate collection evidence identity')
    return result


class CollectionWorkbook:
    """A registered, reusable layout provider; callers choose the source layout."""
    def __init__(self, *, layout='TABLES'):
        if layout not in ('TABLES','NORMALIZED'):
            raise ValueError('Unsupported collection workbook layout')
        self.layout = layout
        self.name = 'COLLECTION_WORKBOOK_1_'+layout
        self.sheets = frozenset(HEADERS) if layout == 'TABLES' else frozenset({'Collection Document'})

    def inspect(self, sheets):
        if self.layout == 'NORMALIZED':
            rows = _table(sheets['Collection Document'], ('Collection document',))
            if len(rows) != 1:
                raise ValueError('Exactly one CE-2.50.1 document required')
            document = CollectionEvidence.from_json(rows[0]['Collection document'])
            return {'document': document.model_dump(mode='json')}
        method_cells = dict(sheets['Collection Method'])
        for address, (raw, formula, kind) in method_cells.items():
            if formula:
                if (address != 'B7' or formula != 'B5+B6' or kind != 'n'
                        or value(method_cells,'A5') != 'Reporting date' or value(method_cells,'A6') != 'Horizon days'
                        or Decimal(raw) != number(method_cells,'B5')+number(method_cells,'B6')):
                    raise ValueError('Unsupported method formula/cache')
                method_cells[address] = (raw,'',kind)
        tables = {name: _table(method_cells if name == 'Collection Method' else sheets[name], header,
                  cached=('Cash inside window',) if name == 'Recovery History' else (),
                  allow_empty=name in ('Existing Recovery','Recovery History','Historical Receipts'))
                  for name, header in HEADERS.items()}
        contexts = {r['Context ID']: r for r in tables['Recovery Context']}
        entities = {r['Entity'] for r in contexts.values()}
        dates = {_date(r['As of']) for r in contexts.values()}
        if len(entities) != 1 or not next(iter(entities)) or len(dates) != 1:
            raise ValueError('Mixed collection entity or assessment date')
        entity, asof = next(iter(entities)), next(iter(dates))
        for name, records in tables.items():
            for r in records:
                c = contexts.get(r['Context ID'])
                if not c or any(not r[k] or r[k] != c[k] for k in ('Entity','Source ID','Dataset version')):
                    raise ValueError('Collection source/context mismatch')
                if 'Currency' in r and r['Currency'] != 'GBP':
                    raise ValueError('Unqualified collection currency')
                if 'As of' in r and _date(r['As of']) != asof:
                    raise ValueError('Collection assessment date mismatch')
        method = {r['Field']: r for r in tables['Collection Method']}
        if not {'Reporting date','Horizon days'} <= method.keys():
            raise ValueError('Missing assessment date/horizon declaration')
        if method['Reporting date']['Unit'] != 'date' or method['Horizon days']['Unit'] != 'calendar days':
            raise ValueError('Unqualified assessment date/horizon units')
        if _date(method['Reporting date']['Recorded method or value']) != asof:
            raise ValueError('Method date differs from evidence')
        horizon = _integer(method['Horizon days']['Recorded method or value'])
        if not 1 <= horizon <= 3660:
            raise ValueError('Invalid declared horizon')
        for r in method.values():
            if _date(r['Approved date']) > asof:
                raise ValueError('Future method declaration')
        contacts = {r['Invoice ID']: r for r in tables['Collection Evidence']}
        if len(contacts) != len(tables['Collection Evidence']):
            raise ValueError('Ambiguous current invoice correspondence')
        authorities = {r['Invoice ID']: r for r in tables['Collection Authority']}
        initiatives = {r['Invoice ID']: r for r in tables['Existing Recovery']}
        if len(authorities) != len(tables['Collection Authority']) or len(initiatives) != len(tables['Existing Recovery']):
            raise ValueError('Ambiguous invoice authority/initiative')
        if set(authorities)-contacts.keys() or set(initiatives)-contacts.keys():
            raise ValueError('Unmatched authority/initiative invoice')
        reviews = []
        def evidence(name, r, observed, authority='SOURCE_RECORD'):
            return Evidence(reference=json.dumps({'sheet':name,'row':r['_row'],'record':r,
                'context':contexts[r['Context ID']]},sort_keys=True,separators=(',',':')),
                authority=authority,observed_on=observed)
        for invoice_id, r in contacts.items():
            if not r['Customer ID']:
                raise ValueError('Missing collection customer identity')
            if r['Customer position'] not in ('ACKNOWLEDGED_PAYABLE','UNVERIFIED'):
                raise ValueError('Unknown customer position')
            if r['Processing context'] not in ('REMITTANCE_IN_PROGRESS','SERVICE_LIAISON_PENDING','MATCHING_CLEARED','NO_CURRENT_RESPONSE','FRAMEWORK_NEGOTIATION'):
                raise ValueError('Unknown processing context')
            if any(r[k] != 'NONE_RECORDED' for k in ('Formal dispute','Payment plan','Credit-note case')) or r['Posted settlement']:
                raise ValueError('Conflicting collection status requires a refreshed receivables source')
            cs = []
            for key, outcome in (('Last contact','CONTACTED'),('Response date','ACKNOWLEDGED')):
                if r[key]:
                    observed = _date(r[key])
                    if observed > asof or outcome == 'ACKNOWLEDGED' and r['Customer position'] != 'ACKNOWLEDGED_PAYABLE':
                        raise ValueError('Invalid dated correspondence')
                    cs.append(Contact(evidence=evidence('Collection Evidence',r,observed),outcome=outcome))
            if r['Recorded promise']:
                if not r['Response date']:
                    raise ValueError('Promise missing observed response date')
                cs.append(Contact(evidence=evidence('Collection Evidence',r,_date(r['Response date'])),
                    outcome='PROMISE_RECEIVED',promised_on=_date(r['Recorded promise'])))
            review = dict(invoice_id=invoice_id,customer_id=r['Customer ID'],contacts=tuple(cs))
            a = authorities.get(invoice_id)
            if a:
                if (a['Ordinary contact'] not in ('PERMITTED','ACCOUNT_CONTACT_ONLY','UNVERIFIED')
                        or a['Commercial mandate'] not in ('APPROVED','NEGOTIATION_ONLY','UNVERIFIED')
                        or a['Internal restriction'] not in ('NONE','INTERNAL_ACCELERATION_HOLD','UNVERIFIED')):
                    raise ValueError('Unknown authority vocabulary')
                if _date(a['Reviewed as of']) > asof:
                    raise ValueError('Future authority review')
                valid = (a['Effective from'] and a['Effective through'] and a['Approval reference'] and a['Recorded owner']
                    and _date(a['Effective from']) <= asof <= _date(a['Effective through'])
                    and _date(a['Reviewed as of']) == asof)
                if valid:
                    review['authority_evidence'] = evidence('Collection Authority',a,asof,'MANAGEMENT_ASSERTION')
                    if a['Internal restriction'] == 'INTERNAL_ACCELERATION_HOLD' and a['Scope and reason']:
                        review.update(addressability='STRATEGIC_CONSTRAINT',constraint_basis=a['Scope and reason'])
                    elif a['Internal restriction'] == 'NONE' and r['Customer position'] == 'ACKNOWLEDGED_PAYABLE':
                        if r['Processing context'] == 'SERVICE_LIAISON_PENDING' and a['Commercial mandate'] == 'APPROVED':
                            review['addressability'] = 'COMMERCIAL_INTERVENTION'
                        elif r['Processing context'] in ('MATCHING_CLEARED','REMITTANCE_IN_PROGRESS') and a['Ordinary contact'] == 'PERMITTED':
                            review['addressability'] = 'ORDINARY_COLLECTION'
            existing = initiatives.get(invoice_id)
            if existing:
                if existing['Customer ID'] != r['Customer ID'] or existing['Posted settlement']:
                    raise ValueError('Initiative identity/settlement conflict')
                if not existing['Recorded owner'] or existing['Observed status'] not in ('IN_PROGRESS','CUSTOMER_REMITTANCE_CONFIRMED'):
                    raise ValueError('Incomplete or unqualified named initiative status')
                started, observed = _date(existing['Initiated date']), _date(existing['Status date'])
                if not started <= observed <= asof:
                    raise ValueError('Invalid initiative chronology')
                review.update(initiative='ALREADY_UNDERWAY',initiative_id=existing['Evidence ID'],
                    initiative_started_on=started,initiative_review=evidence('Existing Recovery',existing,observed))
            # Extract absence never establishes a negative initiative review.
            reviews.append(CollectionReview(**review).model_dump(mode='json'))
        history = {r['Episode ID']: r for r in tables['Recovery History']}
        receipts = tables['Historical Receipts']
        for r in receipts:
            if r['Episode ID'] not in history or r['Posting status'] != 'POSTED' or _date(r['Receipt date']) > asof:
                raise ValueError('Unmatched/unposted/future historical receipt')
            if number(sheets['Historical Receipts'],'D'+str(r['_row'])) < 0:
                raise ValueError('Negative historical receipt is not qualified')
        pairs = {}
        for r in history.values():
            if not all(r[k] for k in ('Customer ID','Pair ID','Cohort ID','Matching review')):
                raise ValueError('Missing historical source identity')
            pairs.setdefault((r['Cohort ID'],r['Pair ID']),[]).append(r)
            start, end = _date(r['Opening date']), _date(r['Window end'])
            if ((end-start).days != _integer(r['Window days']) or not start < end <= _date(r['Recorded date']) <= asof
                    or (_date(r['Contractual due'])-_date(r['Invoice date'])).days != _integer(r['Terms days'])
                    or (start-_date(r['Contractual due'])).days != _integer(r['Age at opening'])):
                raise ValueError('Historical terms/age/window mismatch')
            if r['Observed mechanism'] not in ('ORDINARY_COLLECTION','COMMERCIAL_INTERVENTION','SERVICE_LIAISON') or r['Arm'] not in ('ADDITIONAL_PROCESS','REFERENCE'):
                raise ValueError('Unknown historical intervention/arm')
            amounts = [number(sheets['Historical Receipts'],'D'+str(p['_row'])) for p in receipts
                       if p['Episode ID'] == r['Episode ID'] and start <= _date(p['Receipt date']) <= end]
            with localcontext() as ctx:
                ctx.prec = max(60, sum(len(str(a)) for a in amounts)+10)
                total = sum(amounts,Decimal(0))
            k = str(r['_row']); raw, formula, kind = sheets['Recovery History']['U'+k]
            last = max((p['_row'] for p in receipts),default=4)
            expected = f'SUMIFS(\'Historical Receipts\'!$D$5:$D${last},\'Historical Receipts\'!$B$5:$B${last},A{k},\'Historical Receipts\'!$C$5:$C${last},">="&G{k},\'Historical Receipts\'!$C$5:$C${last},"<="&M{k})'
            if kind != 'n' or formula not in ('',expected) or Decimal(raw) != total or not 0 <= total <= number(sheets['Recovery History'],'K'+k):
                raise ValueError('Historical receipt/cache reconciliation failed')
        for pair in pairs.values():
            if len(pair) != 2 or {r['Arm'] for r in pair} != {'ADDITIONAL_PROCESS','REFERENCE'}:
                raise ValueError('Historical pair requires exactly two distinct arms')
            if any(pair[0][key] != pair[1][key] for key in ('Customer ID','Opening GBP','Currency','Terms days',
                    'Age at opening','Opening date','Window end','Observed mechanism','Matching review')):
                raise ValueError('Conflicting historical pair declaration')
        # This extract has episode IDs, not historical invoice IDs or a complete
        # inception manifest. Retain it in full; do not fabricate MatchedPairs.
        return dict(entity=entity,as_of=asof.isoformat(),horizon_days=horizon,reviews=reviews,tables=tables,
            history_limitations=['HISTORICAL_INVOICE_IDENTITIES_NOT_DECLARED','INCEPTION_COMPLETENESS_NOT_DECLARED',
                                 'PER_CURRENT_INVOICE_COHORT_NOT_DECLARED'],
            source_version=json.dumps(sorted({r['Dataset version'] for r in contexts.values()})))

    def capture(self, service, pack, path, storage_root, *, impact_id):
        """Retain the workbook and use the existing normalized ingestion owner."""
        path = Path(path)
        if hashlib.sha256(path.read_bytes()).hexdigest() != pack['sha256']:
            raise ValueError('Workbook changed after inspection')
        # Revalidate the extension so callers cannot replace the inspected data.
        from profit_doctor.intake.declared_accounting import read_cells
        data = self.inspect(read_cells(path))
        if data != pack['extensions'][self.name]:
            raise ValueError('Collection inspection envelope changed')
        q = service._impact(impact_id)
        from profit_doctor.reasoning.receivables.contracts import Snapshot, population
        snapshot = Snapshot.from_json(q.source_document)
        if self.layout == 'NORMALIZED':
            document = CollectionEvidence.model_validate(data['document'])
            if document.impact_id != impact_id:
                raise ValueError('Workbook names a different Impact')
        else:
            if (data['entity'],data['as_of']) != (snapshot.entity,snapshot.as_of.isoformat()) or pack['entity'] != snapshot.entity:
                raise ValueError('Collection scope differs from canonical receivables')
            document = CollectionEvidence(client_id=service.client_id,run_id=service.run_id,impact_id=impact_id,
                assessed_on=data['as_of'],horizon_days=data['horizon_days'],origin=snapshot.origin,
                coverage='PARTIAL',source_version=data['source_version'],dataset_version_id='pending',reviews=data['reviews'])
        keys = {(i.customer_id,i.invoice_id) for i in population(snapshot)['QUALIFYING_OVERDUE']}
        if {(r.customer_id,r.invoice_id) for r in document.reviews}-keys:
            raise ValueError('Collection invoice is outside canonical Impact population')
        con = service.contexts.source.connection
        with con:
            original = register_file(con,service.client_id,path,Path(storage_root))
        # Preserve every original reference and attach immutable workbook identity.
        def lineage(obj):
            if isinstance(obj,dict):
                if set(obj) == {'reference','authority','observed_on'}:
                    obj = {**obj,'reference':json.dumps({'workbook_id':original,'sha256':pack['sha256'],
                        'provider':self.name,'reference':obj['reference']},sort_keys=True,separators=(',',':'))}
                return {k:lineage(v) for k,v in obj.items()}
            return [lineage(v) for v in obj] if isinstance(obj,list) else obj
        payload = lineage(document.model_dump(mode='json'))
        payload['source_version'] = json.dumps({'source_version':document.source_version,'workbook_id':original,
            'sha256':pack['sha256'],'provider':self.name},sort_keys=True,separators=(',',':'))
        document = CollectionEvidence.model_validate(payload)
        with TemporaryDirectory() as directory:
            source = Path(directory)/'collection.csv'
            with source.open('w',newline='',encoding='utf-8') as stream:
                writer = csv.DictWriter(stream,fieldnames=['collection']);writer.writeheader()
                writer.writerow({'collection':document.to_json()})
            return service.ingest_evidence(source,storage_root)
