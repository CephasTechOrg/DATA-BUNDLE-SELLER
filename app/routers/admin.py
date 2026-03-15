"""
Admin API: login (public), config-check (public), orders and stats (require auth).
Auth: HTTP Basic or Bearer token (token from POST /admin/login).
"""
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import get_db
from ..models import Order, Bundle
from ..schemas import BundleCreate, BundleUpdate
from ..auth import verify_admin, create_admin_token

# Public routes (no auth)
router_public = APIRouter()


class LoginBody(BaseModel):
    username: str = ""
    password: str = ""


@router_public.get("/config-check")
def admin_config_check():
    """No auth. Returns whether admin env vars are set (for debugging)."""
    from ..auth import ADMIN_USERNAME, ADMIN_PASSWORD
    return {"admin_configured": bool(ADMIN_USERNAME and ADMIN_PASSWORD)}


@router_public.post("/login")
def admin_login(body: LoginBody):
    """No auth. Accepts JSON { username, password }, returns { token } if valid."""
    import logging
    from ..auth import _check_credentials, ADMIN_USERNAME, ADMIN_PASSWORD
    username = (body.username or "").strip()
    password = (body.password or "").strip()
    ok = _check_credentials(username, password)
    logging.getLogger("uvicorn.error").info(
        "Admin login: env_username_set=%s, env_password_set=%s, credentials_ok=%s",
        bool(ADMIN_USERNAME),
        bool(ADMIN_PASSWORD),
        ok,
    )
    if not ok:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_admin_token()
    return {"token": token}


# Protected routes (Basic or Bearer)
router = APIRouter(dependencies=[Depends(verify_admin)])


def _mask_phone(phone: Optional[str]) -> str:
    if not phone or len(phone) < 4:
        return "***"
    return phone[:2] + "****" + phone[-2:]


@router.get("/orders")
def list_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = Query(None, description="Filter by order status"),
    payment_status: Optional[str] = Query(None, description="Filter by payment_status"),
    from_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    to_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    """List orders with optional filters and pagination. Requires admin Basic auth."""
    q = db.query(Order).order_by(Order.created_at.desc())
    if status:
        q = q.filter(Order.status == status)
    if payment_status:
        q = q.filter(Order.payment_status == payment_status)
    if from_date:
        try:
            start = datetime.strptime(from_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            q = q.filter(Order.created_at >= start)
        except ValueError:
            pass
    if to_date:
        try:
            end = datetime.strptime(to_date, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)
            q = q.filter(Order.created_at < end)
        except ValueError:
            pass

    total = q.count()
    rows = q.offset(skip).limit(limit).all()
    items = [
        {
            "id": o.id,
            "reference": o.reference,
            "phone_number": _mask_phone(o.phone_number),
            "network": o.network,
            "capacity": o.capacity,
            "price": float(o.price) if o.price is not None else None,
            "status": o.status,
            "payment_status": o.payment_status,
            "created_at": o.created_at.isoformat() if o.created_at else None,
        }
        for o in rows
    ]
    return {"total": total, "skip": skip, "limit": limit, "items": items}


@router.get("/stats")
def get_stats(
    from_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    to_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    """Aggregate stats: order count, revenue (sum of price where payment_status=completed). Requires admin Basic auth."""
    q = db.query(Order)
    q_completed = db.query(Order).filter(Order.payment_status == "completed")

    if from_date:
        try:
            start = datetime.strptime(from_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            q = q.filter(Order.created_at >= start)
            q_completed = q_completed.filter(Order.created_at >= start)
        except ValueError:
            pass
    if to_date:
        try:
            end = datetime.strptime(to_date, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)
            q = q.filter(Order.created_at < end)
            q_completed = q_completed.filter(Order.created_at < end)
        except ValueError:
            pass

    total_orders = q.count()
    revenue_result = q_completed.with_entities(func.coalesce(func.sum(Order.price), 0)).scalar()
    total_revenue = float(revenue_result) if revenue_result is not None else 0.0

    completed_count = q_completed.count()
    failed_count = q.filter(Order.status == "failed").count()
    pending_count = q.filter(Order.status == "pending").count()

    return {
        "total_orders": total_orders,
        "completed_orders": completed_count,
        "failed_orders": failed_count,
        "pending_orders": pending_count,
        "total_revenue_ghs": round(total_revenue, 2),
    }


# ----- Bundles CRUD -----


@router.get("/bundles")
def list_bundles(
    network: Optional[str] = Query(None, description="Filter by network"),
    include_inactive: bool = Query(False, description="Include inactive bundles"),
    db: Session = Depends(get_db),
):
    """List bundles. Requires admin auth."""
    q = db.query(Bundle).order_by(Bundle.network, Bundle.capacity_mb)
    if network:
        q = q.filter(Bundle.network == network)
    if not include_inactive:
        q = q.filter(Bundle.is_active == True)
    rows = q.all()
    items = [
        {
            "id": b.id,
            "network": b.network,
            "capacity_mb": b.capacity_mb,
            "cost_price_ghs": float(b.cost_price_ghs),
            "selling_price_ghs": float(b.selling_price_ghs),
            "is_active": b.is_active,
            "display_order": b.display_order,
        }
        for b in rows
    ]
    return {"total": len(items), "items": items}


@router.post("/bundles")
def create_bundle(body: BundleCreate, db: Session = Depends(get_db)):
    """Add a bundle. Requires admin auth."""
    existing = (
        db.query(Bundle)
        .filter(Bundle.network == body.network.strip(), Bundle.capacity_mb == body.capacity_mb)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"A bundle for {body.network} {body.capacity_mb} MB already exists.",
        )
    b = Bundle(
        network=body.network.strip(),
        capacity_mb=body.capacity_mb,
        cost_price_ghs=body.cost_price_ghs,
        selling_price_ghs=body.selling_price_ghs,
        is_active=body.is_active,
        display_order=body.display_order,
    )
    db.add(b)
    db.commit()
    db.refresh(b)
    return {
        "id": b.id,
        "network": b.network,
        "capacity_mb": b.capacity_mb,
        "cost_price_ghs": float(b.cost_price_ghs),
        "selling_price_ghs": float(b.selling_price_ghs),
        "is_active": b.is_active,
        "display_order": b.display_order,
    }


@router.put("/bundles/{bundle_id}")
def update_bundle(bundle_id: int, body: BundleUpdate, db: Session = Depends(get_db)):
    """Update a bundle (price, active, order). Requires admin auth."""
    b = db.query(Bundle).filter(Bundle.id == bundle_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Bundle not found")
    if body.cost_price_ghs is not None:
        b.cost_price_ghs = body.cost_price_ghs
    if body.selling_price_ghs is not None:
        b.selling_price_ghs = body.selling_price_ghs
    if body.is_active is not None:
        b.is_active = body.is_active
    if body.display_order is not None:
        b.display_order = body.display_order
    db.commit()
    db.refresh(b)
    return {
        "id": b.id,
        "network": b.network,
        "capacity_mb": b.capacity_mb,
        "cost_price_ghs": float(b.cost_price_ghs),
        "selling_price_ghs": float(b.selling_price_ghs),
        "is_active": b.is_active,
        "display_order": b.display_order,
    }


@router.delete("/bundles/{bundle_id}")
def delete_bundle(bundle_id: int, db: Session = Depends(get_db)):
    """Delete a bundle. Requires admin auth."""
    b = db.query(Bundle).filter(Bundle.id == bundle_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Bundle not found")
    db.delete(b)
    db.commit()
    return {"status": "deleted"}
