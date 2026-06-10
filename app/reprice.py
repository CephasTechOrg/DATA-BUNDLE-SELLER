"""
Apply tiered selling margins and deactivate orphan bundles.

Shared by the admin endpoint (POST /admin/bundles/reprice) and the
scripts/reprice_bundles.py CLI so both behave identically.

Tiers (selling = cost + margin, rounded UP to nearest GH0.10):
  - 1-5 GB   : + GH1.50 flat
  - 6-20 GB  : + 10%
  - 25 GB+   : + 7%

Orphans (provider_plan_id IS NULL) are deactivated: ResellerXpress doesn't sell
them, so they must not be purchasable.
"""
import logging
from decimal import Decimal, ROUND_CEILING

from .database import SessionLocal
from .models import Bundle

logger = logging.getLogger(__name__)


def margin_price(capacity_mb: int, cost: float) -> float:
    """Selling = cost + tiered margin, rounded UP to nearest GH0.10 (Decimal-exact)."""
    c = Decimal(str(cost))
    if capacity_mb <= 5000:
        raw = c + Decimal("1.50")
    elif capacity_mb <= 20000:
        raw = c * Decimal("1.10")
    else:
        raw = c * Decimal("1.07")
    return float(raw.quantize(Decimal("0.1"), rounding=ROUND_CEILING))


def reprice_all(deactivate_orphans: bool = True) -> dict:
    """
    Reprice every mapped bundle and (optionally) deactivate orphans.
    Returns a summary: {ok, repriced, deactivated, total}.
    """
    db = SessionLocal()
    try:
        bundles = db.query(Bundle).all()
        repriced = deactivated = 0
        for b in bundles:
            if b.provider_plan_id is None:
                if deactivate_orphans and b.is_active:
                    b.is_active = False
                    deactivated += 1
                continue
            new_sell = margin_price(b.capacity_mb, float(b.cost_price_ghs))
            if abs(new_sell - float(b.selling_price_ghs)) > 0.001:
                b.selling_price_ghs = new_sell
                repriced += 1
        db.commit()
        summary = {"ok": True, "repriced": repriced, "deactivated": deactivated, "total": len(bundles)}
        logger.info("Reprice complete: %s", summary)
        return summary
    except Exception as exc:
        db.rollback()
        logger.exception("Reprice failed: %s", exc)
        return {"ok": False, "message": str(exc), "repriced": 0, "deactivated": 0, "total": 0}
    finally:
        db.close()
