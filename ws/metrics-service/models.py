import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from pydantic import BaseModel
from database import Base

def _utcnow(): return datetime.now(timezone.utc)

class MetricSnapshot(Base):
    __tablename__ = "metric_snapshots"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    cpu_percent: Mapped[float] = mapped_column(Float, nullable=False)
    memory_percent: Mapped[float] = mapped_column(Float, nullable=False)
    request_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False, index=True)

class MetricOut(BaseModel):
    id: uuid.UUID
    service_name: str
    cpu_percent: float
    memory_percent: float
    request_count: int
    error_count: int
    recorded_at: datetime
    model_config = {"from_attributes": True}
