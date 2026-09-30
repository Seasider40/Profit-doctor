"""Registered tabular evidence extension. No company names or target amounts."""
import csv
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from profit_doctor.intake.declared_accounting import value, number, excel_date, data_rows
from profit_doctor.ingestion.northstar import register_file
from profit_doctor.reasoning.receivables.contracts import Invoice, Snapshot, Terms, StatusEvidence


HEADERS = {
 'Customer Terms': ('Terms ID','Customer ID','Contract ID','Net days','Effective from','Effective through','Term basis','Evidence reference','Source ID','Dataset version','Context ID','Entity','Currency','Verified as of'),
 'AR Detail': ('Invoice ID','Customer ID','Terms ID','Invoice date','Terms days','Contractual due','As of','Outstanding GBP','Days overdue','Age bucket','Reviewed status','Status reviewed','Evidence reference','Source ID','Dataset version','Context ID','Entity','Currency'),
 'Inventory Detail': ('Lot ID','SKU','Description','Carrying GBP','Units','Receipt date','Last issue date','Status','Status reviewed','As of','Evidence reference','Source ID','Dataset version','Context ID','Entity','Currency','NRV estimate GBP','Approved write-down GBP','Excess benchmark','Avoidability assessment','Expected loss GBP'),
 'Customer Contracts': ('Customer ID','Customer name','Contract ID','Contract start','Renewal date','Cancellation notice','Reviewed as of','Risk scenario ID','Loss probability','Source ID','Dataset version','Context ID','Entity','Currency'),
 'Payment History': ('Settled invoice ID','Customer ID','Terms ID','Invoice date','Contractual due','Settlement date','Settled GBP','Source ID','Dataset version','Context ID','Entity','Currency'),
 'Evidence Context': ('Context ID','Entity','As of','Currency','Measurement','Coverage','Definition and availability','Source ID','Dataset version','Provenance'),
}


