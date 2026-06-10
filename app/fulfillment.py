"""
Automated bundle fulfillment via ResellerXpress.

Called after a customer's payment is verified. Resolves the bundle's
provider_plan_id, places the order against our wallet, and records the provider
response on the Order. Any failure routes the (already-paid) order to
`manual_review` so it is never silently lost.

Idempotency: we use the order `reference` as the provider `request_id`, and we
never place again once `provider_order_id` is set — so duplicate Paystack webhook
deliveries cannot double-charge the wallet.
"""
import logging
import os

from .database import SessionLocal
from .models import Order, Bundle
from .services import resellerxpress_service
from .utils.phone import normalize_ghana_phone

logger = logging.getLogger(__name__)


def _max_retries() -> int:
    try:
        return int(os.getenv("RESELLERXPRESS_MAX_RETRIES", "2"))
    except ValueError:
        return 2


def map_provider_status(provider_status: str) -> str:
    """Map a ResellerXpress status to our internal order status."""
    p = (provider_status or "").strip().lower()
    if p == "success":
        return "completed"
    if p == "failed":
        return "failed"
    # queued / processing / pending / anything else placed-but-not-final
    return "processing"


def _extract_provider_order(data):
    """
    Pull (provider_order_id, provider_status, provider_amount) from a provider
    response. Handles both place-order shape ({"order": {...}}) and the flat
    order-status shape ({"id":..,"status":..,"amount":..}).
    """
    if not isinstance(data, dict):
        return None, None, None
    order = data.get("order") if isinstance(data.get("order"), dict) else data
    oid = order.get("id")
    status = order.get("status")
    amount = order.get("amount")
    try:
        oid = int(oid) if oid is not None else None
    except (TypeError, ValueError):
        oid = None
    try:
        amount = float(amount) if amount is not None else None
    except (TypeError, ValueError):
        amount = None
    return oid, status, amount


def _to_manual_review(order: Order, reason: str) -> dict:
    order.status = "manual_review"
    order.failure_reason = reason
    logger.warning("Order %s -> manual_review: %s", order.reference, reason)
    return {"status": "manual_review", "reference": order.reference, "reason": reason}


async def _do_place(db, order: Order) -> dict:
    """
    Resolve plan, place the order, and record the result on `order` (no commit).
    Caller is responsible for committing.
    """
    bundle = (
        db.query(Bundle)
        .filter(Bundle.network == order.network, Bundle.capacity_mb == order.capacity)
        .first()
    )
    if bundle is None or bundle.provider_plan_id is None:
        return _to_manual_review(order, "no_provider_plan")

    phone = normalize_ghana_phone(order.phone_number)
    result = await resellerxpress_service.place_order(
        plan_id=bundle.provider_plan_id,
        phone=phone,
        request_id=order.reference,
        quantity=1,
    )

    status_code = result.get("status_code")
    data = result.get("data")

    # Success (202 queued, or any 2xx).
    if result.get("ok"):
        oid, prov_status, amount = _extract_provider_order(data)
        order.provider_order_id = oid
        order.provider_status = prov_status
        if amount is not None:
            order.provider_amount = amount
        order.status = map_provider_status(prov_status)
        order.failure_reason = None
        logger.info(
            "Order %s placed: provider_order_id=%s provider_status=%s amount=%s -> %s",
            order.reference, oid, prov_status, amount, order.status,
        )
        return {"status": order.status, "reference": order.reference, "provider_order_id": oid}

    # Duplicate: already placed earlier (idempotent recovery). Fetch the truth.
    if status_code == 409:
        lookup = await resellerxpress_service.get_order_status(order.reference)
        if lookup.get("ok"):
            oid, prov_status, amount = _extract_provider_order(lookup.get("data"))
            order.provider_order_id = oid
            order.provider_status = prov_status
            if amount is not None:
                order.provider_amount = amount
            order.status = map_provider_status(prov_status)
            order.failure_reason = None
            logger.info("Order %s recovered from 409 duplicate -> %s", order.reference, order.status)
            return {"status": order.status, "reference": order.reference, "provider_order_id": oid}
        return _to_manual_review(order, "duplicate_unresolved")

    # Insufficient wallet balance — do NOT charge customer again; needs top-up.
    if status_code == 400:
        return _to_manual_review(order, result.get("message") or "insufficient_provider_balance")

    # Validation error in our request.
    if status_code == 422:
        return _to_manual_review(order, result.get("message") or "provider_validation_error")

    # Anything else (network error, 5xx, unknown): keep the paid order safe.
    return _to_manual_review(order, result.get("message") or f"provider_error_{status_code}")


async def auto_place_order(reference: str) -> dict:
    """
    Place a freshly-paid order with the provider. Safe to call more than once:
    once `provider_order_id` is set (or the order is past 'pending'), it no-ops.
    """
    db = SessionLocal()
    try:
        order = db.query(Order).filter(Order.reference == reference).first()
        if not order:
            return {"status": "not_found", "reference": reference}
        if order.payment_status != "completed":
            return {"status": "skipped_unpaid", "reference": reference}
        if order.provider_order_id is not None or order.status in ("processing", "completed", "failed"):
            return {"status": "already_placed", "reference": reference, "current": order.status}
        if order.status == "manual_review":
            # Leave exceptions for the admin retry flow.
            return {"status": "manual_review", "reference": reference}

        summary = await _do_place(db, order)
        db.commit()
        return summary
    except Exception as e:
        db.rollback()
        logger.exception("auto_place_order failed for %s: %s", reference, e)
        return {"status": "error", "reference": reference, "message": str(e)}
    finally:
        db.close()


async def retry_order(reference: str) -> dict:
    """
    Admin-triggered retry of a failed / manual_review order. Uses /reprocess/{id}
    when we already have a provider_order_id, otherwise places fresh. Enforces
    RESELLERXPRESS_MAX_RETRIES.
    """
    db = SessionLocal()
    try:
        order = db.query(Order).filter(Order.reference == reference).first()
        if not order:
            return {"status": "not_found", "reference": reference}
        if order.payment_status != "completed":
            return {"status": "skipped_unpaid", "reference": reference}
        if order.status in ("completed",):
            return {"status": "already_completed", "reference": reference}
        if order.retry_count >= _max_retries():
            return {"status": "max_retries_reached", "reference": reference, "retry_count": order.retry_count}

        order.retry_count += 1

        if order.provider_order_id is not None:
            result = await resellerxpress_service.reprocess_order(order.provider_order_id)
            if result.get("ok"):
                _, prov_status, _ = _extract_provider_order(result.get("data"))
                order.provider_status = prov_status or "queued"
                order.status = map_provider_status(order.provider_status)
                order.failure_reason = None
                summary = {"status": order.status, "reference": reference, "via": "reprocess"}
            else:
                summary = _to_manual_review(order, result.get("message") or "reprocess_failed")
        else:
            summary = await _do_place(db, order)
            summary["via"] = "place"

        db.commit()
        return summary
    except Exception as e:
        db.rollback()
        logger.exception("retry_order failed for %s: %s", reference, e)
        return {"status": "error", "reference": reference, "message": str(e)}
    finally:
        db.close()
