-- Sample PII data for Sentinel scanning tests

CREATE DATABASE IF NOT EXISTS ecommerce;
CREATE DATABASE IF NOT EXISTS analytics;

-- ecommerce.users: 개인정보 컬럼 포함
CREATE TABLE IF NOT EXISTS ecommerce.users (
    id          UInt64,
    email       String,
    full_name   String,
    phone       String,
    birth_date  Date,
    created_at  DateTime DEFAULT now()
) ENGINE = MergeTree()
ORDER BY id;

INSERT INTO ecommerce.users (id, email, full_name, phone, birth_date) VALUES
(1, 'hong@example.com',   '홍길동', '010-1234-5678', '1990-03-15'),
(2, 'kim@company.co.kr',  '김영희', '010-9876-5432', '1985-07-22'),
(3, 'lee@mail.net',       '이철수', '010-5555-1234', '1992-11-08'),
(4, 'park@test.org',      '박민수', '010-3333-7777', '1988-01-30'),
(5, 'choi@example.com',   '최지수', '010-2222-8888', '1995-06-14');

-- ecommerce.orders: 주문 + 카드정보
CREATE TABLE IF NOT EXISTS ecommerce.orders (
    order_id        UInt64,
    user_id         UInt64,
    credit_card     String,
    account_number  String,
    amount          Float64,
    ordered_at      DateTime DEFAULT now()
) ENGINE = MergeTree()
ORDER BY order_id;

INSERT INTO ecommerce.orders (order_id, user_id, credit_card, account_number, amount) VALUES
(1001, 1, '4532-1234-5678-9010', '110-123-456789',  50000.0),
(1002, 2, '5412-7512-3456-7890', '209-12-345678',   120000.0),
(1003, 3, '3782-822463-10005',   '301-0123-456789', 35000.0),
(1004, 4, '6011-1111-2222-3333', '110-987-654321',  89000.0),
(1005, 5, '4916-3333-4444-5555', '209-56-789012',   210000.0);

-- analytics.events: 이벤트 로그 (일부 PII 포함)
CREATE TABLE IF NOT EXISTS analytics.events (
    event_id    UInt64,
    user_email  String,
    ip_address  String,
    event_type  String,
    occurred_at DateTime DEFAULT now()
) ENGINE = MergeTree()
ORDER BY event_id;

INSERT INTO analytics.events (event_id, user_email, ip_address, event_type) VALUES
(1, 'hong@example.com', '192.168.1.101', 'login'),
(2, 'kim@company.co.kr','10.0.0.55',     'purchase'),
(3, 'lee@mail.net',     '172.16.0.200',  'logout'),
(4, 'park@test.org',    '192.168.2.10',  'login'),
(5, 'choi@example.com', '10.10.0.1',     'view');

-- analytics.resident_info: 주민등록번호 (민감)
CREATE TABLE IF NOT EXISTS analytics.resident_info (
    id          UInt64,
    full_name   String,
    resident_id String,
    address     String
) ENGINE = MergeTree()
ORDER BY id;

INSERT INTO analytics.resident_info (id, full_name, resident_id, address) VALUES
(1, '홍길동', '900315-1234567', '서울시 강남구 테헤란로 123'),
(2, '김영희', '850722-2345678', '경기도 성남시 분당구 판교로 456'),
(3, '이철수', '921108-1456789', '서울시 마포구 합정동 789');
