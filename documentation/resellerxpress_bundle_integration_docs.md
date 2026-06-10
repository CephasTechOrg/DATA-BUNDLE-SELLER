# ResellerXpress Bundle API Integration Guide

**Project:** Ghana Data Bundle Reselling Platform  
**Provider:** ResellerXpress  
**API Version:** v1.0  
**Base URL:** `https://resellerxpress.shop/api/v1`  
**Networks Supported:** MTN Ghana, AirtelTigo, Telecel Ghana  
**Last Updated:** 2026-06-09

---

## 1. Purpose of This Document

This document explains how to integrate the **ResellerXpress API** into a data-bundle reselling platform.

The goal is to make the system fully automated:

1. A customer selects a data bundle on your app or website.
2. The customer pays you through your own payment system.
3. Your backend verifies the customer payment.
4. Your backend calls the ResellerXpress API using your reseller API key.
5. ResellerXpress queues and processes the bundle order.
6. Your system checks the order status or receives a webhook update.
7. The customer sees the final result: `success`, `failed`, `queued`, or `processing`.

The customer should never interact directly with ResellerXpress. Your backend acts as the bridge between your customer-facing platform and ResellerXpress.

---

## 2. Core Integration Summary

| Item | Value |
|---|---|
| Provider | ResellerXpress |
| API Version | v1.0 |
| Base URL | `https://resellerxpress.shop/api/v1` |
| Authentication | API key in `X-API-KEY` header |
| Order Processing | Asynchronous queue-based processing |
| Payment Model | Your ResellerXpress wallet is debited when you place an order |
| Idempotency | Supported through `request_id` |
| Webhooks | Supported for real-time order notifications |
| Reprocessing | Supported for failed and queued orders |
| Main Networks | `mtn`, `airteltigo`, `telecel` |

---

## 3. Authentication

All ResellerXpress API endpoints require an API key.

The API key must be passed in the HTTP request header:

```http
X-API-KEY: your_api_key_here
```

### Important Security Rule

Never expose the ResellerXpress API key in your frontend, mobile app, JavaScript bundle, or public GitHub repository.

The API key must only be used from your backend server.

Recommended environment variable:

```env
RESELLERXPRESS_API_KEY=your_api_key_here
RESELLERXPRESS_BASE_URL=https://resellerxpress.shop/api/v1
```

---

## 4. Recommended System Architecture

```text
Customer App / Website
        |
        | 1. Customer selects bundle and pays
        v
Your Backend API
        |
        | 2. Verify payment from your payment provider
        | 3. Generate unique request_id
        | 4. Call ResellerXpress /place-order
        v
ResellerXpress API
        |
        | 5. Queue and process order
        v
ResellerXpress Provider System
        |
        | 6. Sends bundle to recipient phone number
        v
Your Backend
        |
        | 7. Receives webhook or checks order status
        v
Customer App / Website
```

---

## 5. Order Status Flow

ResellerXpress uses the following order statuses:

| Status | Meaning | What Your System Should Do |
|---|---|---|
| `pending` | Order has just been created | Show customer: “Order received” |
| `queued` | Order is waiting in queue, often due to platform balance or processing delay | Show customer: “Processing” and keep checking |
| `processing` | Order is being sent to ResellerXpress/provider | Show customer: “Processing” |
| `success` | Bundle has been delivered | Mark order as completed |
| `failed` | Order failed | Mark as failed and allow admin/system retry if appropriate |

Failed and queued orders can be retried using the **Reprocess** endpoint.

### Important Reprocess Rule

According to the API documentation:

- If the failure was caused by **dealer balance**, the wallet may be charged again on retry.
- If the failure was caused by **platform balance** or an **API error**, there should be no extra charge.
- On failure, the wallet is refunded.

Your system should still track every retry attempt carefully so you do not accidentally duplicate customer orders.

---

## 6. Network Codes

Use these network values when working with plans and orders:

| Network Name | API Network Code |
|---|---|
| MTN Ghana | `mtn` |
| AirtelTigo | `airteltigo` |
| Telecel Ghana | `telecel` |

The documentation also mentions `express` and `bigtime` as possible network filters, but the main Ghana mobile networks listed here are MTN, AirtelTigo, and Telecel.

---

## 7. Data Bundle Pricing

Prices can change, so do not hardcode prices permanently in your system.

Use `GET /plans` regularly to fetch the current active plans and prices. You may store a local cached copy in your database, but always treat ResellerXpress as the source of truth for active dealer API prices.

