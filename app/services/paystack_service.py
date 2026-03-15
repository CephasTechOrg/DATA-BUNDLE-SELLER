import logging
import os

import httpx

logger = logging.getLogger(__name__)

PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY", "").strip()
PAYSTACK_BASE_URL = "https://api.paystack.co"
# Optional: where to send user after payment (Paystack appends ?reference=...). Set in .env for production.
CALLBACK_URL = (os.getenv("PAYSTACK_CALLBACK_URL") or os.getenv("FRONTEND_URL", "") or "").strip() or None


async def initialize_payment(email, amount, reference, callback_url=None):
    if not PAYSTACK_SECRET_KEY:
        logger.error("PAYSTACK_SECRET_KEY is not set")
        return {"status": False, "message": "Payment provider not configured (missing secret key)."}

    url = f"{PAYSTACK_BASE_URL}/transaction/initialize"
    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}
    payload = {"email": email, "amount": int(round(amount * 100)), "reference": reference}
    if callback_url:
        payload["callback_url"] = callback_url
    elif CALLBACK_URL:
        payload["callback_url"] = CALLBACK_URL

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
        body = response.json()
        if not response.is_success:
            logger.warning("Paystack API HTTP %s: %s", response.status_code, body)
            return {"status": False, "message": body.get("message", f"Payment provider returned {response.status_code}")}
        return body
    except httpx.RequestError as e:
        logger.exception("Paystack request failed: %s", e)
        return {"status": False, "message": "Unable to reach payment provider. Please try again."}
