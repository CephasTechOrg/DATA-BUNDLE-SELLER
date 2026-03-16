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

    return {"status": "ok"}
