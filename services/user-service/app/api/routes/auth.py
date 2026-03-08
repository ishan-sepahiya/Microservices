from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.user import User, Subscription, RefreshToken
from app.schemas.user import RegisterRequest, LoginRequest, TokenResponse, RefreshTokenRequest
from app.services.auth import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from app.services.events import publish_user_registered

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check duplicate email
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    # Check duplicate username
    existing_username = await db.execute(select(User).where(User.username == body.username))
    if existing_username.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Username already taken")

    # Create user
    user = User(
        email=body.email,
        username=body.username,
        full_name=body.full_name,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    await db.flush()  # Get user.id without committing

    # Create free subscription
    subscription = Subscription(user_id=user.id)
    db.add(subscription)

    # Create tokens
    access_token, expires_in = create_access_token(str(user.id), user.email, user.role.value)
    refresh_token_str, refresh_expires = create_refresh_token(str(user.id))

    refresh_token = RefreshToken(
        user_id=user.id,
        token=refresh_token_str,
        expires_at=refresh_expires,
    )
    db.add(refresh_token)
    await db.commit()

    # Publish event (notification service will send welcome email)
    await publish_user_registered(str(user.id), user.email, user.full_name)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token_str,
        expires_in=expires_in,
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")

    access_token, expires_in = create_access_token(str(user.id), user.email, user.role.value)
    refresh_token_str, refresh_expires = create_refresh_token(str(user.id))

    refresh_token = RefreshToken(
        user_id=user.id,
        token=refresh_token_str,
        expires_at=refresh_expires,
    )
    db.add(refresh_token)
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token_str,
        expires_in=expires_in,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token == body.refresh_token,
            RefreshToken.is_revoked == False,
        )
    )
    stored_token = result.scalar_one_or_none()
    if not stored_token:
        raise HTTPException(status_code=401, detail="Refresh token revoked or not found")

    if stored_token.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Refresh token expired")

    # Revoke old token
    stored_token.is_revoked = True

    # Get user
    user_result = await db.execute(select(User).where(User.id == stored_token.user_id))
    user = user_result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    # Issue new tokens
    access_token, expires_in = create_access_token(str(user.id), user.email, user.role.value)
    new_refresh_str, new_refresh_expires = create_refresh_token(str(user.id))

    new_refresh_token = RefreshToken(
        user_id=user.id,
        token=new_refresh_str,
        expires_at=new_refresh_expires,
    )
    db.add(new_refresh_token)
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_str,
        expires_in=expires_in,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token == body.refresh_token)
    )
    token = result.scalar_one_or_none()
    if token:
        token.is_revoked = True
        await db.commit()