---

### 7.1 AirtelTigo Pricing

**Network Code:** `airteltigo`

| Bundle | Volume | API Price |
|---|---:|---:|
| 1GB | 1 GB | GH₵5.80 |
| 2GB | 2 GB | GH₵9.60 |
| 3GB | 3 GB | GH₵13.50 |
| 4GB | 4 GB | GH₵17.30 |
| 5GB | 5 GB | GH₵21.20 |
| 6GB | 6 GB | GH₵25.00 |
| 7GB | 7 GB | GH₵29.00 |
| 8GB | 8 GB | GH₵32.80 |
| 10GB | 10 GB | GH₵40.30 |
| 15GB | 15 GB | GH₵59.00 |
| 20GB | 20 GB | GH₵78.00 |

---

### 7.2 MTN Pricing

**Network Code:** `mtn`

| Bundle | Volume | API Price |
|---|---:|---:|
| 1GB | 1 GB | GH₵4.00 |
| 2GB | 2 GB | GH₵8.75 |
| 3GB | 3 GB | GH₵13.30 |
| 4GB | 4 GB | GH₵17.00 |
| 5GB | 5 GB | GH₵20.90 |
| 6GB | 6 GB | GH₵24.80 |
| 8GB | 8 GB | GH₵32.50 |
| 10GB | 10 GB | GH₵39.80 |
| 15GB | 15 GB | GH₵58.00 |
| 20GB | 20 GB | GH₵77.00 |
| 25GB | 25 GB | GH₵96.50 |
| 30GB | 30 GB | GH₵116.50 |
| 40GB | 40 GB | GH₵154.50 |
| 50GB | 50 GB | GH₵185.50 |
| 100GB | 100 GB | GH₵360.00 |

---

### 7.3 Telecel Pricing

**Network Code:** `telecel`

| Bundle | Volume | API Price |
|---|---:|---:|
| 10GB | 10 GB | GH₵39.00 |
| 15GB | 15 GB | GH₵55.00 |
| 20GB | 20 GB | GH₵74.00 |
| 25GB | 25 GB | GH₵91.00 |
| 30GB | 30 GB | GH₵108.00 |
| 40GB | 40 GB | GH₵143.00 |
| 50GB | 50 GB | GH₵178.00 |
| 100GB | 100 GB | GH₵350.00 |

---

## 8. API Endpoints

---

## 8.1 Get Available Plans

Use this endpoint to retrieve all active data plans.

You must call this endpoint before placing orders because `plan_id` is required when placing an order.

### Endpoint

```http
GET /api/v1/plans
```

### Full URL

```http
GET https://resellerxpress.shop/api/v1/plans
```

### Optional Query Parameters

| Parameter | Type | Required | Description |
|---|---|---:|---|
| `network` | string | No | Filter by network. Example: `mtn`, `airteltigo`, `telecel` |

### Example Request

```bash
curl -X GET "https://resellerxpress.shop/api/v1/plans?network=mtn" \
  -H "X-API-KEY: your_api_key_here"
```

### Example Success Response

```json
[
  {
    "id": 1,
    "network": "mtn",
    "name": "1GB",
    "volume": "1",
    "volume_mb": 1,
    "price": "5.00"
  }
]
```

### Possible Responses

| Status Code | Meaning |
|---:|---|
| `200` | Success |
| `401` | Unauthorized or invalid API key |

### Implementation Notes

- Store the returned `id` as `provider_plan_id` in your database.
- Display your own selling price to customers, not necessarily the dealer API price.
- Keep a snapshot of the provider price at the time of order.
- Refresh plans regularly because plan IDs, prices, and availability can change.

---

## 8.2 Place Order

Use this endpoint to place a data bundle order.

The order is queued and processed asynchronously. This means you should not assume the bundle has been delivered immediately after this API call returns.

### Endpoint

```http
POST /api/v1/place-order
```

### Full URL

```http
POST https://resellerxpress.shop/api/v1/place-order
```

### Request Body

| Field | Type | Required | Description |
|---|---|---:|---|
| `plan_id` | integer | Yes | Plan ID from `GET /plans` |
| `phone` | string | Yes | Recipient phone number in Ghanaian format. Example: `0551234567` |
| `request_id` | string | No, but strongly recommended | Your unique order reference for idempotency |
| `quantity` | integer | No | Number of bundles. Default is `1`, maximum is `10` |

### Example Request

