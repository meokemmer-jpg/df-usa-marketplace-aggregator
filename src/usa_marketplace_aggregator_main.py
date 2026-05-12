"""USA Marketplace Aggregator Core [CRUX-MK].

Adapter-Pattern fuer 5 USA-OTAs.
Mock-Default. ENV-Var-gated Real-Mode via DF_USA_MARKETPLACE_REAL_ENABLED.

[CRUX-MK]
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Marketplace(str, Enum):
    EXPEDIA = "expedia"
    BOOKING_US = "booking_us"
    HOTELS_COM = "hotels_com"
    PRICELINE = "priceline"
    TRIPADVISOR = "tripadvisor"


@dataclass(frozen=True)
class PropertyListing:
    hotel_id: str
    marketplace: Marketplace
    listing_url: str
    price_per_night_usd: float
    ota_commission_pct: float
    rating_avg: float
    review_count: int
    available: bool


@dataclass(frozen=True)
class PriceSyncReport:
    hotel_id: str
    marketplaces_synced: int
    target_price_usd: float
    deviations: dict[str, float]  # marketplace_id -> price-delta-usd
    max_deviation_usd: float


# Default-Commissions (Stand 2026 Mock)
DEFAULT_COMMISSIONS = {
    Marketplace.EXPEDIA: 0.18,
    Marketplace.BOOKING_US: 0.17,
    Marketplace.HOTELS_COM: 0.18,
    Marketplace.PRICELINE: 0.20,
    Marketplace.TRIPADVISOR: 0.15,
}


class MarketplaceAdapter(ABC):
    """Polymorpher Marketplace-Adapter."""

    def __init__(self, marketplace: Marketplace, sandbox_mode: bool = True):
        self.marketplace = marketplace
        self.sandbox_mode = sandbox_mode

    @abstractmethod
    def fetch_listing(self, hotel_id: str) -> PropertyListing:
        ...


class MockMarketplaceAdapter(MarketplaceAdapter):
    """Sandbox-Mock. Liefert deterministische Mock-Listings."""

    def fetch_listing(self, hotel_id: str) -> PropertyListing:
        return PropertyListing(
            hotel_id=hotel_id,
            marketplace=self.marketplace,
            listing_url=f"https://mock.{self.marketplace.value}.test/{hotel_id}",
            price_per_night_usd=150.0,
            ota_commission_pct=DEFAULT_COMMISSIONS[self.marketplace] * 100,
            rating_avg=4.5,
            review_count=120,
            available=True,
        )


class MarketplaceAggregator:
    """Aggregator ueber 5 USA-OTAs."""

    def __init__(self, sandbox_mode: Optional[bool] = None):
        if sandbox_mode is None:
            sandbox_mode = (
                os.environ.get("DF_USA_MARKETPLACE_REAL_ENABLED", "false").lower() != "true"
            )
        self.sandbox_mode = sandbox_mode
        self.adapters: dict[Marketplace, MarketplaceAdapter] = {
            mp: MockMarketplaceAdapter(mp, sandbox_mode=sandbox_mode)
            for mp in Marketplace
        }

    def list_marketplaces(self) -> list[Marketplace]:
        return list(self.adapters.keys())

    def aggregate_listings(self, hotel_id: str) -> dict[Marketplace, PropertyListing]:
        if not hotel_id:
            raise ValueError("hotel_id required")
        return {
            mp: a.fetch_listing(hotel_id)
            for mp, a in self.adapters.items()
        }

    def sync_prices(
        self,
        hotel_id: str,
        target_price_usd: float,
        tolerance_usd: float = 5.0,
    ) -> PriceSyncReport:
        if target_price_usd < 0:
            raise ValueError("target_price_usd must be >= 0")
        if tolerance_usd < 0:
            raise ValueError("tolerance_usd must be >= 0")
        listings = self.aggregate_listings(hotel_id)
        deviations: dict[str, float] = {}
        max_dev = 0.0
        for mp, listing in listings.items():
            delta = listing.price_per_night_usd - target_price_usd
            deviations[mp.value] = round(delta, 2)
            if abs(delta) > abs(max_dev):
                max_dev = delta
        return PriceSyncReport(
            hotel_id=hotel_id,
            marketplaces_synced=len(listings),
            target_price_usd=target_price_usd,
            deviations=deviations,
            max_deviation_usd=round(max_dev, 2),
        )

    def compute_ota_commission_total(
        self,
        hotel_id: str,
        revenue_per_marketplace_usd: dict[Marketplace, float],
    ) -> float:
        total = 0.0
        for mp, rev in revenue_per_marketplace_usd.items():
            if rev < 0:
                raise ValueError(f"Negative revenue for {mp}")
            commission = rev * DEFAULT_COMMISSIONS.get(mp, 0.0)
            total += commission
        return round(total, 2)
