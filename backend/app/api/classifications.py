from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.dependencies import get_db
from app.models.classification import Classification, ClassificationUpdate, ClassificationRead

router = APIRouter(prefix="/classifications", tags=["classifications"])


@router.get("", response_model=list[ClassificationRead])
async def list_classifications(db: AsyncSession = Depends(get_db)) -> list[ClassificationRead]:
    result = await db.execute(select(Classification).order_by(Classification.created_at.desc()))
    return list(result.scalars().all())


@router.put("/{classification_id}", response_model=ClassificationRead)
async def update_classification(
    classification_id: int,
    payload: ClassificationUpdate,
    db: AsyncSession = Depends(get_db),
) -> ClassificationRead:
    result = await db.execute(select(Classification).where(Classification.id == classification_id))
    classification = result.scalar_one_or_none()
    if classification is None:
        raise HTTPException(status_code=404, detail="Classification not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(classification, field, value)

    await db.commit()
    await db.refresh(classification)
    return classification