```bash
curl -X POST "https://resellerxpress.shop/api/v1/place-order" \
  -H "X-API-KEY: your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "plan_id": 1,
    "phone": "0551234567",
    "request_id": "ORDER_1683123",
    "quantity": 1
  }'
```

### Example Success Response

```json
{
  "message": "Order queued for processing",
  "order": {
    "id": 1,
    "request_id": "ORDER_1683123",
    "status": "queued",
    "amount": "5.00"
  },
  "balance": "145.00"
}
```

### Possible Responses

| Status Code | Meaning | Your Action |
|---:|---|---|
| `202` | Order queued | Save provider order ID and status |
| `400` | Insufficient balance | Mark as provider balance issue; do not charge customer again |
| `409` | Duplicate request | Fetch existing order by `request_id` |
| `422` | Validation error | Fix input data before retrying |

### Idempotency Rule

Always generate and send a unique `request_id` for each customer order.

Example format:

```text
BUNDLE_<internal_order_id>_<timestamp>
```

Example:

```text
BUNDLE_9821_20260609153000
```

If your backend retries the same order because of a timeout or network error, use the same `request_id`. This prevents duplicate bundle purchases.

---

## 8.3 Check Order Status

Use this endpoint to check the current status of an order using your `request_id`.

### Endpoint

```http
GET /api/v1/order-status
```

### Full URL

```http
GET https://resellerxpress.shop/api/v1/order-status?request_id=ORDER_1683123
```

### Required Query Parameters

| Parameter | Type | Required | Description |
|---|---|---:|---|
| `request_id` | string | Yes | Your unique order reference |

### Example Request

```bash
curl -X GET "https://resellerxpress.shop/api/v1/order-status?request_id=ORDER_1683123" \
  -H "X-API-KEY: your_api_key_here"
```

### Example Success Response

```json
{
  "id": 1,
  "request_id": "ORDER_1683123",
  "phone": "0551234567",
  "network": "mtn",
  "volume": "1",
  "status": "success",
  "provider_status": "completed",
  "amount": "5.00",
  "created_at": "2025-01-29T10:30:00Z"
}
```

### Possible Responses

| Status Code | Meaning |
|---:|---|
| `200` | Success |
| `404` | Order not found |

### Implementation Notes

Use this endpoint for fallback polling even if you configure webhooks.

Recommended polling behavior:

| Time Since Order | Polling Frequency |
|---|---|
| First 2 minutes | Every 10–15 seconds |
| 2–10 minutes | Every 30–60 seconds |
| After 10 minutes | Mark as delayed and allow admin review |

---

## 8.4 List Orders

Use this endpoint to retrieve your ResellerXpress orders with filters and pagination.

### Endpoint

```http
GET /api/v1/orders
```

### Full URL

```http
GET https://resellerxpress.shop/api/v1/orders
```

### Query Parameters

| Parameter | Type | Required | Description |
|---|---|---:|---|
| `status` | string | No | Filter by `pending`, `queued`, `processing`, `success`, `failed` |
| `network` | string | No | Filter by `mtn`, `airteltigo`, `telecel`, `express`, `bigtime` |
| `phone` | string | No | Filter by recipient phone number |
| `start_date` | string | No | Start date in `YYYY-MM-DD` format |
| `end_date` | string | No | End date in `YYYY-MM-DD` format |
| `per_page` | integer | No | Results per page, maximum `100` |

### Example Request

```bash
curl -X GET "https://resellerxpress.shop/api/v1/orders?status=success&network=mtn" \
  -H "X-API-KEY: your_api_key_here"
```

### Example Success Response

```json
{
  "data": [
    {
      "id": 1,
      "request_id": "ORDER_1683123",
      "phone": "0551234567",
      "network": "mtn",
      "status": "success",
      "amount": "5.00"
    }
  ],
  "current_page": 1,
  "last_page": 3,
  "total": 42
}
```

### Implementation Notes

This endpoint is useful for:

- Admin dashboard reconciliation.
- Checking provider-side order history.
- Matching your internal orders against ResellerXpress orders.
- Investigating delayed or failed orders.

---

## 8.5 Get Wallet Balance

Use this endpoint to retrieve your current ResellerXpress wallet balance.

### Endpoint

```http
GET /api/v1/wallet-balance
```

### Full URL

```http
GET https://resellerxpress.shop/api/v1/wallet-balance
```

### Example Request

```bash
curl -X GET "https://resellerxpress.shop/api/v1/wallet-balance" \
  -H "X-API-KEY: your_api_key_here"
```

