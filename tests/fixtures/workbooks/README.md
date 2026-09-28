# Workbook regression evidence

`scenario1_synthetic.xlsx` is a **new synthetic CI fixture**, not the missing
external Scenario-1 workbook previously referenced under `/mnt/data`.
Its complete generation code is in `tests/workbook_fixtures.py`:

```text
python -m tests.workbook_fixtures
```

The fixed contract contains 25 customer summaries, 25 staff records, 48 monthly
P&L values, 26 trial-balance records, an AR control mismatch, and five work centres
with implausible productive hours (utilisation above 250%). The invalid capacity
must remain refused, with no repaired hours or invented financial benefit. FY
formula cells deliberately have no cached result. This tests the existing
formula-quality and fail-closed behaviour, not Excel formula evaluation.

Scenario 2 uses `demo/v237_scenario2/uploaded_source.xlsx` unchanged. Its SHA-256 is
`ab0d260fccec7fab83b9e9a0eafb9c40147118bb0d99e2015776c40067963a5a`, matching the
repository's original demo manifest. It retains its original cached formulas and
intentional AR/AP/inventory/debt control problems.

The fixture regression verifies Scenario-2 identity and byte-repeatable
Scenario-1 generation. Fixed ZIP metadata, uncompressed members and a pinned
openpyxl test dependency make regeneration independent of ZIP timestamps/zlib.
`PD_UWB1`/`PD_UWB2` remain explicit opt-in overrides for external evidence; CI uses
the defaults. Passing the synthetic contract is not proof that the absent
original Scenario-1 workbook passes, and neither fixture is real-SME evidence.
