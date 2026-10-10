"""Extend the disposable cumulative gate; never run before architectural approval.

All Neon verification, fail-fast behaviour, resource accounting and historical
checkpoint isolation are delegated to the approved cumulative infrastructure.
Legacy registered CSV/source stores remain local; canonical persistence uses
real PostgreSQL. Each new test receives a fresh current-head disposable schema.
"""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts import qualify_temporal_postgresql_v254 as inherited
from tests import test_production_ownership_service_v255 as ownership
from tests import test_component_margin_v255 as component
from tests import test_component_margin_migrations_v255 as component_migrations
from tests import test_production_evidence_migrations_v255 as migrations
from tests import test_ar_semantics_v255 as ar
from tests import test_production_temporal_v255 as temporal
from tests import test_production_history_v255 as history
from tests import test_zero_ar_v255 as zero
from tests import test_production_assessments_v255 as assessments
from tests import test_evidence_readiness_v255 as readiness
from tests import test_production_history_migrations_v255 as history_migrations
from tests import test_revenue_historical_context_v2551 as historical_context

CURRENT_HEAD='0020_engagement_workspace'
CLASSES=(ownership.ProductionOwnershipServiceV255,component.ComponentMarginV255,
    component_migrations.ComponentMarginMigrationsV255,migrations.ProductionEvidenceMigrationsV255,
    ar.ARSemanticCheckpointV255,temporal.ProductionTemporalV255,history.ProductionHistoryV255,
    zero.ZeroARV255,assessments.ProductionAssessmentsV255,assessments.ARProductionAssessmentsV255,
    readiness.EvidenceReadinessV255,readiness.ARReadinessV255,history_migrations.ProductionHistoryMigrationsV255,
    historical_context.RevenueHistoricalContextV2551)


def live_class(base):
    class Live(base):
        def setUp(self):
            # build_live_suite itself only discovers. This executes exclusively
            # after the approved main has verified the disposable environment.
            url=inherited.cumulative.DatasetContractServiceV253.target_url
            if not isinstance(url,str) or not url.startswith('postgresql+psycopg://'):
                raise ValueError('Verified direct PostgreSQL target unavailable')
            inherited.cumulative._restore_current_head(url)
            self.target_url=url
            super().setUp()
    Live.__name__='Live'+base.__name__
    Live.__qualname__=Live.__name__
    return Live


LIVE_CLASSES=tuple(live_class(base) for base in CLASSES)


def build_live_suite():
    prior=list(inherited.build_live_suite())
    suite=unittest.TestSuite(prior[:-2])
    for cls in LIVE_CLASSES:suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(cls))
    suite.addTests(prior[-2:])
    return suite


def main(argv=None):
    with patch.object(inherited.cumulative,'build_live_suite',build_live_suite),patch.object(
            inherited.cumulative,'CURRENT_HEAD',CURRENT_HEAD):
        return inherited.cumulative.main(argv)


if __name__=='__main__':
    awake=None
    if sys.platform=='win32':
        import ctypes
        awake=ctypes.windll.kernel32.SetThreadExecutionState
        if not awake(0x80000001):raise RuntimeError('Unable to hold Windows awake for qualification')
    try:raise SystemExit(main())
    finally:
        if awake:awake(0x80000000)
