from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import argparse, json
from profit_doctor.product_demo import run_upload_to_report
p=argparse.ArgumentParser(description='Profit Doctor v2.37 upload-to-report demo')
p.add_argument('workbook'); p.add_argument('output_dir'); p.add_argument('--client-id',default='DEMO_CLIENT')
a=p.parse_args(); print(json.dumps(run_upload_to_report(a.workbook,a.output_dir,a.client_id),indent=2,default=str))
