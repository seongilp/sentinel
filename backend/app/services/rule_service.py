import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.rule import Rule, RuleCreate, RuleUpdate


async def get_all(db: AsyncSession) -> list[Rule]:
    result = await db.execute(select(Rule).order_by(Rule.name))
    return list(result.scalars().all())


async def get_by_id(db: AsyncSession, rule_id: int) -> Rule | None:
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    return result.scalar_one_or_none()


async def create(db: AsyncSession, payload: RuleCreate) -> Rule:
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


async def update(db: AsyncSession, rule: Rule, payload: RuleUpdate) -> Rule:
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


async def delete(db: AsyncSession, rule: Rule) -> None:
    await db.delete(rule)
    await db.commit()
