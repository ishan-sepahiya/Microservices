"""routes.py — Payment Service"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from models import Payment, PaymentCreate, PaymentResponse, PaymentStatus

router = APIRouter(prefix="/payments", tags=["Payments"])

@router.post("/", response_model=PaymentResponse, status_code=201)
async def create_payment(payload: PaymentCreate, db: AsyncSession = Depends(get_db)):
    payment = Payment(**payload.model_dump())
    db.add(payment)
    await db.flush()
    await db.refresh(payment)
    # TODO: integrate real payment gateway (Stripe, etc.) here
    return payment

@router.get("/", response_model=dict)
async def list_payments(
    user_id: uuid.UUID | None = Query(default=None),
    status: PaymentStatus | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    q = select(Payment)
    if user_id:
        q = q.where(Payment.user_id == user_id)
    if status:
        q = q.where(Payment.status == status)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    result = await db.execute(q.order_by(Payment.created_at.desc()).offset(skip).limit(limit))
    return {"total": total, "items": [PaymentResponse.model_validate(p) for p in result.scalars().all()]}

@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(payment_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Payment).where(Payment.id == payment_id))
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Payment not found")
    return p

@router.post("/{payment_id}/complete", response_model=PaymentResponse)
async def complete_payment(payment_id: uuid.UUID, reference: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Payment).where(Payment.id == payment_id))
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Payment not found")
    await db.execute(update(Payment).where(Payment.id == payment_id)
                     .values(status=PaymentStatus.COMPLETED, reference=reference))
    await db.refresh(p)
    return p

@router.post("/{payment_id}/refund", response_model=PaymentResponse)
async def refund_payment(payment_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Payment).where(Payment.id == payment_id))
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Payment not found")
    if p.status != PaymentStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Only completed payments can be refunded")
    await db.execute(update(Payment).where(Payment.id == payment_id).values(status=PaymentStatus.REFUNDED))
    await db.refresh(p)
    return p
