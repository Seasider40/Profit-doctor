import unittest,tempfile,uuid
from pathlib import Path
from profit_doctor.core.db import connect
from profit_doctor.ingestion.northstar import ingest_northstar
from profit_doctor.trust.engine import run_trust_layer
from profit_doctor.calc.primitive_engine import run_primitive_engine
from profit_doctor.diagnostic.engine import run_diagnostic_engine
from profit_doctor.reasoning.engine import run_reasoning_engine,add_context_event
ROOT=Path(__file__).resolve().parent/'fixtures'/'northstar'
def now(): return '2026-09-24T00:00:00+00:00'
def setup(d):
 con=connect(Path(d)/'x.db'); c='c_'+uuid.uuid4().hex; r='r_'+uuid.uuid4().hex
 con.execute('INSERT INTO client VALUES (?,?,?,?,?)',(c,'Northstar','GBP','PRODUCT_DISTRIBUTION',now())); con.execute('INSERT INTO engine_run VALUES (?,?,?,?,?,?,?,?,?)',(r,c,'BASELINE',now(),None,'RUNNING',None,r,'0.9.0')); con.commit()
 ing=ingest_northstar(con,c,r,ROOT,Path(d)/'store'); run_trust_layer(con,r,c,ing['dataset_version_id']); run_primitive_engine(con,r,c,ing['dataset_version_id']); run_diagnostic_engine(con,r,c,ing['dataset_version_id']); return con,c,r
