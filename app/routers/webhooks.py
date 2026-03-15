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

logging.basicConfig(level=logging.INFO)

router = APIRouter()
PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY", "")


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
        logging.warning("Paystack webhook signature verification failed")
        return Response(content="Invalid signature", status_code=401)

    payload = json.loads(body)
    event = payload.get("event")

    if event == "charge.success":

        reference = payload["data"]["reference"]
        logging.info(f"Webhook received for reference {reference}")

        db: Session = SessionLocal()

        try:
            order = db.query(Order).filter(Order.reference == reference).first()

            if not order:
                return {"status": "order not found"}

            # Idempotent: prevent duplicate delivery if Paystack retries
            if order.payment_status == "completed":
                logging.info(f"Order {reference} already processed, skipping")
                return {"status": "already processed"}

            order.payment_status = "completed"

            # Wallet balance check before sending bundle (use bundle cost from DB)
            balance = await get_wallet_balance()
            bundle_row = (
                db.query(Bundle)
                .filter(
                    Bundle.network == order.network,
                    Bundle.capacity_mb == order.capacity,
                )
                .first()
            )
            bundle_cost = float(bundle_row.cost_price_ghs) if bundle_row else 0.0

            if balance < bundle_cost:
                order.status = "failed"
                db.commit()
                logging.warning(f"Insufficient wallet balance for {reference}: balance={balance}, cost={bundle_cost}")
                return {"status": "insufficient wallet balance"}

            result = await send_bundle(
                order.reference,
                order.phone_number,
                order.capacity
            )

            logging.info(f"Bundle sent response: {result}")

            # Update order status after delivery
            if result.get("success"):
                order.status = "completed"
            else:
                order.status = "failed"

            db.commit()
        finally:
            db.close()

    return {"status": "ok"}
