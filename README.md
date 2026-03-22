# Sentinel

데이터베이스 내 개인정보(PII)를 자동 탐지하는 웹 어플리케이션.
Oracle, MySQL, MongoDB, ClickHouse, Impala, AWS RDS를 지원하며 컬럼명 휴리스틱 + 정규식 패턴 매칭 방식으로 PII를 식별합니다.

## Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Nuxt 4, Vue 3, Tailwind CSS |
| Backend | Python 3.12, FastAPI, SQLAlchemy, SQLite |
| Package Mgmt | Bun (frontend), uv (backend) |
| DB Drivers | aiomysql, motor (MongoDB), clickhouse-connect |
| Scheduler | APScheduler |

## Quick Start

### 1. 환경변수 설정

```bash
cp backend/.env.example backend/.env
# ENCRYPTION_KEY 생성:
cd backend && uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 2. 의존성 설치

```bash
bun install
cd backend && uv sync
```

### 3. 개발 서버 실행

```bash
bun run dev:all   # 프론트(3000) + 백엔드(8000) 동시 실행
```

### Docker (샘플 DB)

```bash
docker-compose up -d   # MySQL, MongoDB, ClickHouse 샘플 데이터 포함
```

## Menus

| 메뉴 | 설명 |
|------|------|
| Dashboard | 스캔 요약, 사용자 현황, Daily Trend 차트 |
| Connections | DB 연결 CRUD + 연결 테스트 |
| Scans | 스캔 생성/실행/이력, 예약 스캔 |
| Deep Inspect | 샘플링 없이 전체 테이블 데이터 검사 |
| Rules | PII 탐지 규칙 관리 (내장 10종 + 커스텀) |
| Data Classification | 탐지된 PII 컬럼 민감도 분류 |
| Reports | PII 인벤토리, CSV/Excel/PDF 내보내기 |
| Users | 사용자 관리, LDAP 연동, 잠금/잠금 해제 |
| Settings | RBAC 역할 정의, Persona 모드, LDAP/SSO/Kafka/Splunk/Branding 설정 |
| Audit Log | 모든 사용자 활동 이력 |

## RBAC & Persona Mode

Settings > RBAC에서 역할별 권한을 확인하고 **Persona 모드**로 해당 역할 시점의 UI를 테스트할 수 있습니다.

| 역할 | 권한 |
|------|------|
| Admin | 전체 메뉴 읽기 + 쓰기 |
| Analyst | Scans · Rules 편집, 나머지 읽기 전용 |
| Viewer | 전체 읽기 전용 |

## PII Detection

스캔 실행 시 두 단계로 탐지합니다:
1. **ColumnNameDetector** — 컬럼명 패턴 매칭 (신뢰도 0.6~0.8)
2. **RegexPatternDetector** — 샘플 데이터 정규식 매칭

내장 탐지 패턴: 주민등록번호, 전화번호, 이메일, 계좌번호, 신용카드, 여권번호, 운전면허번호 등 10종
