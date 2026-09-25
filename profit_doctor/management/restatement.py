"""v2.31 Dirty Data, Restatement & Revision Qualification.
Immutable revision history and baseline protection for longitudinal advisory.
"""
from decimal import Decimal as D
from datetime import datetime, timezone
import hashlib, json, uuid


def _now(): return datetime.now(timezone.utc).isoformat()
def _id(p): return p+'_'+uuid.uuid4().hex

def _hash(payload):
    raw=json.dumps(payload,sort_keys=True,separators=(',',':'),default=str).encode()
    return hashlib.sha256(raw).hexdigest()

SCHEMA=r'''
CREATE TABLE IF NOT EXISTS source_revision (
 revision_id TEXT PRIMARY KEY, client_id TEXT NOT NULL, logical_source_key TEXT NOT NULL,
 run_id TEXT NOT NULL, revision_number INTEGER NOT NULL, content_hash TEXT NOT NULL,
 revision_type TEXT NOT NULL, prior_revision_id TEXT, reason TEXT NOT NULL,
 effective_period TEXT, created_at TEXT NOT NULL,
 UNIQUE(client_id,logical_source_key,revision_number)
);
CREATE TABLE IF NOT EXISTS restatement_event (
 restatement_event_id TEXT PRIMARY KEY, client_id TEXT NOT NULL, run_id TEXT NOT NULL,
 logical_source_key TEXT NOT NULL, prior_revision_id TEXT, new_revision_id TEXT NOT NULL,
 change_class TEXT NOT NULL, affected_period TEXT, economic_delta TEXT, currency TEXT,
 explanation TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS baseline_revision_lock (
 baseline_lock_id TEXT PRIMARY KEY, client_id TEXT NOT NULL, longitudinal_opportunity_id TEXT NOT NULL,
 baseline_key TEXT NOT NULL, original_amount TEXT NOT NULL, current_restated_amount TEXT NOT NULL,
 currency TEXT NOT NULL, original_revision_id TEXT, current_revision_id TEXT,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 UNIQUE(client_id,longitudinal_opportunity_id,baseline_key)
);
CREATE TABLE IF NOT EXISTS baseline_revision_event (
 baseline_revision_event_id TEXT PRIMARY KEY, baseline_lock_id TEXT NOT NULL, run_id TEXT NOT NULL,
 prior_amount TEXT NOT NULL, restated_amount TEXT NOT NULL, delta TEXT NOT NULL,
 revision_id TEXT, reason TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS dirty_data_exception (
 exception_id TEXT PRIMARY KEY, client_id TEXT NOT NULL, run_id TEXT NOT NULL,
 logical_source_key TEXT NOT NULL, exception_type TEXT NOT NULL, row_key TEXT,
 detail TEXT NOT NULL, action TEXT NOT NULL, created_at TEXT NOT NULL
);
'''

def ensure_schema(con): con.executescript(SCHEMA)

def register_revision(con,client_id,run_id,logical_source_key,payload,reason,effective_period=None):
    ensure_schema(con); digest=_hash(payload); t=_now()
    prior=con.execute('SELECT * FROM source_revision WHERE client_id=? AND logical_source_key=? ORDER BY revision_number DESC LIMIT 1',(client_id,logical_source_key)).fetchone()
    if prior and prior['content_hash']==digest:
        return {'revision_id':prior['revision_id'],'revision_number':prior['revision_number'],'revision_type':'UNCHANGED','is_new':False}
    num=(prior['revision_number']+1) if prior else 1
    typ='ORIGINAL' if not prior else 'RESTATEMENT'
    rid=_id('rev')
    con.execute('INSERT INTO source_revision VALUES (?,?,?,?,?,?,?,?,?,?,?)',(rid,client_id,logical_source_key,run_id,num,digest,typ,prior['revision_id'] if prior else None,reason,effective_period,t))
    if prior:
        con.execute('INSERT INTO restatement_event VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',(_id('rst'),client_id,run_id,logical_source_key,prior['revision_id'],rid,'SOURCE_REVISION',effective_period,None,None,reason,t))
    con.commit(); return {'revision_id':rid,'revision_number':num,'revision_type':typ,'is_new':True}

