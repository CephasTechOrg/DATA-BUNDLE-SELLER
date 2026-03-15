# Deployment Checklist – Bundle Reseller

Use this list before going live to avoid broken behavior on production, mobile (e.g. iPhone), and different browsers.

---

## 1. Environment variables (.env)

- [ ] **DATABASE_URL** – Production PostgreSQL URL (never use SQLite in production if you expect concurrency).
- [ ] **PAYSTACK_SECRET_KEY** – Use `sk_live_...` for live payments (not `sk_test_...`).
- [ ] **FRONTEND_URL** or **PAYSTACK_CALLBACK_URL** – Set to your live frontend URL (e.g. `https://yoursite.com`) so Paystack redirects users back after payment. No trailing slash.
- [ ] **Bundle delivery provider** – API base URL and key (variable names in `.env.example`; set in env only, never commit).
- [ ] **ADMIN_USERNAME** and **ADMIN_PASSWORD** – Strong credentials for the admin panel.
- [ ] **CORS_ORIGINS** (optional) – Comma-separated allowed origins, e.g. `https://yoursite.com`. Needed if the frontend is on a different domain than the API.

---

## 2. Backend (API)

- [ ] Run the app with production ASGI server (e.g. **uvicorn** with `--host 0.0.0.0` behind a reverse proxy).
- [ ] If the `orders` table already existed before adding `payment_reference_phone`, run:  
  `python scripts/add_payment_reference_phone_column.py`  
  (Or use your own migration; the column must exist.)
- [ ] Ensure **HTTPS** in production. Paystack and most hosts expect it.
- [ ] **Webhook URL** in Paystack dashboard must be your public URL, e.g. `https://api.yoursite.com/webhooks/paystack` (and reachable from the internet).

---

## 3. Frontend (customer site)

- [ ] Serve the **frontend** (e.g. `frontend/` contents) from the **same origin** as the API when possible (e.g. same domain). The app uses relative API URLs in production when not on localhost.
- [ ] If the frontend is on a **different domain**, set **CORS_ORIGINS** in the backend to include that origin, and either:
  - Serve a small config that sets `window.API_BASE = "https://api.yoursite.com"`, and update `frontend/js/api.js` to use it when defined, or  
  - Build a small step that replaces `BASE_URL` at deploy time.
- [ ] **viewport and theme**: Already set in `index.html` (`viewport-fit=cover`, `theme-color`, Apple meta). No extra step unless you change the primary color.
- [ ] **iOS**: Form inputs use `font-size: max(0.95rem, 16px)` to reduce zoom on focus. Keep this in your CSS.

---

## 4. Admin panel

- [ ] Serve the **admin** UI (e.g. `admin/` contents) from the same origin as the API in production (e.g. `https://yoursite.com/admin/`). Then the app uses relative URLs and auth works without CORS issues.
- [ ] If the admin is on a **different domain or subdomain**, add it to **CORS_ORIGINS** and ensure the admin page knows the API base URL (same approach as frontend above).

---

## 5. Paystack

- [ ] In Paystack dashboard: **Settings → API Keys** – use live keys in production.
- [ ] **Webhook**: Set the webhook URL to your backend (e.g. `https://api.yoursite.com/webhooks/paystack`). Paystack must be able to reach it (no localhost).
- [ ] Callback after payment is taken from **FRONTEND_URL** or **PAYSTACK_CALLBACK_URL**. Paystack will redirect to that URL with `?reference=...`.

---

## 6. Bundle delivery provider

- [ ] If the provider requires a webhook URL, set it in their dashboard to a public URL reachable by their servers.
- [ ] Ensure wallet/balance is sufficient for the bundles you sell.

---

## 7. Mobile and browser checks

- [ ] **iPhone Safari**: Test login, bundle selection, order flow, and Paystack redirect. Check safe areas (notch/home indicator) and that inputs don’t cause awkward zoom (we use 16px+ for inputs).
- [ ] **Android Chrome**: Same flow; confirm redirect back from Paystack and status display.
- [ ] **Admin on mobile**: Log in, switch Orders/Bundles tabs, open Add/Edit bundle modal, and check table card layout on small width.
- [ ] **&lt;dialog&gt;**: The admin bundle modal uses `<dialog>`. Supported in modern iOS (15.4+) and all current desktop browsers. The code falls back to `setAttribute("open")` if `showModal` is missing.

---

## 8. Security

- [ ] Never commit `.env`. It’s in `.gitignore`.
- [ ] Use strong **ADMIN_PASSWORD** and limit who can open the admin URL.
- [ ] In production, run the API behind HTTPS (e.g. Nginx/Caddy) and optionally restrict admin by IP if needed.

---

## 9. Quick reference

| Item              | Development              | Production example                    |
|-------------------|--------------------------|--------------------------------------|
| API               | `http://127.0.0.1:8000`  | `https://api.yoursite.com`           |
| Frontend          | `http://localhost:5500`  | `https://yoursite.com`               |
| Paystack callback | (optional)               | `https://yoursite.com`               |
| CORS_ORIGINS      | (built-in localhost)     | `https://yoursite.com`               |

After deployment, run through: **customer flow (choose bundle → order → Paystack → return → status)** and **admin flow (login → stats → orders → bundles CRUD)** on both desktop and a real phone.
