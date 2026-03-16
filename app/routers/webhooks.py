import hashlib
import hmac
import json
import logging
import os

from fastapi import APIRouter, Request, Response
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import Order, Bundle
from ..services.ghdataconnect_service import get_wallet_balance, send_bundle

logger = logging.getLogger(__name__)
router = APIRouter()
PAYSTACK_SECRET_KEY = (os.getenv("PAYSTACK_SECRET_KEY") or "").strip()
ALLOW_WEBHOOK_SIMULATE = os.getenv("ALLOW_WEBHOOK_SIMULATE", "").strip().lower() in ("1", "true", "yes")


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
    Shared logic: treat this order as paid and run wallet check + send bundle to provider.
    Used by the real Paystack webhook and by the simulate endpoint (local testing).
    skip_wallet_check: only for simulate endpoint; skip balance check and always attempt send_bundle.
    """
    db: Session = SessionLocal()
    try:
        order = db.query(Order).filter(Order.reference == reference).first()
        if not order:
            logger.warning("Webhook order not found: %s", reference)
            return {"status": "order not found"}

        if order.payment_status == "completed":
            logger.info("Order %s already processed, skipping", reference)
            return {"status": "already processed"}

        order.payment_status = "completed"

        bundle_row = (
            db.query(Bundle)
            .filter(
                Bundle.network == order.network,
                Bundle.capacity_mb == order.capacity,
            )
            .first()
        )
        bundle_cost = float(bundle_row.cost_price_ghs) if bundle_row else 0.0
        logger.info("Order %s: network=%s capacity=%s bundle_cost=%s", reference, order.network, order.capacity, bundle_cost)

        if not skip_wallet_check:
            balance = await get_wallet_balance()
            if balance is not None:
                logger.info("Order %s: wallet balance=%.2f cost=%.2f", reference, balance, bundle_cost)
            if balance is None:
                logger.warning(
                    "Order %s: wallet check failed (API error or bad URL/key). Attempting bundle send anyway.",
                    reference,
                )
            elif balance < bundle_cost:
                order.status = "failed"
                db.commit()
                logger.warning(
                    "Order %s: insufficient wallet balance balance=%s cost=%s",
                    reference, balance, bundle_cost,
                )
                return {"status": "insufficient wallet balance"}
        else:
            logger.info("Order %s: skip_wallet_check=true, sending bundle without balance check", reference)

        result = await send_bundle(
            order.reference,
            order.phone_number,
            order.capacity,
        )

        if result.get("success"):
            order.status = "completed"
            logger.info("Order %s: bundle sent successfully", reference)
        else:
            order.status = "failed"
            logger.warning("Order %s: bundle delivery failed: %s", reference, result.get("message", result))

        db.commit()
        return {"status": "ok", "order_status": order.status, "provider_response": result}
    except ValueError as e:
        logger.exception("Order %s: config error %s", reference, e)
        try:
            o = db.query(Order).filter(Order.reference == reference).first()
            if o:
                o.payment_status = "completed"
                o.status = "failed"
                db.commit()
        except Exception:
            pass
        return {"status": "config error", "message": str(e)}
    finally:
        db.close()


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
        return {"error": "Missing reference", "usage": "POST body: {\"reference\": \"your-order-reference\"} or ?reference=... Add ?skip_wallet=1 to skip wallet check and test send_bundle."}

    logger.info("Simulate payment success for reference=%s (local test) skip_wallet=%s", reference, skip_wallet)
    result = await _process_payment_success(reference, skip_wallet_check=skip_wallet)
    return result
