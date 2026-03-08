import uuid

from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.database import get_db
from app.models.user import User
from app.schemas.user import UserResponse, UpdateUserRequest, ChangePasswordRequest, UserInternal
from app.services.auth import decode_token, hash_password, verify_password

router = APIRouter(prefix="/api/users", tags=["Users"])
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    result = await db.execute(
        select(User)
        .where(User.id == uuid.UUID(payload["sub"]))
        .options(selectinload(User.subscription))
    )
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_me(
    body: UpdateUserRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.username and body.username != current_user.username:
        existing = await db.execute(select(User).where(User.username == body.username))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Username already taken")
        current_user.username = body.username

    if body.full_name is not None:
        current_user.full_name = body.full_name

    if body.avatar_url is not None:
        current_user.avatar_url = body.avatar_url

    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.post("/me/change-password", status_code=204)
async def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    current_user.hashed_password = hash_password(body.new_password)
    await db.commit()


# ── Internal endpoint (called by other services only) ─────────────────────────

@router.get("/internal/{user_id}", response_model=UserInternal, include_in_schema=False)
async def get_user_internal(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Internal endpoint — not exposed publicly via gateway"""
    result = await db.execute(
        select(User).where(User.id == user_id).options(selectinload(User.subscription))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserInternal(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        subscription_plan=user.subscription.plan.value if user.subscription else "free",
    )
