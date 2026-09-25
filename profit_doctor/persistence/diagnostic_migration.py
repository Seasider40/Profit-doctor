"""Controlled legacy -> SQLAlchemy diagnostic persistence migration.

Controlled strangler migration for diagnostic persistence. Calculation logic remains
frozen in the legacy diagnostic engine while successive diagnostic batches migrate
their persisted contracts losslessly and pass equivalence gates before cutover.
"""
from sqlalchemy import select
from .models import Client,EngineRun,TestExecution,Signal,DiagnosticLineage
BATCH1_TESTS=tuple([f'REV-{i:02d}' for i in range(1,7)]+[f'GM-{i:02d}' for i in range(1,8)])
BATCH2_TESTS=tuple([f'CUS-{i:02d}' for i in range(1,8)]+[f'PROD-{i:02d}' for i in range(1,6)]+[f'PRI-{i:02d}' for i in range(1,6)])

def _scope(session, run_id, client_id):
    r=session.get(EngineRun,run_id)
    if not r or r.client_id != client_id: raise ValueError('Run does not belong to client')

def migrate_rev_gm(legacy, session, run_id, client_id):
    _scope(session,run_id,client_id)
    q=','.join('?' for _ in BATCH1_TESTS)
    ex=legacy.execute(f"SELECT * FROM test_execution WHERE run_id=? AND client_id=? AND test_id IN ({q}) ORDER BY test_id,test_execution_id",(run_id,client_id,*BATCH1_TESTS)).fetchall()
    counts={'executions':0,'signals':0,'lineage':0}
    for r in ex:
        if session.get(TestExecution,r['test_execution_id']): continue
        session.add(TestExecution(test_execution_id=r['test_execution_id'],run_id=r['run_id'],client_id=r['client_id'],test_id=r['test_id'],method_id=r['method_id'],eligibility_state=r['eligibility_state'],execution_status=r['execution_status'],signal_count=r['signal_count'],limitation=r['limitation'],started_at=r['started_at'],completed_at=r['completed_at'])); counts['executions']+=1
        sigs=legacy.execute('SELECT * FROM signal WHERE test_execution_id=? ORDER BY signal_id',(r['test_execution_id'],)).fetchall()
        for x in sigs:
            session.add(Signal(signal_id=x['signal_id'],test_execution_id=x['test_execution_id'],run_id=x['run_id'],client_id=x['client_id'],test_id=x['test_id'],signal_type=x['signal_type'],entity_type=x['entity_type'],entity_id=x['entity_id'],period_from=x['period_from'],period_to=x['period_to'],observed_value=x['observed_value'],comparison_value=x['comparison_value'],variance_value=x['variance_value'],unit=x['unit'],materiality_state=x['materiality_state'],status=x['status'],evidence_summary=x['evidence_summary'],source_primitive_id=x['source_primitive_id'],created_at=x['created_at'])); session.flush(); counts['signals']+=1
            for z in legacy.execute('SELECT * FROM diagnostic_lineage WHERE signal_id=? ORDER BY diagnostic_lineage_id',(x['signal_id'],)).fetchall():
                session.add(DiagnosticLineage(diagnostic_lineage_id=z['diagnostic_lineage_id'],signal_id=z['signal_id'],source_object_type=z['source_object_type'],source_object_id=z['source_object_id'],relationship_type=z['relationship_type'],scope_definition=z['scope_definition'])); counts['lineage']+=1
    return counts

