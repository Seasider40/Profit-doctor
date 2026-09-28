"""Audit frozen Signal emission sites; write intentional qualification coverage.

This is static producer coverage, not a claim every conditional Signal appeared
in a particular workbook. Dynamic emissions are explicitly expanded, never guessed.
"""
import ast
from dataclasses import asdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from profit_doctor.reasoning.canonical.registry import REGISTRY, REFUSALS, ZERO_DENOMINATOR_GUARDS


def inventory():
    path = ROOT / 'profit_doctor/diagnostic/engine.py'
    tree = ast.parse(path.read_text(encoding='utf-8'))
    parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    results = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        fields = {k.value: v for k, v in zip(node.keys, node.values) if isinstance(k, ast.Constant)}
        if not {'type', 'evidence'} <= fields.keys():
            continue
        typ = fields['type']
        if isinstance(typ, ast.Constant):
            types = [typ.value]
        elif isinstance(typ, ast.IfExp):
            types = [ast.literal_eval(typ.body), ast.literal_eval(typ.orelse)]
        elif isinstance(typ, ast.JoinedStr) and ast.unparse(typ) == "f'{etype}_MARGIN_VARIANCE'":
            types = ['CUSTOMER_MARGIN_VARIANCE', 'PRODUCT_MARGIN_VARIANCE']
        elif isinstance(typ, ast.Name):
            owner = parents[node]
            while not isinstance(owner, ast.For):
                owner = parents[owner]
            if typ.id == 'p':
                types = ast.literal_eval(owner.iter)
            elif typ.id == 'typ':
                types = [ast.literal_eval(x.elts[0]) for x in owner.iter.elts]
            else:
                raise ValueError('Unreviewed dynamic Signal expression')
        else:
            raise ValueError('Unreviewed Signal expression')
        owner = node
        while not isinstance(owner, ast.FunctionDef):
            owner = parents[owner]
        # Source site + producer function are retained even where one type is
        # emitted by multiple diagnostics with different semantics.
        for name in types:
            mappings = [asdict(m) | {'refuse_ambiguous_zero_slot': ZERO_DENOMINATOR_GUARDS.get((m.diagnostic, m.signal_type))}
                        for (_, t), m in REGISTRY.items() if t == name]
            if mappings:
                classification, reason = 'SAFE_TO_CANONICALISE', 'Only listed producer mappings; record-level eligibility, slots, denominator guards and lineage must also pass'
            elif name in REFUSALS:
                classification, reason = REFUSALS[name]
            else:
                raise ValueError(f'Unclassified emitted Signal: {name}')
            results.append(dict(signal_type=name, producer=owner.name, source=f'profit_doctor/diagnostic/engine.py:{node.lineno}',
                classification=classification, reason=reason, mappings=mappings,
                source_slots={k: ast.unparse(fields[k]) for k in ('observed', 'comparison', 'variance', 'unit') if k in fields}))
    return sorted(results, key=lambda r: (r['signal_type'], r['source']))


def main():
    rows = inventory()
    document = {'baseline': '16576f6805f73287fac5bba1b8c050bd2ae432a4',
        'coverage_basis': 'All frozen static emission sites, including explicit closed dynamic expansions; not runtime occurrence coverage',
        'writer': 'diagnostic.engine._execute; intake bridge calls the same engine; SQLAlchemy migration copies existing Signals',
        'distinct_signal_types': len({r['signal_type'] for r in rows}), 'emission_variants': len(rows), 'signals': rows}
    (ROOT/'qualification/signal_mapping_v244.json').write_text(json.dumps(document, indent=2)+'\n', encoding='utf-8')
    lines = ['# v2.44 Signal mapping coverage', '', document['coverage_basis'], '',
             '| Signal | Classification | Reason |', '|---|---|---|']
    seen = set()
    for row in rows:
        if row['signal_type'] not in seen:
            seen.add(row['signal_type'])
            lines.append(f"| {row['signal_type']} | {row['classification']} | {row['reason']} |")
    (ROOT/'docs/V2_44_SIGNAL_MAPPING.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in document.items() if k != 'signals'}))


if __name__ == '__main__':
    main()
