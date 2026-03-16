# Bundle delivery – troubleshooting checklist

When **Payment = completed** but **Status = failed** and GH Data Connect never shows the order, use this checklist. The webhook runs after Paystack confirms payment; it checks wallet balance then sends the bundle to the provider.

---

## 0. Test locally without real payment

To test that the request is sent to GH Connect **without** deducting real money from Paystack:

1. **Create an order** (frontend or API) so you have a reference. You can stop before completing Paystack—just get the order reference from the response or from the DB.
2. In **.env** set: `ALLOW_WEBHOOK_SIMULATE=true` (do **not** set this on Render/production).
3. Start the backend: `uvicorn app.main:app --reload`.
4. Trigger the same logic as “payment completed”:
   ```bash
   curl -X POST "http://127.0.0.1:8000/webhooks/simulate-success" -H "Content-Type: application/json" -d "{\"reference\": \"YOUR_ORDER_REFERENCE\"}"
   ```
   Or with query param: `curl -X POST "http://127.0.0.1:8000/webhooks/simulate-success?reference=YOUR_ORDER_REFERENCE"`
5. Check the terminal logs: you should see wallet request, then createOrder request/response. Check GH Connect portal to see if the order appeared.

With `ALLOW_WEBHOOK_SIMULATE` unset or false, `POST /webhooks/simulate-success` returns 403.

---

## 1. Confirm GH Data Connect API config (Render / .env)


| Variable            | Required | Where to get it                          | Example                                             |
| ------------------- | -------- | ---------------------------------------- | --------------------------------------------------- |
| **GHDATA_BASE_URL** | Yes      | Portal → API Documentation               | `https://ghdataconnect.com/api` (no trailing slash) |
| **GHDATA_API_KEY**  | Yes      | Portal → Profile → generate Bearer token | Your token string only (we add `Bearer` in code)    |


- Both must be set on **Render** (Environment) for the web service.
- No spaces or quotes around values.
- Redeploy after changing env vars.

---

## 2. Check Render logs for this order

After a test payment, open **Render → your backend service → Logs** and search for your order reference (e.g. `cbc0bcd5-f903-40dc-9906-87525b0a13b4`). You should see one of these patterns.

### A. Wallet request and balance

- `**Bundle provider wallet request: https://ghdataconnect.com/api/v1/getWalletBalance`**  
Confirms we’re calling the right URL.
- `**Order ...: wallet balance=X.XX cost=Y.YY**`  
Wallet check succeeded; balance and bundle cost are logged.
- `**Order ...: wallet check failed (API error or bad URL/key). Attempting bundle send anyway.**`  
Wallet API failed (wrong URL, wrong key, or timeout). We still try to send the bundle; check the next log line for the createOrder result.

### B. Create order request and response

- `**Bundle provider createOrder: url=... payload={...}**`  
Confirms we’re calling the create-order endpoint with the right payload.
- `**Bundle provider createOrder response HTTP 200: { "success": true, ... }**`  
Provider accepted the order → status should turn **completed**.
- `**Bundle provider createOrder response HTTP 401: ...`**  
Unauthorized → wrong or expired API key. Regenerate token in Profile and update **GHDATA_API_KEY**.
- `**Bundle provider createOrder response HTTP 404: ...`**  
Endpoint not found → wrong base URL or path. Confirm in their docs: base URL and exact path for “create order” / “create bundle”.
- `**Bundle provider createOrder response HTTP 4xx/5xx: ...**`  
Read the response body in the log; it usually explains validation or server error.

### C. Final status

- `**Order ...: bundle sent successfully**` → Status should be **completed** and order visible on GH Data Connect.
- `**Order ...: bundle delivery failed: <message>`** → Use the message and the HTTP response in the log to fix (key, URL, payload, or capacity unit).

---

## 3. Common causes and fixes


| Symptom                                                             | Likely cause                          | Fix                                                                                                                                                                       |
| ------------------------------------------------------------------- | ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Logs: **wallet check failed** and **createOrder response HTTP 401** | Wrong or missing API key              | Set **GHDATA_API_KEY** to the Bearer token from Portal → Profile. Redeploy.                                                                                               |
| Logs: **wallet request** then **wallet request failed** or timeout  | Wrong base URL or network             | Set **GHDATA_BASE_URL** to `https://ghdataconnect.com/api`. If it still fails, confirm with provider.                                                                     |
| Logs: **createOrder response HTTP 404**                             | Wrong create-order path               | Our code uses `POST /v1/createIshareBundleOrder`. If their docs show a different path, we need to update the code.                                                        |
| Logs: **createOrder response HTTP 400** and message about field     | Wrong payload format                  | We send `{ "reference", "msisdn", "capacity" }`. Confirm in their API docs; e.g. if they want **capacity in GB** (1, 2) instead of MB (1000, 2000), we’d need to convert. |
| Logs: **insufficient wallet balance**                               | Real low balance on provider wallet   | Top up the dealer/agent wallet in the GH Data Connect portal.                                                                                                             |
| No webhook logs for this reference                                  | Paystack webhook not reaching backend | In Paystack dashboard set Webhook URL to `https://<your-render-url>/webhooks/paystack`. Ensure backend is deployed and URL is reachable.                                  |
| **Invalid signature** in logs                                       | Paystack webhook secret mismatch      | Use the **same** Paystack secret (live/test) in **PAYSTACK_SECRET_KEY** as the one used for the payment.                                                                  |


---

## 4. API reference (from your docs)

- **Base URL:** `https://ghdataconnect.com/api`
- **Auth:** `Authorization: Bearer <token>` (token from Profile).
- **Get Wallet Balance:** `GET /v1/getWalletBalance` → `{ "success": true, "data": { "balance": "207.46" } }`.
- **Check Order Status:** `GET /v1/checkOrderStatus/:reference`.
- **Create order:** We use `POST /v1/createIshareBundleOrder` with body `{ "reference", "msisdn", "capacity" }` (capacity in MB). If their docs show a different path or body, the code must be aligned.

---

## 5. After fixing

1. Set correct **GHDATA_BASE_URL** and **GHDATA_API_KEY** on Render.
2. Redeploy the backend.
3. Run a **new** test payment (old orders stay failed).
4. Check Render logs for that reference and confirm you see either **bundle sent successfully** or a clear error message/HTTP code to fix next.

