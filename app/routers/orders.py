import logging
import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Order, Bundle
from ..schemas import CreateOrder
from ..services import resellerxpress_service
from ..services.paystack_service import initialize_payment
from ..utils.reference import generate_reference

logger = logging.getLogger(__name__)
router = APIRouter()

try:
    LOW_BALANCE_THRESHOLD = float(os.getenv("RESELLERXPRESS_LOW_BALANCE_THRESHOLD", "50") or 50)
except ValueError:
    LOW_BALANCE_THRESHOLD = 50.0

# Shown to the customer when the provider wallet can't cover the order. Kept vague
# on purpose (no "wallet" talk) so it reads as a temporary service blip.
UNAVAILABLE_MSG = (
    "We're having a brief issue completing orders right now. Please try again in "
    "about 30 minutes. You have not been charged."
)


async def _wallet_can_fulfill(cost_price: float) -> bool:
    """
    True if the ResellerXpress wallet can cover this order (>= the larger of the
    low-balance threshold and the bundle's dealer cost).

    Fails OPEN: if the balance can't be read (provider hiccup), we allow the order
    through — the post-payment auto-placement + manual_review net still protects a
    paid-but-undeliverable order. We only block when we *know* the wallet is short.
    """
    result = await resellerxpress_service.get_wallet_balance()
    if not result.get("ok"):
        logger.warning("Wallet pre-check unavailable, allowing order: %s", result.get("message"))
        return True
    data = result.get("data") or {}
    try:
        balance = float(data.get("balance"))
    except (TypeError, ValueError):
        logger.warning("Wallet pre-check: unparseable balance %r, allowing order", data.get("balance"))
        return True
    required = max(LOW_BALANCE_THRESHOLD, float(cost_price or 0))
    if balance < required:
        logger.warning("Order blocked: wallet balance %.2f below required %.2f", balance, required)
        return False
    return True


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
        # Sort strictly by size within each network so order is always predictable
        # (1GB -> 100GB). display_order is intentionally ignored to avoid re-added
        # bundles jumping to the front.
        .order_by(Bundle.network, Bundle.capacity_mb)
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

    # Pre-checkout guard: don't take payment if the provider wallet can't fulfill it.
    if not await _wallet_can_fulfill(float(bundle.cost_price_ghs)):
        raise HTTPException(status_code=503, detail=UNAVAILABLE_MSG)

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

    # Paystack requires an email. Customers no longer enter one, so use theirs if
    # provided, else synthesize a valid placeholder from the recipient phone.
    email = (order.email or "").strip()
    if not email:
        digits = "".join(ch for ch in (order.phone_number or "") if ch.isdigit()) or "customer"
        email = f"{digits}@noreply.xtradata.innovatex.ink"

    # Initialize Paystack payment (amount = selling price). Callback URL from env when set.
    payment = await initialize_payment(
        email=email,
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

    # Polling fallback: when asked to refresh a non-final order that has been placed,
    # pull the latest status from ResellerXpress and persist it. Webhooks are primary;
    # this covers missed/late webhook deliveries.
    if refresh and order.provider_order_id and order.status not in ("completed", "failed"):
        from ..services import resellerxpress_service
        from ..fulfillment import map_provider_status, _extract_provider_order

        lookup = await resellerxpress_service.get_order_status(reference)
        if lookup.get("ok"):
            _, prov_status, amount = _extract_provider_order(lookup.get("data"))
            if prov_status:
                order.provider_status = prov_status
                order.status = map_provider_status(prov_status)
            if amount is not None and order.provider_amount is None:
                order.provider_amount = amount
            db.commit()

    return {
        "reference": order.reference,
        "status": order.status,
        "payment_status": order.payment_status,
    }
