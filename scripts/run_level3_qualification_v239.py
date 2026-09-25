import sys,json,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from profit_doctor.qualification_level3 import build_level3_case
out=ROOT/'qualification_outputs'/'v239'; out.mkdir(parents=True,exist_ok=True)
db=out/'level3_manufacturing.db'
if db.exists(): db.unlink()
con,s=build_level3_case(db,ROOT/'tests'/'fixtures'/'northstar',out/'immutable_store')
(out/'qualification_summary.json').write_text(json.dumps(s,indent=2))
rows=[dict(r) for r in con.execute('select test_id,execution_status,eligibility_state,signal_count from test_execution where run_id=? order by test_id',(s['run_id'],))]
(out/'diagnostic_coverage.json').write_text(json.dumps(rows,indent=2)); con.close(); print(json.dumps(s,indent=2))
