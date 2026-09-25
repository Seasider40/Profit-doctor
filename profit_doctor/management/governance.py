"""v2.32 Multi-client isolation, security and data-governance qualification.
Fail-closed tenant scoping for legacy SQLite runtime plus lineage/integrity guards.
"""
import uuid
from datetime import datetime, timezone

def _now(): return datetime.now(timezone.utc).isoformat()
def _id(p): return p+'_'+uuid.uuid4().hex

SCHEMA='''
CREATE TABLE IF NOT EXISTS governance_event (
 governance_event_id TEXT PRIMARY KEY, client_id TEXT NOT NULL, run_id TEXT,
 event_type TEXT NOT NULL, object_type TEXT, object_id TEXT, outcome TEXT NOT NULL,
 detail TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS client_archive_state (
 client_id TEXT PRIMARY KEY, archive_state TEXT NOT NULL, updated_at TEXT NOT NULL
);
'''
def ensure_schema(con): con.executescript(SCHEMA)

def audit(con,client_id,event_type,outcome,detail,run_id=None,object_type=None,object_id=None):
 ensure_schema(con); con.execute('INSERT INTO governance_event VALUES (?,?,?,?,?,?,?,?,?)',(_id('gov'),client_id,run_id,event_type,object_type,object_id,outcome,detail,_now())); con.commit()

def assert_run_owned(con,client_id,run_id):
 row=con.execute('SELECT client_id FROM engine_run WHERE run_id=?',(run_id,)).fetchone()
 if not row or row['client_id']!=client_id:
  audit(con,client_id,'TENANT_SCOPE','BLOCKED',f'run {run_id} is not owned by client',run_id)
  raise PermissionError('CROSS_CLIENT_RUN_ACCESS_BLOCKED')
 return True

def scoped_rows(con,client_id,table,where='1=1',params=()):
 cols={r['name'] for r in con.execute(f'PRAGMA table_info({table})').fetchall()}
 if 'client_id' not in cols: raise ValueError('TABLE_NOT_TENANT_SCOPED')
 return con.execute(f'SELECT * FROM {table} WHERE client_id=? AND ({where})',(client_id,*params)).fetchall()

def assert_object_owned(con,client_id,table,id_col,object_id):
 rows=scoped_rows(con,client_id,table,f'{id_col}=?',(object_id,))
 if not rows:
  audit(con,client_id,'TENANT_SCOPE','BLOCKED',f'{table}:{object_id} unavailable to tenant',object_type=table,object_id=object_id)
  raise PermissionError('CROSS_CLIENT_OBJECT_ACCESS_BLOCKED')
 return rows[0]

def assert_same_client_relationship(con,client_id,from_table,from_id_col,from_id,to_table,to_id_col,to_id):
 assert_object_owned(con,client_id,from_table,from_id_col,from_id); assert_object_owned(con,client_id,to_table,to_id_col,to_id); return True

def validate_lineage(con,client_id,signal_id):
 sig=assert_object_owned(con,client_id,'signal','signal_id',signal_id)
 links=con.execute('SELECT * FROM diagnostic_lineage WHERE signal_id=?',(signal_id,)).fetchall()
 problems=[]
 table_map={'primitive_result':('primitive_result','primitive_result_id'),'signal':('signal','signal_id'),'finding':('finding','finding_id'),'opportunity':('opportunity','opportunity_id')}
 for x in links:
  typ=x['source_object_type']; oid=x['source_object_id']
  if typ in table_map:
   t,c=table_map[typ]
   try: assert_object_owned(con,client_id,t,c,oid)
   except PermissionError: problems.append((typ,oid))
 if problems: raise PermissionError('CROSS_CLIENT_LINEAGE_BLOCKED')
 return {'signal_id':sig['signal_id'],'lineage_links':len(links),'valid':True}

def set_archive_state(con,client_id,state):
 if state not in {'ACTIVE','ARCHIVED'}: raise ValueError('INVALID_ARCHIVE_STATE')
 ensure_schema(con); con.execute('INSERT OR REPLACE INTO client_archive_state VALUES (?,?,?)',(client_id,state,_now())); con.commit()

def assert_client_active(con,client_id):
 ensure_schema(con); r=con.execute('SELECT archive_state FROM client_archive_state WHERE client_id=?',(client_id,)).fetchone()
 if r and r['archive_state']=='ARCHIVED': raise PermissionError('CLIENT_ARCHIVED')
 return True

def governance_summary(con,client_id):
 ensure_schema(con); return {'blocked_events':con.execute("SELECT COUNT(*) n FROM governance_event WHERE client_id=? AND outcome='BLOCKED'",(client_id,)).fetchone()['n']}
