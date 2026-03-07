"""
control_api/routes.py
The dedicated API that user-provided microservices talk to.

Services call this to:
  POST /control/register          — announce themselves to the agent
  POST /control/heartbeat         — stay-alive ping every 30s
  GET  /control/services          — list all registered services
  GET  /control/services/{name}   — get one service's details
  PATCH /control/services/{name}/instructions  — update management rules
  DELETE /control/services/{name} — deregister
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from registry.models import (
    HeartbeatRequest,
    RegisteredService,
    ServiceInstruction,
    ServiceRegisterRequest,
    ServiceResponse,
    ServiceStatus,
    ServiceUpdateInstructions,
)

router = APIRouter(prefix="/control", tags=["Control API"])


# ── Auth: services authenticate with the shared CONTROL_API_KEY ───────────────

async def verify_control_key(x_control_key: str = Header(...)):
    """
    All control API calls require X-Control-Key header.
    This key is shared between the agent and all registered services via .env.
    """
    if x_control_key != settings.control_api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid control API key",
        )


# ── Register ──────────────────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=ServiceResponse,
    status_code=201,
    dependencies=[Depends(verify_control_key)],
    summary="Register a microservice with the agent",
)
async def register_service(
    payload: ServiceRegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> ServiceResponse:
    """
    Called by a microservice on startup.
    If the service is already registered, its details are updated (upsert).

    Example (called from your service's startup):
        httpx.post(
            "http://agent:8000/control/register",
            json={...},
            headers={"X-Control-Key": os.getenv("CONTROL_API_KEY")}
        )
    """
    existing_result = await db.execute(
        select(RegisteredService).where(RegisteredService.name == payload.name)
    )
    service = existing_result.scalar_one_or_none()

    if service:
        # Update existing registration
        await db.execute(
            update(RegisteredService)
            .where(RegisteredService.name == payload.name)
            .values(
                base_url=payload.base_url,
                health_url=payload.health_url,
                description=payload.description,
                instructions=payload.instructions,
                meta=payload.meta,
                is_active=True,
                status=ServiceStatus.HEALTHY,
                last_seen=datetime.now(timezone.utc),
            )
        )
        await db.refresh(service)
    else:
        service = RegisteredService(
            name=payload.name,
            service_type=payload.service_type,
            base_url=payload.base_url,
            health_url=payload.health_url,
            description=payload.description,
            instructions=payload.instructions,
            meta=payload.meta,
            status=ServiceStatus.HEALTHY,
            last_seen=datetime.now(timezone.utc),
        )
        db.add(service)
        await db.flush()
        await db.refresh(service)

    # Log initial instructions
    if payload.instructions:
        db.add(ServiceInstruction(
            service_id=service.id,
            service_name=service.name,
            instruction=payload.instructions,
            set_by="registration",
        ))

    return service


# ── Heartbeat ─────────────────────────────────────────────────────────────────

@router.post(
    "/heartbeat",
    status_code=200,
    dependencies=[Depends(verify_control_key)],
    summary="Service keep-alive ping",
)
async def heartbeat(
    payload: HeartbeatRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Services call this every 30 seconds. Agent marks them DOWN if missed for > 90s.
    """
    result = await db.execute(
        select(RegisteredService).where(RegisteredService.name == payload.name)
    )
    service = result.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=404, detail="Service not registered")

    await db.execute(
        update(RegisteredService)
        .where(RegisteredService.name == payload.name)
        .values(
            status=payload.status,
            last_seen=datetime.now(timezone.utc),
            meta=payload.meta or service.meta,
        )
    )
    return {"status": "ok", "service": payload.name}


# ── List / Get ────────────────────────────────────────────────────────────────

@router.get(
    "/services",
    response_model=list[ServiceResponse],
    summary="List all registered services",
)
async def list_services(db: AsyncSession = Depends(get_db)) -> list[ServiceResponse]:
    result = await db.execute(
        select(RegisteredService)
        .where(RegisteredService.is_active == True)  # noqa: E712
        .order_by(RegisteredService.registered_at)
    )
    return list(result.scalars().all())


@router.get(
    "/services/{name}",
    response_model=ServiceResponse,
    summary="Get a specific service",
)
async def get_service(name: str, db: AsyncSession = Depends(get_db)) -> ServiceResponse:
    result = await db.execute(
        select(RegisteredService).where(RegisteredService.name == name)
    )
    service = result.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    return service


# ── Update instructions ───────────────────────────────────────────────────────

@router.patch(
    "/services/{name}/instructions",
    response_model=ServiceResponse,
    summary="Update how the agent manages this service",
)
async def update_instructions(
    name: str,
    payload: ServiceUpdateInstructions,
    db: AsyncSession = Depends(get_db),
) -> ServiceResponse:
    """
    User sends natural-language instructions here to change agent behaviour.
    Example: "If this service's error rate exceeds 10%, restart it and alert me."
    """
    result = await db.execute(
        select(RegisteredService).where(RegisteredService.name == name)
    )
    service = result.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    await db.execute(
        update(RegisteredService)
        .where(RegisteredService.name == name)
        .values(instructions=payload.instructions)
    )

    # Log the change
    db.add(ServiceInstruction(
        service_id=service.id,
        service_name=name,
        instruction=payload.instructions,
        set_by="user",
    ))

    await db.refresh(service)
    return service


# ── Deregister ────────────────────────────────────────────────────────────────

@router.delete(
    "/services/{name}",
    status_code=204,
    dependencies=[Depends(verify_control_key)],
    summary="Deregister a service",
)
async def deregister_service(
    name: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(
        select(RegisteredService).where(RegisteredService.name == name)
    )
    service = result.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    await db.execute(
        update(RegisteredService)
        .where(RegisteredService.name == name)
        .values(is_active=False, status=ServiceStatus.DOWN)
    )
