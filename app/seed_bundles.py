"""
One-time seed: if bundles table is empty, populate from pricing.py (cost + default markup = selling).
"""
from .database import SessionLocal
from .models import Bundle
from .utils.pricing import BUNDLES_BY_NETWORK

DEFAULT_MARKUP_GHS = 1.0


def seed_bundles_if_empty():
    db = SessionLocal()
    try:
        if db.query(Bundle).count() > 0:
            return
        display_order = 0
        for network, capacity_to_cost in BUNDLES_BY_NETWORK.items():
            for capacity_mb, cost in sorted(capacity_to_cost.items()):
                selling = round(cost + DEFAULT_MARKUP_GHS, 2)
                db.add(
                    Bundle(
                        network=network,
                        capacity_mb=capacity_mb,
                        cost_price_ghs=cost,
                        selling_price_ghs=selling,
                        is_active=True,
                        display_order=display_order,
                    )
                )
                display_order += 1
        db.commit()
    finally:
        db.close()
