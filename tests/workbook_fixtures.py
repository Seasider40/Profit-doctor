"""Explicit CI workbook evidence; external PD_UWB overrides remain supported.

Scenario 2 is the original repository demo workbook, byte-for-byte. Scenario 1
is a NEW synthetic regression contract, not a reconstruction of the absent
external workbook. Its deliberately invalid capacity and control discrepancies
must remain visible and must never become invented financial benefits.
"""
import os
from pathlib import Path
from datetime import datetime
from zipfile import ZipFile, ZipInfo, ZIP_STORED
from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC = ROOT / 'tests' / 'fixtures' / 'workbooks' / 'scenario1_synthetic.xlsx'
SCENARIO2 = ROOT / 'demo' / 'v237_scenario2' / 'uploaded_source.xlsx'


def scenario_path(number):
    override = os.environ.get(f'PD_UWB{number}')
    return Path(override) if override else {1: SYNTHETIC, 2: SCENARIO2}[number]


def generate_scenario1(path):
    """Generate fixed synthetic evidence without Excel or a formula evaluator."""
    from io import BytesIO
    workbook = Workbook()
    workbook.remove(workbook.active)
    workbook.properties.creator = 'Profit Doctor synthetic CI fixtures'
    workbook.properties.created = datetime(2026, 1, 1)
    workbook.properties.modified = datetime(2026, 1, 1)

    def sheet(name, headers, rows):
        ws = workbook.create_sheet(name)
        ws.append([f'SYNTHETIC CI Scenario 1 FY2026 - {name}'])
        ws.append([])
        ws.append(headers)
        for row in rows:
            ws.append(row)
        return ws

    sheet('Customers', ['Customer Ledger', 'Annual Sales (£)', 'Gross Margin %',
                        'AR Balance (£)', 'Debtor Days'],
          [[f'Synthetic Customer {i:02}', 1200000 if i == 1 else 100000 + i * 1000,
            0.15 if i == 1 else 0.35, 10000 + i * 100, 60]
           for i in range(1, 26)])
    sheet('Staff Costs', ['Employee', 'Role', 'Department', 'FTE', 'Total Cost (£)'],
          [[f'Synthetic Employee {i:02}', 'Operator', 'Production', 1, 40000 + i * 100]
           for i in range(1, 26)])
    sheet('Capacity', ['Work Centre', 'Practical Capacity Hrs', 'Actual Productive Hrs',
                       'Actual Utilisation %'],
          [[f'Synthetic Centre {i}', 100, 1000 + i * 100, 1000 + i * 100]
           for i in range(1, 6)])
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    sheet('Management Accounts', ['£000 unless stated', *months, 'FY'], [
        ['Revenue', *[300 + i * 5 for i in range(12)], '=SUM(B4:M4)'],
        ['Cost of Sales', *[200 + i * 4 for i in range(12)], '=SUM(B5:M5)'],
        ['Gross Profit', *[100 + i for i in range(12)], '=SUM(B6:M6)'],
        ['EBITDA', *[40 + i for i in range(12)], '=SUM(B7:M7)'],
    ])
    sheet('Trial Balance', ['Code', 'Account', 'Category', 'Debit (£)', 'Credit (£)'], [
        ['1100', 'Trade Receivables', 'ASSET', 2000000, 0],
        ['1200', 'Cash at bank', 'ASSET', 95000, 0],
        ['1300', 'Inventory', 'ASSET', 300000, 0],
        ['2100', 'Trade Payables', 'LIABILITY', 0, 250000],
        *[[str(3000 + i), f'Synthetic Control {i}', 'ASSET', 100 + i, 0]
          for i in range(22)],
    ])
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    buffer = BytesIO()
    try:
        workbook.save(buffer)
    finally:
        workbook.close()
    # Fixed timestamps, metadata and uncompressed members avoid OS/zlib-dependent bytes.
    with ZipFile(BytesIO(buffer.getvalue())) as source, ZipFile(path, 'w', ZIP_STORED) as target:
        for name in sorted(source.namelist()):
            data = source.read(name)
            if name == 'docProps/core.xml':
                import re
                data = re.sub(rb'(<dcterms:modified[^>]*>).*?(</dcterms:modified>)',
                              rb'\g<1>2026-01-01T00:00:00Z\g<2>', data)
            info = ZipInfo(name, (2026, 1, 1, 0, 0, 0))
            info.create_system = 0
            info.external_attr = 0o600 << 16
            info.compress_type = ZIP_STORED
            target.writestr(info, data)


if __name__ == '__main__':
    generate_scenario1(SYNTHETIC)