### Example Success Response

```json
{
  "id": 1,
  "user_id": 2,
  "balance": "150.50",
  "total_funded": "500.00",
  "total_spent": "349.50"
}
```

### Possible Responses

| Status Code | Meaning |
|---:|---|
| `200` | Success |
| `401` | Unauthorized or invalid API key |

### Implementation Notes

Your backend should check wallet balance regularly.

Recommended behavior:

- Warn admin when balance falls below a configured threshold.
- Pause customer orders or show “temporarily unavailable” if balance is too low.
- Never accept customer payment if you already know you cannot fulfill the order.

Recommended environment variable:

```env
RESELLERXPRESS_LOW_BALANCE_THRESHOLD=50.00
```

---

## 8.6 Get Reprocessable Orders

Use this endpoint to retrieve failed or queued orders that can be retried.

### Endpoint

```http
GET /api/v1/reprocessable
```

### Full URL

```http
GET https://resellerxpress.shop/api/v1/reprocessable
```

### Example Request

```bash
curl -X GET "https://resellerxpress.shop/api/v1/reprocessable" \
  -H "X-API-KEY: your_api_key_here"
```

### Example Success Response

```json
[
  {
    "id": 45,
    "request_id": "ORDER_1683123",
    "phone": "0551234567",
    "network": "mtn",
    "status": "failed",
    "failure_reason": "api_error",
    "can_reprocess": true,
    "retry_count": 1
  }
]
```

### Implementation Notes

Use this endpoint for admin tools and scheduled retry workers.

Your system should store:

- Provider order ID.
- Retry count.
- Failure reason.
- Last retry time.
- Whether admin manually triggered the retry.

---

## 8.7 Reprocess an Order

Use this endpoint to retry a failed or queued order.

### Endpoint

```http
POST /api/v1/reprocess/{id}
```

### Full URL Example

```http
POST https://resellerxpress.shop/api/v1/reprocess/45
```

### Path Parameters

| Parameter | Type | Required | Description |
|---|---|---:|---|
| `id` | integer | Yes | ResellerXpress order ID to reprocess |

### Example Request

```bash
curl -X POST "https://resellerxpress.shop/api/v1/reprocess/45" \
  -H "X-API-KEY: your_api_key_here"
```

### Example Success Response

```json
{
  "message": "Order re-queued for processing",
  "order": {
    "id": 45,
    "status": "queued"
  }
}
```

### Possible Responses

| Status Code | Meaning |
|---:|---|
| `202` | Order re-queued |
| `400` | Reprocess failed |

### Implementation Notes

Do not allow unlimited retries.

Recommended retry rules:

| Condition | Recommended Action |
|---|---|
| First failure due to API error | Auto-retry once |
| Repeated failure | Send to admin review |
| Dealer balance issue | Check wallet before retry |
| Customer asks for help | Show clear status and support message |

---

## 8.8 Configure Webhook

Use this endpoint to configure your webhook URL for real-time order updates.

### Endpoint

```http
POST /api/v1/webhook
```

### Full URL

```http
POST https://resellerxpress.shop/api/v1/webhook
```

### Request Body

| Field | Type | Required | Description |
|---|---|---:|---|
| `url` | string | Yes | Your webhook endpoint URL |
| `enabled` | boolean | Yes | Enable or disable webhook |
| `events` | array | Yes | Events to subscribe to |

### Supported Events

From the documentation example:

```json
["order_success", "order_failed"]
```

### Example Request

```bash
curl -X POST "https://resellerxpress.shop/api/v1/webhook" \
  -H "X-API-KEY: your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://yourapp.com/webhooks/resellerxpress",
    "enabled": true,
    "events": ["order_success", "order_failed"]
  }'
```

### Example Success Response

```json
{
  "id": 1,
  "url": "https://yourapp.com/webhooks",
  "enabled": true,
  "events": [
    "order_success",
    "order_failed"
  ]
}
```

### Webhook Endpoint Recommendation

Use a dedicated backend route like:

```http
POST /api/webhooks/resellerxpress
```

### Webhook Handling Rules

Your webhook handler should:

1. Accept the payload.
2. Log the full webhook event safely.
3. Find the internal order using `request_id` or provider order ID.
4. Update the internal order status.
5. Notify the customer if the status is final.
6. Return a fast `200 OK` response.

Do not run heavy processing directly inside the webhook request. Save the event first, then process it in a background job if needed.

---

## 9. Recommended Internal Database Tables

