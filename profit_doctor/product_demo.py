"""v2.37 upload-to-report demonstration orchestration.
Runs an uploaded workbook through the existing intake/engine and exports only product-boundary JSON.
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, shutil
from profit_doctor.intake.bridge import execute_unknown_workbook
from profit_doctor.core.db import connect
from profit_doctor.api.service import get_product_view_json, get_priority_detail, get_diagnostic_detail
from profit_doctor.intake.readiness import build_upload_readiness

DEMO_VERSION='UDR-2.37'

def _sha256(p:Path):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def _json(path:Path,obj): path.write_text(json.dumps(obj,indent=2,ensure_ascii=False,default=str),encoding='utf-8')

def run_upload_to_report(workbook:str|Path, output_dir:str|Path, client_id='DEMO_CLIENT'):
    src=Path(workbook); out=Path(output_dir); out.mkdir(parents=True,exist_ok=True)
    uploaded=out/'uploaded_source.xlsx'; shutil.copy2(src,uploaded)
    db=out/'profit_doctor_demo.db'
    result=execute_unknown_workbook(uploaded,db,client_id=client_id)
    con=connect(db); run_id=result['run_id']
    review=get_product_view_json(con,run_id,client_id); _json(out/'review.json',review)
    readiness=build_upload_readiness(uploaded,review); _json(out/'upload_readiness.json',readiness)
    priority_files=[]
    for p in review['management_attention']:
        detail=get_priority_detail(con,run_id,client_id,p['theme']).model_dump(mode='json')
        fn=f"priority_{p['rank']:02d}_{p['theme'].lower()}.json"; _json(out/fn,detail); priority_files.append(fn)
    diagnostic_files=[]
    tids=sorted(set(review['performance_diagnostics']['completed']+review['performance_diagnostics']['partial']))
    for tid in tids:
        try: detail=get_diagnostic_detail(con,run_id,client_id,tid).model_dump(mode='json')
        except KeyError: continue
        fn=f"diagnostic_{tid.lower()}.json"; _json(out/fn,detail); diagnostic_files.append(fn)
    con.close()
    manifest={
      'demo_version':DEMO_VERSION,'created_at':datetime.now(timezone.utc).isoformat(),'run_id':run_id,'client_id':client_id,
      'source':{'original_name':src.name,'stored_name':uploaded.name,'sha256':_sha256(uploaded)},
      'pipeline':['UPLOAD','INTAKE_PROFILE','SEMANTIC_MAPPING','RECONCILIATION','CANONICAL_HANDOFF','PRIMITIVES','DIAGNOSTICS','FD_REASONING','ECONOMIC_ENGINE','MANAGEMENT_ATTENTION','OPPORTUNITY_REGISTER','PRODUCT_VIEW'],
      'intake':result['intake'],'canonical':result['canonical'],'diagnostics':result['diagnostics'],
      'outputs':{'upload_readiness':'upload_readiness.json','review':'review.json','priority_details':priority_files,'diagnostic_details':diagnostic_files,'database':db.name},
      'guardrails':['Product outputs are projections of persisted engine evidence.','No reconciliation residual is converted into a saving or loss.','Cash release and profit are not added together.','Unavailable evidence remains unavailable; the demo does not invent precision.']
    }
    _json(out/'manifest.json',manifest)
    return manifest
