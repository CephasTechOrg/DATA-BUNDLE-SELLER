"""
One-time seed: if bundles table is empty, populate from pricing.py (cost + default markup = selling).
Runs on every app startup (e.g. Render deploy or cold start).
"""
import logging

from .database import SessionLocal
from .models import Bundle
from .utils.pricing import BUNDLES_BY_NETWORK

logger = logging.getLogger(__name__)
DEFAULT_MARKUP_GHS = 1.0


def seed_bundles_if_empty():
    db = SessionLocal()
    try:
        count = db.query(Bundle).count()
        if count > 0:
            logger.info("Bundles table already has %s rows, skipping seed.", count)
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
        logger.info("Seeded bundles table with %s rows.", display_order)
    except Exception as e:
        logger.exception("Bundle seed failed: %s", e)
        raise
    finally:
        db.close()
