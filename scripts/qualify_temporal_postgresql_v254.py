"""Extend the approved cumulative disposable PostgreSQL gate through v2.54.

Uses the unchanged v2.53 Neon verification, credentials, fail-fast execution,
checkpoint isolation, report redaction and resource tracking. No live execution
is authorized until local architectural review is complete.
"""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

from scripts import qualify_dataset_postgresql_v253 as cumulative
from tests import test_temporal_contracts_v254 as domain
from tests import test_temporal_service_v254 as persistence
from tests import test_temporal_migrations_v254 as migrations

_inherited_suite=cumulative.build_live_suite


def build_live_suite():
    # Configure live-only fixture destinations after the cumulative main has
    # passed API verification. Static discovery itself opens no connections.
    persistence.TemporalServiceV254.target_url=cumulative.DatasetContractServiceV253.target_url
    persistence.TemporalReceivablesV254.target_url=cumulative.DatasetContractServiceV253.target_url
    migrations.TemporalMigrationsV254.target_url=cumulative.DatasetContractMigrationsV253.target_url
    inherited=list(_inherited_suite())
    # The last two inherited modules are PostgreSQL readiness and the v2.41
    # resource/isolation gate. Keep both last, exactly once, after v2.54.
    inherited_tail=inherited[-2:]
    suite=unittest.TestSuite(inherited[:-2])
    loader=unittest.defaultTestLoader
    suite.addTests([
        migrations.TemporalMigrationsV254('test_clean_creation_and_repeat_head'),
        migrations.TemporalMigrationsV254('test_frozen_v253_rows_preserved_temporal_rows_removed_downgrade_and_reupgrade'),
        loader.loadTestsFromModule(domain),
        loader.loadTestsFromModule(persistence),
    ])
    suite.addTests(inherited_tail)
    return suite


def main(argv=None):
    with patch.object(cumulative,'build_live_suite',build_live_suite):
        return cumulative.main(argv)


if __name__=='__main__':
    awake=None
    if sys.platform=='win32':
        import ctypes
        awake=ctypes.windll.kernel32.SetThreadExecutionState
        if not awake(0x80000001):raise RuntimeError('Unable to hold Windows awake for live qualification')
    try:
        raise SystemExit(main())
    finally:
        if awake:awake(0x80000000)
