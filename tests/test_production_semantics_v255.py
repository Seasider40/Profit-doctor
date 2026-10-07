"""Isolated engineering source fixtures; no production temporal or measurement writer."""
import csv
from datetime import date
import unittest

from profit_doctor.ingestion.northstar import register_dataset_version
from profit_doctor.reasoning.domain.contracts import Actor
from profit_doctor.reasoning.domain.service import RevisionConflict, ScopeError
from profit_doctor.reasoning.production_evidence.contracts import EvidenceDeclaration
from profit_doctor.reasoning.production_evidence.semantics import Manifest, Mapping, SourceChart, SemanticVerificationService
from profit_doctor.reasoning.production_evidence.source import DOMAIN, FIELDS, PROVIDER
from tests import test_production_evidence_foundation_v255 as foundation
from tests.test_production_evidence_foundation_v255 import record, scope


class SemanticVerificationV255(unittest.TestCase):
    def setUp(self):
        self.fx = foundation.RegisteredSourceFoundationV255('runTest')
        self.fx.setUp()
        self.addCleanup(self.fx.doCleanups)
        self.con = self.fx.connection
        self.counter = 0
        self.grants = {}
        self.scope = scope(definition='NET_REVENUE')
        self.actor = Actor(actor_type='HUMAN',actor_id='adviser1',source_authority='HUMAN_FD_JUDGEMENT')
        self.service = SemanticVerificationService(self.con,'c1','r1',self.authority)
        self.records = self.amounts('s1','100')
        self.controls = self.amounts('control1','100')
        self.manifest = Manifest(report_id='sales1',system_id='source-system1',extraction_id='export1',
            record_version_id=self.records,scope=self.scope,family='SALES_TRANSACTIONS',record_ids=('s1',),
            record_count=1,boundary=self.scope.population,inclusion_exclusion='all posted net sales',
            extraction_query='posted net sales, no customer or product filter',
            extraction_start='2026-01-01',extraction_end='2026-01-31',revision_id='source-rev1',
            change_kind='ORIGINAL',change_reference='original source report revision')
        self.chart = SourceChart(policy_reference='policy1',scope=self.scope,effective_from='2026-01-01',
            effective_to='2026-12-31',definition='NET_REVENUE',revenue_accounts=('4000',),
            recognition_basis='POSTED_ACCRUAL',revenue_basis='NET_OF_TAX_AND_CREDITS',
            cost_basis='NOT_APPLICABLE',amount_convention='POSITIVE_REVENUE_POSITIVE_COST')
        self.chart_version = self.document(self.chart,'chart')
        self.mapping = Mapping(mapping_id='mapping1',revision=1,scope=self.scope,effective_from='2026-01-01',
            effective_to='2026-12-31',actor=self.actor,definition='NET_REVENUE',revenue_accounts=('4000',),
            source_policy_reference='policy1',source_chart_version=self.chart_version)

    def authority(self,client,version,profile,digest):
        grant = self.grants.get(version)
        return grant[2] if client == 'c1' and grant and grant[:2] == (profile,digest) else None

    def register(self,path,profile,authority='SOURCE_DATA'):
        version,_,_,_ = register_dataset_version(self.con,'c1','j1',path,DOMAIN,profile,self.fx.root/'store')
        self.con.execute("UPDATE dataset_version SET ingestion_status='COMPLETED' WHERE dataset_version_id=?",(version,))
        self.con.commit()
        digest = self.con.execute('SELECT f.file_hash FROM dataset_version v JOIN source_file f ON f.source_file_id=v.source_file_id WHERE v.dataset_version_id=?',(version,)).fetchone()[0]
        self.grants[version] = (profile,digest,authority)
        return version

    def amounts(self,name,amount,*,changes=None,extras=()):
        self.counter += 1
        path = self.fx.root/f'records-{self.counter}.csv'
        values = dict(zip(FIELDS,(name,'4000','SALES',amount,'e1','l1','all-net-sales','2026-01-01',
            '2026-01-31','MONTHLY','GBP','NET_REVENUE')))
        if name.startswith('control'):
            values['record_kind'] = 'TB_ACTIVITY'
        values.update(changes or {})
        with path.open('w',newline='',encoding='utf-8') as stream:
            writer = csv.DictWriter(stream,fieldnames=FIELDS); writer.writeheader();writer.writerow(values)
            for extra in extras:
                writer.writerow({**values,**extra})
        return self.register(path,PROVIDER)

    def document(self,value,kind,authority='SOURCE_DATA'):
        self.counter += 1
        path = self.fx.root/f'evidence-{self.counter}.csv'
        with path.open('w',newline='',encoding='utf-8') as stream:
            writer = csv.writer(stream);writer.writerow(['evidence']);writer.writerow([value.to_json()])
        return self.register(path,'production-evidence:'+kind+'-1',authority)

    def assess(self,manifest=None,mapping=None,**kw):
        return self.service.assess(self.records,self.controls,self.document(manifest or self.manifest,'manifest'),
            mapping_version=self.document(mapping or self.mapping,'mapping','HUMAN_FD_JUDGEMENT'),**kw)

    def test_complete_manifest_control_and_source_mapping_verify_separate_dimensions(self):
        result = self.assess()
        self.assertTrue(all(s == 'VERIFIED' for s in result.states.values()))
        self.assertEqual(result.contract.coverage.verified_value['completeness'],'COMPLETE')
        self.assertEqual(len(result.contract.claims()),11)
        self.assertFalse(hasattr(result,'trajectory'))

    def test_arithmetic_match_without_manifest_identities_does_not_verify_coverage(self):
        result = self.assess(self.manifest.model_copy(update={'record_ids':None}))
        self.assertEqual(result.states['coverage'],'INSUFFICIENT_EVIDENCE')
        self.assertIn('MATCH',result.reconciliation)

    def test_arithmetic_match_without_mapping_does_not_verify_definition(self):
        result = self.service.assess(self.records,self.controls,self.document(self.manifest,'manifest'))
        self.assertEqual(result.states['definition'],'INSUFFICIENT_EVIDENCE')
        self.assertEqual(result.states['coverage'],'VERIFIED')

    def test_count_alone_does_not_verify_population(self):
        result = self.assess(self.manifest.model_copy(update={'record_ids':None}))
        self.assertIsNone(result.contract.population.verified_value)

    def test_partial_manifest_is_verified_as_partial_not_complete(self):
        result = self.assess(self.manifest.model_copy(update={'excluded_record_ids':('excluded1',)}))
        self.assertEqual(result.contract.coverage.verified_value['completeness'],'PARTIAL')

    def test_no_authority_by_default(self):
        service = SemanticVerificationService(self.con,'c1','r1')
        result = service.assess(self.records,self.controls,self.document(self.manifest,'manifest'))
        self.assertTrue(all(s == 'INSUFFICIENT_EVIDENCE' for s in result.states.values()))

    def declaration(self,who='MANAGEMENT',dimension='coverage',claim='Complete'):
        a = Actor(actor_type=who,actor_id='person1',source_authority='MANAGEMENT_ASSERTION' if who=='MANAGEMENT' else 'HUMAN_FD_JUDGEMENT')
        return EvidenceDeclaration(declaration_id='d1',client_id='c1',actor=a,effective_on='2026-01-31',
            dimension=dimension,claim=claim,lineage=record().lineage,revision=1)

    def test_management_completeness_remains_declared(self):
        self.grants.clear()
        result = self.assess(declarations=(self.declaration(),))
        self.assertEqual(result.states['coverage'],'DECLARED')
        self.assertIsNone(result.contract.coverage.verified_value)

    def test_adviser_completeness_remains_declared(self):
        self.grants.clear()
        result = self.assess(declarations=(self.declaration('HUMAN'),))
        self.assertEqual(result.states['coverage'],'DECLARED')

    def test_source_contradiction_retains_both_values(self):
        result = self.assess(declarations=(self.declaration(dimension='currency',claim='EUR'),))
        self.assertEqual(result.states['currency'],'CONFLICTED')
        self.assertEqual((result.contract.currency.declared_value,result.contract.currency.verified_value),('EUR','GBP'))

    def test_same_total_different_manifest_identity_refuses_population(self):
        result = self.assess(self.manifest.model_copy(update={'record_ids':('different1',)}))
        self.assertEqual(result.states['population'],'MISMATCH')

    def test_unknown_revenue_definition_refuses(self):
        result = self.assess(mapping=self.mapping.model_copy(update={'definition':'UNKNOWN'}))
        self.assertEqual(result.states['definition'],'INSUFFICIENT_EVIDENCE')

    def test_conflicting_source_chart_refuses_definition(self):
        chart = self.chart.model_copy(update={'revenue_accounts':('4999',)})
        m = self.mapping.model_copy(update={'source_chart_version':self.document(chart,'chart')})
        self.assertEqual(self.assess(mapping=m).states['definition'],'CONFLICTED')

    def test_source_semantics_do_not_hide_control_mismatch(self):
        self.controls = self.amounts('control2','99')
        result = self.assess()
        self.assertEqual(result.states['definition'],'VERIFIED')
        self.assertEqual(result.states['coverage'],'MISMATCH')

    def test_mapping_remains_attributable_when_definition_corroborated(self):
        result = self.assess()
        self.assertEqual(result.mapping.actor.source_authority,'HUMAN_FD_JUDGEMENT')
        self.assertEqual(result.contract.definition.verification_authority,'SYSTEM_DERIVED')

    def c0(self):
        self.scope = self.scope.model_copy(update={'definition':'REVENUE_MINUS_DIRECT_COST'})
        self.records = self.amounts('s1','100',changes={'definition':'REVENUE_MINUS_DIRECT_COST'},
            extras=({'record_id':'s2','account_code':'5000','amount':'40'},))
        self.controls = self.amounts('control1','100',changes={'definition':'REVENUE_MINUS_DIRECT_COST'},
            extras=({'record_id':'control2','account_code':'5000','amount':'40'},))
        self.manifest = self.manifest.model_copy(update={'scope':self.scope,'record_version_id':self.records,
            'record_ids':('s1','s2'),'record_count':2})
        self.chart = self.chart.model_copy(update={'scope':self.scope,'definition':'REVENUE_MINUS_DIRECT_COST','direct_cost_accounts':('5000',),
            'cost_basis':'ATTRIBUTABLE_DIRECT_COST_BEFORE_CTS_AND_OVERHEAD'})
        self.mapping = self.mapping.model_copy(update={'scope':self.scope,'definition':'REVENUE_MINUS_DIRECT_COST',
            'direct_cost_accounts':('5000',),'source_chart_version':self.document(self.chart,'chart')})

    def test_explicit_c0_source_membership_verifies_definition_not_value(self):
        self.c0(); result = self.assess()
        self.assertEqual(result.states['definition'],'VERIFIED')
        self.assertEqual(result.contract.definition.verified_value['definition'],'REVENUE_MINUS_DIRECT_COST')
        self.assertEqual(result.contract.coverage.verified_value['completeness'],'COMPLETE')
        self.assertFalse(hasattr(result,'monthly_value'))

    def test_c0_incomplete_account_mapping_refuses(self):
        self.c0()
        self.assertEqual(self.assess(mapping=self.mapping.model_copy(update={'direct_cost_accounts':()})).states['definition'],'CONFLICTED')

    def test_guessed_account_name_is_not_a_mapping_field(self):
        with self.assertRaises(ValueError):
            Mapping.model_validate({**self.mapping.model_dump(),'account_name':'materials'})

    def test_untrusted_chart_cannot_upgrade_adviser_mapping(self):
        profile,digest,_ = self.grants[self.chart_version]
        self.grants[self.chart_version] = (profile,digest,'HUMAN_FD_JUDGEMENT')
        self.assertEqual(self.assess().states['definition'],'INSUFFICIENT_EVIDENCE')

    def test_qualified_restatement_retains_predecessor(self):
        old = self.assess()
        self.records = self.amounts('s1','101'); self.controls = self.amounts('control1','101')
        manifest = self.manifest.model_copy(update={'record_version_id':self.records,'change_kind':'RESTATEMENT',
            'predecessor_version_id':old.contract.source_version.source_id,'revision_id':'source-rev2'})
        result = self.assess(manifest,previous=old)
        self.assertEqual(result.contract.revision_relationship.verified_value,'RESTATEMENT')
        self.assertEqual(result.contract.revision_target_contract_id,old.contract.contract_id)
        self.assertEqual(result.supersedes,old.assessment_id)

    def test_same_period_duplicate_without_revision_authority_refuses(self):
        old = self.assess()
        self.records = self.amounts('s1','101');self.controls = self.amounts('control1','101')
        result = self.assess(self.manifest.model_copy(update={'record_version_id':self.records}),previous=old)
        self.assertIsNone(result.contract.revision_relationship.verified_value)

    def test_later_revision_id_alone_is_not_restatement(self):
        result = self.assess(self.manifest.model_copy(update={'revision_id':'later','change_kind':'UNKNOWN'}))
        self.assertEqual(result.states['revision_relationship'],'INSUFFICIENT_EVIDENCE')

    def test_mapping_revision_keeps_original(self):
        old = self.assess()
        new = self.mapping.model_copy(update={'mapping_id':'mapping2','revision':2,'supersedes':'mapping1'})
        result = self.assess(mapping=new,previous=old)
        self.assertEqual((old.mapping.mapping_id,result.mapping.mapping_id),('mapping1','mapping2'))
        self.assertEqual(result.mapping.supersedes,old.mapping.mapping_id)

    def test_mapping_change_without_predecessor_refuses(self):
        old = self.assess()
        with self.assertRaises(RevisionConflict):
            self.assess(mapping=self.mapping.model_copy(update={'source_policy_reference':'changed'}),previous=old)

    def test_cross_client_manifest_refuses(self):
        m = self.manifest.model_copy(update={'scope':self.scope.model_copy(update={'client_id':'c2'})})
        with self.assertRaises(ScopeError): self.assess(m)

    def test_cross_entity_manifest_refuses(self):
        with self.assertRaises(ScopeError): self.assess(self.manifest.model_copy(update={'scope':self.scope.model_copy(update={'entity_id':'e2'})}))

    def test_wrong_mapping_period_refuses(self):
        with self.assertRaises(ScopeError): self.assess(mapping=self.mapping.model_copy(update={'effective_from':date(2026,2,1)}))

    def test_cross_client_declaration_refuses(self):
        with self.assertRaises(ValueError): self.assess(declarations=(self.declaration().model_copy(update={'client_id':'c2'}),))

    def test_unchanged_replay_returns_same_assessment(self):
        old = self.assess()
        self.assertEqual(self.assess(previous=old),old)

    def test_changed_semantics_appends_revision_without_mutating_old(self):
        old = self.assess()
        result = self.assess(self.manifest.model_copy(update={'extraction_query':'different query'}),previous=old)
        self.assertEqual(result.revision,2)
        self.assertEqual(old.revision,1)

    def test_incomplete_extraction_boundary_does_not_verify_completeness(self):
        self.assertEqual(self.assess(self.manifest.model_copy(update={'extraction_query':None})).states['coverage'],'INSUFFICIENT_EVIDENCE')

    def test_manifest_cannot_inject_verified_answer(self):
        with self.assertRaises(ValueError): Manifest.model_validate({**self.manifest.model_dump(),'verified':True})

    def test_invalid_origin_cannot_relabel_synthetic_source(self):
        with self.assertRaises(ValueError): Manifest.model_validate({**self.manifest.model_dump(),'origin':'SYNTHETIC_QUALIFICATION'})

    def test_lossless_dataset_roundtrip(self):
        result = self.assess()
        self.assertEqual(type(result).from_json(result.to_json()),result)

    def test_cross_client_mapping_refuses(self):
        m = self.mapping.model_copy(update={'scope':self.scope.model_copy(update={'client_id':'c2'})})
        with self.assertRaises(ScopeError): self.assess(mapping=m)

    def test_wrong_currency_control_refuses(self):
        self.controls = self.amounts('control2','100',changes={'currency':'EUR'})
        with self.assertRaises(ScopeError): self.assess()

    def test_wrong_reporting_period_control_refuses(self):
        self.controls = self.amounts('control2','100',changes={'period_start':'2026-02-01','period_end':'2026-02-28'})
        with self.assertRaises(ScopeError): self.assess()

    def test_same_total_wrong_control_account_refuses_coverage(self):
        self.controls = self.amounts('control2','100',changes={'account_code':'4999'})
        result = self.assess()
        self.assertEqual(result.states['coverage'],'MISMATCH')
        self.assertIn('MATCH',result.reconciliation)

    def test_sales_copy_is_not_accounting_control(self):
        self.controls = self.amounts('copied','100')
        self.assertEqual(self.assess().states['coverage'],'INSUFFICIENT_EVIDENCE')

    def test_unknown_recognition_policy_refuses_definition(self):
        chart = self.chart.model_copy(update={'recognition_basis':'UNKNOWN'})
        m = self.mapping.model_copy(update={'source_chart_version':self.document(chart,'chart')})
        self.assertEqual(self.assess(mapping=m).states['definition'],'INSUFFICIENT_EVIDENCE')

    def test_c0_requires_direct_cost_observation_not_inferred_zero(self):
        self.c0()
        self.records = self.amounts('s1','100',changes={'definition':'REVENUE_MINUS_DIRECT_COST'})
        self.controls = self.amounts('control1','100',changes={'definition':'REVENUE_MINUS_DIRECT_COST'})
        m = self.manifest.model_copy(update={'record_version_id':self.records,'record_ids':('s1',),'record_count':1})
        result = self.assess(m)
        self.assertEqual(result.states['definition'],'VERIFIED')
        self.assertEqual(result.states['coverage'],'INSUFFICIENT_EVIDENCE')

    def test_duplicate_without_supplied_history_is_found_in_source_registry(self):
        old = self.assess()
        self.records = self.amounts('s1','101');self.controls = self.amounts('control1','101')
        m = self.manifest.model_copy(update={'record_version_id':self.records,'change_kind':'UNKNOWN'})
        self.assess(m)
        # The old source is still retained but cannot replay a positive current
        # revision classification after a competing unqualified root appears.
        self.records = old.contract.source_version.source_id
        self.controls = old.source_versions[1]
        result = self.assess(previous=old)
        self.assertEqual(result.states['revision_relationship'],'INSUFFICIENT_EVIDENCE')
        self.assertNotEqual(result.assessment_id,old.assessment_id)

    def test_mapping_actor_cannot_masquerade_as_adviser(self):
        actor = Actor(actor_type='SYSTEM',actor_id='bot1',source_authority='HUMAN_FD_JUDGEMENT')
        with self.assertRaises(ValueError):
            Mapping.model_validate({**self.mapping.model_dump(),'actor':actor})

    def test_manifest_does_not_invent_missing_identity(self):
        with self.assertRaises(ValueError):
            Manifest.model_validate({**self.manifest.model_dump(),'record_count':2})

    def test_comparability_consumes_existing_dataset_contract_dimensions(self):
        from profit_doctor.reasoning.dataset.comparability import assess_dataset_comparability
        old = self.assess()
        self.records = self.amounts('s1','101');self.controls = self.amounts('control1','101')
        changed = self.assess(self.manifest.model_copy(update={'record_version_id':self.records,'change_kind':'RESTATEMENT',
            'predecessor_version_id':old.contract.source_version.source_id,'revision_id':'rev2'}),previous=old)
        comparison = assess_dataset_comparability(old.contract,changed.contract)
        self.assertEqual(len(comparison.dimensions),11)
        self.assertEqual(comparison.temporal_evidence_role,'REVISION_ONLY')

    def test_expired_authority_changes_assessment_without_overwriting_old(self):
        old = self.assess()
        profile,digest,_ = self.grants[self.records]
        self.grants[self.records] = (profile,digest,None)
        changed = self.assess(previous=old)
        self.assertEqual(changed.states['population'],'INSUFFICIENT_EVIDENCE')
        self.assertEqual(old.states['population'],'VERIFIED')
