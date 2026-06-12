"""Category mapping management API routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.ingestion.category_sync import CategorySyncService
from app.models.category_mapping import CategoryMapping
from app.schemas.spending import CategoryMappingResponse, CategoryMappingUpdate

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("", response_model=list[CategoryMappingResponse])
async def list_categories(
    _user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CategoryMapping).order_by(
            CategoryMapping.parent_category, CategoryMapping.normalized_category
        )
    )
    return [CategoryMappingResponse.from_model(m) for m in result.scalars().all()]


@router.put("/{category_id}", response_model=CategoryMappingResponse)
async def update_category(
    category_id: str,
    body: CategoryMappingUpdate,
    _user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CategoryMapping).where(CategoryMapping.id == category_id)
    )
    mapping = result.scalar_one_or_none()
    if not mapping:
        raise HTTPException(status_code=404, detail="Category mapping not found")

    update_data = body.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(mapping, key, value)

    await db.commit()
    await db.refresh(mapping)
    return CategoryMappingResponse.from_model(mapping)


@router.post("/sync")
async def trigger_category_sync(
    _user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = CategorySyncService(db)
    count = await svc.sync_from_transactions()
    await db.commit()
    return {"message": f"Synced {count} categories", "count": count}