class ReceivablesWorkbook:
    name = 'RECEIVABLES_WORKBOOK_1'
    sheets = frozenset(HEADERS)

    def inspect(self, sheets):
        rows = {name:data_rows(sheets[name], header) for name,header in HEADERS.items()}
        t, a = sheets['Customer Terms'], sheets['AR Detail']
        terms = {}
        for r in rows['Customer Terms']:
            k = str(r); key = value(t,'A'+k)
            if key in terms: raise ValueError('Duplicate terms identity')
            if value(t,'G'+k) != 'Calendar days after invoice date': raise ValueError('Unqualified term convention')
            days = number(t,'D'+k)
            if days != int(days): raise ValueError('Fractional terms days are unsupported')
            terms[key] = (r, value(t,'B'+k), Terms(reference=value(t,'H'+k),days=int(days),
                effective_from=excel_date(t,'E'+k),effective_to=excel_date(t,'F'+k)))
        contexts = {}
        c = sheets['Evidence Context']
        for r in rows['Evidence Context']:
            key=value(c,'A'+str(r))
            if key in contexts: raise ValueError('Duplicate evidence context')
            contexts[key] = r
        invoices=[]; entities=set(); versions=set(); sources=set(); dates=set(); context_ids=set()
        for r in rows['AR Detail']:
            k=str(r); term_row,customer,term = terms[value(a,'C'+k)]
            if value(a,'B'+k)!=customer: raise ValueError('Terms customer mismatch')
            date=excel_date(a,'D'+k); asof=excel_date(a,'G'+k)
            if excel_date(t,'N'+str(term_row))!=asof: raise ValueError('Terms review date mismatch')
            if value(t,'L'+str(term_row))!=value(a,'Q'+k) or value(t,'M'+str(term_row))!=value(a,'R'+k):
                raise ValueError('Terms entity/currency mismatch')
            # Validate supported source formulas and their caches independently.
            expected = {'E'+k:(Decimal(term.days),f"VLOOKUP(C{k},'Customer Terms'!$A$5:$D${max(rows['Customer Terms'])},4,0)"),
                        'F'+k:(number(a,'D'+k)+term.days,f'D{k}+E{k}'),
                        'I'+k:(Decimal(max(0,(asof-date-timedelta(days=term.days)).days)),f'MAX(0,G{k}-F{k})')}
            for address,(computed,formula) in expected.items():
                raw,actual,kind=a[address]
                if kind!='n' or Decimal(raw)!=computed or actual not in ('',formula):
                    raise ValueError('Contractual calculation/cache mismatch: '+address)
            days=int(expected['I'+k][0]); bucket='Within terms' if days==0 else '1-30' if days<=30 else '31-60' if days<=60 else '61-90' if days<=90 else '90+'
            if a['J'+k][0]!=bucket: raise ValueError('Age bucket disagrees with terms')
            invoices.append(Invoice(invoice_id=value(a,'A'+k),customer_id=customer,invoice_date=date,
                explicit_due=date+timedelta(days=term.days),terms=term,outstanding=number(a,'H'+k),
                currency=value(a,'R'+k),as_of=asof,status=StatusEvidence(status=value(a,'K'+k),
                    reviewed_at=excel_date(a,'L'+k),authority='SOURCE_RECORD',reference=value(a,'M'+k)),
                source_reference=f'AR Detail!A{r}:R{r}; Customer Terms!A{term_row}:N{term_row}'))
            entities.add(value(a,'Q'+k)); versions.add(value(a,'O'+k)); sources.add(value(a,'N'+k));dates.add(asof);context_ids.add(value(a,'P'+k))
        if any(len(s)!=1 for s in (entities,versions,sources,dates,context_ids)): raise ValueError('Mixed snapshot context')
        cr=contexts[next(iter(context_ids))]; ck=str(cr)
        if (value(c,'B'+ck),excel_date(c,'C'+ck),value(c,'D'+ck),value(c,'H'+ck),value(c,'I'+ck)) != (next(iter(entities)),next(iter(dates)),'GBP',next(iter(sources)),next(iter(versions))):
            raise ValueError('Evidence registry disagrees with invoice population')
        coverage=value(c,'F'+ck)
        if coverage!='Open trade receivables; complete entity': raise ValueError('Unqualified workbook coverage declaration')
        return dict(invoices=[i.model_dump(mode='json') for i in invoices],entity=next(iter(entities)),
            as_of=next(iter(dates)).isoformat(),source_version=next(iter(versions)),source_id=next(iter(sources)),
            coverage='COMPLETE',coverage_basis=coverage,
            explicitly_unconsumed={name:'Retained evidence only; no positive Impact provider for this population' for name in ('Inventory Detail','Customer Contracts','Payment History')})

    def capture(self, provider, pack, path, storage_root, *, origin, ledger_id, expected_previous=None):
        data=pack['extensions'][self.name]
        controls=[r for r in pack['records'] if r['metric']=='AR' and r['period']==data['as_of'] and r['segment']=='LEGAL_ENTITY']
        if len(controls)!=1: raise ValueError('Unique matching governed AR control required')
        if pack['entity']!=data['entity']: raise ValueError('AR entity differs from accounting pack')
        con=provider.contexts.source.connection
        with con: original=register_file(con,provider.client_id,Path(path),Path(storage_root))
        snapshot=Snapshot(client_id=provider.client_id,run_id=provider.run_id,ledger_id=ledger_id,
            entity=data['entity'],as_of=data['as_of'],scope='LEGAL_ENTITY',coverage=data['coverage'],coverage_basis=data['coverage_basis'],
            source_version=data['source_version'],origin=origin,invoices=tuple(data['invoices']),
            control_amount=controls[0]['amount'],control_reference=f"{controls[0]['sheet']}!{controls[0]['column']}{controls[0]['row']}",
            dataset_version_id='pending',workbook_source_id=original)
        with TemporaryDirectory() as directory:
            source=Path(directory)/'receivables.csv'
            with source.open('w',newline='',encoding='utf-8') as stream:
                writer=csv.DictWriter(stream,fieldnames=['snapshot']);writer.writeheader();writer.writerow({'snapshot':snapshot.to_json()})
            return provider.ingest_csv(source,storage_root,expected_previous=expected_previous)
