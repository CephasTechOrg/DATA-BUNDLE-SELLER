import httpx
import os

BASE_URL = os.getenv("GHDATA_BASE_URL")
API_KEY = os.getenv("GHDATA_API_KEY")


async def get_wallet_balance():
    url = f"{BASE_URL}/v1/getWalletBalance"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
    data = response.json().get("data", {})
    balance = data.get("balance", 0)
    return float(balance) if balance is not None else 0.0


async def send_bundle(reference, phone, capacity):

    url = f"{BASE_URL}/v1/createIshareBundleOrder"

    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }

    payload = {
        "reference": reference,
        "msisdn": phone,
        "capacity": capacity
    }

    async with httpx.AsyncClient() as client:

        response = await client.post(
            url,
            json=payload,
            headers=headers
        )

    return response.json()


async def update_order_status(order):
    url = f"{BASE_URL}/v1/checkOrderStatus/{order.reference}"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
    data = response.json().get("data", {})
    order.status = data.get("status", order.status)