def classify_period_change(con,client_id,run_id,logical_source_key,new_revision_id,affected_period,prior_amount,new_amount,currency='GBP',reason=''):
    """Past-period changes are restatements; current/future-period changes are business movements."""
    ensure_schema(con); prior=D(str(prior_amount)); new=D(str(new_amount)); delta=new-prior
    # caller explicitly supplies affected period; run period convention YYYY-MM-DD and run timestamp/ID need not encode date.
    # A revision to a period already represented by a prior revision is a data correction/restatement.
    old=con.execute('SELECT COUNT(*) n FROM source_revision WHERE client_id=? AND logical_source_key=? AND revision_id<>?',(client_id,logical_source_key,new_revision_id)).fetchone()['n']
    cls='DATA_RESTATEMENT' if old else 'BUSINESS_CHANGE'
    con.execute('INSERT INTO restatement_event VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',(_id('rst'),client_id,run_id,logical_source_key,None,new_revision_id,cls,affected_period,str(delta),currency,reason or cls,_now())); con.commit()
    return {'change_class':cls,'delta':delta}

def record_dirty_exception(con,client_id,run_id,logical_source_key,exception_type,detail,row_key=None,action='EXCLUDE_AND_REVIEW'):
    ensure_schema(con)
    allowed={'DUPLICATE_ROW','MISSING_PERIOD','MAPPING_CHANGE','CONTROL_RESTATEMENT','LATE_JOURNAL','INVALID_UNIT','SOURCE_CONFLICT'}
    if exception_type not in allowed: raise ValueError('Unsupported dirty-data exception')
    eid=_id('dirty'); con.execute('INSERT INTO dirty_data_exception VALUES (?,?,?,?,?,?,?,?,?)',(eid,client_id,run_id,logical_source_key,exception_type,row_key,detail,action,_now())); con.commit(); return eid

def deduplicate_rows(rows,key_fields):
    """Deterministic exact-key de-duplication. Conflicting duplicates are refused, never silently chosen."""
    seen={}; clean=[]; conflicts=[]; exact=[]
    for r in rows:
        key=tuple(r.get(k) for k in key_fields)
        if key not in seen: seen[key]=r; clean.append(r); continue
        if seen[key]==r: exact.append(key)
        else: conflicts.append(key)
    if conflicts: raise ValueError('CONFLICTING_DUPLICATE_KEYS:'+repr(conflicts[:5]))
    return clean,exact

def detect_missing_periods(periods,expected_periods):
    have=set(periods); return [p for p in expected_periods if p not in have]

def lock_baseline(con,client_id,longitudinal_opportunity_id,baseline_key,amount,currency='GBP',revision_id=None):
    ensure_schema(con); t=_now(); row=con.execute('SELECT * FROM baseline_revision_lock WHERE client_id=? AND longitudinal_opportunity_id=? AND baseline_key=?',(client_id,longitudinal_opportunity_id,baseline_key)).fetchone()
    if row: return row['baseline_lock_id']
    bid=_id('block'); con.execute('INSERT INTO baseline_revision_lock VALUES (?,?,?,?,?,?,?,?,?,?,?)',(bid,client_id,longitudinal_opportunity_id,baseline_key,str(D(str(amount))),str(D(str(amount))),currency,revision_id,revision_id,t,t)); con.commit(); return bid

def restate_baseline(con,client_id,run_id,longitudinal_opportunity_id,baseline_key,new_amount,reason,revision_id=None):
    ensure_schema(con); row=con.execute('SELECT * FROM baseline_revision_lock WHERE client_id=? AND longitudinal_opportunity_id=? AND baseline_key=?',(client_id,longitudinal_opportunity_id,baseline_key)).fetchone()
    if not row: raise ValueError('Baseline must be locked before restatement')
    prior=D(row['current_restated_amount']); new=D(str(new_amount)); delta=new-prior; t=_now()
    con.execute('INSERT INTO baseline_revision_event VALUES (?,?,?,?,?,?,?,?,?)',(_id('brev'),row['baseline_lock_id'],run_id,str(prior),str(new),str(delta),revision_id,reason,t))
    con.execute('UPDATE baseline_revision_lock SET current_restated_amount=?,current_revision_id=?,updated_at=? WHERE baseline_lock_id=?',(str(new),revision_id,t,row['baseline_lock_id']))
    con.commit(); return {'original_amount':D(row['original_amount']),'prior_restated_amount':prior,'current_restated_amount':new,'delta':delta}

def restatement_summary(con,client_id):
    ensure_schema(con)
    return {
      'source_revisions':con.execute('SELECT COUNT(*) n FROM source_revision WHERE client_id=?',(client_id,)).fetchone()['n'],
      'restatement_events':con.execute('SELECT COUNT(*) n FROM restatement_event WHERE client_id=?',(client_id,)).fetchone()['n'],
      'dirty_exceptions':con.execute('SELECT COUNT(*) n FROM dirty_data_exception WHERE client_id=?',(client_id,)).fetchone()['n'],
      'baseline_locks':con.execute('SELECT COUNT(*) n FROM baseline_revision_lock WHERE client_id=?',(client_id,)).fetchone()['n']
    }