class ReasoningTests(unittest.TestCase):
 def test_reasoning_creates_evidence_bound_objects_and_queue(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r=setup(d); out=run_reasoning_engine(con,r,c); self.assertGreater(out['facts'],0); self.assertGreater(out['interpretations'],0); self.assertGreater(out['fd_queue'],0)
   self.assertEqual(con.execute('SELECT count(*) n FROM finding_version fv LEFT JOIN finding_candidate fc ON fc.finding_candidate_id=fv.finding_candidate_id WHERE fc.finding_candidate_id IS NULL').fetchone()['n'],0)
 def test_informational_signals_do_not_become_findings(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r=setup(d); run_reasoning_engine(con,r,c); info=con.execute("SELECT count(*) n FROM signal WHERE run_id=? AND materiality_state='INFORMATIONAL'",(r,)).fetchone()['n']; self.assertGreater(info,0)
   self.assertEqual(con.execute("SELECT count(*) n FROM finding_version fv JOIN finding_candidate fc ON fc.finding_candidate_id=fv.finding_candidate_id JOIN evidence_bundle eb ON eb.evidence_bundle_id=fc.evidence_bundle_id JOIN signal s ON s.signal_id=eb.primary_signal_id WHERE fv.run_id=? AND s.materiality_state='INFORMATIONAL'",(r,)).fetchone()['n'],0)
 def test_management_context_suppresses_without_deleting_signal(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r=setup(d); s=con.execute("SELECT * FROM signal WHERE run_id=? AND signal_type='CUSTOMER_BRIDGE_LEG' AND materiality_state<>'INFORMATIONAL' LIMIT 1",(r,)).fetchone(); self.assertIsNotNone(s)
   add_context_event(con,c,'KNOWN_ONE_OFF','Customer decline is known to reflect a one-off contract timing event.',entity_type='CUSTOMER',entity_id=s['entity_id'])
   before=con.execute('SELECT count(*) n FROM signal WHERE signal_id=?',(s['signal_id'],)).fetchone()['n']; out=run_reasoning_engine(con,r,c); self.assertGreater(out['suppressed'],0); self.assertEqual(before,1); self.assertEqual(con.execute('SELECT count(*) n FROM signal WHERE signal_id=?',(s['signal_id'],)).fetchone()['n'],1)
   self.assertGreater(con.execute('SELECT count(*) n FROM suppression_result WHERE signal_id=?',(s['signal_id'],)).fetchone()['n'],0)
 def test_interpretation_does_not_claim_causality_or_opportunity(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r=setup(d); run_reasoning_engine(con,r,c); txt=' '.join(x['interpretation_text'].lower() for x in con.execute('SELECT interpretation_text FROM interpretation WHERE run_id=?',(r,)).fetchall())
   self.assertNotIn('caused by',txt); self.assertNotIn('recoverable saving',txt); self.assertNotIn('opportunity value',txt)
 def test_customer_decline_candidate_asks_investigation_question(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r=setup(d); run_reasoning_engine(con,r,c); row=con.execute("""SELECT fc.* FROM finding_candidate fc JOIN evidence_bundle eb ON eb.evidence_bundle_id=fc.evidence_bundle_id JOIN signal s ON s.signal_id=eb.primary_signal_id WHERE fc.run_id=? AND s.signal_type='COMPARABLE_REVENUE_CHANGE' LIMIT 1""",(r,)).fetchone(); self.assertIsNotNone(row); self.assertIn('driver',row['management_question'].lower())
 def test_every_finding_is_in_fd_review_queue(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r=setup(d); run_reasoning_engine(con,r,c); f=con.execute('SELECT count(*) n FROM finding WHERE first_run_id=?',(r,)).fetchone()['n']; q=con.execute("SELECT count(*) n FROM fd_review_queue WHERE run_id=? AND object_type='FINDING'",(r,)).fetchone()['n']; self.assertLessEqual(q,7); self.assertLessEqual(q,f); self.assertEqual(q,con.execute("SELECT count(*) n FROM fd_review_queue q JOIN finding f ON f.finding_id=q.object_id WHERE q.run_id=? AND q.object_type='FINDING'",(r,)).fetchone()['n'])

 def test_partial_eligibility_reduces_reasoning_confidence(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r=setup(d); con.execute("UPDATE test_execution SET eligibility_state='PARTIAL-B' WHERE run_id=? AND test_id='REV-01'",(r,)); con.commit(); run_reasoning_engine(con,r,c); row=con.execute("""SELECT i.confidence_state FROM interpretation i JOIN evidence_bundle eb ON eb.evidence_bundle_id=i.evidence_bundle_id JOIN signal s ON s.signal_id=eb.primary_signal_id WHERE i.run_id=? AND s.test_id='REV-01' LIMIT 1""",(r,)).fetchone(); self.assertEqual(row['confidence_state'],'MEDIUM')

if __name__=='__main__': unittest.main()

class ReasoningHardeningTests(unittest.TestCase):
 def test_attention_budget_caps_primary_queue_without_deleting_findings(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r=setup(d); out=run_reasoning_engine(con,r,c,max_primary_items=3); self.assertLessEqual(out['fd_queue'],3); self.assertGreaterEqual(out['findings'],out['fd_queue']); b=con.execute('SELECT * FROM management_attention_budget WHERE run_id=?',(r,)).fetchone(); self.assertEqual(b['max_primary_items'],3); self.assertEqual(b['queued_primary_items'],out['fd_queue'])
 def test_related_signals_are_clustered_but_preserved(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r=setup(d); before=con.execute('SELECT count(*) n FROM signal WHERE run_id=?',(r,)).fetchone()['n']; out=run_reasoning_engine(con,r,c); after=con.execute('SELECT count(*) n FROM signal WHERE run_id=?',(r,)).fetchone()['n']; self.assertEqual(before,after); self.assertGreater(out['clusters'],0); self.assertGreater(con.execute('SELECT count(*) n FROM finding_cluster_member WHERE finding_cluster_id IN (SELECT finding_cluster_id FROM finding_cluster WHERE run_id=?)',(r,)).fetchone()['n'],0)
 def test_contradictory_context_holds_candidate_and_weakens_interpretation(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r=setup(d); s=con.execute("SELECT * FROM signal WHERE run_id=? AND materiality_state IN ('MEDIUM','HIGH') LIMIT 1",(r,)).fetchone(); self.assertIsNotNone(s); add_context_event(con,c,'MANAGEMENT_DISPUTE','Management disputes the apparent movement pending contract timing evidence.',entity_type=s['entity_type'],entity_id=s['entity_id']); out=run_reasoning_engine(con,r,c); self.assertGreater(out['contradictions'],0); ce=con.execute('SELECT * FROM contradictory_evidence WHERE run_id=? LIMIT 1',(r,)).fetchone(); self.assertIsNotNone(ce); cand=con.execute("SELECT fc.* FROM finding_candidate fc JOIN evidence_bundle eb ON eb.evidence_bundle_id=fc.evidence_bundle_id WHERE eb.primary_signal_id=?",(s['signal_id'],)).fetchone(); self.assertEqual(cand['candidate_status'],'HELD_CONTRADICTORY')
 def test_longitudinal_identity_reuses_finding_across_runs(self):
  with tempfile.TemporaryDirectory() as d:
   con,c,r1=setup(d); run_reasoning_engine(con,r1,c); first=con.execute('SELECT count(*) n FROM finding WHERE client_id=?',(c,)).fetchone()['n']; self.assertGreater(first,0)
   r2='r_'+uuid.uuid4().hex; con.execute('INSERT INTO engine_run VALUES (?,?,?,?,?,?,?,?,?)',(r2,c,'MONTHLY',now(),None,'RUNNING',r1,r1,'1.0.0'))
   # Copy diagnostic evidence to simulate same issue recurring in next run, preserving test execution relationships.
   exmap={}
   for e in con.execute('SELECT * FROM test_execution WHERE run_id=?',(r1,)).fetchall():
    ne='te_'+uuid.uuid4().hex; exmap[e['test_execution_id']]=ne; con.execute('INSERT INTO test_execution VALUES (?,?,?,?,?,?,?,?,?,?,?)',(ne,r2,c,e['test_id'],e['method_id'],e['eligibility_state'],e['execution_status'],e['signal_count'],e['limitation'],now(),now()))
   for s in con.execute('SELECT * FROM signal WHERE run_id=?',(r1,)).fetchall():
    ns='sig_'+uuid.uuid4().hex; con.execute('INSERT INTO signal VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(ns,exmap[s['test_execution_id']],r2,c,s['test_id'],s['signal_type'],s['entity_type'],s['entity_id'],s['period_from'],s['period_to'],s['observed_value'],s['comparison_value'],s['variance_value'],s['unit'],s['materiality_state'],s['status'],s['evidence_summary'],s['source_primitive_id'],now()))
   con.commit(); run_reasoning_engine(con,r2,c); second=con.execute('SELECT count(*) n FROM finding WHERE client_id=?',(c,)).fetchone()['n']; self.assertEqual(first,second); self.assertGreater(con.execute('SELECT count(*) n FROM finding_version WHERE run_id=?',(r2,)).fetchone()['n'],0)
