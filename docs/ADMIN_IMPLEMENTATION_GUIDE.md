# Admin Panel – Implementation Guide

Step-by-step guide to build a **read-only** admin for monitoring orders, revenue, and failed/pending items. Auth uses **username + password from `.env`** for a simple, secure setup.

---

## Authentication: Simple setup (`.env`)

**Recommendation: store admin username and password in `.env`.**

- **Why it’s OK for this use case:** One or a few trusted admins, no self-service signup, no “forgot password”. You control who has the env file. No database tables or session store needed at first.
- **How:** Read `ADMIN_USERNAME` and `ADMIN_PASSWORD` from the environment. In protected routes, check the `Authorization` header (e.g. Basic auth) or a simple Bearer token (e.g. a shared secret) against those values.
- **Security:** Use a **strong password** (long, random). Never commit `.env`. In production, set env vars on the server or in your host’s config.
- **When to upgrade:** If you add more admins, need audit trails, or compliance, add proper auth later (e.g. hashed passwords in DB, sessions or JWT, or OAuth).

**Example `.env` entries:**

```env
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your_strong_password_here
```

Optional: use a single shared secret for “Bearer” style checks instead of username+password (e.g. `ADMIN_SECRET=...` and send `Authorization: Bearer <ADMIN_SECRET>` from the admin frontend). Same idea: secret in `.env`, never in code.

---

## Phase 1: Backend – Auth and admin endpoints

### Step 1.1 – Add env vars

- In `.env`: `ADMIN_USERNAME`, `ADMIN_PASSWORD` (or one `ADMIN_SECRET` if you prefer Bearer).
- In `.env.example`: add the same keys with placeholder values and a short comment.

### Step 1.2 – Auth dependency (FastAPI)

- Create a small auth module (e.g. `app/auth.py` or `app/deps.py`).
- Read `ADMIN_USERNAME` and `ADMIN_PASSWORD` from `os.getenv`.
- Implement a dependency that:
  - Reads `Authorization: Basic <base64(username:password)>` or `Authorization: Bearer <secret>`.
  - Compares to the value(s) from `.env`.
  - Returns 401 if missing or wrong.
- Optionally add a simple login endpoint `POST /admin/login` that accepts `username` + `password` in JSON and returns a token or “ok” so the admin frontend can store a token and send it on later requests.

### Step 1.3 – Admin API routes

- New router, e.g. `app/routers/admin.py`, mounted under `/admin` (or `/api/admin`).
- Protect all routes with the auth dependency.
- Endpoints to implement:
  1. **GET /admin/orders**  
     Query params: `skip`, `limit`, optional `status`, `payment_status`, `from_date`, `to_date`.  
     Return list of orders (reference, network, capacity, price, status, payment_status, created_at, phone_number masked if desired). Order by `created_at` desc.
  2. **GET /admin/stats**  
     Query params: optional `from_date`, `to_date`.  
     Return: total order count, count by status/payment_status, **total revenue** (sum of `price` where `payment_status == "completed"`), maybe today’s count/revenue.
- Use your existing `Order` model and DB session; no new tables needed for Phase 1.

### Step 1.4 – CORS and mount

- If the admin frontend is on another origin, add that origin to CORS in `main.py`.
- Mount the admin router: e.g. `app.include_router(admin.router, prefix="/admin", tags=["admin"])`.

---

## Phase 2: Admin frontend (simple UI)

### Step 2.1 – Where to put it

- Option A: New folder, e.g. `admin/` in the repo (separate HTML/JS/CSS, or a small SPA).
- Option B: A single `admin.html` (or `admin/index.html`) that uses the same backend; login form + orders table + stats.

### Step 2.2 – Login

- One page or section: username + password.
- On submit, call your login endpoint (or directly call a protected endpoint with Basic auth). If using a token, store it (e.g. in `sessionStorage`) and send it in `Authorization: Bearer <token>` for all later requests.
- On success, redirect or show the main admin view; on failure, show an error.

### Step 2.3 – Main view

