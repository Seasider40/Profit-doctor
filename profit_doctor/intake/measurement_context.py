"""Opt-in upstream context capture for the existing management-account extractor.

Numerical extraction remains the frozen _ma_rows implementation. This adapter
preserves original workbook provenance and explicit month/year declarations.
It does not certify accounting policy or population completeness.
"""
import csv
from pathlib import Path
import re
from tempfile import TemporaryDirectory

from profit_doctor.intake.bridge import _ma_rows
from profit_doctor.intake.workbook import open_workbook, _header_row, _norm
from profit_doctor.ingestion.northstar import register_file
from profit_doctor.ingestion.accounting import ingest_accounting_file


def capture_management_accounts(path, storage_root, context_service):
    path, storage_root = Path(path), Path(storage_root)
    source = context_service.source
    rows = _ma_rows(path)  # No changed values, rounding or new financial formula.
    if not rows:
        return ()
    source_id = register_file(source.connection, source.client_id, path, storage_root)
    source.connection.commit()  # Existing source store owns ingestion commits.
    with open_workbook(path, data_only=True) as wb:
        sheet = next(w for w in wb.worksheets if 'management accounts' in _norm(w.title))
        hr = _header_row(sheet)
        year = re.search(r'(20\d{2})', str(sheet.cell(1, 1).value or ''))
        months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
        columns = [(c, months.index(str(sheet.cell(hr, c).value))+1) for c in range(1, sheet.max_column+1)
                   if str(sheet.cell(hr, c).value) in months]
        aliases = {'revenue':'REV','sales':'REV','turnover':'REV','cost of sales':'COGS',
                   'cogs':'COGS','gross profit':'GP','ebitda':'EBITDA'}
        positions = [(r,c,m) for r in range(hr+1, sheet.max_row+1)
                     if _norm(sheet.cell(r,1).value) in aliases
                     for c,m in columns if isinstance(sheet.cell(r,c).value,(int,float))]
        if len(positions) != len(rows):
            raise ValueError('Upstream context no longer matches frozen extraction order')
        # Currency/scale needs the declaration that the old extractor assumes.
        scale_declared = '£000' in str(sheet.cell(hr,1).value or '')
        for row, (r,c,month) in zip(rows, positions):
            row['source_workbook_id'] = source_id
            row['source_locator'] = f'{sheet.title}!R{r}C{c}'
            row['currency'] = 'GBP' if scale_declared else ''
            row['period_start'] = f'{year.group(1)}-{month:02d}-01' if year else ''
            row['reporting_basis'] = 'MONTHLY' if year else 'UNKNOWN'
            row['reporting_convention'] = 'Calendar month, inclusive bounds' if year else ''
            # If the existing fallback year or scale was used, it is not evidence.
            # Currency/basis gaps therefore remain visible to qualification.
    with TemporaryDirectory() as directory:
        generated = Path(directory)/'management-accounts-context.csv'
        with generated.open('w', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        captured = []
        def capture(version):
            captured.extend(context_service.capture_dataset(version))
        ingest_accounting_file(source.connection, source.client_id, context_service.run_id,
            generated, 'D01_PNL', storage_root, context_sink=capture)
    return tuple(captured)