Below is a practical database structure for your own platform.

---

## 9.1 `bundle_plans`

Stores local copies of ResellerXpress plans.

```sql
CREATE TABLE bundle_plans (
    id BIGSERIAL PRIMARY KEY,
    provider VARCHAR(50) NOT NULL DEFAULT 'resellerxpress',
    provider_plan_id BIGINT NOT NULL,
    network VARCHAR(50) NOT NULL,
    name VARCHAR(100) NOT NULL,
    volume VARCHAR(50),
    provider_price NUMERIC(12, 2) NOT NULL,
    selling_price NUMERIC(12, 2) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_synced_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(provider, provider_plan_id)
);
```

### Notes

- `provider_price` is your ResellerXpress API cost.
- `selling_price` is what your customer pays you.
- You can set profit margins per network or per plan.

---

## 9.2 `bundle_orders`

Stores all customer orders.

```sql
CREATE TABLE bundle_orders (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT,
    provider VARCHAR(50) NOT NULL DEFAULT 'resellerxpress',
    provider_order_id BIGINT,
    request_id VARCHAR(120) NOT NULL UNIQUE,
    plan_id BIGINT REFERENCES bundle_plans(id),
    provider_plan_id BIGINT NOT NULL,
    network VARCHAR(50) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    provider_amount NUMERIC(12, 2),
    customer_amount NUMERIC(12, 2) NOT NULL,
    profit NUMERIC(12, 2),
    status VARCHAR(30) NOT NULL DEFAULT 'pending',
    provider_status VARCHAR(100),
    failure_reason TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    payment_reference VARCHAR(120),
    paid_at TIMESTAMPTZ,
    placed_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    failed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### Recommended Internal Statuses

You may map provider statuses into your own statuses:

| Internal Status | Provider Statuses |
|---|---|
| `pending_payment` | Before customer pays |
| `paid` | Customer payment verified |
| `queued` | Provider returned `queued` |
| `processing` | Provider returned `processing` |
| `success` | Provider returned `success` |
| `failed` | Provider returned `failed` |
| `manual_review` | Too many retries or unclear provider response |

---

## 9.3 `provider_webhook_events`

Stores incoming webhook payloads.

```sql
CREATE TABLE provider_webhook_events (
    id BIGSERIAL PRIMARY KEY,
    provider VARCHAR(50) NOT NULL DEFAULT 'resellerxpress',
    event_type VARCHAR(100),
    request_id VARCHAR(120),
    provider_order_id BIGINT,
    payload JSONB NOT NULL,
    processed BOOLEAN NOT NULL DEFAULT FALSE,
    processed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### Notes

Always store webhook events before processing them. This helps with debugging, reconciliation, and support.

---

## 9.4 `wallet_snapshots`

Stores periodic ResellerXpress wallet balance checks.

```sql
CREATE TABLE wallet_snapshots (
    id BIGSERIAL PRIMARY KEY,
    provider VARCHAR(50) NOT NULL DEFAULT 'resellerxpress',
    balance NUMERIC(12, 2) NOT NULL,
    total_funded NUMERIC(12, 2),
    total_spent NUMERIC(12, 2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

## 10. Recommended Backend Service Design

Create a dedicated service/module for ResellerXpress.

Example folder structure:

```text
backend/
  app/
    services/
      resellerxpress_service.py
    api/
      routes/
        bundle_orders.py
        webhooks.py
    models/
      bundle_plan.py
      bundle_order.py
      provider_webhook_event.py
    workers/
      sync_bundle_plans.py
      check_pending_orders.py
      retry_failed_orders.py
```

---

## 11. ResellerXpress Service Responsibilities

Your `ResellerXpressService` should handle:

- Adding the `X-API-KEY` header.
- Calling `GET /plans`.
- Calling `POST /place-order`.
- Calling `GET /order-status`.
- Calling `GET /wallet-balance`.
- Calling `GET /reprocessable`.
- Calling `POST /reprocess/{id}`.
- Handling HTTP errors.
- Handling provider timeouts.
- Normalizing provider responses.

---

## 12. Example Python Service

```python
import os
import httpx
from typing import Any, Dict, Optional


class ResellerXpressError(Exception):
    pass


class ResellerXpressService:
    def __init__(self) -> None:
        self.base_url = os.getenv("RESELLERXPRESS_BASE_URL", "https://resellerxpress.shop/api/v1")
        self.api_key = os.getenv("RESELLERXPRESS_API_KEY")

        if not self.api_key:
            raise ResellerXpressError("RESELLERXPRESS_API_KEY is not configured")

        self.headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json",
        }

    async def get_plans(self, network: Optional[str] = None) -> Any:
        params = {}
        if network:
            params["network"] = network

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{self.base_url}/plans",
                headers=self.headers,
                params=params,
            )
        return self._handle_response(response)

    async def place_order(
        self,
        plan_id: int,
        phone: str,
        request_id: str,
        quantity: int = 1,
    ) -> Dict[str, Any]:
        payload = {
            "plan_id": plan_id,
            "phone": phone,
            "request_id": request_id,
            "quantity": quantity,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/place-order",
                headers=self.headers,
                json=payload,
            )
        return self._handle_response(response)

    async def get_order_status(self, request_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{self.base_url}/order-status",
                headers=self.headers,
                params={"request_id": request_id},
            )
        return self._handle_response(response)

    async def get_wallet_balance(self) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{self.base_url}/wallet-balance",
                headers=self.headers,
            )
        return self._handle_response(response)

    async def get_reprocessable_orders(self) -> Any:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{self.base_url}/reprocessable",
                headers=self.headers,
            )
        return self._handle_response(response)

    async def reprocess_order(self, provider_order_id: int) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/reprocess/{provider_order_id}",
                headers=self.headers,
            )
        return self._handle_response(response)

    def _handle_response(self, response: httpx.Response) -> Any:
        try:
            data = response.json()
        except ValueError:
            data = {"raw": response.text}

        if response.status_code >= 400:
            raise ResellerXpressError(
                f"ResellerXpress API error {response.status_code}: {data}"
            )

        return data
