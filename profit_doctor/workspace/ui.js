/* No client-side analytical derivation or persistent secret storage. */
'use strict';
let csrf='', current=null, receipts=[];
const el=id=>document.getElementById(id), val=id=>el(id).value.trim();
const message=text=>{el('message').textContent=text;};
const path=()=>`/clients/${encodeURIComponent(current.client_id)}/engagements/${encodeURIComponent(current.engagement_id)}`;
async function api(url,method='GET',body=null,headers={}){
  const opts={method,headers:{'X-CSRF-Token':csrf,...headers},credentials:'same-origin'};
  if(method!=='GET') opts.headers['Idempotency-Key']=crypto.randomUUID();
  if(body!==null){if(body instanceof Blob)opts.body=body;else{opts.body=JSON.stringify(body);opts.headers['Content-Type']='application/json';}}
  const res=await fetch(url,opts), data=await res.json();
  if(!res.ok)throw new Error(data.error||JSON.stringify(data.detail)||'Request refused');
  return data;
}
function safe(task){return async e=>{e.preventDefault();try{await task();message('Saved / loaded successfully.');}catch(err){message(err.message);}};}
function options(id,items,empty=false){const node=el(id);node.replaceChildren();if(empty)node.add(new Option('None',''));items.forEach(x=>node.add(new Option(x.label,x.id)));}
function card(container,title,data){const box=document.createElement('div');box.className='card';const h=document.createElement('h3');h.textContent=title;const pre=document.createElement('pre');pre.textContent=JSON.stringify(data,null,2);box.append(h,pre);el(container).append(box);return box;}
async function loadClients(){const rows=await api('/clients');options('clients',rows.map(x=>({id:x.client_id,label:x.client_name})));await loadEngagements();}
async function loadEngagements(){el('review').hidden=true;current=null;if(!val('clients'))return;const rows=await api(`/clients/${encodeURIComponent(val('clients'))}/engagements`);options('engagements',rows.map(x=>({id:x.engagement_id,label:`${x.title} · ${x.status}`})));}
async function openWorkspace(id){const data=await api(`/clients/${encodeURIComponent(val('clients'))}/engagements/${encodeURIComponent(id)}`);current=data.engagement;receipts=data.inventory.map(x=>x.receipt);el('review').hidden=false;el('review-title').textContent=`${current.title} · ${current.status} · revision ${current.revision}`;el('scope').textContent=JSON.stringify(current.scope);el('runs').value=current.run_ids.join(',');el('readiness-ids').value=current.readiness_ids.join(',');el('readiness-mode').value=current.readiness_view;
  ['inventory','requests','history','readiness'].forEach(x=>el(x).replaceChildren());
  data.inventory.forEach(x=>{const box=card('inventory',x.receipt.filename,x);const a=document.createElement('a');a.textContent='Download retained original';a.href=`/clients/${encodeURIComponent(current.client_id)}/receipts/${encodeURIComponent(x.receipt.receipt_id)}`;box.append(a);});
  const choices=receipts.map(x=>({id:x.receipt_id,label:x.filename+' · '+x.receipt_id}));options('predecessor',choices,true);options('registration-receipt',choices);
  data.requests.forEach(x=>{const box=card('requests',x.question,x);const select=document.createElement('select');['OPEN','EVIDENCE_RECEIVED','FULFILMENT_REVIEWED','WITHDRAWN'].forEach(s=>select.add(new Option(s,s)));select.value=x.status;
    const chosen=document.createElement('select');chosen.multiple=true;choices.forEach(c=>{const o=new Option(c.label,c.id);o.selected=x.receipt_ids.includes(c.id);chosen.add(o);});const rationale=document.createElement('textarea');rationale.placeholder='Review / withdrawal rationale';rationale.value=x.review_rationale||'';const button=document.createElement('button');button.textContent='Save request revision';button.onclick=safe(async()=>{await api(path()+'/requests','POST',{value:{...x,revision:x.revision+1,status:select.value,receipt_ids:[...chosen.selectedOptions].map(o=>o.value),review_rationale:rationale.value||null},expected_revision:x.revision});await openWorkspace(current.engagement_id);});box.append(select,chosen,rationale,button);});
  data.history.forEach(x=>card('history',x.document.event,x));
  (await api(path()+'/readiness')).forEach(x=>card('readiness',x.domain||x.assessment?.domain||'Readiness',x));
  card('readiness','Separate legacy diagnostic coverage',await api(path()+'/coverage'));
}
el('login').onsubmit=safe(async()=>{const res=await fetch('/session',{method:'POST',body:val('code'),headers:{'Content-Type':'text/plain'}});const data=await res.json();el('code').value='';if(!res.ok)throw new Error(data.error);csrf=data.csrf;options('new-client',data.client_grants.map(x=>({id:x,label:x})));el('login').hidden=true;el('workspace').hidden=false;await loadClients();});
el('client-form').onsubmit=safe(async()=>{await api('/clients','POST',{client_id:val('new-client'),name:val('client-name')});await loadClients();});
el('clients').onchange=safe(loadEngagements);
el('open').onclick=safe(async()=>{if(val('engagements'))await openWorkspace(val('engagements'));});
el('engagement-form').onsubmit=safe(async()=>{const value={engagement_id:crypto.randomUUID(),client_id:val('clients'),revision:1,title:val('title'),scope:{entity_id:val('entity'),ledger_id:val('ledger'),period_start:val('start'),period_end:val('end')}};const result=await api(`/clients/${encodeURIComponent(value.client_id)}/engagements`,'POST',{value,expected_revision:0});await loadEngagements();await openWorkspace(result.engagement_id);});
async function saveCurrent(value){const result=await api(`/clients/${encodeURIComponent(current.client_id)}/engagements`,'POST',{value:{...value,revision:current.revision+1},expected_revision:current.revision});await openWorkspace(result.engagement_id);}
el('close').onclick=safe(async()=>saveCurrent({...current,status:current.status==='OPEN'?'CLOSED':'OPEN'}));
el('selection-form').onsubmit=safe(async()=>saveCurrent({...current,run_ids:val('runs').split(',').map(x=>x.trim()).filter(Boolean),readiness_ids:val('readiness-ids').split(',').map(x=>x.trim()).filter(Boolean),readiness_view:val('readiness-mode')}));
el('receipt-form').onsubmit=safe(async()=>{for(const file of el('files').files){if(file.size>50*1024*1024)throw new Error('Receipt exceeds 50 MiB');const headers={'X-Filename':file.name,'X-Source-Role':val('role')};if(val('predecessor'))headers['X-Predecessor']=val('predecessor');await api(path()+'/receipts','POST',file,headers);}el('files').value='';await openWorkspace(current.engagement_id);});
el('registration-form').onsubmit=safe(async()=>{await api(path()+'/registration','POST',{receipt_id:val('registration-receipt'),version_id:val('version-id')});await openWorkspace(current.engagement_id);});
el('request-form').onsubmit=safe(async()=>{await api(path()+'/requests','POST',{value:{request_id:crypto.randomUUID(),client_id:current.client_id,engagement_id:current.engagement_id,revision:1,question:val('question'),evidence_required:val('required'),prerequisite:val('prerequisite')||null,due_date:val('due')||null},expected_revision:0});await openWorkspace(current.engagement_id);});
async function readiness(historical){const rows=await api(path()+'/readiness?historical='+historical);el('readiness').replaceChildren();rows.forEach(x=>card('readiness',x.domain||x.assessment?.domain||'Readiness',x));}
el('readiness-current').onclick=safe(async()=>readiness(false));el('readiness-history').onclick=safe(async()=>readiness(true));
