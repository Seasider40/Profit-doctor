"""Additive cumulative gate; architectural approval required before live execution."""
import sys
from pathlib import Path
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts import qualify_workspace_postgresql_v256 as inherited
from tests import test_adviser_setup_v257 as setup, test_adviser_migrations_v257 as migrations, test_adviser_home_v257 as home

CURRENT_HEAD='0021_adviser_setup'
CLASSES=(setup.AdviserSetupV257,migrations.AdviserMigrationsV257,home.AdviserHomeV257)
LIVE_CLASSES=tuple(inherited.inherited.live_class(c) for c in CLASSES)


def build_live_suite():
    previous=list(inherited.build_live_suite())
    suite=unittest.TestSuite(previous[:-2])
    for cls in LIVE_CLASSES:suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(cls))
    suite.addTests(previous[-2:])
    return suite


def main(argv=None):
    cumulative=inherited.inherited.inherited.cumulative
    with patch.object(cumulative,'build_live_suite',build_live_suite),patch.object(cumulative,'CURRENT_HEAD',CURRENT_HEAD):
        return cumulative.main(argv)


if __name__=='__main__':
    awake=None
    if sys.platform=='win32':
        import ctypes
        awake=ctypes.windll.kernel32.SetThreadExecutionState
        if not awake(0x80000001):raise RuntimeError('Unable to hold Windows awake')
    try:raise SystemExit(main())
    finally:
        if awake:awake(0x80000000)
