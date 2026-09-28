"""Adversarial graph tests using real canonical writers and owning-store rows."""
import json
import unittest
from datetime import date
from decimal import Decimal
from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError
from profit_doctor.persistence.graph_schema import graph_record
from profit_doctor.persistence import reasoning_schema
from profit_doctor.reasoning.domain.contracts import ReasoningObject, EvidenceLink
from profit_doctor.reasoning.domain.service import ScopeError, RevisionConflict
from profit_doctor.reasoning.graph.contracts import GraphRecord, SeriesBasis
from profit_doctor.reasoning.graph.service import EvidenceGraph, temporal
from tests import test_canonical_facts_findings_v244 as canonical_tests
T = canonical_tests.T


class EvidenceGraphV245(unittest.TestCase):
    target_url = canonical_tests.CanonicalV244.target_url
    prepare_target = canonical_tests.CanonicalV244.prepare_target
    signal = canonical_tests.CanonicalV244.signal
    revenue = canonical_tests.CanonicalV244.revenue

    def setUp(self):
        canonical_tests.CanonicalV244.setUp(self)
        self.legacy.execute("INSERT INTO client VALUES ('c1','Test','GBP',NULL,?)", (T,))
        self.legacy.execute("INSERT INTO engine_run VALUES ('r1','c1','BASELINE',?,NULL,'COMPLETED',NULL,NULL,'2.44')", (T,))
        self.legacy.execute("INSERT INTO ingestion_job VALUES ('ing','r1','c1',?,NULL,'COMPLETED',NULL)", (T,))
        for key in 'abcd':
            self.legacy.execute('INSERT INTO source_file VALUES (?,?,?,?,?,?,?,?)',
                ('f'+key,'c1',key+'.csv','test',key*64,1,1,T))
            self.legacy.execute('INSERT INTO dataset VALUES (?,?,?,?,?,?)',
                ('d'+key,'c1','f'+key,'D07_SALES_TRANSACTIONS',key,T))
            self.legacy.execute('INSERT INTO dataset_version VALUES (?,?,?,?,?,?,?,?,?,?)',
                ('v'+key,'d'+key,'ing','f'+key,1,1,None,None,'COMPLETED',T))
        self.legacy.commit()
        self.graph = EvidenceGraph(self.session, 'c1','r1', self.actor,self.source)

    def fact(self, sid, roots=('a',), **kwargs):
        self.signal(sid, **kwargs)
        self.legacy.execute('DELETE FROM diagnostic_lineage WHERE signal_id=?', (sid,))
        for i,key in enumerate(roots):
            self.legacy.execute('INSERT INTO diagnostic_lineage VALUES (?,?,?,?,?,?)',
                (f'line-{sid}-{i}',sid,'DATASET_VERSION','v'+key,'DERIVED_FROM','captured dataset scope'))
        self.legacy.commit()
        return self.service.canonicalise(sid).fact

    def pair(self, roots_a=('a',), roots_b=('b',)):
        return self.fact('a',roots_a), self.fact('b',roots_b)

    def test_three_diagnostics_same_revenue_ancestry_not_three_confirmations(self):
        facts = []
        for i,(test,typ) in enumerate([('REV-01','COMPARABLE_REVENUE_CHANGE'),
                ('REV-02','REVENUE_BRIDGE_TOTAL'),('GM-02','CONTRIBUTION_CHANGE')]):
            facts.append(self.fact(str(i),test=test,typ=typ,entity=None,entity_id=None))
        for other in facts[1:]:
            result=self.graph.characteristics(facts[0].object_id,other.object_id)
            self.assertEqual('SAME_ANCESTRY',result.independence)
            self.assertEqual(('LEGACY_SQLITE:source_file:fa',),result.shared_source_files)
        self.assertEqual((),self.graph.independent_evidence(facts[0].object_id,[f.object_id for f in facts]))

    def test_disjoint_resolved_sources_can_be_independent(self):
        a,b=self.pair()
        c=self.graph.characteristics(a.object_id,b.object_id)
        self.assertEqual('INDEPENDENT',c.independence)
        self.assertIn('not statistical',c.independence_basis)
        self.assertEqual((b.object_id,),self.graph.independent_evidence(a.object_id,[b.object_id]))

    def test_partial_overlap_preserves_both_unique_sides(self):
        a,b=self.pair(('a','b'),('b','c'))
        self.assertEqual('PARTIALLY_SHARED',self.graph.characteristics(a.object_id,b.object_id).independence)

    def test_wholly_contained_ancestry_is_substantially_shared(self):
        a,b=self.pair(('a',),('a','b'))
        self.assertEqual('SUBSTANTIALLY_SHARED',self.graph.characteristics(a.object_id,b.object_id).independence)

    def test_different_datasets_same_file_are_not_independent(self):
        self.legacy.execute("UPDATE dataset SET source_file_id='fa' WHERE dataset_id='db'")
        self.legacy.execute("UPDATE dataset_version SET source_file_id='fa' WHERE dataset_id='db'")
        a,b=self.pair()
        self.assertEqual('SUBSTANTIALLY_SHARED',self.graph.characteristics(a.object_id,b.object_id).independence)

    def test_missing_source_file_is_indeterminate(self):
        a,b=self.pair()
        self.legacy.execute("UPDATE source_file SET immutable_flag=0 WHERE source_file_id='fa'")
        c=self.graph.characteristics(a.object_id,b.object_id)
        self.assertEqual('INDETERMINATE',c.independence)
        self.assertEqual((False,True),c.lineage_complete)

    def test_unknown_lineage_does_not_guess(self):
        sid=self.signal()
        self.legacy.execute("UPDATE diagnostic_lineage SET source_object_type='UNSUPPORTED' WHERE signal_id=?",(sid,))
        a=self.service.canonicalise(sid).fact
        b=self.fact('b')
        self.assertEqual('INDETERMINATE',self.graph.characteristics(a.object_id,b.object_id).independence)

    def test_partial_eligibility_not_independent_corroboration(self):
        a=self.fact('a',eligibility='PARTIAL-A'); b=self.fact('b',('b',))
        self.assertEqual('INDETERMINATE',self.graph.characteristics(a.object_id,b.object_id).independence)

    def test_management_context_retains_authority(self):
        a=self.fact('a',test='REV-01',typ='COMPARABLE_REVENUE_CHANGE',entity=None,entity_id=None)
        context=self.service.foundation.create_object(ReasoningObject(client_id='c1',run_id='r1',
            object_type='SIGNAL',source_authority='MANAGEMENT_ASSERTION'))
        edge=self.graph.link(context.object_id,a.object_id,'CONTEXTUALISES','Management-provided context; unverified')
        self.assertEqual('MANAGEMENT_ASSERTION',self.graph.foundation.get_link(edge.link_id).source_authority)
        self.assertEqual('INDETERMINATE',edge.characteristics.independence)
        with self.assertRaises(ValueError):
            self.graph.link(context.object_id,a.object_id,'SUPPORTS','Claimed corroboration')

    def test_temporal_order_not_causality(self):
        a=self.fact('a',period_from='2026-01-01',period_to='2026-01-31')
        b=self.fact('b',period_from='2026-03-01',period_to='2026-03-31')
        self.assertEqual('PRECEDES',temporal(self.graph.node(a.object_id),self.graph.node(b.object_id)))
        self.assertEqual('FOLLOWS',temporal(self.graph.node(b.object_id),self.graph.node(a.object_id)))
        edge=self.graph.link(a.object_id,b.object_id,'TEMPORALLY_PRECEDES','Disjoint recorded comparable periods; no causality')
        self.assertEqual('PRECEDES',edge.characteristics.temporal)
        with self.assertRaises(ValueError):
            self.graph.link(b.object_id,a.object_id,'TEMPORALLY_PRECEDES','Reverse chronology')

    def test_same_and_overlapping_periods_are_distinct(self):
        a=self.fact('a',period_from='2026-01-01',period_to='2026-01-31')
        b=self.fact('b',period_from='2026-01-01',period_to='2026-01-31')
        c=self.fact('c',period_from='2026-01-15',period_to='2026-02-14')
        self.assertEqual('SAME_COMPARABLE_PERIOD',self.graph.characteristics(a.object_id,b.object_id).temporal)
        self.assertEqual('OVERLAPS',self.graph.characteristics(a.object_id,c.object_id).temporal)

    def test_missing_and_incomparable_periods_never_make_edges(self):
        a,b=self.pair()
        self.assertEqual('INSUFFICIENT_PERIOD_INFORMATION',self.graph.characteristics(a.object_id,b.object_id).temporal)
        other=self.fact('c',entity_id='customer-b')
        self.assertEqual('NOT_COMPARABLE',self.graph.characteristics(a.object_id,other.object_id).temporal)
        with self.assertRaises(ValueError): self.graph.link(a.object_id,b.object_id,'TEMPORALLY_PRECEDES','No dates')

    def series(self):
        sides=[]
        for side in ('a','b'):
            ids=[]
            for i,month in enumerate((1,3,5,7)):
                f=self.fact(f'{side}-{i}',(side,),observed=str((i+1)*10)+'.00000000000000000001',
                    period_from=f'2026-{month:02}-01',period_to=f'2026-{month:02}-31')
                ids.append(f.object_id)
            sides.append(tuple(ids))
        return SeriesBasis(source_facts=sides[0],target_facts=sides[1])

    def test_co_movement_requires_series_not_same_run(self):
        a,b=self.pair()
        with self.assertRaises(ValueError): self.graph.link(a.object_id,b.object_id,'CO_MOVES_WITH','Same run')
        with self.assertRaises(ValueError): SeriesBasis(source_facts=(a.object_id,)*4,target_facts=(b.object_id,)*4)

    def test_co_movement_is_symmetric_exact_and_replay_safe(self):
        basis=self.series()
        a,b=basis.source_facts[-1],basis.target_facts[-1]
        first=self.graph.link(a,b,'CO_MOVES_WITH','Aligned nonzero direction changes; not causality',series=basis)
        reverse=SeriesBasis(source_facts=basis.target_facts,target_facts=basis.source_facts)
        second=self.graph.link(b,a,'CO_MOVES_WITH','Aligned nonzero direction changes; not causality',series=reverse)
        self.assertEqual(first,second)
        self.assertEqual(first,GraphRecord.from_json(first.to_json()))
        self.assertEqual(Decimal('40.00000000000000000001'),self.service.get_fact(a).observed.value)

    def test_co_movement_rejects_reversed_periods(self):
        basis=self.series()
        invalid=basis.model_copy(update={'source_facts':tuple(reversed(basis.source_facts))})
        with self.assertRaises(ValueError):
            self.graph.link(invalid.source_facts[-1],invalid.target_facts[-1],'CO_MOVES_WITH','Invalid chronology',series=invalid)

    def test_contradiction_is_first_class_without_causal_rejection(self):
        a,b=self.pair()
        edge=self.graph.link(a.object_id,b.object_id,'CONTRADICTS','Declared evidence tension')
        self.assertEqual((edge.link_id,),tuple(x.link_id for x in self.graph.neighbours(b.object_id,relationship='CONTRADICTS',direction='incoming')))
        self.assertTrue(self.graph.characteristics(a.object_id,b.object_id).contradiction_present)
        self.assertEqual('OBSERVED',self.service.get_fact(b.object_id).state)

    def test_entity_scope_and_missing_endpoints(self):
        a=self.fact('a'); b=self.fact('b',entity_id='customer-b')
        with self.assertRaises(ScopeError): self.graph.link(a.object_id,b.object_id,'SUPPORTS','Wrong entity')
        with self.assertRaises(ScopeError): self.graph.link(a.object_id,'missing','SUPPORTS','Missing')

    def test_foreign_tenant_and_run_are_rejected(self):
        a=self.fact('a')
        with self.assertRaises(ScopeError): EvidenceGraph(self.session,'c1','r2',self.actor,self.source)
        with self.assertRaises(ScopeError): self.graph.node(a.object_id,observation_run='r3')
        foreign=self.session.execute(select(reasoning_schema.reasoning_object.c.object_id).where(reasoning_schema.reasoning_object.c.client_id=='c2')).all()
        self.assertEqual([],foreign)

    def test_self_and_causal_relationships_rejected(self):
        a,b=self.pair()
        for relation in ('POTENTIALLY_DRIVES','SUPPORTED_DRIVER_OF','EXPLAINS','UNKNOWN'):
            with self.assertRaises(ValueError): self.graph.link(a.object_id,b.object_id,relation,'Unsupported')
        with self.assertRaises(ValueError): self.graph.link(a.object_id,a.object_id,'SUPPORTS','Self')

    def test_replay_has_no_duplicate_edges_or_audits(self):
        a,b=self.pair()
        edge=self.graph.link(a.object_id,b.object_id,'MITIGATES','Explicit mitigating evidence')
        before=self.foundation_audits(b.object_id)
        self.assertEqual(edge,self.graph.link(a.object_id,b.object_id,'MITIGATES','Explicit mitigating evidence'))
        self.assertEqual(before,self.foundation_audits(b.object_id))
        self.assertEqual(1,len(list(self.session.scalars(select(graph_record.c.link_id)))))

    def foundation_audits(self,oid):
        return self.service.foundation.audit_events(object_id=oid)

    def test_existing_canonical_link_is_adopted_not_copied(self):
        a,b=self.pair()
        existing=self.service.foundation.link_evidence(EvidenceLink(client_id='c1',run_id='r1',source_id=a.object_id,
            target_id=b.object_id,relationship_type='SUPPORTS',source_authority='SYSTEM_DERIVED'))
        record=self.graph.link(a.object_id,b.object_id,'SUPPORTS','Explicit reviewed support')
        self.assertEqual(existing.link_id,record.link_id)
        self.assertEqual((existing.link_id,),tuple(link.link_id for link in
            self.graph.neighbours(b.object_id,relationship='SUPPORTS',direction='incoming') if link.source_id==a.object_id))

    def test_signal_envelope_preserves_owning_entity_and_support_link(self):
        fact=self.fact('a')
        link=self.graph.neighbours(fact.object_id,relationship='SUPPORTS',direction='incoming')[0]
        node=self.graph.node(link.source_id)
        self.assertEqual(fact.scope,node.scope)
        governed=self.graph.link(link.source_id,fact.object_id,'SUPPORTS','Existing Signal describes canonical Fact')
        self.assertEqual(link.link_id,governed.link_id)
        self.assertEqual('INDETERMINATE',governed.characteristics.independence)

    def test_queries_filter_entity_period_family_and_authority(self):
        a=self.fact('a',period_from='2026-01-01',period_to='2026-01-31')
        self.fact('b',entity_id='customer-b')
        nodes=self.graph.nodes(entity=('CUSTOMER','customer-a'),period=(date(2026,1,1),date(2026,1,31)),family='CUS',authority='SYSTEM_DERIVED')
        source_id=self.graph.neighbours(a.object_id,relationship='SUPPORTS',direction='incoming')[0].source_id
        self.assertEqual({a.object_id,source_id},{n.object_id for n in nodes})
        self.assertEqual({'FACT','SIGNAL'},{n.object_type for n in nodes})

    def test_caller_transaction_rollback_and_committed_reader(self):
        a,b=self.pair()
        record=self.graph.link(a.object_id,b.object_id,'SUPPORTS','Declared support')
        self.session.commit()
        with self.factory() as reader:
            self.assertEqual(record,EvidenceGraph(reader,'c1','r1',self.actor,self.source).get(record.link_id))
        next_edge=self.graph.link(b.object_id,a.object_id,'MITIGATES','Declared mitigation')
        self.session.rollback()
        with self.assertRaises(ScopeError): self.graph.get(next_edge.link_id)

    def test_database_foreign_keys_and_unique_link(self):
        a,b=self.pair()
        record=self.graph.link(a.object_id,b.object_id,'SUPPORTS','Declared support')
        row=dict(link_id=record.link_id,revision=1,client_id='c1',run_id='r1',source_id=a.object_id,target_id=b.object_id,document=record.to_json())
        with self.assertRaises(IntegrityError),self.session.begin_nested(): self.session.execute(insert(graph_record).values(**row))
        row['link_id']='missing'
        with self.assertRaises(IntegrityError),self.session.begin_nested(): self.session.execute(insert(graph_record).values(**row))

    def test_document_corruption_and_changed_revision_fail_closed(self):
        a,b=self.pair()
        record=self.graph.link(a.object_id,b.object_id,'SUPPORTS','Declared support')
        self.service.invalidate(a.object_id,'Corrected source')
        self.assertEqual('STALE',self.graph.freshness(record.link_id))
        with self.assertRaises(RevisionConflict): self.graph.link(a.object_id,b.object_id,'SUPPORTS','Declared support')
        doc=json.loads(record.to_json()); doc['source_id']='wrong'
        self.session.execute(graph_record.update().where(graph_record.c.link_id==record.link_id).values(document=json.dumps(doc)))
        with self.assertRaises(ValueError): self.graph.get(record.link_id)

    def test_primitive_path_and_cyclic_ancestry(self):
        self.legacy.execute("INSERT INTO primitive_registry VALUES ('p','p','test','revenue','FLOW','GBP','ADDITIVE','1')")
        self.legacy.execute("INSERT INTO primitive_result VALUES ('pr','r1','c1','p','test',NULL,NULL,NULL,NULL,'1','GBP','VALID',?)",(T,))
        self.legacy.execute("INSERT INTO calculation_lineage VALUES ('cl','pr','DATASET_VERSION','va','DERIVED_FROM','captured')")
        sid=self.signal('primitive')
        self.legacy.execute("UPDATE diagnostic_lineage SET source_object_type='PRIMITIVE_RESULT',source_object_id='pr' WHERE signal_id=?",(sid,))
        fact=self.service.canonicalise(sid).fact
        node=self.graph.node(fact.object_id)
        self.assertTrue(node.ancestry.complete)
        self.assertIn('LEGACY_SQLITE:primitive_result:pr',node.ancestry.primitives)
        self.assertIn('LEGACY_SQLITE:source_file:fa',node.ancestry.source_files)
        cycle=self.signal('cycle')
        self.legacy.execute("UPDATE diagnostic_lineage SET source_object_type='SIGNAL',source_object_id=? WHERE signal_id=?",(cycle,cycle))
        cf=self.service.canonicalise(cycle).fact
        self.assertFalse(self.graph.node(cf.object_id).ancestry.complete)

    def test_cross_client_endpoint_and_database_scope_rejected(self):
        from profit_doctor.reasoning.domain.service import FoundationService
        foreign=FoundationService(self.session,'c2',self.actor).create_object(ReasoningObject(
            client_id='c2',run_id='r2',object_type='SIGNAL',source_authority='MANAGEMENT_ASSERTION'))
        a,b=self.pair()
        with self.assertRaises(ScopeError): self.graph.link(foreign.object_id,a.object_id,'CONTEXTUALISES','Foreign')
        record=self.graph.link(a.object_id,b.object_id,'SUPPORTS','Declared support')
        self.session.execute(graph_record.delete().where(graph_record.c.link_id==record.link_id))
        with self.assertRaises(IntegrityError),self.session.begin_nested():
            self.session.execute(insert(graph_record).values(link_id=record.link_id,revision=1,client_id='c2',run_id='r2',
                source_id=a.object_id,target_id=b.object_id,document=record.to_json()))

    def test_governance_loss_requires_restore_not_silent_reconstruction(self):
        a,b=self.pair()
        record=self.graph.link(a.object_id,b.object_id,'SUPPORTS','Declared support')
        self.session.execute(graph_record.delete().where(graph_record.c.link_id==record.link_id))
        with self.assertRaises(RevisionConflict): self.graph.link(a.object_id,b.object_id,'SUPPORTS','Declared support')

    def test_finding_projection_uses_explicit_observation(self):
        a=self.fact('a',test='REV-01',typ='COMPARABLE_REVENUE_CHANGE',entity=None,entity_id=None,
            observed='120',comparison='100',variance='20')
        assessment=self.service.assess(a.object_id)
        node=self.graph.node(assessment.finding_id)
        self.assertEqual('FINDING',node.object_type)
        self.assertEqual(self.graph.node(a.object_id).ancestry,node.ancestry)
        with self.assertRaises(ScopeError): self.graph.node(assessment.finding_id,observation_run='r3')

    def test_quantification_and_context_queries_do_not_promote_facts(self):
        a,b=self.pair()
        for relation in ('QUANTIFIES','CONTEXTUALISES','MITIGATES'):
            record=self.graph.link(a.object_id,b.object_id,relation,'Explicit declared evidence relationship')
            self.assertEqual(record.link_id,self.graph.neighbours(b.object_id,relationship=relation)[0].link_id)
        self.assertEqual('OBSERVED',self.service.get_fact(b.object_id).state)

    def test_explicit_relationship_revision_preserves_history_and_checks_version(self):
        a,b=self.pair()
        old=self.graph.link(a.object_id,b.object_id,'SUPPORTS','Initial declared basis')
        new=self.graph.link(a.object_id,b.object_id,'SUPPORTS','Reviewed replacement basis',expected_revision=1)
        self.assertEqual((old.link_id,2),(new.link_id,new.revision))
        self.assertEqual((old,new),self.graph.history(old.link_id))
        self.assertEqual(old,self.graph.get(old.link_id,revision=1))
        with self.assertRaises(RevisionConflict):
            self.graph.link(a.object_id,b.object_id,'SUPPORTS','Stale writer',expected_revision=1)
        self.assertEqual(new,self.graph.link(a.object_id,b.object_id,'SUPPORTS','Reviewed replacement basis'))
        audits=self.foundation_audits(b.object_id)
        self.assertTrue(any(isinstance(e.previous,dict) and 'graph_record' in e.previous for e in audits))


if __name__=='__main__': unittest.main()
