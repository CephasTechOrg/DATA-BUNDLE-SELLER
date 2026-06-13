"""
ResellerXpress bundle provider client.

Auth: API key in the `X-API-KEY` header (NOT Bearer).
Base URL: https://resellerxpress.shop/api/v1

Orders are identified by `plan_id` (from GET /plans), not by raw capacity.
The provider debits its own dealer price for the plan against our wallet, so we
never send a price; we only choose the correct plan_id. Idempotency uses our
order `reference` as the `request_id`.

All functions normalise the provider response into a dict:
  { "ok": bool, "status_code": int, "data": <parsed body>, "message": <str|None> }
so callers can branch without re-parsing HTTP details.
"""
import logging
import os
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

BASE_URL = (os.getenv("RESELLERXPRESS_BASE_URL") or "https://resellerxpress.shop/api/v1").strip()
API_KEY = (os.getenv("RESELLERXPRESS_API_KEY") or "").strip()

DEFAULT_TIMEOUT = 30.0


class ResellerXpressError(Exception):
    """Raised when the provider is misconfigured (missing API key)."""


def _check_config() -> None:
    if not BASE_URL or not API_KEY:
        raise ResellerXpressError(
            "RESELLERXPRESS_BASE_URL and RESELLERXPRESS_API_KEY must be set for bundle delivery."
        )


def _headers(json_body: bool = False) -> Dict[str, str]:
    headers = {"X-API-KEY": API_KEY}
    if json_body:
        headers["Content-Type"] = "application/json"
    return headers


def _normalise(response: httpx.Response) -> Dict[str, Any]:
    """Turn an httpx.Response into our standard result dict."""
    try:
        data: Any = response.json()
    except ValueError:
        data = {"raw": response.text[:1000]}

    ok = 200 <= response.status_code < 300
    message = None
    if isinstance(data, dict):
        message = data.get("message")
    if not ok:
        logger.warning("ResellerXpress HTTP %s: %s", response.status_code, data)
    return {
        "ok": ok,
        "status_code": response.status_code,
        "data": data,
        "message": message,
    }


def _error_result(exc: Exception) -> Dict[str, Any]:
    logger.exception("ResellerXpress request failed: %s", exc)
    return {"ok": False, "status_code": 0, "data": None, "message": str(exc)}


async def get_plans(network: Optional[str] = None) -> Dict[str, Any]:
    """GET /plans — list active plans. `network` is the provider code (mtn/airteltigo/telecel)."""
    _check_config()
    params = {"network": network} if network else None
    url = f"{BASE_URL.rstrip('/')}/plans"
    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            response = await client.get(url, headers=_headers(), params=params)
        return _normalise(response)
    except httpx.HTTPError as exc:
        return _error_result(exc)


async def place_order(
    plan_id: int,
    phone: str,
    request_id: str,
    quantity: int = 1,
) -> Dict[str, Any]:
    """
    POST /place-order — queue a bundle order. The wallet is debited the dealer
    price for `plan_id`. `request_id` (our order reference) makes this idempotent:
    retrying with the same value returns the existing order (409) instead of
    double-charging.

    Returns the standard result dict. A 202 means *queued*, not delivered.
    """
    _check_config()
    payload = {
        "plan_id": int(plan_id),
        "phone": str(phone).strip(),
        "request_id": request_id,
        "quantity": int(quantity),
    }
    url = f"{BASE_URL.rstrip('/')}/place-order"
    logger.info("ResellerXpress place-order: request_id=%s plan_id=%s phone=%s", request_id, plan_id, phone)
    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            response = await client.post(url, headers=_headers(json_body=True), json=payload)
        result = _normalise(response)
        logger.info(
            "ResellerXpress place-order result: request_id=%s status=%s body=%s",
            request_id, result["status_code"], result["data"],
        )
        return result
    except httpx.HTTPError as exc:
        return _error_result(exc)


async def get_order_status(request_id: str) -> Dict[str, Any]:
    """GET /order-status?request_id=... — current provider status for one order."""
    _check_config()
    url = f"{BASE_URL.rstrip('/')}/order-status"
    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            response = await client.get(url, headers=_headers(), params={"request_id": request_id})
        return _normalise(response)
    except httpx.HTTPError as exc:
        return _error_result(exc)


async def get_wallet_balance() -> Dict[str, Any]:
    """GET /wallet-balance — our ResellerXpress wallet. data: {balance, total_funded, total_spent}."""
    _check_config()
    url = f"{BASE_URL.rstrip('/')}/wallet-balance"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, headers=_headers())
        return _normalise(response)
    except httpx.HTTPError as exc:
        return _error_result(exc)


async def get_reprocessable_orders() -> Dict[str, Any]:
    """GET /reprocessable — failed/queued orders that can be retried."""
    _check_config()
    url = f"{BASE_URL.rstrip('/')}/reprocessable"
    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            response = await client.get(url, headers=_headers())
        return _normalise(response)
    except httpx.HTTPError as exc:
        return _error_result(exc)


async def reprocess_order(provider_order_id: int) -> Dict[str, Any]:
    """POST /reprocess/{id} — retry a failed/queued provider order by its provider order id."""
    _check_config()
    url = f"{BASE_URL.rstrip('/')}/reprocess/{int(provider_order_id)}"
    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            response = await client.post(url, headers=_headers())
        return _normalise(response)
    except httpx.HTTPError as exc:
        return _error_result(exc)


async def configure_webhook(url: str, events: list[str], enabled: bool = True) -> Dict[str, Any]:
    """POST /webhook — register our webhook URL for real-time order updates."""
    _check_config()
    endpoint = f"{BASE_URL.rstrip('/')}/webhook"
    payload = {"url": url, "enabled": enabled, "events": events}
    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            response = await client.post(endpoint, headers=_headers(json_body=True), json=payload)
        return _normalise(response)
    except httpx.HTTPError as exc:
        return _error_result(exc)
