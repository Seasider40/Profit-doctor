"""Declared Accounting Pack 1: opt-in source binding, never an answer-key reader.

Exact source declarations govern this narrow layout. Unknown definitions refuse.
Read OOXML numeric lexemes as Decimal; never recalculate or rewrite the workbook.
Only authoritative input cells and the supported detail multiplication are used.
"""
import csv
from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal, localcontext
import hashlib
import json
from pathlib import Path
import re
from tempfile import TemporaryDirectory
from zipfile import ZipFile
import xml.etree.ElementTree as ET

from profit_doctor.ingestion.accounting import ingest_accounting_file
from profit_doctor.ingestion.northstar import register_file
from profit_doctor.management.restatement import register_revision, ensure_schema, _hash

NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
REL = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'
PL_BASIS = 'Accrual management accounts. Contribution 0 equals revenue less costs before C0. Same accounting basis throughout.'
BS_BASIS = 'Consistent balance definitions. Net trade working capital equals trade receivables plus inventory less trade payables.'
DETAIL_BASIS = 'Revenue and Contribution 0 by customer/product. A/B units comparable within SKU. Other unit fields are blank.'


def read_cells(path):
    """Literal text/numeric lexemes and formula text, with no executable content."""
    with ZipFile(path) as archive:
        if sum(i.file_size for i in archive.infolist()) > 50_000_000:
            raise ValueError('Source pack exceeds the bounded reader contract')
        wb = ET.fromstring(archive.read('xl/workbook.xml'))
        props = wb.find('m:workbookPr', NS)
        if props is not None and props.get('date1904') in ('1', 'true'):
            raise ValueError('1904 date system is not qualified by this input contract')
        shared = []
        if 'xl/sharedStrings.xml' in archive.namelist():
            shared = [''.join(x.itertext()) for x in ET.fromstring(archive.read('xl/sharedStrings.xml')).findall('m:si', NS)]
        links = {r.get('Id'): r.get('Target') for r in ET.fromstring(archive.read('xl/_rels/workbook.xml.rels'))}
        sheets = {}
        for sheet in wb.findall('m:sheets/m:sheet', NS):
            target = links[sheet.get(REL)]
            target = target.lstrip('/') if target.startswith('/') else 'xl/' + target
            cells = {}
            for cell in ET.fromstring(archive.read(target)).findall('m:sheetData/m:row/m:c', NS):
                kind = cell.get('t', 'n')
                value = cell.findtext('m:v', '', NS)
                if kind == 'inlineStr':
                    value = ''.join(cell.find('m:is', NS).itertext())
                elif kind == 's':
                    value = shared[int(value)]
                cells[cell.get('r')] = (value, cell.findtext('m:f', '', NS), kind)
            sheets[sheet.get('name')] = cells
        return sheets


def value(cells, address):
    raw, formula, kind = cells.get(address, ('', '', ''))
    if formula or kind == 'e':
        raise ValueError('Expected an authoritative literal at ' + address)
    return raw


def number(cells, address, *, detail=False):
    raw, formula, kind = cells.get(address, ('', '', ''))
    if kind != 'n' or not raw:
        raise ValueError('Missing/non-numeric measurement at ' + address)
    result = Decimal(raw)
    if not result.is_finite():
        raise ValueError('Non-finite source number')
    if formula:
        # Only source-defined C0 multiplication for this row; no general engine.
        match = re.fullmatch(r'E(\d+)\*([0-9]+(?:\.[0-9]+)?)', formula)
        if not detail or not match or address != 'H' + match[1]:
            raise ValueError('Unsupported authoritative formula at ' + address)
        with localcontext() as ctx:
            ctx.prec = 60
            if number(cells, 'E' + match[1]) * Decimal(match[2]) != result:
                raise ValueError('Formula cache disagrees with exact source arithmetic')
    return result


def excel_date(cells, address):
    serial = number(cells, address)
    if serial != int(serial) or serial < 61:
        raise ValueError('Unsupported Excel date')
    return date(1899, 12, 30) + timedelta(days=int(serial))


def data_rows(cells, header):
    actual = tuple(value(cells, chr(65+i)+'4') for i in range(len(header)))
    if actual != tuple(header):
        raise ValueError('Unqualified source layout/header')
    rows = sorted({int(re.search(r'\d+', key)[0]) for key in cells if key.startswith('A') and int(key[1:]) >= 5 and value(cells, key)})
    if not rows:
        raise ValueError('Empty source table')
    return rows


