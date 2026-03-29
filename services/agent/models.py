"""
models.py — Agent Service
RegisteredService: every microservice the user plugs in
AgentAction:       audit log of everything the agent does
ServiceInstruction: versioned history of user instructions
"""
import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Enum, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from pydantic import BaseModel, Field
from database import Base

def _utcnow():
    return datetime.now(timezone.utc)

class ServiceType(str, enum.Enum):
    REST      = "rest"
    WEBSOCKET = "websocket"

class ServiceStatus(str, enum.Enum):
    ACTIVE   = "active"
    INACTIVE = "inactive"
    ERROR    = "error"

class ActionStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED  = "failed"

class RegisteredService(Base):
    __tablename__ = "registered_services"
    id: Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name: Mapped[str]           = mapped_column(String(100), unique=True, nullable=False)
    service_type: Mapped[ServiceType] = mapped_column(Enum(ServiceType), nullable=False)
    base_url: Mapped[str]       = mapped_column(String(255), nullable=False)
    health_url: Mapped[str]     = mapped_column(String(255), nullable=False)
    api_schema: Mapped[dict | None]   = mapped_column(JSON, nullable=True)
    instructions: Mapped[str | None]  = mapped_column(Text, nullable=True)
    api_key: Mapped[str | None]       = mapped_column(String(255), nullable=True)
    status: Mapped[ServiceStatus]     = mapped_column(Enum(ServiceStatus), nullable=False, default=ServiceStatus.ACTIVE)
    is_active: Mapped[bool]     = mapped_column(Boolean, default=True, nullable=False)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    registered_at: Mapped[datetime]   = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime]      = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

class AgentAction(Base):
    __tablename__ = "agent_actions"
    id: Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    service_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    action_type: Mapped[str]    = mapped_column(String(100), nullable=False, index=True)
    reasoning: Mapped[str | None]     = mapped_column(Text, nullable=True)
    request_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    response_data: Mapped[dict | None]= mapped_column(JSON, nullable=True)
    status: Mapped[ActionStatus]      = mapped_column(Enum(ActionStatus), nullable=False, default=ActionStatus.PENDING)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime]      = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

class ServiceInstruction(Base):
    __tablename__ = "service_instructions"
    id: Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    instructions: Mapped[str]= mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

# ── Pydantic schemas ──────────────────────────────────────────────────────────
class ServiceRegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    service_type: ServiceType
    base_url: str = Field(min_length=1, max_length=255)
    health_url: str = Field(min_length=1, max_length=255)
    api_key: str | None = None
    instructions: str | None = None

class ServiceUpdateRequest(BaseModel):
    instructions: str | None = None
    api_key: str | None = None
    is_active: bool | None = None

class ServiceResponse(BaseModel):
    id: uuid.UUID
    name: str
    service_type: ServiceType
    base_url: str
    health_url: str
    instructions: str | None
    status: ServiceStatus
    is_active: bool
    last_seen: datetime | None
    registered_at: datetime
    model_config = {"from_attributes": True}

class AgentActionResponse(BaseModel):
    id: uuid.UUID
    service_id: uuid.UUID | None
    action_type: str
    reasoning: str | None
    status: ActionStatus
    error_message: str | None
    created_at: datetime
    model_config = {"from_attributes": True}

class InstructRequest(BaseModel):
    service_id: uuid.UUID
    message: str = Field(min_length=1, max_length=4000)

class InstructResponse(BaseModel):
    reply: str
    actions_taken: list[str] = []

