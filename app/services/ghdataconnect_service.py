import logging
import os

import httpx

logger = logging.getLogger(__name__)

BASE_URL = (os.getenv("GHDATA_BASE_URL") or "").strip()
API_KEY = (os.getenv("GHDATA_API_KEY") or "").strip()


def _check_config():
    """Raise if provider env vars are missing (so webhook can log clearly)."""
    if not BASE_URL or not API_KEY:
        raise ValueError("GHDATA_BASE_URL and GHDATA_API_KEY must be set for bundle delivery.")


async def get_wallet_balance():
    """
    Return wallet balance (float) or None if the API request failed.
    Per GH Data Connect docs: GET /v1/getWalletBalance, Authorization: Bearer <token>.
    Response: { "success": true, "data": { "balance": "207.46" } } (balance is string).
    """
    _check_config()
    url = f"{BASE_URL.rstrip('/')}/v1/getWalletBalance"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    logger.info("Bundle provider wallet request: %s", url)
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, headers=headers)
        body = response.json()
        if not response.is_success:
            logger.warning("Bundle provider wallet API HTTP %s: %s", response.status_code, body)
            return None
        if not body.get("success"):
            logger.warning("Bundle provider wallet API success=false: %s", body)
            return None
        data = body.get("data") or {}
        balance = data.get("balance", 0)
        if balance is None:
            return None
        return float(balance)
    except (httpx.RequestError, ValueError) as e:
        logger.exception("Bundle provider wallet request failed: %s", e)
        return None


async def send_bundle(reference, phone, capacity):
    """
    Send bundle order to provider. Returns dict with 'success' (bool) and optional 'message'.
    Payload per docs: { reference, msisdn, capacity }. We send capacity in MB (e.g. 1000 = 1GB).
    """
    _check_config()
    url = f"{BASE_URL.rstrip('/')}/v1/createIshareBundleOrder"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    payload = {"reference": reference, "msisdn": str(phone).strip(), "capacity": int(capacity)}
    logger.info("Bundle provider createOrder: url=%s payload=%s", url, payload)
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
        try:
            body = response.json()
        except Exception as e:
            logger.warning("Bundle provider createOrder response not JSON: %s body=%s", e, response.text[:500])
            return {"success": False, "message": f"Invalid response: {response.status_code}"}
        logger.info("Bundle provider createOrder response HTTP %s: %s", response.status_code, body)

        if not response.is_success:
            return {"success": False, "message": body.get("message", f"HTTP {response.status_code}")}
        if body.get("success") is True:
            return {"success": True, "data": body.get("data")}
        return {"success": False, "message": body.get("message", "Provider returned success=false")}
    except (httpx.RequestError, ValueError) as e:
        logger.exception("Bundle provider createOrder request failed: %s", e)
        return {"success": False, "message": str(e)}


async def update_order_status(order):
    """Poll provider for delivery status; no-op if config missing."""
    if not BASE_URL or not API_KEY:
        return
    url = f"{BASE_URL.rstrip('/')}/v1/checkOrderStatus/{order.reference}"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, headers=headers)
        if not response.is_success:
            return
        body = response.json()
        data = (body.get("data") or {}) if body.get("success") else {}
        if data.get("status"):
            order.status = data.get("status", order.status)
    except (httpx.RequestError, ValueError, KeyError):
        pass
