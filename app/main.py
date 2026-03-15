import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine
from . import models  # noqa: F401 - register Bundle model
from .routers import orders, webhooks, admin
from .seed_bundles import seed_bundles_if_empty

Base.metadata.create_all(bind=engine)
seed_bundles_if_empty()

app = FastAPI()

# CORS: local dev origins + optional CORS_ORIGINS from env (comma-separated for production)
_default_origins = [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5501",
    "http://localhost:5501",
    "null",
]
_cors_origins_env = os.getenv("CORS_ORIGINS", "").strip()
allow_origins = _default_origins + [o.strip() for o in _cors_origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    """Used by Render (and others) to confirm the service is up."""
    return {"status": "ok"}


app.include_router(orders.router)
app.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
app.include_router(admin.router_public, prefix="/admin", tags=["admin"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
