"""models.py — Product Service"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, Integer, String, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from pydantic import BaseModel, Field

from database import Base

def _utcnow(): return datetime.now(timezone.utc)

class Product(Base):
    __tablename__ = "products"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sku: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    stock_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

# Pydantic schemas
class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    sku: str = Field(min_length=1, max_length=100)
    price: Decimal = Field(gt=0)
    stock_quantity: int = Field(ge=0, default=0)

class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    price: Decimal | None = Field(default=None, gt=0)
    stock_quantity: int | None = Field(default=None, ge=0)
    is_active: bool | None = None

class ProductResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    sku: str
    price: Decimal
    stock_quantity: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}
