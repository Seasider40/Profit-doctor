"""Run the Profit Doctor live PostgreSQL qualification gate.
Exit 2 when no live PostgreSQL URL is supplied so CI cannot mistake a skip for a pass.
"""
import os, subprocess, sys
url=os.getenv('PROFIT_DOCTOR_POSTGRES_TEST_URL','')
if not url.startswith('postgresql'):
    print('POSTGRESQL QUALIFICATION: NOT RUN — set PROFIT_DOCTOR_POSTGRES_TEST_URL to a disposable PostgreSQL database.')
    raise SystemExit(2)
cmd=[sys.executable,'-W','error::ResourceWarning','-m','unittest','-v','tests.test_postgresql_readiness_v217','tests.test_postgresql_live_qualification_v218']
raise SystemExit(subprocess.call(cmd))
