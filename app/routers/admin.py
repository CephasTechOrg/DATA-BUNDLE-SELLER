"""
Admin API: login (public), config-check (public), orders and stats (require auth).
Auth: HTTP Basic or Bearer token (token from POST /admin/login).
"""
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from ..database import get_db
from ..models import Order, Bundle
from ..schemas import BundleCreate, BundleUpdate, OrderStatusUpdate
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
    """Deprecated: kept for compatibility (we now display the full recipient phone)."""
    if not phone or len(phone) < 4:
        return "***"
    return phone[:2] + "****" + phone[-2:]


@router.get("/orders")
def list_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = Query(None, description="Filter by order status"),
    payment_status: Optional[str] = Query(None, description="Filter by payment_status"),
    sort: str = Query("desc", description="Sort by created_at: asc or desc"),
    from_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    to_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    """List orders with optional filters and pagination. Requires admin Basic auth."""
    sort = (sort or "desc").strip().lower()
    created_order = Order.created_at.asc() if sort == "asc" else Order.created_at.desc()
    q = db.query(Order).order_by(created_order)
    if status:
        # Allow comma-separated statuses for convenience, e.g. "completed,failed" (used by History UI).
        status_values = [s.strip() for s in status.split(",") if s.strip()]
        if status_values:
            if len(status_values) == 1:
                q = q.filter(Order.status == status_values[0])
            else:
                q = q.filter(Order.status.in_(status_values))
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
            "phone_number": o.phone_number,
            "payment_reference_phone": o.payment_reference_phone,
            "network": o.network,
            "capacity": o.capacity,
            "price": float(o.price) if o.price is not None else None,
            "status": o.status,
            "payment_status": o.payment_status,
            "claimed_by": o.claimed_by,
            "claimed_at": o.claimed_at.isoformat() if o.claimed_at else None,
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


@router.post("/orders/{reference}/claim")
def claim_order(reference: str, db: Session = Depends(get_db), admin_id: str = Depends(verify_admin)):
    """
    Claim an order so only one admin fulfills it.

    Visual effect in the admin UI:
    - unclaimed: action buttons show "Claim"
    - claimed by another admin: actions are disabled and show "Locked"
    - claimed by me: actions become available
    """
    order = db.query(Order).filter(Order.reference == reference).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.payment_status != "completed":
        raise HTTPException(status_code=400, detail="Payment not completed for this order")
    if order.status != "pending":
        raise HTTPException(status_code=400, detail=f"Order is not pending (current status: {order.status})")

    # Idempotency: already claimed by me.
    if order.claimed_by == admin_id:
        return {
            "reference": order.reference,
            "claimed_by": order.claimed_by,
            "claimed_at": order.claimed_at.isoformat() if order.claimed_at else None,
        }

    if order.claimed_by and order.claimed_by != admin_id:
        raise HTTPException(status_code=409, detail="Order already claimed by another admin")

    # Atomic claim: only one admin can claim when claimed_by IS NULL.
    now = datetime.now(timezone.utc)
    updated = (
        db.query(Order)
        .filter(
            Order.reference == reference,
            Order.payment_status == "completed",
            Order.status == "pending",
            Order.claimed_by.is_(None),
        )
        .update({"claimed_by": admin_id, "claimed_at": now}, synchronize_session=False)
    )

    if updated != 1:
        # Someone else claimed between our read and update.
        order = db.query(Order).filter(Order.reference == reference).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        if order.claimed_by != admin_id:
            raise HTTPException(status_code=409, detail="Order already claimed by another admin")

    db.commit()
    db.refresh(order)
    return {
        "reference": order.reference,
        "claimed_by": order.claimed_by,
        "claimed_at": order.claimed_at.isoformat() if order.claimed_at else None,
    }


@router.patch("/orders/{reference}/status")
def update_order_fulfillment_status(
    reference: str,
    body: OrderStatusUpdate,
    db: Session = Depends(get_db),
    admin_id: str = Depends(verify_admin),
):
    """
    Manually fulfill an order.

    Allowed only when the payment is confirmed via Paystack:
    - payment_status must be "completed"
    - order.status can be updated from "pending" to "completed"/"failed"
    """
    order = db.query(Order).filter(Order.reference == reference).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.payment_status != "completed":
        raise HTTPException(status_code=400, detail="Payment not completed for this order")

    if order.status == body.status and order.status in ("completed", "failed"):
        # Idempotent: same final outcome.
        return {"reference": order.reference, "status": order.status, "payment_status": order.payment_status}

    # Enforce locking via atomic update:
    # - must still be pending
    # - must still be claimed_by == this admin
    updated = (
        db.query(Order)
        .filter(
            Order.reference == reference,
            Order.payment_status == "completed",
            Order.status == "pending",
            Order.claimed_by == admin_id,
        )
        .update({"status": body.status}, synchronize_session=False)
    )

    if updated != 1:
        # Re-read to return the correct error.
        order = db.query(Order).filter(Order.reference == reference).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        if order.status != "pending":
            raise HTTPException(status_code=400, detail=f"Order is not pending (current status: {order.status})")
        if order.claimed_by != admin_id:
            raise HTTPException(status_code=409, detail="Order is locked by another admin (or not claimed)")
        raise HTTPException(status_code=400, detail="Order cannot be fulfilled in its current state")

    db.commit()
    db.refresh(order)
    return {"reference": order.reference, "status": order.status, "payment_status": order.payment_status}


@router.delete("/orders/{reference}")
def delete_order_for_admin(
    reference: str,
    db: Session = Depends(get_db),
    admin_id: str = Depends(verify_admin),
):
    """
    Delete an order from the queue.

    Allowed only when:
    - payment_status == completed
    - status == pending
    - and either unclaimed or claimed_by == this admin
    """
    # Atomic delete: allow if unclaimed OR claimed_by == this admin.
    deleted = (
        db.query(Order)
        .filter(
            Order.reference == reference,
            Order.payment_status == "completed",
            Order.status == "pending",
            or_(Order.claimed_by.is_(None), Order.claimed_by == admin_id),
        )
        .delete(synchronize_session=False)
    )

    if deleted != 1:
        order = db.query(Order).filter(Order.reference == reference).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        if order.payment_status != "completed" or order.status != "pending":
            raise HTTPException(status_code=400, detail="Only pending paid orders can be deleted")
        raise HTTPException(status_code=409, detail="Order locked by another admin")

    db.commit()
    return {"status": "deleted", "reference": reference}
