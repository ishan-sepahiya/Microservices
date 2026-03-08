"""models.py — Payment Service"""
import uuid, enum
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import DateTime, Numeric, Enum, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from pydantic import BaseModel, Field
from database import Base

def _utcnow(): return datetime.now(timezone.utc)

class PaymentStatus(str, enum.Enum):
    PENDING   = "pending"
    COMPLETED = "completed"
    FAILED    = "failed"
    REFUNDED  = "refunded"

class PaymentMethod(str, enum.Enum):
    CARD   = "card"
    WALLET = "wallet"
    BANK   = "bank"

class Payment(Base):
    __tablename__ = "payments"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod), nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False, index=True)
    reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

class PaymentCreate(BaseModel):
    order_id: uuid.UUID
    user_id: uuid.UUID
    amount: Decimal = Field(gt=0)
    currency: str = Field(default="USD", max_length=3)
    method: PaymentMethod

class PaymentResponse(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    user_id: uuid.UUID
    amount: Decimal
    currency: str
    method: PaymentMethod
    status: PaymentStatus
    reference: str | None
    failure_reason: str | None
    created_at: datetime
    model_config = {"from_attributes": True}
