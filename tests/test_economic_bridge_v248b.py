"""Blind source acceptance plus independently specified adversarial invariants.

Expected arithmetic below is derived from the supplied workbook, not a private
answer key. Synthetic mutations are confined to disposable copies.
"""
from decimal import Decimal
import json
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET
import unittest
from sqlalchemy import insert, select, text
from sqlalchemy.exc import IntegrityError
from profit_doctor.intake.declared_accounting import capture_pack, inspect_pack, NS
from profit_doctor.persistence import bridge_schema as tables
from profit_doctor.reasoning.bridge.engine import BridgeEngine, pack_binding_groups
from profit_doctor.reasoning.bridge.service import BridgeService
from profit_doctor.reasoning.bridge.contracts import EconomicBridge
from profit_doctor.reasoning.domain.service import ScopeError, RevisionConflict
from profit_doctor.reasoning.measurement.service import MeasurementContextService
from tests import test_measurement_context_v248 as fixtures

SOURCE=Path(__file__).parent/'fixtures/bridge_v248/Golden_Manufacturing_v2.48_Blind.xlsx'


class EconomicBridgeV248B(unittest.TestCase):
    target_url=fixtures.MeasurementContextV248.target_url
    prepare_target=fixtures.MeasurementContextV248.prepare_target
    signal=fixtures.MeasurementContextV248.signal
    fact=fixtures.MeasurementContextV248.fact

    def setUp(self):
        fixtures.MeasurementContextV248.setUp(self)
        self.pack,self.captured=capture_pack(self.contexts,SOURCE,self.directory/'store')
        self.bridges=BridgeService(self.contexts)

    def inputs(self,family='REVENUE_BRIDGE'):
        return pack_binding_groups(self.contexts,self.captured,family,self.pack['years'])

    def assess(self,family='REVENUE_BRIDGE',*,detail=True):
        a,b,d=self.inputs(family)
        return self.bridges.engine.assess(family,2025,2026,a,b,d if detail else ())

    def create(self,family='REVENUE_BRIDGE',*,detail=True,previous=None):
        a,b,d=self.inputs(family)
        return self.bridges.create(family,2025,2026,a,b,d if detail else (),expected_previous=previous)

    def count(self,table):
        return self.session.scalar(select(text('count(*)')).select_from(table))

    def mutate(self,sheet_name,address,value):
        # Raw OOXML mutation avoids changing any unrelated source/cached cells.
        path=self.directory/'mutated.xlsx'
        with ZipFile(SOURCE) as source,ZipFile(path,'w') as target:
            wb=ET.fromstring(source.read('xl/workbook.xml'))
            relations={x.get('Id'):x.get('Target').lstrip('/') for x in ET.fromstring(source.read('xl/_rels/workbook.xml.rels'))}
            changes=value if isinstance(value,dict) else {(sheet_name,address):value}
            edits={}
            for (name,cell_address),replacement in changes.items():
                sheet=next(x for x in wb.findall('m:sheets/m:sheet',NS) if x.get('name')==name)
                part=relations[sheet.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')]
                if not part.startswith('xl/'):part='xl/'+part
                edits.setdefault(part,[]).append((cell_address,replacement))
            for info in source.infolist():
                content=source.read(info.filename)
                if info.filename in edits:
                    xml=ET.fromstring(content)
                    for cell_address,replacement in edits[info.filename]:
                        cell=next(x for x in xml.findall('.//m:c',NS) if x.get('r')==cell_address)
                        if cell.get('t') in ('s','inlineStr'):
                            cell.set('t','inlineStr')
                            for child in list(cell):cell.remove(child)
                            inline=ET.SubElement(cell,'{'+NS['m']+'}is')
                            literal=ET.SubElement(inline,'{'+NS['m']+'}t')
                        else:literal=cell.find('m:v',NS)
                        literal.text=replacement
                    content=ET.tostring(xml,encoding='utf-8')
                target.writestr(info,content)
        return path

    def test_source_identity_and_explicit_context(self):
        self.assertEqual('5a3a627c465f15f6bef34eeb339cf0aabb3c037059e5d07e73b8af63adf89af2',self.pack['sha256'])
        self.assertEqual(168,len(self.captured))
        self.assertEqual(26,len(self.pack['releases']))
        self.assertTrue(all(c.entity_id=='c1' and c.currency=='GBP' for c in self.captured))

    def test_revenue_exact_reconciliation_and_unexplained_residual(self):
        b=self.assess().bridge
        self.assertIsNotNone(b)
        self.assertEqual((Decimal('12000000'),Decimal('13500000')),(b.opening,b.closing))
        self.assertEqual(Decimal('1725000'),b.components[0].amount)
        self.assertEqual(Decimal('-225000'),b.residual)
        self.assertEqual(b.closing,b.opening+sum(c.amount for c in b.components)+b.residual)

    def test_contribution_zero_never_relabelled_as_gross_profit(self):
        b=self.assess('MARGIN_OR_PROFIT_BRIDGE').bridge
        self.assertEqual('contribution_0',b.metric)
        self.assertEqual((Decimal('3600000'),Decimal('3712500')),(b.opening,b.closing))
        self.assertEqual(Decimal('200750'),b.components[0].amount)
        self.assertEqual(Decimal('-88250'),b.residual)

    def test_working_capital_explicit_stock_and_cash_signs(self):
        b=self.assess('WORKING_CAPITAL_BRIDGE').bridge
        self.assertEqual((Decimal('1650000'),Decimal('2350000')),(b.opening,b.closing))
        self.assertEqual(Decimal(0),b.residual)
        self.assertEqual({'AR_MOVEMENT':Decimal('550000'),'INVENTORY_MOVEMENT':Decimal('350000'),'AP_MOVEMENT':Decimal('-200000')},{c.kind:c.amount for c in b.components})
        self.assertTrue(all(c.cash_direction_amount==-c.amount for c in b.components))

    def test_missing_attribution_retains_whole_movement_as_residual(self):
        b=self.assess(detail=False).bridge
        self.assertEqual((),b.components)
        self.assertEqual(Decimal('1500000'),b.residual)

    def test_partial_coverage_is_not_extrapolated(self):
        b=self.assess().bridge
        self.assertEqual('PARTIAL',b.components[0].coverage)
        self.assertEqual(24,len(b.components[0].input_bindings))
        self.assertNotEqual(b.closing-b.opening,b.components[0].amount)

    def test_restated_releases_not_added_as_movements(self):
        march=[r for r in self.pack['releases'] if r['period']=='2026-03-01']
        self.assertEqual({'SUPERSEDED','CANONICAL'},{r['status'] for r in march})
        rows=self.legacy.execute("SELECT amount FROM financial_statement_line WHERE line_code='REVENUE' AND period_end='2026-03-31'").fetchall()
        self.assertEqual([Decimal('1067000')],[Decimal(r[0]) for r in rows])
        self.assertTrue(all(c.revision_state=='RESTATEMENT' for c in self.captured if c.period.nature=='FLOW'))

    def test_cash_stock_does_not_qualify_operating_cash(self):
        result=self.assess('PROFIT_TO_CASH_BRIDGE')
        self.assertEqual('REFUSED',result.status);self.assertIsNone(result.bridge)
        self.assertIn('CLASSIFIED_OPERATING_CASH_AND_RECONCILIATION_MISSING',result.gaps)

    def test_incomplete_output_does_not_qualify_cost_output(self):
        self.assertEqual('REFUSED',self.assess('COST_TO_OUTPUT_BRIDGE').status)

    def test_missing_month_refuses_no_fabricated_bridge(self):
        a,b,d=self.inputs()
        r=self.bridges.create('REVENUE_BRIDGE',2025,2026,a[:-1],b,d)
        self.assertEqual('REFUSED',r.status);self.assertEqual(0,self.count(tables.bridge_snapshot))

    def test_duplicate_endpoint_refused(self):
        a,b,d=self.inputs()
        self.assertEqual('REFUSED',self.bridges.engine.assess('REVENUE_BRIDGE',2025,2026,a+a[:1],b,d).status)

    def test_wrong_measure_not_substituted(self):
        a,b,d=self.inputs('MARGIN_OR_PROFIT_BRIDGE')
        self.assertEqual('REFUSED',self.bridges.engine.assess('REVENUE_BRIDGE',2025,2026,a,b,d).status)

    def test_partial_accounting_endpoints_refused(self):
        a,b,d=self.inputs()
        self.assertEqual('REFUSED',self.bridges.engine.assess('REVENUE_BRIDGE',2025,2026,d[:12],d[12:],()).status)

    def test_stale_source_refused_historical_bridge_preserved(self):
        b=self.create().bridge
        row=self.contexts.get_binding(b.opening_bindings[0]).owner.source_id
        self.legacy.execute('UPDATE financial_statement_line SET amount=? WHERE statement_line_id=?',('999',row))
        self.assertEqual(b,self.bridges.get(b.snapshot_id))
        with self.assertRaises(RevisionConflict):self.bridges.get(b.snapshot_id,current=True)

    def test_replay_no_duplicate_history_or_audit(self):
        first=self.create().bridge
        self.assertEqual(first,self.create().bridge)
        self.assertEqual(1,self.count(tables.bridge_snapshot));self.assertEqual(1,self.count(tables.bridge_audit))
        self.assertEqual(first,self.bridges.get(first.snapshot_id,current=True))

    def test_changed_evidence_selection_requires_explicit_history(self):
        first=self.create(detail=False).bridge
        with self.assertRaises(RevisionConflict):self.create()
        second=self.create(previous=first.snapshot_id).bridge
        self.assertNotEqual(first.snapshot_id,second.snapshot_id)
        self.assertEqual(first.series_id,second.series_id)
        self.assertEqual(first,self.bridges.get(first.snapshot_id))
        rows=self.session.execute(select(tables.bridge_snapshot).order_by(tables.bridge_snapshot.c.revision)).mappings().all()
        self.assertEqual([1,2],[r['revision'] for r in rows]);self.assertEqual(first.snapshot_id,rows[1]['prior_id'])

    def test_caller_owned_rollback(self):
        self.session.commit();self.create();self.session.rollback()
        self.assertEqual(0,self.count(tables.bridge_snapshot));self.assertEqual(0,self.count(tables.bridge_input));self.assertEqual(0,self.count(tables.bridge_audit))

    def test_foreign_scope_read_and_database_input_rejected(self):
        b=self.create().bridge
        other=BridgeService(MeasurementContextService(self.session,'c2','r2',self.actor,self.legacy))
        with self.assertRaises(ScopeError):other.get(b.snapshot_id)
        with self.assertRaises(IntegrityError),self.session.begin_nested():
            self.session.execute(insert(tables.bridge_input).values(snapshot_id=b.snapshot_id,client_id='c2',binding_id=b.opening_bindings[0],role='OPENING'))

    def test_missing_binding_database_fk(self):
        b=self.create().bridge
        with self.assertRaises(IntegrityError),self.session.begin_nested():
            self.session.execute(insert(tables.bridge_input).values(snapshot_id=b.snapshot_id,client_id='c1',binding_id='absent',role='COMPONENT'))

    def test_decimal_serialization_and_tamper_rejected(self):
        b=self.assess('MARGIN_OR_PROFIT_BRIDGE').bridge
        self.assertEqual(b,EconomicBridge.from_json(b.to_json()))
        data=b.model_dump();data['closing']=float(b.closing)
        with self.assertRaises(ValueError):EconomicBridge.model_validate(data)
        data=b.model_dump();data['residual']='0'
        with self.assertRaises(ValueError):EconomicBridge.model_validate(data)

    def test_no_downstream_promotions(self):
        names=('reasoning_object_v243','canonical_story','canonical_hypothesis','economic_impact_v2','opportunity_v2')
        before={n:self.session.scalar(text('SELECT count(*) FROM '+n)) for n in names}
        self.create()
        self.assertEqual(before,{n:self.session.scalar(text('SELECT count(*) FROM '+n)) for n in names})

    def test_no_price_volume_mix_or_cost_component_fabricated(self):
        self.assertEqual({'SELECTED_POPULATION_MOVEMENT'},{c.kind for c in self.assess().bridge.components})

    def test_source_supersession_tamper_refused(self):
        path=self.mutate('Versions','E20','1067001')
        with self.assertRaisesRegex(ValueError,'canonical release'):inspect_pack(path)

    def test_unknown_context_declaration_refused(self):
        path=self.mutate('Context','F5','Unknown population')
        with self.assertRaisesRegex(ValueError,'context definition'):inspect_pack(path)

    def test_formula_cache_mismatch_refused(self):
        path=self.mutate('Customer Product','H122','999')
        with self.assertRaisesRegex(ValueError,'cache disagrees'):inspect_pack(path)

    def test_repeated_capture_reuses_contexts_and_revisions(self):
        old=tuple(c.context_id for c in self.captured)
        _,again=capture_pack(self.contexts,SOURCE,self.directory/'store')
        self.assertEqual(old,tuple(c.context_id for c in again))

    def test_missing_selected_month_cannot_be_zero(self):
        path=self.mutate('Customer Product','C5','DIFFERENT-CUSTOMER')
        with self.assertRaisesRegex(ValueError,'missing monthly'):inspect_pack(path)

    def test_fractional_version_number_rejected(self):
        path=self.mutate('Versions','D5','1.5')
        with self.assertRaisesRegex(ValueError,'version number'):inspect_pack(path)

    def test_unknown_currency_scale_rejected(self):
        path=self.mutate('Context','C5','GBP / thousands')
        with self.assertRaisesRegex(ValueError,'context definition'):inspect_pack(path)

    def test_different_period_comparison_refused(self):
        a,b,d=self.inputs()
        self.assertEqual('REFUSED',self.bridges.engine.assess('REVENUE_BRIDGE',2024,2026,a,b,d).status)

    def test_corrected_source_history_precision_and_supersession(self):
        first=self.create().bridge
        path=self.mutate(None,None,{('Management PL','C28'):'1347000.00000000000000000001',('Versions','E30'):'1347000.00000000000000000001'})
        pack,contexts=capture_pack(self.contexts,path,self.directory/'store')
        inputs=pack_binding_groups(self.contexts,contexts,'REVENUE_BRIDGE',pack['years'])
        second=self.bridges.create('REVENUE_BRIDGE',2025,2026,*inputs,expected_previous=first.snapshot_id).bridge
        self.assertEqual(Decimal('13500000.00000000000000000001'),second.closing)
        self.assertEqual(second,self.bridges.get(second.snapshot_id,current=True))
        self.assertEqual(first,self.bridges.get(first.snapshot_id))
        self.assertEqual('REFUSED',self.assess().status)

    def test_source_record_identity_not_guessed(self):
        path=self.mutate('Management PL','O5','UNRELATED-SOURCE')
        with self.assertRaisesRegex(ValueError,'source identity'):inspect_pack(path)

    def test_duplicate_source_version_key_rejected(self):
        path=self.mutate('Versions','D19','2')
        with self.assertRaisesRegex(ValueError,'Duplicate source release key'):inspect_pack(path)