def inspect_pack(path, *, providers=()):
    """Return retained declarations/records; no inferred missing classifications."""
    sheets = read_cells(path)
    required = {'README', 'Management PL', 'Balance Sheet', 'Customer Product', 'Versions', 'Cash and Output', 'Context'}
    claimed = set()
    extensions = {}
    for provider in providers:
        if claimed & provider.sheets or required & provider.sheets:
            raise ValueError('Conflicting workbook evidence providers')
        claimed.update(provider.sheets)
    if set(sheets) != required | claimed:
        raise ValueError('Unqualified source sheet catalogue')
    for provider in providers:
        if provider.name in extensions: raise ValueError('Duplicate evidence provider')
        extensions[provider.name] = provider.inspect(sheets)
    registry = sheets['Context']
    rows = data_rows(registry, ('Context ID','Entity','Currency / scale','Measurement','Period scope','Population','Basis / definition','Source / version','Availability notes'))
    contexts = {value(registry, 'A'+str(r)): {k:value(registry, chr(65+i)+str(r)) for i,k in enumerate(('id','entity','unit','nature','period','population','basis','version','notes'))} for r in rows}
    if len(contexts) != len(rows):
        raise ValueError('Duplicate context identities')
    for key, nature, population, basis in [('CTX-PL','Monthly flow','Complete legal entity',PL_BASIS),
            ('CTX-BS','Month-end stock','Complete legal entity',BS_BASIS),
            ('CTX-DETAIL','Monthly flow','Nonrandom selected customer/product population',DETAIL_BASIS)]:
        c = contexts[key]
        if (c['unit'], c['nature'], c['population'], c['basis']) != ('GBP / whole pounds', nature, population, basis):
            raise ValueError('Unknown source context definition: ' + key)
    entity = contexts['CTX-PL']['entity']
    if not entity or any(contexts[k]['entity'] != entity for k in ('CTX-BS','CTX-DETAIL')):
        raise ValueError('Inconsistent entity scope')
    if 'aligned to restated accounts' not in contexts['CTX-DETAIL']['version']:
        raise ValueError('Detail vintage alignment is unqualified')
    versions = sheets['Versions']
    vr = data_rows(versions, ('Record ID','Period','Metric','Version','Amount','Status','Superseded by','Release date','Context ID','Reason'))
    releases = {}
    for r in vr:
        s = str(r)
        record = dict(id=value(versions,'A'+s), period=excel_date(versions,'B'+s), metric=value(versions,'C'+s),
            version=int(number(versions,'D'+s)), amount=number(versions,'E'+s), status=value(versions,'F'+s),
            successor=value(versions,'G'+s), context=value(versions,'I'+s), row=r)
        if number(versions,'D'+s)!=record['version'] or record['version']<1:
            raise ValueError('Invalid source version number')
        if record['id'] in releases or record['metric'] != 'Revenue' or record['context'] != 'CTX-PL':
            raise ValueError('Ambiguous source release')
        releases[record['id']] = record
    canonical = {}
    release_keys=[(r['period'],r['metric'],r['version']) for r in releases.values()]
    if len(release_keys)!=len(set(release_keys)):
        raise ValueError('Duplicate source release key')
    for record in releases.values():
        if record['status'] == 'CANONICAL' and not record['successor']:
            if record['period'] in canonical:
                raise ValueError('Multiple canonical versions for a period')
            canonical[record['period']] = record
        elif record['status'] == 'SUPERSEDED':
            new = releases.get(record['successor'])
            if not new or new['status'] != 'CANONICAL' or new['period'] != record['period'] or new['version'] <= record['version']:
                raise ValueError('Broken supersession chain')
        else:
            raise ValueError('Unknown release status')
    output = []
    def add(sheet, row, col, metric, amount, period, context, segment, stock=False):
        c = contexts[context]
        output.append(dict(sheet=sheet,row=row,column=col,metric=metric,amount=str(amount),period=period.isoformat(),
            context=context,segment=segment,stock=stock,source_id=value(sheets[sheet], ('O' if sheet=='Management PL' else 'R' if sheet=='Balance Sheet' else 'J')+str(row))))
    pl = sheets['Management PL']
    pr = data_rows(pl, ('Period','FY','Revenue','Contribution 0','C0 margin','Costs before C0','Payroll after C0','Other overhead','Depreciation','Operating profit','Interest expense','Profit before tax','Tax expense','Profit after tax','Source ID','Version','Context ID'))
    periods = []
    for r in pr:
        s=str(r); p=excel_date(pl,'A'+s); periods.append(p)
        release=canonical.get(p)
        if p.day != 1 or int(number(pl,'B'+s)) != p.year or value(pl,'Q'+s) != 'CTX-PL' or not release or release['amount'] != number(pl,'C'+s) or release['version'] != number(pl,'P'+s):
            raise ValueError('P&L period/version/amount does not match canonical release')
        if release['id'] != value(pl,'O'+s)+'-REV-v'+str(release['version']):
            raise ValueError('P&L source identity does not match canonical release')
        for col, metric in [('C','REVENUE'),('D','CONTRIBUTION_0')]:
            add('Management PL',r,col,metric,number(pl,col+s),p,'CTX-PL','LEGAL_ENTITY')
    if len(set(periods)) != len(periods) or set(canonical) != set(periods):
        raise ValueError('Duplicate or unmatched accounting periods')
    years=sorted({p.year for p in periods})
    if len(years) != 2 or years[1] != years[0]+1 or set(periods) != {date(y,m,1) for y in years for m in range(1,13)}:
        raise ValueError('This contract requires two complete consecutive calendar years')
    expected_scope=f'Jan {years[0]} to Dec {years[1]}'
    if any(contexts[k]['period'] != expected_scope for k in ('CTX-PL','CTX-BS','CTX-DETAIL')):
        raise ValueError('Context period envelope disagrees with records')
    bs=sheets['Balance Sheet']; seen=set()
    br=data_rows(bs, ('Period','FY','Trade AR','Inventory','Trade AP','Net trade WC','Cash','Net fixed assets','Other current assets','Total assets','Other liabilities','Tax payable','Borrowings','Share capital','Retained earnings','Liabilities + equity','Balance check','Source ID','Context ID'))
    for r in br:
        s=str(r); p=excel_date(bs,'A'+s)
        if p in seen or p.day != monthrange(p.year,p.month)[1] or value(bs,'S'+s) != 'CTX-BS' or number(bs,'B'+s) != p.year:
            raise ValueError('Invalid balance-sheet as-of')
        seen.add(p)
        for col,metric in [('C','AR'),('D','INVENTORY'),('E','AP')]:
            add('Balance Sheet',r,col,metric,number(bs,col+s),p,'CTX-BS','LEGAL_ENTITY',True)
    if {(p.year,p.month) for p in seen} != {(p.year,p.month) for p in periods}:
        raise ValueError('Balance-sheet periods missing')
    detail=sheets['Customer Product']; keys=set()
    dr=data_rows(detail, ('Period','FY','Customer ID','Product','Revenue','Units sold','Unit price GBP','Contribution 0','Lifecycle','Source ID','Context ID'))
    for r in dr:
        s=str(r); p=excel_date(detail,'A'+s); key=(p,value(detail,'C'+s),value(detail,'D'+s))
        if p not in periods or key in keys or not all(key[1:]) or value(detail,'K'+s) != 'CTX-DETAIL' or number(detail,'B'+s) != p.year:
            raise ValueError('Ambiguous detail key/period/scope')
        keys.add(key)
        segment='CUSTOMER_PRODUCT:'+json.dumps(key[1:],separators=(',',':'))
        for col,metric in [('E','REVENUE'),('H','CONTRIBUTION_0')]:
            add('Customer Product',r,col,metric,number(detail,col+s,detail=True),p,'CTX-DETAIL',segment)
    population={key[1:] for key in keys}
    if keys!={(p,*member) for p in periods for member in population}:
        raise ValueError('Selected population has missing monthly records; absence is not zero')
    return dict(contract='DECLARED_ACCOUNTING_PACK_1',sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(),
        entity=entity,years=years,contexts=contexts,records=output,releases=[{k:str(v) if isinstance(v,(Decimal,date)) else v for k,v in x.items()} for x in releases.values()], **({'extensions':extensions} if providers else {}))