```

---

## 13. Recommended Customer Order Flow

### Step 1: Customer Selects Bundle

The customer chooses:

- Network: MTN, AirtelTigo, or Telecel.
- Bundle volume: for example, 1GB, 5GB, 10GB.
- Recipient phone number.

Your frontend should show your own selling price.

---

### Step 2: Backend Creates Pending Order

Create a local order with status:

```text
pending_payment
```

At this point, do not call ResellerXpress yet.

---

### Step 3: Customer Pays You

The customer pays through your own payment provider.

Examples:

- Paystack
- Flutterwave
- Hubtel
- Mobile Money integration
- Manual wallet balance inside your own app

---

### Step 4: Verify Payment

Only proceed after your backend verifies that payment was successful.

Never trust only the frontend payment success screen.

---

### Step 5: Place Order with ResellerXpress

Generate a unique `request_id` and call:

```http
POST /api/v1/place-order
```

Save these returned values:

- ResellerXpress order ID.
- ResellerXpress status.
- Provider amount.
- Remaining wallet balance if returned.

---

### Step 6: Update Customer Order Status

If ResellerXpress returns `queued`, mark your internal order as:

```text
queued
```

Tell the customer:

```text
Your data bundle order has been received and is being processed.
```

---

### Step 7: Wait for Webhook or Poll Status

Use webhooks for real-time updates.

Also keep polling as backup because webhook delivery can fail.

---

### Step 8: Finalize Order

If status becomes `success`:

- Mark internal order as `success`.
- Send customer success notification.
- Record profit.

If status becomes `failed`:

- Mark internal order as `failed`.
- Allow retry or admin review.
- Decide whether to refund customer based on your business policy.

---

## 14. Webhook Implementation Example

```python
from fastapi import APIRouter, Request, HTTPException

router = APIRouter()


@router.post("/webhooks/resellerxpress")
async def resellerxpress_webhook(request: Request):
    payload = await request.json()

    # 1. Store the raw payload first.
    # 2. Extract request_id and status from payload.
    # 3. Find the local bundle order.
    # 4. Update the order status.
    # 5. Return 200 quickly.

    return {"received": True}