def canonical_legacy(legacy,run_id,client_id):
    q=','.join('?' for _ in BATCH1_TESTS)
    ex=[tuple(r) for r in legacy.execute(f"SELECT test_id,method_id,eligibility_state,execution_status,signal_count,COALESCE(limitation,'') FROM test_execution WHERE run_id=? AND client_id=? AND test_id IN ({q}) ORDER BY test_id",(run_id,client_id,*BATCH1_TESTS)).fetchall()]
    sg=[tuple(r) for r in legacy.execute(f"SELECT test_id,signal_type,COALESCE(entity_type,''),COALESCE(entity_id,''),COALESCE(period_from,''),COALESCE(period_to,''),COALESCE(observed_value,''),COALESCE(comparison_value,''),COALESCE(variance_value,''),COALESCE(unit,''),materiality_state,status,evidence_summary,COALESCE(source_primitive_id,'') FROM signal WHERE run_id=? AND client_id=? AND test_id IN ({q}) ORDER BY test_id,signal_type,entity_type,entity_id,observed_value,variance_value",(run_id,client_id,*BATCH1_TESTS)).fetchall()]
    return ex,sg

def canonical_v2(session,run_id,client_id):
    es=session.scalars(select(TestExecution).where(TestExecution.run_id==run_id,TestExecution.client_id==client_id,TestExecution.test_id.in_(BATCH1_TESTS)).order_by(TestExecution.test_id)).all()
    ex=[(r.test_id,r.method_id,r.eligibility_state,r.execution_status,r.signal_count,r.limitation or '') for r in es]
    ss=session.scalars(select(Signal).where(Signal.run_id==run_id,Signal.client_id==client_id,Signal.test_id.in_(BATCH1_TESTS))).all()
    sg=sorted([(r.test_id,r.signal_type,r.entity_type or '',r.entity_id or '',r.period_from or '',r.period_to or '',r.observed_value or '',r.comparison_value or '',r.variance_value or '',r.unit or '',r.materiality_state,r.status,r.evidence_summary,r.source_primitive_id or '') for r in ss])
    return ex,sg


def migrate_diagnostic_batch(legacy, session, run_id, client_id, test_ids):
    _scope(session,run_id,client_id)
    test_ids=tuple(test_ids)
    if not test_ids: return {'executions':0,'signals':0,'lineage':0}
    q=','.join('?' for _ in test_ids)
    ex=legacy.execute(f"SELECT * FROM test_execution WHERE run_id=? AND client_id=? AND test_id IN ({q}) ORDER BY test_id,test_execution_id",(run_id,client_id,*test_ids)).fetchall()
    counts={'executions':0,'signals':0,'lineage':0}
    for r in ex:
        if session.get(TestExecution,r['test_execution_id']): continue
        session.add(TestExecution(test_execution_id=r['test_execution_id'],run_id=r['run_id'],client_id=r['client_id'],test_id=r['test_id'],method_id=r['method_id'],eligibility_state=r['eligibility_state'],execution_status=r['execution_status'],signal_count=r['signal_count'],limitation=r['limitation'],started_at=r['started_at'],completed_at=r['completed_at'])); counts['executions']+=1
        for x in legacy.execute('SELECT * FROM signal WHERE test_execution_id=? ORDER BY signal_id',(r['test_execution_id'],)).fetchall():
            session.add(Signal(signal_id=x['signal_id'],test_execution_id=x['test_execution_id'],run_id=x['run_id'],client_id=x['client_id'],test_id=x['test_id'],signal_type=x['signal_type'],entity_type=x['entity_type'],entity_id=x['entity_id'],period_from=x['period_from'],period_to=x['period_to'],observed_value=x['observed_value'],comparison_value=x['comparison_value'],variance_value=x['variance_value'],unit=x['unit'],materiality_state=x['materiality_state'],status=x['status'],evidence_summary=x['evidence_summary'],source_primitive_id=x['source_primitive_id'],created_at=x['created_at'])); session.flush(); counts['signals']+=1
            for z in legacy.execute('SELECT * FROM diagnostic_lineage WHERE signal_id=? ORDER BY diagnostic_lineage_id',(x['signal_id'],)).fetchall():
                session.add(DiagnosticLineage(diagnostic_lineage_id=z['diagnostic_lineage_id'],signal_id=z['signal_id'],source_object_type=z['source_object_type'],source_object_id=z['source_object_id'],relationship_type=z['relationship_type'],scope_definition=z['scope_definition'])); counts['lineage']+=1
    return counts