- **Stats block:** Show totals from `GET /admin/stats` (total revenue, order count, maybe today’s numbers). Optional: simple text or a very small chart (e.g. “last 7 days” counts).
- **Orders table:** Call `GET /admin/orders` with optional filters (date range, status, payment_status). Table columns: reference, network, capacity, price, status, payment_status, created_at; optionally masked phone.
- **Filters:** Dropdowns or inputs for date range, status, payment_status; “Apply” or auto-refresh when changed.
- **Optional:** “Export CSV” that uses the same filters and downloads a CSV (either client-side from the JSON or a new endpoint `GET /admin/orders/export?format=csv`).

### Step 2.4 – Security (frontend)

- Use HTTPS in production.
- Don’t store passwords in the frontend; only send them on login (or send the token once you have it).
- If using a token, send it only to your backend; don’t expose it in URLs or logs.

---

## Phase 3: Optional improvements

- **Dashboard:** Small cards or chart for “today / this week” orders and revenue.
- **Failed / Pending highlight:** Badge or filter for `status != "completed"` or `payment_status != "completed"` so you can chase issues.
- **Pagination:** Already supported if you use `skip`/`limit`; add Previous/Next in the UI.
- **Stronger auth later:** Replace `.env` credentials with a proper user table, hashed passwords, and sessions or JWT when you need multiple admins or compliance.

---

## Checklist (summary)

| Step | Task |
|------|------|
| 1.1 | Add `ADMIN_USERNAME` and `ADMIN_PASSWORD` (or `ADMIN_SECRET`) to `.env` and `.env.example` |
| 1.2 | Implement auth dependency and optional `POST /admin/login` |
| 1.3 | Implement `GET /admin/orders` and `GET /admin/stats` with filters |
| 1.4 | Mount admin router and update CORS if needed |
| 2.1 | Create admin frontend (folder or single page) |
| 2.2 | Login form and token/Basic handling |
| 2.3 | Stats block + orders table + filters (+ optional CSV export) |
| 2.4 | Use HTTPS; don’t store passwords in frontend |

**Phase 2 implemented:** `admin/index.html`, `admin/style.css`, `admin/app.js` — login (Basic auth), stats, orders table with filters and pagination, Export CSV.

---

## Running the admin (Phase 2)

1. **Backend:** Set `ADMIN_USERNAME` and `ADMIN_PASSWORD` in `.env`, then run:
   ```bash
   uvicorn app.main:app --reload
   ```

2. **Admin UI:** Serve the `admin/` folder (e.g. from repo root: `python -m http.server 5501`) and open `http://localhost:5501/admin/` in the browser. Or use your IDE’s Live Server on port 5501 so CORS allows the backend at 8000.

3. **Login** with your `.env` admin credentials. Use the filters and “Export CSV” as needed; “Sign out” clears the session.

---

## File structure (suggestion)

```
app/
  auth.py           # or deps.py: get env credentials, verify Basic/Bearer
  routers/
    admin.py        # GET /orders, GET /stats, optional POST /login
  ...
docs/
  ADMIN_IMPLEMENTATION_GUIDE.md   # this file
admin/             # optional: admin UI
  index.html
  style.css
  app.js
.env               # ADMIN_USERNAME, ADMIN_PASSWORD (or ADMIN_SECRET)
.env.example       # same keys, placeholders
```

You can start with Phase 1 (backend auth + endpoints), then add the frontend in Phase 2. Using username and password from `.env` is a simple and reasonable way to get going.

---

## Running the admin (Phase 2)

1. **Backend:** Ensure `ADMIN_USERNAME` and `ADMIN_PASSWORD` are set in `.env`, then run:
   ```bash
   uvicorn app.main:app --reload
   ```

2. **Admin UI:** Open the admin frontend in a browser. You can:
   - Use a local server that serves the `admin/` folder (e.g. run from repo root: `python -m http.server 5501` then open `http://localhost:5501/admin/` or `http://127.0.0.1:5501/admin/`).
   - Or open `admin/index.html` via your IDE’s “Live Server” and set the port to 5501 so CORS allows the backend at 8000.

3. **Login** with the same username and password as in `.env`. After that you’ll see the dashboard (stats + orders table). Use filters and “Export CSV” as needed. “Sign out” clears the session.
