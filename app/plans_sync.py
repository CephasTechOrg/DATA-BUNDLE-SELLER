"""
Sync local `bundles` with ResellerXpress `GET /plans`.

ResellerXpress is the source of truth for which plans exist and their dealer
price. This sync:
  - fetches all active plans,
  - maps each provider network code -> our internal display name,
  - upserts a Bundle per (network, capacity_mb), storing provider_plan_id and the
    dealer cost (cost_price_ghs),
  - preserves the admin-set selling_price (only sets a default for brand-new bundles),
  - deactivates bundles that previously had a provider_plan_id but are no longer
    returned by the provider (safe: never touches manually-created bundles whose
    provider_plan_id is NULL).

Run as an admin action (POST /admin/plans/sync) or from a scheduled worker.
"""
import logging
from typing import Any, Dict, List, Optional

from .database import SessionLocal
from .models import Bundle
from .services import resellerxpress_service
from .utils.pricing import internal_network_name

logger = logging.getLogger(__name__)

DEFAULT_MARKUP_GHS = 1.0


def _capacity_mb_from_plan(plan: Dict[str, Any]) -> Optional[int]:
    """
    Derive capacity in MB from a plan. Prefer `volume` (GB) * 1000; fall back to
    `volume_mb`. Returns None if neither yields a positive value.
    """
    volume = plan.get("volume")
    if volume is not None:
        try:
            gb = float(volume)
            if gb > 0:
                return int(round(gb * 1000))
        except (TypeError, ValueError):
            pass
    volume_mb = plan.get("volume_mb")
    try:
        mb = int(volume_mb)
        if mb > 0:
            return mb
    except (TypeError, ValueError):
        pass
    return None


def _coerce_price(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


async def sync_plans() -> Dict[str, Any]:
    """
    Pull plans from ResellerXpress and reconcile the bundles table.

    Returns a summary: {ok, created, updated, deactivated, skipped, errors}.
    Never raises for provider/data issues — failures are reported in the summary.
    """
    result = await resellerxpress_service.get_plans()
    if not result.get("ok"):
        return {
            "ok": False,
            "message": result.get("message") or f"Provider returned HTTP {result.get('status_code')}",
            "created": 0, "updated": 0, "deactivated": 0, "skipped": 0, "errors": [],
        }

    plans = result.get("data")
    if not isinstance(plans, list):
        return {
            "ok": False,
            "message": f"Unexpected /plans response shape: {type(plans).__name__}",
            "created": 0, "updated": 0, "deactivated": 0, "skipped": 0, "errors": [],
        }

    created = updated = skipped = 0
    errors: List[str] = []
    seen_plan_ids: set[int] = set()

    db = SessionLocal()
    try:
        for plan in plans:
            if not isinstance(plan, dict):
                skipped += 1
                continue

            plan_id = plan.get("id")
            network_code = plan.get("network")
            internal_network = internal_network_name(network_code)
            capacity_mb = _capacity_mb_from_plan(plan)
            cost = _coerce_price(plan.get("price"))

            if plan_id is None or internal_network is None or capacity_mb is None or cost is None:
                skipped += 1
                errors.append(f"Skipped plan {plan_id!r} (network={network_code!r}, plan data incomplete)")
                continue

            try:
                plan_id = int(plan_id)
            except (TypeError, ValueError):
                skipped += 1
                errors.append(f"Skipped plan with non-integer id {plan_id!r}")
                continue

            seen_plan_ids.add(plan_id)

            bundle = (
                db.query(Bundle)
                .filter(Bundle.network == internal_network, Bundle.capacity_mb == capacity_mb)
                .first()
            )

            if bundle is None:
                db.add(
                    Bundle(
                        network=internal_network,
                        capacity_mb=capacity_mb,
                        cost_price_ghs=cost,
                        selling_price_ghs=round(cost + DEFAULT_MARKUP_GHS, 2),
                        is_active=True,
                        display_order=0,
                        provider_plan_id=plan_id,
                    )
                )
                created += 1
            else:
                # Update provider mapping + dealer cost; keep the admin's selling price.
                bundle.provider_plan_id = plan_id
                bundle.cost_price_ghs = cost
                bundle.is_active = True
                updated += 1

        # Deactivate bundles we previously mapped but the provider no longer lists.
        deactivated = 0
        stale = (
            db.query(Bundle)
            .filter(Bundle.provider_plan_id.isnot(None), Bundle.is_active == True)  # noqa: E712
            .all()
        )
        for b in stale:
            if b.provider_plan_id not in seen_plan_ids:
                b.is_active = False
                deactivated += 1

        db.commit()
    except Exception as exc:  # pragma: no cover - defensive
        db.rollback()
        logger.exception("Plans sync failed: %s", exc)
        return {
            "ok": False, "message": str(exc),
            "created": created, "updated": updated, "deactivated": 0,
            "skipped": skipped, "errors": errors,
        }
    finally:
        db.close()

    summary = {
        "ok": True,
        "created": created,
        "updated": updated,
        "deactivated": deactivated,
        "skipped": skipped,
        "errors": errors,
    }
    logger.info("Plans sync complete: %s", summary)
    return summary
