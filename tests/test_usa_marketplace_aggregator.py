"""Tests fuer DF-USA-Marketplace-Aggregator [CRUX-MK]. 10 Tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.usa_marketplace_aggregator_main import (
    MarketplaceAggregator,
    Marketplace,
    MockMarketplaceAdapter,
    PropertyListing,
    DEFAULT_COMMISSIONS,
)
from src.audit_logger import AuditLogger
from src.adapter_orchestrator import main as orchestrator_main


# ============== Main: 6 Tests ==============

def test_aggregator_initializes_five_marketplaces():
    """Test 1: Aggregator hat 5 Marketplaces."""
    agg = MarketplaceAggregator(sandbox_mode=True)
    mps = agg.list_marketplaces()
    assert len(mps) == 5
    assert Marketplace.EXPEDIA in mps
    assert Marketplace.BOOKING_US in mps
    assert Marketplace.HOTELS_COM in mps
    assert Marketplace.PRICELINE in mps
    assert Marketplace.TRIPADVISOR in mps


def test_aggregate_listings_returns_all_five():
    """Test 2: aggregate_listings liefert alle 5 Listings."""
    agg = MarketplaceAggregator(sandbox_mode=True)
    listings = agg.aggregate_listings("HOTEL-001")
    assert len(listings) == 5
    for mp, listing in listings.items():
        assert isinstance(listing, PropertyListing)
        assert listing.hotel_id == "HOTEL-001"
        assert listing.marketplace == mp


def test_aggregate_listings_empty_hotel_id_raises():
    """Test 3: empty hotel_id raises."""
    agg = MarketplaceAggregator(sandbox_mode=True)
    with pytest.raises(ValueError):
        agg.aggregate_listings("")


def test_sync_prices_computes_deviations():
    """Test 4: sync_prices liefert Deviations je Marketplace."""
    agg = MarketplaceAggregator(sandbox_mode=True)
    report = agg.sync_prices("HOTEL-001", target_price_usd=140.0)
    # Mock-Listing 150 USD, target 140 USD → deviation = 10
    assert report.marketplaces_synced == 5
    for mp_value, delta in report.deviations.items():
        assert delta == 10.0  # 150 - 140
    assert report.max_deviation_usd == 10.0


def test_sync_prices_negative_target_raises():
    """Test 5: negativer target raises."""
    agg = MarketplaceAggregator(sandbox_mode=True)
    with pytest.raises(ValueError):
        agg.sync_prices("HOTEL-001", target_price_usd=-100.0)


def test_compute_ota_commission_total():
    """Test 6: Commission-Total korrekt berechnet."""
    agg = MarketplaceAggregator(sandbox_mode=True)
    rev = {
        Marketplace.EXPEDIA: 1000.0,         # *0.18 = 180
        Marketplace.BOOKING_US: 1000.0,      # *0.17 = 170
        Marketplace.TRIPADVISOR: 1000.0,     # *0.15 = 150
    }
    total = agg.compute_ota_commission_total("HOTEL-001", rev)
    # 180+170+150 = 500
    assert total == 500.0


# ============== Orchestrator: 4 Tests ==============

def test_audit_chain_valid(tmp_path):
    """Test 7: Audit-Chain valid."""
    a = AuditLogger(audit_path=tmp_path / "a.jsonl", secret="s")
    a.append({"e": "1"})
    a.append({"e": "2"})
    assert a.verify_chain()["valid"] is True


def test_sandbox_default_via_env(monkeypatch):
    """Test 8: ENV default → sandbox."""
    monkeypatch.delenv("DF_USA_MARKETPLACE_REAL_ENABLED", raising=False)
    agg = MarketplaceAggregator()
    assert agg.sandbox_mode is True


def test_mock_adapter_yields_consistent_listings():
    """Test 9: MockAdapter liefert konsistente Mock-Daten."""
    for mp in Marketplace:
        adapter = MockMarketplaceAdapter(mp, sandbox_mode=True)
        listing = adapter.fetch_listing("HOTEL-001")
        assert listing.marketplace == mp
        assert listing.available is True
        # Commission matches DEFAULT
        assert listing.ota_commission_pct == DEFAULT_COMMISSIONS[mp] * 100


def test_orchestrator_main_exits_zero(monkeypatch, tmp_path):
    """Test 10: orchestrator_main() exit-code 0."""
    monkeypatch.setenv("HOME", str(tmp_path))
    rc = orchestrator_main([])
    assert rc == 0
