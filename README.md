# Bundle Reseller

Sell **MTN** and **Telecel** data bundles in Ghana. Customer-facing site for browsing and buying; **Paystack** for payments; bundle delivery via a configured provider API. FastAPI backend with an admin dashboard for orders, bundle management, and stats.

---

## Features

- **Customer site** — Browse MTN & Telecel bundles, checkout with Paystack, view order status
- **Admin panel** — Login, view orders & stats, manage bundles (add / edit / delete, set prices), export CSV
- **Paystack** — Payment initialization, webhook for successful charges
- **Bundle delivery** — Wallet balance check and delivery via provider API (credentials in env)
- **Database** — PostgreSQL; orders and configurable bundles (selling price per size/network)

---

## Tech stack

| Layer      | Stack |
|-----------|--------|
| Backend   | FastAPI, SQLAlchemy, Pydantic, httpx |
| Database  | PostgreSQL |
| Payments  | Paystack |
| Delivery  | Provider API (see .env) |
| Frontend  | HTML, CSS, JavaScript (vanilla) |
| Deploy    | Backend + DB: Render · Frontend: Vercel / Netlify |

---

## Project structure

```
├── app/
│   ├── main.py              # FastAPI app, CORS, /health
│   ├── database.py          # SQLAlchemy engine, session
│   ├── models.py            # Order, Bundle
│   ├── schemas.py           # Pydantic models
│   ├── auth.py              # Admin auth (env credentials, Bearer tokens)
│   ├── routers/             # orders, webhooks, admin
│   ├── services/            # paystack, delivery provider
│   ├── utils/               # pricing, reference
│   └── seed_bundles.py      # Seed bundles from config if DB empty
├── frontend/                # Customer UI (static; deploy to Vercel/Netlify)
├── admin/                   # Admin UI (static; same or separate host)
├── documentation/           # Guides (DEPLOYMENT.md, etc.); not the live site
├── docs/                   # Built site for GitHub Pages (run scripts/build-gh-pages.*)
├── render.yaml              # Render blueprint (backend + Postgres)
├── requirements.txt
└── .env.example
```

---

## Local setup

### Prerequisites

- Python 3.11+
- PostgreSQL (local or cloud)
- [Paystack](https://paystack.com) account for payments
- Bundle delivery provider API credentials (see `.env.example` for required keys)

### 1. Clone and install

```bash
git clone https://github.com/your-username/bundlereseller.git
cd bundlereseller
python -m venv venv
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
```

### 2. Environment

```bash
cp .env.example .env
```

Edit `.env` and set at least:

- `DATABASE_URL` — PostgreSQL connection string
- `PAYSTACK_SECRET_KEY` — From Paystack dashboard (use `sk_test_` for testing)
- Delivery provider API URL and key (variable names in `.env.example`; do not commit real values)
- `ADMIN_USERNAME` and `ADMIN_PASSWORD` — For admin panel login

Optional: `FRONTEND_URL` / `PAYSTACK_CALLBACK_URL` for redirect after payment; `CORS_ORIGINS` if frontend is on another domain.

### 3. Run the API

```bash
uvicorn app.main:app --reload --port 8000
```

- API: http://127.0.0.1:8000  
- Docs: http://127.0.0.1:8000/docs  

### 4. Frontend and admin (local)

- **Customer site:** Open `frontend/index.html` via a local server (e.g. Live Server on port 5500) or serve the `frontend/` folder. It will call the API at `http://127.0.0.1:8000` when on localhost.
- **Admin:** Open `admin/index.html` (or serve the `admin/` folder). Log in with `ADMIN_USERNAME` / `ADMIN_PASSWORD`.

---

## Deployment

- **Backend + database:** Use the **Render** blueprint. From the repo root, connect the repo in Render and create a new **Blueprint**; it will use `render.yaml` to create the web service and Postgres DB. Set secrets (Paystack, delivery API credentials, admin, `FRONTEND_URL`, `CORS_ORIGINS`) in the Render dashboard.
- **Frontend + Admin:** Deploy to **Vercel**, **Netlify**, or **GitHub Pages** (see below). The app is already configured to call the Render backend when not on localhost.

### GitHub Pages

GitHub only serves from a folder named **`docs`**. Your written guides (e.g. DEPLOYMENT.md) live in **`documentation/`**. The **customer** and **admin** UIs live in `frontend/` and `admin/`, so a build step copies them into **`docs/`** for Pages to serve.

1. **Build the site** (from repo root):
   - **Windows (PowerShell):** `.\scripts\build-gh-pages.ps1`
   - **Mac/Linux/Git Bash:** `bash scripts/build-gh-pages.sh`
   This overwrites **`docs/`** with `index.html` (customer) at the root and `admin/` (admin panel).
2. **Commit and push** the `docs/` folder.
3. In GitHub: **Settings → Pages → Build and deployment**: Source = **Deploy from a branch**; Branch = `main`; Folder = **/docs**.
4. Your site will be at `https://<username>.github.io/<repo-name>/` (customer). Admin: `https://<username>.github.io/<repo-name>/admin/`.

After you change `frontend/` or `admin/`, run the script again, then commit and push `docs/`. In Render, set **CORS_ORIGINS** to your GitHub Pages URL (e.g. `https://yourusername.github.io/bundlereseller`) so the browser allows API requests.

See **[documentation/DEPLOYMENT.md](documentation/DEPLOYMENT.md)** for a full checklist (env vars, Paystack webhook, CORS, mobile checks).

---

## API overview

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check (e.g. for Render) |
| GET | `/bundles` | List active bundles (public) |
| POST | `/orders` | Create order, returns Paystack payment URL |
| GET | `/orders/{reference}` | Order status (public) |
| POST | `/webhooks/paystack` | Paystack webhook (charge.success) |
| POST | `/admin/login` | Admin login (returns Bearer token) |
| GET | `/admin/orders` | List orders (auth) |
| GET | `/admin/stats` | Aggregated stats (auth) |
| GET/POST/PUT/DELETE | `/admin/bundles` | Bundle CRUD (auth) |

---

## License

Private / All rights reserved. Use and reuse only as permitted by the repository owner.
