import os
from pathlib import Path

# Must be set before any app import so pydantic-settings picks up the test DB URL
_TEST_DB_FILE = Path(__file__).parent.parent / "test_sentinel.db"
os.environ["SENTINEL_DB_URL"] = f"sqlite+aiosqlite:///{_TEST_DB_FILE}"

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport


# ---------------------------------------------------------------------------
# Session-scoped: create / drop schema once per test run
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="session", autouse=True)
async def init_db():
    from app.database import engine, Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    _TEST_DB_FILE.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Function-scoped: wipe all rows before each test for isolation
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(autouse=True)
async def reset_tables():
    from app.database import engine, Base

    async with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())
    yield


# ---------------------------------------------------------------------------
# Shared DB session (same connection as the overridden get_db)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def db_session():
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        yield session


# ---------------------------------------------------------------------------
# HTTP test client with get_db overridden to the test session
# Note: lifespan runs on each client creation (seeds builtin rules & settings)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def builtin_rules(db_session):
    """Seed builtin.json rules into the test DB (replaces lifespan seeding)."""
    import json
    from pathlib import Path
    from app.models.rule import Rule

    builtin_json = Path(__file__).parent.parent / "app" / "rules" / "builtin.json"
    entries = json.loads(builtin_json.read_text(encoding="utf-8"))
    for entry in entries:
        rule = Rule(
            name=entry["name"],
            pii_type=entry["pii_type"],
            detection_method=entry["detection_method"],
            column_patterns=json.dumps(entry.get("column_patterns", [])),
            data_patterns=json.dumps(entry.get("data_patterns", [])),
            is_builtin=True,
            is_active=True,
        )
        db_session.add(rule)
    await db_session.commit()
    return entries


@pytest_asyncio.fixture
async def client(db_session):
    from app.main import app
    from app.dependencies import get_db

    async def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