def migrate_cus_prod_pri(legacy,session,run_id,client_id):
    return migrate_diagnostic_batch(legacy,session,run_id,client_id,BATCH2_TESTS)

def canonical_batch_legacy(legacy,run_id,client_id,test_ids):
    test_ids=tuple(test_ids); q=','.join('?' for _ in test_ids)
    ex=[tuple(r) for r in legacy.execute(f"SELECT test_id,method_id,eligibility_state,execution_status,signal_count,COALESCE(limitation,'') FROM test_execution WHERE run_id=? AND client_id=? AND test_id IN ({q}) ORDER BY test_id",(run_id,client_id,*test_ids)).fetchall()]
    sg=[tuple(r) for r in legacy.execute(f"SELECT test_id,signal_type,COALESCE(entity_type,''),COALESCE(entity_id,''),COALESCE(period_from,''),COALESCE(period_to,''),COALESCE(observed_value,''),COALESCE(comparison_value,''),COALESCE(variance_value,''),COALESCE(unit,''),materiality_state,status,evidence_summary,COALESCE(source_primitive_id,'') FROM signal WHERE run_id=? AND client_id=? AND test_id IN ({q}) ORDER BY test_id,signal_type,entity_type,entity_id,observed_value,variance_value",(run_id,client_id,*test_ids)).fetchall()]
    return ex,sg

def canonical_batch_v2(session,run_id,client_id,test_ids):
    test_ids=tuple(test_ids)
    es=session.scalars(select(TestExecution).where(TestExecution.run_id==run_id,TestExecution.client_id==client_id,TestExecution.test_id.in_(test_ids)).order_by(TestExecution.test_id)).all()
    ex=[(r.test_id,r.method_id,r.eligibility_state,r.execution_status,r.signal_count,r.limitation or '') for r in es]
    ss=session.scalars(select(Signal).where(Signal.run_id==run_id,Signal.client_id==client_id,Signal.test_id.in_(test_ids))).all()
    sg=sorted([(r.test_id,r.signal_type,r.entity_type or '',r.entity_id or '',r.period_from or '',r.period_to or '',r.observed_value or '',r.comparison_value or '',r.variance_value or '',r.unit or '',r.materiality_state,r.status,r.evidence_summary,r.source_primitive_id or '') for r in ss])
    return ex,sg

# v2.12 batch 3: People & Productivity + Suppliers & Overheads.
BATCH3_TESTS=tuple([f'PEO-{i:02d}' for i in range(1,6)]+[f'SUP-{i:02d}' for i in range(1,7)])

def migrate_peo_sup(legacy,session,run_id,client_id):
    """Losslessly persist PEO-01..05 and SUP-01..06 diagnostic contracts."""
    return migrate_diagnostic_batch(legacy,session,run_id,client_id,BATCH3_TESTS)

# v2.13 batch 4: Working Capital & Cash.
BATCH4_TESTS=tuple([f'WC-{i:02d}' for i in range(1,8)])

def migrate_working_capital(legacy,session,run_id,client_id):
    """Losslessly persist WC-01..07 diagnostic contracts."""
    return migrate_diagnostic_batch(legacy,session,run_id,client_id,BATCH4_TESTS)

# v2.14 batch 5 (final): Forecasting & Performance + Financial Risk & Controls.
BATCH5_TESTS=tuple([f'FCST-{i:02d}' for i in range(1,5)]+[f'RISK-{i:02d}' for i in range(1,5)])

def migrate_fcst_risk(legacy,session,run_id,client_id):
    """Losslessly persist FCST-01..04 and RISK-01..04 diagnostic contracts."""
    return migrate_diagnostic_batch(legacy,session,run_id,client_id,BATCH5_TESTS)
