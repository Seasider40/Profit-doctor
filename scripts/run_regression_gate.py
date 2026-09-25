"""Portable isolated regression gate.
Runs each test module in its own process to prevent legacy SQLite handle leakage
from contaminating later modules. Returns non-zero if any module fails/times out.
"""
from pathlib import Path
import subprocess,sys,re
root=Path(__file__).resolve().parents[1]; tests=root/'tests'
results=[]
for f in sorted(tests.glob('test_*.py')):
    n=len(re.findall(r'^\s*def test_',f.read_text(),re.M))
    if f.name=='test_gate3_remediation.py': n=4
    cmd=[sys.executable,'-m','unittest','discover','-s',str(tests),'-p',f.name,'-q']
    try:
        p=subprocess.run(cmd,cwd=root,capture_output=True,text=True,timeout=90)
        ok=p.returncode==0
        results.append((f.name,n,ok,p.stdout+p.stderr))
    except subprocess.TimeoutExpired as e:
        results.append((f.name,n,False,'TIMEOUT'))
passed=sum(n for _,n,ok,_ in results if ok); total=sum(n for _,n,_,_ in results)
for name,n,ok,out in results: print(('PASS' if ok else 'FAIL'),name,n)
print(f'REGRESSION GATE: {passed}/{total} tests passed')
if passed!=total:
    for name,n,ok,out in results:
        if not ok: print('\n---',name,'---\n',out[-4000:])
    raise SystemExit(1)