```

### Webhook Security Notes

The provided documentation does not show a webhook signature verification method.

Because of that, you should add your own protection where possible:

- Use a private, hard-to-guess webhook URL.
- Add a secret query parameter if ResellerXpress allows it.
- Restrict accepted methods to `POST` only.
- Log all webhook payloads.
- Do not trust webhook updates blindly if they look invalid.
- Use `GET /order-status` to verify suspicious webhook events.

Example webhook URL with your own secret:

```text
https://yourdomain.com/api/webhooks/resellerxpress?secret=your_internal_webhook_secret
```

---

## 15. Phone Number Validation

The API example uses Ghanaian local format:

```text
0551234567
```

Recommended validation rules:

- Accept only Ghana phone numbers.
- Remove spaces and dashes.
- Normalize numbers before sending to ResellerXpress.
- Confirm the network if your app allows customer-selected network.

Example accepted formats:

```text
0551234567
233551234567
+233551234567
```

Recommended normalized format for the provider:

```text
0551234567
```

### Important

If the customer selects MTN but enters a Telecel number, the order may fail or deliver incorrectly depending on provider behavior.

Use a Ghana phone number prefix map to reduce mistakes, but also allow manual correction because number portability can make prefix-based detection imperfect.

---

## 16. Profit Calculation

Your profit is:

```text
customer_selling_price - provider_api_price - payment_processing_fee
```

Example:

```text
Customer pays: GH₵5.00
Provider cost: GH₵4.00
Payment fee: GH₵0.10
Profit: GH₵0.90
```

Recommended fields to store per order:

- `provider_amount`
- `customer_amount`
- `payment_fee`
- `profit`
- `network`
- `volume`
- `status`

---

## 17. Admin Dashboard Requirements

Your admin dashboard should include:

### Orders Page

Show:

- Customer phone number.
- Network.
- Bundle.
- Customer price.
- Provider cost.
- Profit.
- Status.
- Request ID.
- Provider order ID.
- Created time.
- Completed time.
- Retry count.

### Wallet Page

Show:

- Current ResellerXpress wallet balance.
- Total funded.
- Total spent.
- Low-balance warning.
- Last balance check time.

### Reprocess Page

Show:

- Failed orders.
- Queued orders.
- Failure reason.
- Retry count.
- Manual retry button.

### Plans Page

Show:

- Network.
- Bundle name.
- Provider price.
- Your selling price.
- Profit margin.
- Active/inactive status.
- Last sync time.

---

## 18. Error Handling Rules

| Situation | Recommended Backend Action | Customer Message |
|---|---|---|
| Invalid API key | Alert admin immediately | “Service temporarily unavailable” |
| Provider wallet low | Pause order or send to admin review | “Order is pending processing” |
| Customer payment failed | Do not call provider API | “Payment failed. Please try again.” |
| Provider timeout | Check status using same `request_id` before retrying | “Order is being confirmed” |
| Duplicate request ID | Fetch existing provider order | “Order already exists and is being processed” |
| Provider failed order | Mark failed and optionally reprocess | “Order failed. We are reviewing it.” |
| Webhook missing | Use polling fallback | No customer-facing issue unless delayed |

---

## 19. Background Jobs You Should Build

### 19.1 Sync Plans Job

Runs every few hours.

Purpose:

- Fetch active plans from `GET /plans`.
- Update local plan prices.
- Disable missing plans if needed.
- Alert admin if prices changed.

---

### 19.2 Pending Order Checker

Runs every few minutes.

Purpose:

- Find internal orders with `queued` or `processing` status.
- Call `GET /order-status`.
- Update local order status.

---

### 19.3 Wallet Balance Checker

Runs every 5–15 minutes.

Purpose:

- Call `GET /wallet-balance`.
- Store wallet snapshot.
- Alert admin if balance is low.

---

### 19.4 Failed Order Retry Worker

Runs on a controlled schedule.

Purpose:

- Fetch reprocessable orders.
- Retry safe failures.
- Stop after configured retry limit.
- Send repeated failures to manual review.

---

## 20. Testing Checklist

Before launching, test the following:

### Authentication

- Invalid API key returns `401`.
- Valid API key can fetch plans.

### Plans

- Fetch all plans.
- Fetch only MTN plans.
- Fetch only AirtelTigo plans.
- Fetch only Telecel plans.
- Store provider plan IDs correctly.

### Orders

- Place order with valid phone and plan.
- Place order with invalid phone.
- Place order with invalid plan ID.
- Place order with insufficient provider wallet balance.
- Retry same request with same `request_id`.
- Confirm duplicate request does not create duplicate customer order.

### Status

- Check status for existing order.
- Check status for non-existing `request_id`.
- Confirm `success` updates internal order correctly.
- Confirm `failed` updates internal order correctly.

### Webhook

- Configure webhook URL.
- Receive success webhook.
- Receive failed webhook.
- Store raw webhook payload.
- Ignore webhook for unknown order.

### Reprocess

- Fetch reprocessable orders.
- Retry failed order.
- Retry queued order.
- Stop retries after max retry count.

### Wallet

- Fetch wallet balance.
- Trigger low-balance alert.
- Prevent new orders when balance is too low if that is your business rule.

---

## 21. Production Safety Rules

Follow these rules before going live:

1. Keep the ResellerXpress API key only on the backend.
2. Use HTTPS for your backend and webhook URL.
3. Verify customer payment before calling `POST /place-order`.
4. Always use a unique `request_id`.
5. Store provider responses for audit/debugging.
6. Never assume `202` means success; it only means queued.
7. Use webhooks and polling together.
8. Keep enough ResellerXpress wallet balance.
9. Add admin tools for failed and queued orders.
10. Set retry limits to avoid duplicate or repeated charges.
11. Keep a price snapshot for every order.
12. Reconcile provider orders with your internal orders daily.

---

## 22. Recommended Environment Variables

```env
RESELLERXPRESS_BASE_URL=https://resellerxpress.shop/api/v1
RESELLERXPRESS_API_KEY=your_api_key_here
RESELLERXPRESS_LOW_BALANCE_THRESHOLD=50.00
RESELLERXPRESS_WEBHOOK_SECRET=your_internal_webhook_secret
RESELLERXPRESS_MAX_RETRIES=2
```

---

## 23. Recommended Internal API Endpoints for Your App

These are endpoints you can expose from your own backend.

```http
GET /api/bundles/plans
POST /api/bundles/orders
GET /api/bundles/orders/{id}
GET /api/admin/bundles/orders
POST /api/admin/bundles/orders/{id}/retry
GET /api/admin/bundles/wallet
POST /api/webhooks/resellerxpress
```

### Public Customer Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/bundles/plans` | Show available bundles to customers |
| `POST /api/bundles/orders` | Create customer order after payment flow starts |
| `GET /api/bundles/orders/{id}` | Let customer check order status |

