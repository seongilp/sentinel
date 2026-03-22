-- sentinel_test 데이터베이스는 MYSQL_DATABASE 환경변수로 자동 생성됨
USE sentinel_test;

-- 사용자 테이블 (개인정보 다량 포함)
CREATE TABLE users (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    username    VARCHAR(50)  NOT NULL,
    email       VARCHAR(255) NOT NULL,
    phone       VARCHAR(20),
    password    VARCHAR(255) NOT NULL,
    birth_date  DATE,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 주문 테이블
CREATE TABLE orders (
    id           BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id      BIGINT NOT NULL,
    product_name VARCHAR(255),
    amount       DECIMAL(10, 2),
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 결제 정보 테이블 (민감 정보)
CREATE TABLE payments (
    id             BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id        BIGINT NOT NULL,
    credit_card    VARCHAR(20),
    account_number VARCHAR(30),
    created_at     DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 직원 테이블
CREATE TABLE employees (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    full_name       VARCHAR(100) NOT NULL,
    resident_id     VARCHAR(14),
    email           VARCHAR(255),
    phone           VARCHAR(20),
    department      VARCHAR(100),
    salary          DECIMAL(12, 2),
    hire_date       DATE
);

-- 샘플 데이터
INSERT INTO users (username, email, phone, password, birth_date) VALUES
  ('kim_minjun',   'minjun.kim@example.com',   '010-1234-5678', '$2b$12$abc123', '1990-03-15'),
  ('lee_soyeon',   'soyeon.lee@example.com',   '010-9876-5432', '$2b$12$def456', '1992-07-22'),
  ('park_jihoon',  'jihoon.park@example.com',  '010-5555-1234', '$2b$12$ghi789', '1988-11-05'),
  ('choi_yuna',    'yuna.choi@example.com',    '010-3333-7890', '$2b$12$jkl012', '1995-01-30'),
  ('jung_hyunwoo', 'hyunwoo.jung@example.com', '010-7777-4321', '$2b$12$mno345', '1985-09-18');

INSERT INTO orders (user_id, product_name, amount) VALUES
  (1, 'MacBook Pro 14"', 2990000.00),
  (1, 'AirPods Pro',      359000.00),
  (2, 'iPhone 15 Pro',   1550000.00),
  (3, 'iPad Air',         899000.00),
  (4, 'Apple Watch',      599000.00);

INSERT INTO payments (user_id, credit_card, account_number) VALUES
  (1, '4111-1111-1111-1111', '110-123-456789'),
  (2, '5500-0000-0000-0004', '우리-456-789012'),
  (3, '3714-496353-98431',   'KB-789-012345'),
  (4, '6011-1111-1111-1117', '신한-012-345678'),
  (5, '4012-8888-8888-1881', '하나-345-678901');

INSERT INTO employees (full_name, resident_id, email, phone, department, salary, hire_date) VALUES
  ('김민준', '900315-1234567', 'minjun.kim@corp.com',   '010-1234-5678', '개발팀',  5500000.00, '2018-03-01'),
  ('이소연', '920722-2345678', 'soyeon.lee@corp.com',   '010-9876-5432', '마케팅팀', 4800000.00, '2019-07-15'),
  ('박지훈', '881105-1456789', 'jihoon.park@corp.com',  '010-5555-1234', '인사팀',  4200000.00, '2020-01-10'),
  ('최유나', '950130-2567890', 'yuna.choi@corp.com',    '010-3333-7890', '재무팀',  5100000.00, '2017-09-01'),
  ('정현우', '850918-1678901', 'hyunwoo.jung@corp.com', '010-7777-4321', '개발팀',  6200000.00, '2015-04-20');
