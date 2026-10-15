"""Synthetic local browser fixture. Stdin owns graceful shutdown and test clock."""
import argparse
from pathlib import Path
import sys
import threading
import time
import tempfile
import gc
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from alembic import command
from sqlalchemy import text
import uvicorn
from profit_doctor.persistence import DatabaseConfig, build_engine, session_factory
from profit_doctor.workspace.app import create_app
from profit_doctor.workspace.contracts import Operator
from profit_doctor.workspace.storage import EvidenceStore
from tests.test_postgresql_live_qualification_v218 import alembic_config


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--port',type=int,required=True)
    parser.add_argument('--resume',action='store_true')
    args=parser.parse_args()
    root=args.root.resolve()
    if not root.name.startswith('pd-adviser-browser-') or root.parent!=Path(tempfile.gettempdir()).resolve():
        raise ValueError('Fresh disposable browser fixture root required')
    db=root/'workspace.db'
    if db.exists()!=args.resume: raise ValueError('Explicit fixture creation/resumption required')
    url='sqlite+pysqlite:///'+db.as_posix()
    if not args.resume: command.upgrade(alembic_config(url),'head')
    engine=build_engine(DatabaseConfig(url))
    advance=[0.0]
    app=create_app(session_factory(engine),Operator('synthetic-browser-adviser',frozenset({'browser-c1','browser-c2'})),
        EvidenceStore(root/'originals'),port=args.port,access_code='synthetic-local-browser-access',
        session_clock=lambda:time.monotonic()+advance[0])
    server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=args.port,access_log=False,log_level='error'))
    thread=threading.Thread(target=server.run)
    unraisable=[]
    previous_hook=sys.unraisablehook
    sys.unraisablehook=lambda event:unraisable.append(event.exc_type.__name__)
    thread.start()
    try:
        # Synchronise with the server event, not a retry of a product assertion.
        deadline=time.monotonic()+20
        while not server.started and thread.is_alive():
            if time.monotonic()>deadline:raise RuntimeError('Browser fixture startup timed out')
            time.sleep(.01)
        if not server.started:raise RuntimeError('Browser fixture failed to start')
        print('TEST_SERVER_READY',flush=True)
        for line in sys.stdin:
            if line.strip()=='STOP':break
            if line.startswith('ADVANCE '):
                advance[0]+=float(line.split()[1]);print('CLOCK_ADVANCED',flush=True)
    finally:
        server.should_exit=True
        thread.join(20)
        engine.dispose()
        gc.collect()
        sys.unraisablehook=previous_hook
        if thread.is_alive():raise RuntimeError('Browser fixture failed graceful shutdown')
        if unraisable:raise RuntimeError('Browser fixture unraisable resource errors: '+','.join(unraisable))
        print('TEST_SERVER_CLOSED',flush=True)


if __name__=='__main__':main()
