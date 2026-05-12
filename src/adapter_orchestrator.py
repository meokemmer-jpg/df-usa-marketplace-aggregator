"""Adapter-Orchestrator (LaunchAgent-Entry) [CRUX-MK]."""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class OrchestratorResult:
    hotel_id: str
    marketplaces_aggregated: int
    max_price_deviation_usd: float
    sandbox_mode: bool
    audit_hash: str


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO)
    if Path("/tmp/df-usa-marketplace-aggregator.stop").exists():
        return 0

    from .usa_marketplace_aggregator_main import MarketplaceAggregator
    from .audit_logger import AuditLogger

    agg = MarketplaceAggregator()
    audit = AuditLogger()

    hotel_id = "CAPE-CORAL-PILOT-01"
    listings = agg.aggregate_listings(hotel_id)
    sync = agg.sync_prices(hotel_id, target_price_usd=149.0)

    audit_hash = audit.append({
        "type": "marketplace_aggregation",
        "hotel_id": hotel_id,
        "marketplaces": len(listings),
        "max_deviation_usd": sync.max_deviation_usd,
        "sandbox_mode": agg.sandbox_mode,
    })

    result = OrchestratorResult(
        hotel_id=hotel_id,
        marketplaces_aggregated=len(listings),
        max_price_deviation_usd=sync.max_deviation_usd,
        sandbox_mode=agg.sandbox_mode,
        audit_hash=audit_hash,
    )
    logger.info(f"USA-Marketplace-Aggregator: {result}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
