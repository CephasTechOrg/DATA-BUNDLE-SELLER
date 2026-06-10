import hashlib
import hmac
import json
import logging
import os

from fastapi import APIRouter, Request, Response
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import Order, ProviderWebhookEvent
from ..fulfillment import auto_place_order, map_provider_status, _extract_provider_order

logger = logging.getLogger(__name__)
router = APIRouter()
PAYSTACK_SECRET_KEY = (os.getenv("PAYSTACK_SECRET_KEY") or "").strip()
ALLOW_WEBHOOK_SIMULATE = os.getenv("ALLOW_WEBHOOK_SIMULATE", "").strip().lower() in ("1", "true", "yes")
RESELLERXPRESS_WEBHOOK_SECRET = (os.getenv("RESELLERXPRESS_WEBHOOK_SECRET") or "").strip()


def _verify_paystack_signature(payload_bytes: bytes, signature: str) -> bool:
    """Verify Paystack webhook using HMAC SHA512 of raw body."""
    if not PAYSTACK_SECRET_KEY or not signature:
        return False
    computed = hmac.new(
        PAYSTACK_SECRET_KEY.encode("utf-8"),
        payload_bytes,
        hashlib.sha512,
    ).hexdigest()
    return hmac.compare_digest(computed, signature)


async def _process_payment_success(reference: str, skip_wallet_check: bool = False) -> dict:
    """
    On Paystack `charge.success`:
    1. Mark `payment_status = "completed"` (idempotent).
    2. Auto-place the order with ResellerXpress (debits our wallet).

    Placement is delegated to `fulfillment.auto_place_order`, which is itself
    idempotent (no double-charge on duplicate webhook deliveries) and routes any
    provider failure to `manual_review` so a paid order is never lost.
    """
    db: Session = SessionLocal()
    try:
        order = db.query(Order).filter(Order.reference == reference).first()
        if not order:
            logger.warning("Webhook order not found: %s", reference)
            return {"status": "order not found"}

        already_paid = order.payment_status == "completed"
        if not already_paid:
            order.payment_status = "completed"
            if order.status not in ("completed", "failed", "processing", "manual_review"):
                order.status = "pending"
            db.commit()
            logger.info("Order %s: payment_status=completed", reference)
    except Exception as e:
        db.rollback()
        logger.exception("Order %s: payment update failed: %s", reference, e)
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

    # Auto-fulfill (own DB session; safe to call repeatedly).
    placement = await auto_place_order(reference)
    logger.info("Order %s: placement result=%s", reference, placement)
    return {"status": "ok", "placement": placement}


@router.post("/paystack")
async def paystack_webhook(request: Request):

    body = await request.body()
    signature = request.headers.get("x-paystack-signature", "")

    if not _verify_paystack_signature(body, signature):
        logger.warning("Paystack webhook signature verification failed")
        return Response(content="Invalid signature", status_code=401)

    payload = json.loads(body)
    event = payload.get("event")

    if event == "charge.success":
        reference = payload.get("data", {}).get("reference")
        if not reference:
            logger.warning("Paystack webhook missing reference in data")
            return {"status": "missing reference"}
        logger.info("Webhook charge.success for reference=%s", reference)
        return await _process_payment_success(reference)

    return {"status": "ok"}


@router.post("/simulate-success")
async def simulate_payment_success(request: Request):
    """
    Local testing only: simulate "payment completed" for an order without calling Paystack.
    Set ALLOW_WEBHOOK_SIMULATE=true in .env (do NOT set in production).
    Body: { "reference": "order-reference-uuid" } or form reference=...
    """
    if not ALLOW_WEBHOOK_SIMULATE:
        return Response(content="Simulate disabled. Set ALLOW_WEBHOOK_SIMULATE=true for local testing.", status_code=403)

    reference = (request.query_params.get("reference") or "").strip()
    skip_wallet = request.query_params.get("skip_wallet", "").strip().lower() in ("1", "true", "yes")
    if not reference:
        try:
            body = await request.json()
            reference = (reference or (body.get("reference") or "").strip())
            skip_wallet = skip_wallet or str(body.get("skip_wallet", "")).strip().lower() in ("1", "true", "yes")
        except Exception:
            pass
    if not reference:
        return {"error": "Missing reference", "usage": "POST body: {\"reference\": \"your-order-reference\"} or ?reference=..."}

    logger.info("Simulate payment success for reference=%s (local test) skip_wallet=%s", reference, skip_wallet)
    result = await _process_payment_success(reference, skip_wallet_check=skip_wallet)
    return result


def _extract_request_id(payload: dict) -> str:
    """Find our order reference (request_id) in a provider webhook payload."""
    if not isinstance(payload, dict):
        return ""
    # Try common shapes: top-level, or nested under "order"/"data".
    for container in (payload, payload.get("order"), payload.get("data")):
        if isinstance(container, dict):
            for key in ("request_id", "reference"):
                val = container.get(key)
                if val:
                    return str(val)
    return ""


@router.post("/resellerxpress")
async def resellerxpress_webhook(request: Request):
    """
    Inbound ResellerXpress order updates (order_success / order_failed).

    Auth: shared secret via ?secret=... (the docs expose no signature scheme).
    Stores the raw event first, then updates the matching order. Always returns
    200 quickly so the provider does not retry storms us.
    """
    if RESELLERXPRESS_WEBHOOK_SECRET:
        if request.query_params.get("secret", "") != RESELLERXPRESS_WEBHOOK_SECRET:
            logger.warning("ResellerXpress webhook rejected: bad/missing secret")
            return Response(content="Invalid secret", status_code=401)

    try:
        payload = await request.json()
    except Exception:
        logger.warning("ResellerXpress webhook: non-JSON body")
        return {"received": True}

    event_type = payload.get("event") or payload.get("event_type")
    request_id = _extract_request_id(payload)
    _, prov_status, _ = _extract_provider_order(payload)

    db: Session = SessionLocal()
    try:
        # 1. Store the raw event for audit/debugging before doing anything.
        db.add(
            ProviderWebhookEvent(
                event_type=event_type,
                request_id=request_id or None,
                provider_order_id=_extract_provider_order(payload)[0],
                payload=json.dumps(payload)[:10000],
                processed=False,
            )
        )
        db.commit()

        # 2. Find the local order and update its status.
        if not request_id:
            logger.warning("ResellerXpress webhook had no request_id: %s", payload)
            return {"received": True}

        order = db.query(Order).filter(Order.reference == request_id).first()
        if not order:
            logger.warning("ResellerXpress webhook for unknown order: %s", request_id)
            return {"received": True}

        # Derive status from explicit event when present, else from payload status.
        if event_type == "order_success":
            new_status = "completed"
        elif event_type == "order_failed":
            new_status = "failed"
        else:
            new_status = map_provider_status(prov_status)

        if prov_status:
            order.provider_status = prov_status
        # Don't downgrade a finalized order.
        if order.status not in ("completed", "failed"):
            order.status = new_status
        db.commit()
        logger.info("ResellerXpress webhook: order %s -> %s (event=%s)", request_id, order.status, event_type)
        return {"received": True, "status": order.status}
    except Exception as e:
        db.rollback()
        logger.exception("ResellerXpress webhook processing failed: %s", e)
        return {"received": True}
    finally:
        db.close()
