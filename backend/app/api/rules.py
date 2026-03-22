import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.dependencies import get_db
from app.models.rule import Rule, RuleCreate, RuleUpdate, RuleRead

router = APIRouter(prefix="/rules", tags=["rules"])


@router.get("", response_model=list[RuleRead])
async def list_rules(db: AsyncSession = Depends(get_db)) -> list[RuleRead]:
    result = await db.execute(select(Rule).order_by(Rule.name))
    return list(result.scalars().all())


@router.post("", response_model=RuleRead, status_code=201)
async def create_rule(
    payload: RuleCreate,
    db: AsyncSession = Depends(get_db),
) -> RuleRead:
    rule = Rule(
        name=payload.name,
        pii_type=payload.pii_type,
        detection_method=payload.detection_method,
        column_patterns=json.dumps(payload.column_patterns) if payload.column_patterns else None,
        data_patterns=json.dumps(payload.data_patterns) if payload.data_patterns else None,
        is_builtin=False,
        is_active=payload.is_active,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.get("/{rule_id}", response_model=RuleRead)
async def get_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
) -> RuleRead:
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule


@router.put("/{rule_id}", response_model=RuleRead)
async def update_rule(
    rule_id: int,
    payload: RuleUpdate,
    db: AsyncSession = Depends(get_db),
) -> RuleRead:
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")

    update_data = payload.model_dump(exclude_unset=True)
    if "column_patterns" in update_data:
        rule.column_patterns = json.dumps(update_data.pop("column_patterns"))
    if "data_patterns" in update_data:
        rule.data_patterns = json.dumps(update_data.pop("data_patterns"))
    for field, value in update_data.items():
        setattr(rule, field, value)

    await db.commit()
    await db.refresh(rule)
    return rule


@router.delete("/{rule_id}", status_code=204)
async def delete_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")
    if rule.is_builtin:
        raise HTTPException(status_code=400, detail="Cannot delete built-in rules")
    await db.delete(rule)
    await db.commit()
