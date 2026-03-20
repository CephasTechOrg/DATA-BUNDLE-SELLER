# Manual fulfillment migration checklist (no GH Data Connect)

## Overview
This checklist migrates the system from **automatic bundle delivery** (via GH Data Connect) to **manual fulfillment by admin**, while keeping:
- Paystack payment initialization
- Paystack webhook verification (`charge.success`)
- Order creation + admin visibility

After migration:
1. Customer pays via Paystack.
2. Paystack webhook marks the order as `payment_status=completed`.
3. The system **does NOT** call GH Data Connect for wallet/bundle delivery.
4. Admin manually delivers the bundle from their GH Data Connect portal (outside your backend).
5. Admin marks the order `status=completed` or `status=failed`.
6. Admin has a **History** view for fulfilled outcomes (completed/failed).

## Current state (important)
Today, the webhook handler does:
- verify Paystack signature
- on `charge.success`: mark `payment_status=completed`
- then check GH wallet + send bundle automatically
- then set `order.status` based on provider response

Manual mode means you must stop the GH wallet + send-bundle steps entirely, otherwise:
- orders can incorrectly become `failed` due to missing/invalid GH config
- you continue consuming/charging your reseller wallet automatically

## Definitions (use these exact values)
In the DB model:
- `order.payment_status` is `pending | completed`
- `order.status` is `pending | completed | failed`

Manual fulfillment rules:
- After webhook: `payment_status=completed` AND `status=pending`
- Admin action:
  - set `status=completed` when delivery was successfully done manually
  - set `status=failed` when delivery failed manually
- `payment_status` should not change again after it becomes `completed`

## Phase 1 — Webhook: remove GH calls, keep only state changes

### 1.1 Update the payment-success handler
File to check/update: `app/routers/webhooks.py`

In the shared function that processes `charge.success` (currently `_process_payment_success`), ensure on successful Paystack charge you:
- fetch the `Order` by `reference`
- keep idempotency: if already processed (`payment_status == completed`), return early
- set:
  - `order.payment_status = "completed"`
  - `order.status = "pending"` (awaiting manual fulfillment)
- commit and return
- do **NOT** call:
  - `get_wallet_balance()`
  - `send_bundle()`
  - any GH Data Connect functions

### 1.2 Confirm webhook won’t mark orders failed due to missing GH config
Your current GH service raises `ValueError` when `GHDATA_BASE_URL` or `GHDATA_API_KEY` are missing.
The existing webhook handler catches `ValueError` and can set `status="failed"`.

Manual mode checklist:
- After implementing “no GH calls”, `POST /webhooks/paystack` must never reach the GH code path.
- Verification:
  - backend logs for a payment should NOT contain:
    - `Bundle provider wallet request`
    - `createOrder request`
    - any GH provider URL patterns

### 1.3 Keep signature verification unchanged
Do not modify `_verify_paystack_signature` logic.
Manual migration should not weaken webhook security.

## Phase 2 — Admin API: add endpoint to mark fulfillment outcome

## (Required) Before enabling claim/lock in the UI
1. Run the DB migration to add locking columns:
   - `python scripts/add_order_claim_fields.py`
2. Restart the backend so the updated `Order` model is used.

### 2.1 Add protected route for admin fulfillment actions
File(s) to update: `app/routers/admin.py` (and auth is already present)

Add a protected endpoint such as:
- `PATCH /admin/orders/{reference}/status`

Recommended additional endpoints:
- `POST /admin/orders/{reference}/claim` (atomic claim for multi-admin safety)
- `DELETE /admin/orders/{reference}` (delete pending paid orders from the queue)

Request body (example):
```json
{ "status": "completed", "note": "optional" }
```

Backend rules checklist:
- `Order.reference` must exist
- only allow transitions to `completed`/`failed` when:
  - `order.payment_status == "completed"`
  - current `order.status == "pending"` (optional but recommended to prevent re-fulfillment)
- and the order must be claimed by the calling admin (prevents multiple admins from fulfilling the same paid order)
- do not update `payment_status` in this endpoint
- commit and return updated order fields needed by the UI (at least `reference`, `status`, `payment_status`, `created_at`)

### 2.2 Consider admin action idempotency
Optional but recommended:
- If admin marks the same order to the same final status multiple times, it should be safe.

