from datetime import datetime, timezone

def now(): return datetime.now(timezone.utc).isoformat()
DEFAULTS=[
 ('RECURRING_SUBSCRIPTION','Recurring Subscription','RECURRING',1,'HIGH'),('RETAINER','Retainer','RECURRING',1,'HIGH'),
 ('USAGE','Usage / Consumption','VARIABLE_RECURRING',1,'VARIABLE'),('PRODUCT_SALE','Product Sale','TRANSACTIONAL',0,'VARIABLE'),
 ('PROJECT','Project / Contract','PROJECT',0,'VARIABLE'),('IMPLEMENTATION','Implementation','PROJECT',0,'VARIABLE'),
 ('EVENT','Event Revenue','EVENT',0,'VARIABLE'),('SERVICE','Service','TRANSACTIONAL',0,'VARIABLE'),
 ('MEDIA','Media / Advertising','CAMPAIGN',0,'VARIABLE'),('SUPPORT','Support','RECURRING',1,'HIGH')]

def seed_revenue_types(con):
    for r in DEFAULTS: con.execute('INSERT OR IGNORE INTO revenue_type_definition VALUES (?,?,?,?,?,1)',r)
    con.commit()

def assign_product_revenue_type(con,client_id,product_key,revenue_type_code,evidence_basis='MANAGEMENT_CONFIRMED',effective_from='1900-01-01'):
    seed_revenue_types(con)
    if not con.execute('SELECT 1 FROM revenue_type_definition WHERE revenue_type_code=?',(revenue_type_code,)).fetchone(): raise ValueError('Unknown revenue type')
    con.execute('INSERT OR REPLACE INTO product_revenue_semantics VALUES (?,?,?,?,?,?,?)',(client_id,product_key,revenue_type_code,effective_from,None,evidence_basis,now())); con.commit()

def revenue_mix(con,client_id,dataset_version_id):
    seed_revenue_types(con)
    rows=con.execute('''SELECT s.net_revenue, prs.revenue_type_code, r.cadence_type,r.recurring_flag
      FROM sales_transaction s LEFT JOIN product_revenue_semantics prs ON prs.client_id=s.client_id AND prs.product_key=(SELECT source_entity_key FROM entity_alias WHERE entity_id=s.product_entity_id ORDER BY entity_alias_id LIMIT 1)
      LEFT JOIN revenue_type_definition r ON r.revenue_type_code=prs.revenue_type_code
      WHERE s.client_id=? AND s.dataset_version_id=? AND s.record_status='ACTIVE' ''',(client_id,dataset_version_id)).fetchall()
    from decimal import Decimal
    total=sum((Decimal(r['net_revenue']) for r in rows),Decimal('0')); recurring=sum((Decimal(r['net_revenue']) for r in rows if r['recurring_flag']==1),Decimal('0')); unmapped=sum((Decimal(r['net_revenue']) for r in rows if r['revenue_type_code'] is None),Decimal('0'))
    return {'total_revenue':total,'recurring_revenue':recurring,'recurring_pct':(recurring/total*100 if total else None),'unmapped_revenue':unmapped,'unmapped_pct':(unmapped/total*100 if total else None)}
