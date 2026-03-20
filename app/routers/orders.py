import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Order, Bundle
from ..schemas import CreateOrder
from ..services.paystack_service import initialize_payment
from ..utils.reference import generate_reference

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_bundle(db: Session, network: str, capacity: int):
    """Return active bundle for network+capacity or None."""
    return (
        db.query(Bundle)
        .filter(
            Bundle.network == network,
            Bundle.capacity_mb == capacity,
            Bundle.is_active,
        )
        .first()
    )


@router.get("/bundles")
def get_bundles(db: Session = Depends(get_db)):
    """Return active bundles from DB, grouped by network, with selling price."""
    rows = (
        db.query(Bundle)
        .filter(Bundle.is_active)
        .order_by(Bundle.network, Bundle.display_order, Bundle.capacity_mb)
        .all()
    )
    by_network = {}
    for b in rows:
        key = b.network
        if key not in by_network:
            by_network[key] = []
        by_network[key].append({"capacity": b.capacity_mb, "price": float(b.selling_price_ghs)})
    result = [{"name": k, "key": k, "bundles": v} for k, v in by_network.items()]
    return result


@router.post("/orders")
async def create_order(order: CreateOrder, db: Session = Depends(get_db)):
    bundle = _get_bundle(db, order.network, order.capacity)
    if not bundle:
        raise HTTPException(
            status_code=400,
            detail=f"Bundle not supported: {order.network} {order.capacity} MB. Choose a size from the bundle list.",
        )

    reference = generate_reference()
    selling_price = float(bundle.selling_price_ghs)

    new_order = Order(
        reference=reference,
        phone_number=order.phone_number,
        payment_reference_phone=order.payment_reference_phone if order.payment_reference_phone else None,
        network=order.network,
        capacity=order.capacity,
        price=selling_price,
    )

    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    # Initialize Paystack payment (amount = selling price). Callback URL from env when set.
    payment = await initialize_payment(
        email=order.email,
        amount=selling_price,
        reference=reference,
    )

    if not payment.get("status"):
        msg = payment.get("message", "Payment initialization failed")
        logger.warning("Paystack initialize failed for ref %s: %s", reference, msg)
        raise HTTPException(status_code=502, detail=msg)

    data = payment.get("data") or {}
    authorization_url = data.get("authorization_url")
    access_code = data.get("access_code")

    if not authorization_url:
        msg = payment.get("message", "No payment URL from provider")
        logger.warning("Paystack missing authorization_url for ref %s: %s", reference, payment)
        raise HTTPException(status_code=502, detail=msg)

    return {
        "reference": reference,
        "payment_url": authorization_url,
        "access_code": access_code,
        "status": "pending",
    }


@router.get("/orders/{reference}")
async def get_order_status(reference: str, refresh: bool = False, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.reference == reference).first()
    if not order:
        return {"error": "Order not found"}
    # Manual fulfillment mode:
    # We intentionally do NOT poll GH Data Connect. Admin fulfillment is the source of truth.
    return {
        "reference": order.reference,
        "status": order.status,
        "payment_status": order.payment_status
    }
