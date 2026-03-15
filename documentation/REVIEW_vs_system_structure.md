# Review: Project vs system_structure.md

## What matches the doc

| Doc section | Your implementation | Status |
|-------------|---------------------|--------|
| **Payment flow** | Order creation → Paystack init → redirect | OK |
| **Webhook** | `charge.success` → bundle delivery | OK |
| **GHDataConnect** | `createIshareBundleOrder`, `getWalletBalance`, `checkOrderStatus` | OK |
| **Wallet check** | Balance checked before sending bundle | OK |
| **Order status after delivery** | `order.status = completed/failed` from `result.get("success")` | OK |
| **Idempotent webhook** | `payment_status == "completed"` → return "already processed" | OK |
| **Order status endpoint** | `GET /orders/{reference}` with optional `?refresh=true` | OK |
| **Unique reference** | UUID in `generate_reference()` | OK |
| **Database: Orders** | id, reference, phone_number, network, capacity, price, status, created_at | OK (no `user_id`) |

---

## Gaps and issues

### 1. Paystack webhook signature verification (security – doc §12) — FIXED

- **Doc:** “Always verify Paystack webhook signatures to prevent fraud.”
- **Current:** Webhook now verifies `x-paystack-signature` using HMAC-SHA512 of the raw body and returns 401 if invalid.

---

### 2. Webhook URL path (doc §5) — FIXED

- **Doc:** `POST /webhooks/paystack`
- **Current:** Webhook router is mounted with `prefix="/webhooks"`, so the route is **`POST /webhooks/paystack`**.
- **Action:** In Paystack Dashboard → Settings → Webhooks, set the URL to `https://your-domain.com/webhooks/paystack`.

---

### 3. Wallet balance type (doc §7) — FIXED

- **Doc:** `"data": { "balance": "207.46" }` (string).
- **Current:** `get_wallet_balance()` now coerces balance to `float` so comparisons with `bundle_cost` are safe.

---

### 4. Bundle discovery from GHDataConnect (doc §9)

- **Doc:** Use `GET /v1/getAllNetworks` to get networks and bundles (name, key, bundles with capacity, price).
- **Current:** `GET /bundles` uses a hardcoded list from `NETWORK_PRICES` and `BUNDLE_CAPACITIES`.
- **Impact:** Your catalog is static; price/catalog changes from GHDataConnect are not reflected.
- **Fix (optional):** Add a GHDataConnect `get_all_networks()` and use it for `/bundles`, or keep static list and document the choice.

---

### 5. Database: Users and Transactions (doc §10)

- **Doc:** Recommends **Users** (id, email, phone, created_at) and **Transactions** (id, reference, payment_gateway, payment_status, amount, created_at).
- **Current:** No `User` model; no separate `Transaction` model; payment info lives on `Order` (e.g. `payment_status`).
- **Impact:** Fine for MVP; you give up user history and a clear payment audit trail.
- **Fix (optional):** Add `User` and `Transaction` when you need user accounts or stricter payment reporting.

---

### 6. Order price vs selling price (doc: “sell at higher prices for profit”)

- **Doc:** “Your platform can sell bundles at higher prices for profit.”
- **Current:** Backend uses `calculate_selling_price()` (cost + markup, same tiers as frontend) for `order.price` and Paystack amount. `/bundles` returns base cost; frontend adds markup for display; the amount charged matches the frontend display.

---

### 7. Error handling and logging

- **Doc:** Backend should manage orders and log transactions.
- **Current:** Basic logging; no explicit handling for Paystack init failure or GHDataConnect errors (e.g. network/timeout).
- **Improvement:** Log errors; on Paystack init failure return a clear message and do not mark order as paid; on GHDataConnect failure consider retry or clear `order.status = "failed"` and alerting.

---

### 8. CORS for frontend — FIXED

- **Doc:** Frontend and backend are separate.
- **Current:** CORS middleware added in `main.py` for `127.0.0.1:5500`, `localhost:5500`, and common dev ports so the frontend can call the API.

---

## Summary checklist

| Item | Priority | Status |
|------|----------|--------|
| Verify Paystack webhook signature | High (security) | **Done** |
| Coerce wallet balance to float | High (correctness) | **Done** |
| Charge selling price (markup), not cost | High (business) | **Done** |
| CORS for frontend | High (works end-to-end) | **Done** |
| Webhook path `/webhooks/paystack` | Low | **Done** (set Paystack URL to `/webhooks/paystack`) |
| Bundle discovery from GHDataConnect | Low | Optional |
| Users + Transactions tables | Low | Optional |
| Stronger error handling and logging | Medium | Partial |

**Frontend:** Ensure your Paystack webhook URL is `https://<your-domain>/webhooks/paystack`. Selling price is computed on the backend (same markup tiers as the frontend) when creating an order and charging Paystack.
