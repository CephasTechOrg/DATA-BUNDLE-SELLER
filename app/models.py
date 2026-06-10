from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, UniqueConstraint
from sqlalchemy.sql import func
from .database import Base


class Order(Base):

    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)

    reference = Column(String, unique=True)

    phone_number = Column(String)
    payment_reference_phone = Column(String, nullable=True)

    network = Column(String)

    capacity = Column(Integer)

    price = Column(Float)

    # Internal status: pending | processing | completed | failed | manual_review
    status = Column(String, default="pending")

    payment_status = Column(String, default="pending")

    # ----- ResellerXpress provider tracking (Phase 2 automation) -----
    # Provider's order id, needed to call /reprocess/{id}.
    provider_order_id = Column(Integer, nullable=True, index=True)
    # Dealer price actually debited from our wallet for this order (provider's amount).
    provider_amount = Column(Float, nullable=True)
    # Raw provider status (queued/processing/success/failed) as last seen.
    provider_status = Column(String, nullable=True)
    # Why a provider order failed / went to manual review.
    failure_reason = Column(String, nullable=True)
    # Number of auto/admin retries attempted (capped by RESELLERXPRESS_MAX_RETRIES).
    retry_count = Column(Integer, default=0, nullable=False)

    # Manual fulfillment lock/ownership for multi-admin environments.
    # When set, only the claiming admin can finalize the order.
    claimed_by = Column(String, nullable=True)
    claimed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Bundle(Base):

    __tablename__ = "bundles"

    id = Column(Integer, primary_key=True, index=True)
    network = Column(String, nullable=False, index=True)
    capacity_mb = Column(Integer, nullable=False)
    cost_price_ghs = Column(Float, nullable=False)
    selling_price_ghs = Column(Float, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    display_order = Column(Integer, default=0, nullable=False)

    # ResellerXpress plan id for this bundle. Required to auto-place orders
    # (the provider charges its dealer price for this plan against our wallet).
    # Populated by the /plans sync; NULL means the bundle cannot be auto-fulfilled yet.
    provider_plan_id = Column(Integer, nullable=True, index=True)

    __table_args__ = (UniqueConstraint("network", "capacity_mb", name="uq_bundle_network_capacity"),)


class ProviderWebhookEvent(Base):
    """Audit log of inbound ResellerXpress webhook payloads (stored before processing)."""

    __tablename__ = "provider_webhook_events"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, nullable=True)
    request_id = Column(String, nullable=True, index=True)
    provider_order_id = Column(Integer, nullable=True)
    payload = Column(Text, nullable=False)  # raw JSON as text (portable across PG/SQLite)
    processed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
