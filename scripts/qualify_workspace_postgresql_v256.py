"""Additive live gate. Execute only after architectural live approval."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import qualify_production_postgresql_v255 as inherited
from tests import test_workspace_v256 as workflow
from tests import test_workspace_migrations_v256 as migrations
from tests import test_workspace_readers_v256 as readers

CURRENT_HEAD = '0020_engagement_workspace'
CLASSES = (workflow.WorkspaceV256, migrations.WorkspaceMigrationsV256, readers.WorkspaceReadersV256)
LIVE_CLASSES = tuple(inherited.live_class(cls) for cls in CLASSES)


def build_live_suite():
    prior = list(inherited.build_live_suite())
    suite = unittest.TestSuite(prior[:-2])
    for cls in LIVE_CLASSES:
        suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(cls))
    suite.addTests(prior[-2:])
    return suite


def main(argv=None):
    cumulative = inherited.inherited.cumulative
    with patch.object(cumulative, 'build_live_suite', build_live_suite), patch.object(cumulative, 'CURRENT_HEAD', CURRENT_HEAD):
        return cumulative.main(argv)


if __name__ == '__main__':
    awake = None
    if sys.platform == 'win32':
        import ctypes
        awake = ctypes.windll.kernel32.SetThreadExecutionState
        if not awake(0x80000001):
            raise RuntimeError('Unable to hold Windows awake for qualification')
    try:
        raise SystemExit(main())
    finally:
        if awake:
            awake(0x80000000)
