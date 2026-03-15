import httpx
import os

PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")
PAYSTACK_BASE_URL = "https://api.paystack.co"
# Optional: where to send user after payment (Paystack appends ?reference=...). Set in .env for production.
CALLBACK_URL = os.getenv("PAYSTACK_CALLBACK_URL") or os.getenv("FRONTEND_URL", "").strip() or None


async def initialize_payment(email, amount, reference, callback_url=None):
    url = f"{PAYSTACK_BASE_URL}/transaction/initialize"
    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}
    payload = {"email": email, "amount": amount * 100, "reference": reference}
    if callback_url:
        payload["callback_url"] = callback_url
    elif CALLBACK_URL:
        payload["callback_url"] = CALLBACK_URL
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)
    return response.json()