def capture_pack(service, path, storage_root, *, providers=()):
    pack=inspect_pack(path, providers=providers)  # Validate entire source before any ingestion write.
    service.workbook_providers = tuple(providers)
    con=service.source.connection
    original=register_file(con,service.client_id,Path(path),Path(storage_root)); con.commit()
    ensure_schema(con)
    captured=[]
    for stock,contract,logical in [(False,'D01_PNL','accounting:pnl'),(True,'D02_BALANCE_SHEET','accounting:balance_sheet')]:
        selected=[r for r in pack['records'] if r['stock']==stock]
        payload={'source_hash':pack['sha256'],'records':selected,'releases':pack['releases'] if not stock else []}
        prior=con.execute('SELECT * FROM source_revision WHERE client_id=? AND logical_source_key=? AND content_hash=?',
            (service.client_id,logical,_hash(payload))).fetchone()
        if prior is None:
            if not stock and any(r['status']=='SUPERSEDED' for r in pack['releases']):
                # Preserve existing revision architecture; original history is
                # evidence metadata, never appended to canonical accounting rows.
                register_revision(con,service.client_id,service.run_id,logical,
                    {'source_hash':pack['sha256'],'superseded_history':[r for r in pack['releases'] if r['status']=='SUPERSEDED']},
                    'Retained superseded revenue releases; excluded from canonical measurements')
            revision=register_revision(con,service.client_id,service.run_id,logical,payload,
                'Validated canonical source snapshot; no restatement treated as movement')
            prior=con.execute('SELECT * FROM source_revision WHERE revision_id=?',(revision['revision_id'],)).fetchone()
        # A separate selected-population subtotal, not duplicate company totals
        # and not an invented financial transaction. Preserve every source cell.
        detail_groups={}
        for r in selected:
            if r['context']=='CTX-DETAIL':
                detail_groups.setdefault((r['period'],r['metric']),[]).append(r)
        inputs=[r for r in selected if r['context']!='CTX-DETAIL']
        with localcontext() as arithmetic:
            arithmetic.prec=60
            for group in detail_groups.values():
                r=dict(group[0]);r['segment']='SELECTED_CUSTOMER_PRODUCT'
                r['amount']=str(sum((Decimal(x['amount']) for x in group),Decimal(0)))
                r['locators']=','.join(x['column']+str(x['row']) for x in group)
                inputs.append(r)
        rows=[]
        for r in inputs:
            p=date.fromisoformat(r['period']); detail=r['context']=='CTX-DETAIL'
            end=p if stock else date(p.year,p.month,monthrange(p.year,p.month)[1])
            code=('SELECTED_' if detail else '')+r['metric']
            name=('Selected population Contribution 0' if r['metric']=='CONTRIBUTION_0' else 'Selected population revenue') if detail else ('Contribution 0' if r['metric']=='CONTRIBUTION_0' else r['metric'])
            rows.append(dict(period_end=end.isoformat(),line_code=code,line_name=name,amount=r['amount'],
                period_start=p.isoformat(),reporting_basis='POINT_IN_TIME' if stock else 'MONTHLY',reporting_convention='Calendar inclusive',
                currency='GBP',economic_basis=BS_BASIS if stock else PL_BASIS,entity_type='CLIENT',entity_id=service.client_id,
                segment_scope=r['segment'],coverage='PARTIAL' if detail else 'COMPLETE',
                coverage_basis=pack['contexts'][r['context']]['population'],source_workbook_id=original,
                source_locator=f"{r['sheet']}!{r.get('locators',r['column']+str(r['row']))}; Context={r['context']}; Source={r['source_id']}; contract=DECLARED_ACCOUNTING_PACK_1",
                source_revision_id=prior['revision_id'],source_revision_content_hash=prior['content_hash']))
        with TemporaryDirectory() as directory:
            csvpath=Path(directory)/('balance-context.csv' if stock else 'flow-context.csv')
            with csvpath.open('w',newline='',encoding='utf-8') as stream:
                writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
            result=ingest_accounting_file(con,service.client_id,service.run_id,csvpath,contract,storage_root)
            captured.extend(service.capture_dataset(result['dataset_version_id']))
    return pack, tuple(captured)
