import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import create_tables, AsyncSessionLocal
from app.models.rule import Rule
from app.models.setting import Setting

from app.api import (
    connections,
    scans,
    rules,
    dashboard,
    reports,
    classifications,
    settings as settings_router,
    audit_log,
    deep_inspect,
)

_BUILTIN_JSON = Path(__file__).parent / "rules" / "builtin.json"

DEFAULT_SETTINGS = [
    # Scan
    {"key": "scan.default_sample_size", "value": "100", "description": "스캔 시 컬럼당 샘플링할 최대 행 수"},
    {"key": "scan.confidence_threshold", "value": "0.5", "description": "PII 탐지 결과를 저장할 최소 신뢰도 (0.0~1.0)"},
    {"key": "scan.timeout_seconds", "value": "30", "description": "DB 연결 및 쿼리 타임아웃 (초)"},
    {"key": "scan.max_concurrent_tables", "value": "5", "description": "동시에 스캔할 최대 테이블 수"},
    {"key": "scan.exclude_system_schemas", "value": "true", "description": "시스템 스키마(information_schema 등) 제외 여부"},
    # Notifications
    {"key": "notification.slack_webhook_url", "value": "", "description": "스캔 완료/위험 탐지 시 알림을 보낼 Slack Webhook URL"},
    {"key": "notification.email_recipients", "value": "", "description": "알림 이메일 수신자 (쉼표로 구분)"},
    {"key": "notification.notify_on_scan_complete", "value": "false", "description": "스캔 완료 시 알림"},
    {"key": "notification.notify_on_high_risk", "value": "true", "description": "High Risk PII 탐지 시 알림"},
    # System
    {"key": "system.data_retention_days", "value": "90", "description": "스캔 결과 보관 기간 (일)"},
    {"key": "system.max_scan_history", "value": "100", "description": "보관할 최대 스캔 이력 수"},
    # Branding
    {"key": "system.app_name", "value": "Sentinel", "description": "앱 표시 이름"},
    {"key": "system.logo_data", "value": "", "description": "커스텀 로고 이미지 (base64 data URL)"},
    # Kafka
    {"key": "kafka.enabled", "value": "false", "description": "Kafka 이벤트 스트리밍 활성화"},
    {"key": "kafka.brokers", "value": "", "description": "Kafka Bootstrap Brokers (쉼표 구분)"},
    {"key": "kafka.topic", "value": "sentinel.pii-events", "description": "이벤트를 발행할 Kafka 토픽"},
    {"key": "kafka.security_protocol", "value": "PLAINTEXT", "description": "PLAINTEXT|SSL|SASL_PLAINTEXT|SASL_SSL"},
    {"key": "kafka.sasl_mechanism", "value": "", "description": "SASL 인증 방식 (PLAIN|SCRAM-SHA-256|SCRAM-SHA-512)"},
    {"key": "kafka.sasl_username", "value": "", "description": "SASL 사용자명"},
    {"key": "kafka.sasl_password", "value": "", "description": "SASL 비밀번호"},
    {"key": "kafka.ssl_ca_location", "value": "", "description": "SSL CA 인증서 경로"},
    {"key": "kafka.client_id", "value": "sentinel", "description": "Kafka 클라이언트 ID"},
    # Splunk / Syslog
    {"key": "splunk.enabled", "value": "false", "description": "Splunk/Syslog 로그 포워딩 활성화"},
    {"key": "splunk.mode", "value": "hec", "description": "전송 방식: hec|syslog"},
    {"key": "splunk.hec_url", "value": "", "description": "Splunk HEC URL"},
    {"key": "splunk.hec_token", "value": "", "description": "Splunk HEC Token"},
    {"key": "splunk.hec_index", "value": "sentinel", "description": "Splunk HEC Index"},
    {"key": "splunk.hec_source", "value": "sentinel:pii", "description": "Splunk HEC Source"},
    {"key": "splunk.syslog_host", "value": "", "description": "Syslog 서버 호스트"},
    {"key": "splunk.syslog_port", "value": "514", "description": "Syslog 포트 (기본: 514)"},
    {"key": "splunk.syslog_protocol", "value": "UDP", "description": "Syslog 프로토콜: UDP|TCP|TLS"},
]


async def _seed_default_settings() -> None:
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select

        for s in DEFAULT_SETTINGS:
            existing = await session.execute(select(Setting).where(Setting.key == s["key"]))
            if existing.scalar_one_or_none() is None:
                session.add(Setting(**s))
        await session.commit()


async def _seed_builtin_rules() -> None:
    if not _BUILTIN_JSON.exists():
        return

    raw = json.loads(_BUILTIN_JSON.read_text(encoding="utf-8"))

    async with AsyncSessionLocal() as db:
        from sqlalchemy import select

        result = await db.execute(select(Rule).where(Rule.is_builtin == True))  # noqa: E712
        existing_types = {r.pii_type for r in result.scalars().all()}

        for entry in raw:
            if entry["pii_type"] in existing_types:
                continue
            rule = Rule(
                name=entry["name"],
                pii_type=entry["pii_type"],
                detection_method=entry["detection_method"],
                column_patterns=json.dumps(entry.get("column_patterns", [])),
                data_patterns=json.dumps(entry.get("data_patterns", [])),
                is_builtin=True,
                is_active=True,
            )
            db.add(rule)

        await db.commit()


async def _migrate_scan_columns() -> None:
    """Add new columns to existing tables if not present (SQLite-safe)."""
    from app.database import engine
    from sqlalchemy import text
    migrations = [
        ("scans",      "cron_expression", "ALTER TABLE scans ADD COLUMN cron_expression VARCHAR(100)"),
        ("scans",      "is_scheduled",    "ALTER TABLE scans ADD COLUMN is_scheduled BOOLEAN DEFAULT FALSE"),
        ("audit_logs", "user_id",         "ALTER TABLE audit_logs ADD COLUMN user_id VARCHAR(255) NOT NULL DEFAULT 'system'"),
        ("audit_logs", "menu",            "ALTER TABLE audit_logs ADD COLUMN menu VARCHAR(100)"),
        ("audit_logs", "result",          "ALTER TABLE audit_logs ADD COLUMN result VARCHAR(50) NOT NULL DEFAULT 'success'"),
    ]
    async with engine.begin() as conn:
        for _table, _col, ddl in migrations:
            try:
                await conn.execute(text(ddl))
            except Exception:
                pass  # Column already exists


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await create_tables()
    await _migrate_scan_columns()
    await _seed_builtin_rules()
    await _seed_default_settings()

    from app.services.scheduler_service import scheduler, restore_scheduled_scans
    scheduler.start()
    await restore_scheduled_scans()

    yield

    scheduler.shutdown(wait=False)


app = FastAPI(
    title="Sentinel API",
    description="PII detection and data governance backend",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routers under /api prefix
for _router in (
    connections.router,
    scans.router,
    rules.router,
    dashboard.router,
    reports.router,
    classifications.router,
    settings_router.router,
    audit_log.router,
    deep_inspect.router,
):
    app.include_router(_router, prefix="/api")


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