## Phase 3 — Admin UI: Orders queue, actions, History view

### 3.1 Update Orders tab to support manual fulfillment
File to update: `admin/app.js` (UI logic)

UI checklist:
- Orders queue should show only:
  - `payment_status === "completed"`
  - `status === "pending"`
- Add per-row actions with claim/lock UI:
  - if `claimed_by` is empty: show `Claim` (and optionally `Delete`)
  - if `claimed_by` belongs to the current admin token: show `Mark Completed` / `Mark Failed`
  - if `claimed_by` belongs to another admin: show a visual `Locked` state and disable actions
- When action is performed:
  - call backend fulfillment endpoint
  - refresh orders list

Visual/state checklist:
- “Awaiting fulfillment” should be recognizable even though backend `status` remains `pending`.
- Avoid misleading badges that treat `pending` as “payment pending”.
  - Suggested UI label rule (implementation detail): when `payment_status=completed` and `status=pending`, show “Paid - Awaiting Fulfillment”.

### 3.2 Add History tab/section
No history exists today in admin UI.

History checklist:
- add a new tab or section named `History`
- default filter:
  - `payment_status = completed`
  - `status in (completed, failed)`
- show columns that help manual reconciliation:
  - `reference`, `network`, `capacity`, `price`
  - `phone_number`
  - `payment_status`, `status`
  - `created_at`

### 3.3 Ensure CSV export matches the admin workflow
If you keep “Export CSV” from Orders tab:
- include fulfillment actions state (payment_status + status)
- consider separate CSV export for History if that’s easier for ops

## Phase 4 — Customer status behavior (optional but recommended)
Your customer-facing modal already shows `payment_status` and `status`.

Customer UX checklist:
- After webhook, customer may see `Status = pending`.
- Recommended copy:
  - Payment confirmed; delivery is being handled manually by admin.

This reduces confusion while keeping backend logic correct.

## Phase 5 — Environment and config cleanup

### 5.1 Make GH provider env optional (for runtime)
After removing GH calls from the webhook:
- you should be able to run without `GHDATA_BASE_URL` and `GHDATA_API_KEY`

Checklist:
- run a full payment test in a “GH env not set” environment and confirm:
  - `payment_status` becomes `completed`
  - `status` remains `pending`

### 5.2 Keep Paystack env required
Must keep:
- `PAYSTACK_SECRET_KEY`
- `DATABASE_URL`
- `ADMIN_USERNAME` / `ADMIN_PASSWORD`

### 5.3 Ensure webhook simulate remains local-only
Keep `ALLOW_WEBHOOK_SIMULATE` enabled only for development/testing.

## End-to-end testing checklist (order matters)

### Test A — Webhook state change (without GH env)
1. Start backend locally with Paystack + DB configured.
2. Ensure GH env vars are NOT set (or set to invalid values).
3. Create a real order and get a `reference`.
4. Trigger webhook processing (for example using your existing simulate endpoint in local dev).
5. Verify in DB/admin:
   - `payment_status == completed`
   - `status == pending`
6. Verify logs show:
   - Paystack webhook processed successfully
   - no GH wallet/send requests occurred

### Test B — Admin fulfillment actions
1. Admin logs in successfully.
2. Find the paid order in Orders queue.
3. Click `Mark Completed`.
4. Verify:
   - `status == completed`
   - History shows it in the completed list
5. Repeat with `Mark Failed` and verify History.

### Test C — Idempotency / webhook retries
1. Trigger the same webhook reference twice.
2. Verify:
   - `payment_status` stays `completed`
   - `status` does not regress unexpectedly
   - no duplicate side effects happen (there should be no GH calls anyway)

### Test D — CSV export and pagination
1. Export Orders CSV and verify it includes correct fields.
2. Page through Orders and History to ensure filters work.

## Rollback plan (if anything breaks)
- Revert webhook changes to restore GH-based delivery.
- Restore GH env vars.
- Re-run Test A then Test B.

## Done criteria
The migration is complete when:
1. Paid orders never become `failed` due to missing GH config.
2. Webhook processing only records payment success and sets `status=pending`.
3. Admin can mark orders completed/failed.
4. History exists and shows fulfilled outcomes.
5. Customer view shows payment confirmed (even if delivery remains pending until admin marks it).

