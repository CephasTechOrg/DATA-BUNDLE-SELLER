from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, UniqueConstraint
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

    status = Column(String, default="pending")

    payment_status = Column(String, default="pending")

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

    __table_args__ = (UniqueConstraint("network", "capacity_mb", name="uq_bundle_network_capacity"),)