### Admin Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/admin/bundles/orders` | View all orders |
| `POST /api/admin/bundles/orders/{id}/retry` | Retry failed/queued order |
| `GET /api/admin/bundles/wallet` | View provider wallet balance |

### Webhook Endpoint

| Endpoint | Purpose |
|---|---|
| `POST /api/webhooks/resellerxpress` | Receive ResellerXpress order notifications |

---

## 24. Recommended Launch Flow

Use this order when building the integration:

1. Add environment variables.
2. Build `ResellerXpressService`.
3. Build `GET /plans` sync.
4. Create `bundle_plans` table.
5. Build customer bundle listing page.
6. Build payment collection flow.
7. Create `bundle_orders` table.
8. After payment verification, call `POST /place-order`.
9. Build order-status polling.
10. Configure webhook.
11. Build admin order dashboard.
12. Build wallet balance checker.
13. Build retry/reprocess logic.
14. Test end-to-end with small orders.
15. Launch with monitoring and manual review enabled.

---

## 25. Minimum Viable Integration

If you want the simplest working version first, build only this:

1. `GET /plans` to fetch bundles.
2. Customer selects bundle and pays.
3. Backend verifies payment.
4. Backend calls `POST /place-order`.
5. Backend stores `request_id`, provider order ID, and status.
6. Backend checks `GET /order-status` until final status.
7. Admin manually handles failed orders.

After that works, add:

- Webhooks.
- Wallet checker.
- Auto-retry.
- Admin dashboard.
- Price sync alerts.

---

## 26. Final Recommended Implementation Logic

The most important rule is this:

```text
Do not call ResellerXpress until the customer's payment is verified.
```

Then use this backend logic:

```text
1. Customer pays you.
2. Verify payment on backend.
3. Generate unique request_id.
4. Create internal bundle order.
5. Call ResellerXpress /place-order.
6. Save provider response.
7. Show customer “processing”.
8. Wait for webhook or poll /order-status.
9. If success, mark completed.
10. If failed, retry or send to admin review.
```

This keeps your platform safe from duplicate orders, unpaid orders, leaked API keys, and provider-side delays.

---

## 27. Source Notes

This document is based on the ResellerXpress API v1.0 details provided for the integration, including:

- Base URL: `https://resellerxpress.shop/api/v1`
- Authentication via `X-API-KEY`
- Plans endpoint
- Place order endpoint
- Order status endpoint
- List orders endpoint
- Wallet balance endpoint
- Reprocess endpoints
- Webhook configuration endpoint
- Current listed dealer API prices for MTN, AirtelTigo, and Telecel

Because bundle prices and availability may change, the production app should always use `GET /api/v1/plans` as the live source of truth.
