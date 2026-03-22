# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Is

**Sentinel** — 데이터베이스 개인정보(PII) 탐지 시스템. Oracle, MySQL, MongoDB, ClickHouse를 스캔하여 PII를 식별하는 사이드바 형태의 웹 어플리케이션.

- **Frontend**: Nuxt 4 + Vue 3 + Nuxt UI v4 (Bun)
- **Backend**: Python FastAPI + SQLAlchemy + SQLite (uv)
- Frontend(`localhost:3000`) → `/api/**` proxy → Backend(`localhost:8000`)

## Commands

### Development
```bash
bun run dev:all        # 프론트엔드 + 백엔드 동시 실행 (권장)
bun run dev            # Nuxt 프론트엔드만 (port 3000)
bun run dev:backend    # FastAPI 백엔드만 (port 8000)
```

### Frontend (Bun)
```bash
bun run build          # 프로덕션 빌드
bun run preview        # 프로덕션 빌드 미리보기
bun run postinstall    # .nuxt/ 타입 재생성 (모듈 추가 후 필요)
```

### Backend (uv)
```bash
cd backend
uv sync                         # 의존성 설치
uv run uvicorn app.main:app --reload --port 8000   # 개발 서버
uv run pytest                   # 테스트 실행
uv run pytest tests/test_foo.py # 단일 테스트 파일
uv run alembic upgrade head     # DB 마이그레이션 적용
uv run alembic revision --autogenerate -m "description"  # 마이그레이션 생성
```

## Architecture

```
sentinel/
├── app/                          # Nuxt 4 Frontend
│   ├── layouts/default.vue       # 사이드바 레이아웃 (8개 메뉴)
│   ├── pages/                    # 파일 기반 라우팅
│   │   ├── index.vue             # Dashboard
│   │   ├── connections/          # DB 연결 관리 (index, new, [id])
│   │   ├── scans/                # 스캔 작업 (index, new, [id])
│   │   ├── rules/                # PII 규칙 (index, new, [id])
│   │   ├── classification/       # 데이터 분류
│   │   ├── reports/              # 리포트
│   │   ├── settings/             # 설정
│   │   └── audit-log/            # 감사 로그
│   └── composables/
│       └── useApi.ts             # $fetch wrapper → /api/*
│
├── backend/
│   ├── pyproject.toml            # uv 의존성 관리
│   ├── app/
│   │   ├── main.py               # FastAPI 앱, CORS, lifespan
│   │   ├── config.py             # Pydantic Settings (.env)
│   │   ├── database.py           # SQLAlchemy async engine + session
│   │   ├── api/                  # API 라우터 (8개 도메인)
│   │   ├── models/               # SQLAlchemy ORM + Pydantic 스키마
│   │   ├── services/             # 비즈니스 로직
│   │   ├── connectors/           # DB 어댑터 (MySQL 구현, 나머지 Phase 2)
│   │   │   ├── base.py           # DatabaseConnector 추상 인터페이스
│   │   │   ├── factory.py        # create_connector(db_type, config)
│   │   │   └── mysql.py          # aiomysql 기반 MySQL 커넥터
│   │   ├── detectors/            # PII 탐지 엔진
│   │   │   ├── column_name.py    # 컬럼명 휴리스틱 (신뢰도 0.6~0.8)
│   │   │   ├── regex_pattern.py  # 정규식 매칭 (신뢰도 match_ratio)
│   │   │   └── orchestrator.py   # 두 탐지기 조율 + 신뢰도 병합
│   │   └── rules/builtin.json    # 내장 PII 규칙 10종
│   └── data/                     # sentinel.db (SQLite, gitignored)
│
├── nuxt.config.ts                # @nuxt/ui 모듈, /api/** proxy 설정
├── .env.example                  # 환경변수 템플릿
└── CLAUDE.md
```

## Backend API Endpoints

```
GET  /api/health
GET/POST              /api/connections
GET/PUT/DELETE        /api/connections/{id}
POST                  /api/connections/{id}/test
GET/POST              /api/scans
GET                   /api/scans/{id}
POST                  /api/scans/{id}/cancel
GET/POST              /api/rules
GET/PUT/DELETE        /api/rules/{id}
GET                   /api/dashboard/summary
GET                   /api/dashboard/recent-activity
GET                   /api/classifications
PUT                   /api/classifications/{id}
GET                   /api/reports/pii-inventory
GET                   /api/reports/export?format=csv|excel|pdf
GET/PUT               /api/settings
GET                   /api/audit-log
```

## Key Patterns

### Frontend API calls
모든 API 호출은 `useApi()` composable을 통해 `/api/*`로 요청 → Nuxt proxy가 백엔드 8000포트로 전달:
```typescript
const api = useApi()
const data = await api.get<ConnectionRead[]>('/connections')
await api.post('/connections', payload)
```

### Backend DB Session
FastAPI dependency injection으로 세션 주입:
```python
async def get_connections(db: AsyncSession = Depends(get_db)):
    ...
```

### New DB Connector (Phase 2)
`backend/app/connectors/base.py`의 `DatabaseConnector` ABC를 상속하고 `factory.py`의 `create_connector()`에 등록.

### PII Detection
스캔 실행 시 `DetectionOrchestrator`가 `ColumnNameDetector`(컬럼명 패턴) → `RegexPatternDetector`(데이터 샘플링) 순서로 실행. 신뢰도 0.5 이상만 `scan_results`에 저장.

## Environment Setup

```bash
cp .env.example .env
# ENCRYPTION_KEY 생성:
cd backend && uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## DB Schema (SQLite)

`connections`, `scans`, `scan_results`, `rules`, `classifications`, `settings`, `audit_logs`

첫 실행 시 `main.py` lifespan에서 자동 생성 + builtin.json 규칙 시드.
