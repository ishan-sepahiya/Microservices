"""routes.py — Product Service"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from models import Product, ProductCreate, ProductResponse, ProductUpdate

router = APIRouter(prefix="/products", tags=["Products"])

@router.post("/", response_model=ProductResponse, status_code=201)
async def create_product(payload: ProductCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Product).where(Product.sku == payload.sku))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="SKU already exists")
    product = Product(**payload.model_dump())
    db.add(product)
    await db.flush()
    await db.refresh(product)
    return product

@router.get("/", response_model=dict)
async def list_products(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    active_only: bool = Query(default=True),
    db: AsyncSession = Depends(get_db),
):
    q = select(Product)
    if active_only:
        q = q.where(Product.is_active == True)  # noqa
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    result = await db.execute(q.order_by(Product.created_at.desc()).offset(skip).limit(limit))
    items = [ProductResponse.model_validate(p) for p in result.scalars().all()]
    return {"total": total, "items": items}

@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await _get_or_404(db, product_id)

@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(product_id: uuid.UUID, payload: ProductUpdate, db: AsyncSession = Depends(get_db)):
    product = await _get_or_404(db, product_id)
    data = payload.model_dump(exclude_unset=True)
    if data:
        await db.execute(update(Product).where(Product.id == product_id).values(**data))
        await db.refresh(product)
    return product

@router.delete("/{product_id}", status_code=204)
async def delete_product(product_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    product = await _get_or_404(db, product_id)
    await db.execute(update(Product).where(Product.id == product_id).values(is_active=False))

async def _get_or_404(db, product_id):
    result = await db.execute(select(Product).where(Product.id == product_id))
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    return p
