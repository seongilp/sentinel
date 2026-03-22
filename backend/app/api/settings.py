from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.dependencies import get_db
from app.models.setting import Setting, SettingUpdate, SettingRead

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=list[SettingRead])
async def list_settings(db: AsyncSession = Depends(get_db)) -> list[SettingRead]:
    result = await db.execute(select(Setting).order_by(Setting.key))
    return list(result.scalars().all())


@router.post("/bulk", response_model=list[SettingRead])
async def bulk_update_settings(
    payload: dict[str, str | None],
    db: AsyncSession = Depends(get_db),
) -> list[SettingRead]:
    updated = []
    for key, value in payload.items():
        result = await db.execute(select(Setting).where(Setting.key == key))
        setting = result.scalar_one_or_none()
        if setting is None:
            setting = Setting(key=key, value=value)
            db.add(setting)
        else:
            setting.value = value
        updated.append(setting)
    await db.commit()
    for s in updated:
        await db.refresh(s)
    return updated


@router.get("/{key}", response_model=SettingRead)
async def get_setting(
    key: str,
    db: AsyncSession = Depends(get_db),
) -> SettingRead:
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()
    if setting is None:
        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")
    return setting


@router.put("/{key}", response_model=SettingRead)
async def update_setting(
    key: str,
    payload: SettingUpdate,
    db: AsyncSession = Depends(get_db),
) -> SettingRead:
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()
    if setting is None:
        # create on first write
        setting = Setting(key=key, value=payload.value)
        db.add(setting)
    else:
        setting.value = payload.value

    await db.commit()
    await db.refresh(setting)
    return setting
