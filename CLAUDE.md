# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Is

**Sentinel** — 데이터베이스 개인정보(PII) 탐지 시스템. MySQL, MongoDB, ClickHouse, Oracle, Impala, AWS RDS를 스캔하여 PII를 식별하는 사이드바 형태의 웹 어플리케이션.

- **Frontend**: Nuxt 4 + Vue 3 + Tailwind CSS (Bun)
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
uv sync                                                      # 의존성 설치
uv run uvicorn app.main:app --reload --port 8000            # 개발 서버
uv run pytest                                                # 전체 테스트
uv run pytest tests/test_foo.py                             # 단일 테스트 파일
uv run alembic upgrade head                                  # DB 마이그레이션 적용
uv run alembic revision --autogenerate -m "description"     # 마이그레이션 생성
```

### Docker (샘플 DB)
```bash
docker-compose up -d   # MySQL, MongoDB, ClickHouse 컨테이너 + 샘플 데이터
```

## Architecture

```
sentinel/
├── app/                          # Nuxt 4 Frontend
│   ├── layouts/default.vue       # 사이드바 레이아웃 + Persona 모드 배너
│   ├── pages/
│   │   ├── index.vue             # Dashboard (스탯 카드, Trend 차트)
│   │   ├── connections/          # DB 연결 CRUD (index, new, [id])
│   │   ├── scans/                # 스캔 (index, new, [id])
│   │   ├── rules/                # PII 규칙 (index, new, [id])
│   │   ├── deep-inspect/         # 전체 데이터 검사 (?conn=ID&schema=X&table=Y)
│   │   ├── classification/       # PII 컬럼 분류 (connection 필터, Deep Inspect 연동)
│   │   ├── reports/              # 리포트 + export
│   │   ├── users/                # 사용자 관리 (LDAP 연동, 잠금/해제)
│   │   ├── settings/             # 설정 (RBAC, Persona, LDAP, SSO, Branding 등)
│   │   └── audit-log/            # 감사 로그
│   └── composables/
│       ├── useApi.ts             # $fetch wrapper → /api/*
│       ├── useUsers.ts           # 사용자 상태 (잠금/해제/lock, audit events)
│       ├── usePersona.ts         # RBAC Persona 모드 (admin/analyst/viewer)
│       ├── useBranding.ts        # 로고/앱명 커스텀
│       └── useTheme.ts           # 라이트/다크 테마
│
├── backend/
│   ├── pyproject.toml            # uv 의존성 관리
│   ├── app/
│   │   ├── main.py               # FastAPI 앱, CORS, lifespan (DB 자동 생성 + 규칙 시드)
│   │   ├── api/                  # API 라우터
│   │   │   ├── connections.py    # CRUD + /test + /schemas + /tables
│   │   │   ├── scans.py          # CRUD + BackgroundTask 실행 + 예약
│   │   │   ├── rules.py          # CRUD
│   │   │   ├── dashboard.py      # summary (스캔 상태별 카운트 포함) + recent-activity
│   │   │   ├── classifications.py # PII 컬럼 분류 CRUD
│   │   │   ├── deep_inspect.py   # 전체 테이블 검사 API
│   │   │   ├── reports.py        # PII 인벤토리 + CSV/Excel/PDF export + daily-trend
│   │   │   ├── settings.py       # GET/PUT/bulk
│   │   │   └── audit_log.py      # GET + POST (수동 기록)
│   │   ├── connectors/           # DB 어댑터
│   │   │   ├── base.py           # DatabaseConnector 추상 인터페이스
│   │   │   ├── factory.py        # create_connector(db_type, config)
│   │   │   ├── mysql.py          # aiomysql
│   │   │   ├── mongodb.py        # motor
│   │   │   └── clickhouse.py     # clickhouse-connect (list_schemas는 실제 DB 목록 조회)
│   │   ├── detectors/            # PII 탐지 엔진
│   │   │   ├── column_name.py    # 컬럼명 휴리스틱 (신뢰도 0.6~0.8)
│   │   │   ├── regex_pattern.py  # 정규식 매칭
│   │   │   └── orchestrator.py   # 두 탐지기 조율 + 신뢰도 병합
│   │   ├── services/
│   │   │   ├── scan_service.py   # 스캔 실행 오케스트레이션
│   │   │   ├── scheduler_service.py  # APScheduler 예약 스캔
│   │   │   ├── audit_service.py  # audit_log 기록 헬퍼
│   │   │   └── deep_inspect_service.py
│   │   └── rules/builtin.json    # 내장 PII 규칙 10종 시드
│   └── data/                     # sentinel.db (SQLite, gitignored)
│
├── docker-compose.yml            # MySQL, MongoDB, ClickHouse 샘플 DB
├── nuxt.config.ts                # /api/** proxy → localhost:8000
└── backend/.env.example          # 환경변수 템플릿
```

## Backend API Endpoints

```
GET  /api/health

GET/POST              /api/connections
GET/PUT/DELETE        /api/connections/{id}
POST                  /api/connections/{id}/test
GET                   /api/connections/{id}/schemas
GET                   /api/connections/{id}/tables?schema=xxx

GET/POST              /api/scans
GET                   /api/scans/{id}
POST                  /api/scans/{id}/cancel

GET/POST              /api/rules
GET/PUT/DELETE        /api/rules/{id}

GET                   /api/dashboard/summary          # scans_completed/pending/cancelled 포함
GET                   /api/dashboard/recent-activity

GET                   /api/classifications
PUT                   /api/classifications/{id}

GET                   /api/deep-inspect/jobs
POST                  /api/deep-inspect/jobs
GET                   /api/deep-inspect/jobs/{id}

GET                   /api/reports/pii-inventory
GET                   /api/reports/daily-trend?days=30|hours=1
GET                   /api/reports/export?format=csv|excel|pdf

GET/PUT               /api/settings
POST                  /api/settings/bulk

GET                   /api/audit-log
POST                  /api/audit-log

GET                   /api/deep-inspect/connections/{id}/schemas
GET                   /api/deep-inspect/connections/{id}/tables?schema=xxx
```

## Key Patterns

### Persona Mode (RBAC 테스트)
`usePersona()` composable로 역할 전환. `default.vue`에서 `isReadOnly` 계산 후 read-only 페이지에 투명 오버레이를 씌워 클릭 차단:
```typescript
const { persona, isPersonaMode, canWrite } = usePersona()
// Admin: 전체 쓰기 / Analyst: scans·rules만 쓰기 / Viewer: 전체 읽기 전용
```

### User Lock/Unlock
`useUsers()` composable에서 `manuallyLocked`/`manuallyUnlocked` 배열로 상태 관리. `isLocked()` 우선순위: manuallyLocked > manuallyUnlocked > 90일 미로그인 자동 잠금.

### ClickHouse Connector
`list_schemas()`는 config의 database 값 무시하고 `SHOW DATABASES`로 실제 목록 반환 (`default` 스키마 문제 방지).

### Deep Inspect 연동
Classification 페이지에서 Deep Inspect 버튼 클릭 시 `connection_id`를 `?conn=ID` 쿼리 파라미터로 전달 → Deep Inspect 페이지가 `onMounted`에서 자동 선택.

## Environment Setup

```bash
cp backend/.env.example backend/.env
# ENCRYPTION_KEY 생성:
cd backend && uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## DB Schema (SQLite)

`connections`, `scans`, `scan_results`, `rules`, `classifications`, `settings`, `audit_logs`, `deep_inspect_jobs`

첫 실행 시 `main.py` lifespan에서 자동 생성 + `builtin.json` 규칙 시드.
