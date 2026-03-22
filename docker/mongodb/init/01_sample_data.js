// Sample PII data for Sentinel scanning tests
// Runs as MONGO_INITDB_ROOT user against sentinel_test DB

db = db.getSiblingDB('sentinel_test');

// Create a dedicated user for this DB
db.createUser({
  user: 'sentinel',
  pwd: 'sentinel123',
  roles: [{ role: 'readWrite', db: 'sentinel_test' }],
});

// ── ecommerce.users ───────────────────────────────────────────────────────────
db.createCollection('users');
db.users.insertMany([
  { email: 'hong@example.com',  full_name: '홍길동', phone: '010-1234-5678', birth_date: '1990-03-15', resident_id: '900315-1234567', address: '서울시 강남구 테헤란로 123' },
  { email: 'kim@company.co.kr', full_name: '김영희', phone: '010-9876-5432', birth_date: '1985-07-22', resident_id: '850722-2345678', address: '경기도 성남시 분당구 판교로 456' },
  { email: 'lee@mail.net',      full_name: '이철수', phone: '010-5555-1234', birth_date: '1992-11-08', resident_id: '921108-1456789', address: '서울시 마포구 합정동 789' },
  { email: 'park@test.org',     full_name: '박민수', phone: '010-3333-7777', birth_date: '1988-01-30', address: '부산시 해운대구 해운대로 100' },
  { email: 'choi@example.com',  full_name: '최지수', phone: '010-2222-8888', birth_date: '1995-06-14', address: '대구시 중구 동성로 55' },
]);

// ── ecommerce.orders ──────────────────────────────────────────────────────────
db.createCollection('orders');
db.orders.insertMany([
  { order_id: 1001, user_email: 'hong@example.com', credit_card: '4532-1234-5678-9010', account_number: '110-123-456789',  amount: 50000  },
  { order_id: 1002, user_email: 'kim@company.co.kr', credit_card: '5412-7512-3456-7890', account_number: '209-12-345678',   amount: 120000 },
  { order_id: 1003, user_email: 'lee@mail.net',      credit_card: '3782-822463-10005',   account_number: '301-0123-456789', amount: 35000  },
  { order_id: 1004, user_email: 'park@test.org',     credit_card: '6011-1111-2222-3333', account_number: '110-987-654321',  amount: 89000  },
  { order_id: 1005, user_email: 'choi@example.com',  credit_card: '4916-3333-4444-5555', account_number: '209-56-789012',   amount: 210000 },
]);

// ── analytics.events ──────────────────────────────────────────────────────────
db.createCollection('events');
db.events.insertMany([
  { event_id: 1, user_email: 'hong@example.com',  ip_address: '192.168.1.101', event_type: 'login'    },
  { event_id: 2, user_email: 'kim@company.co.kr', ip_address: '10.0.0.55',     event_type: 'purchase' },
  { event_id: 3, user_email: 'lee@mail.net',       ip_address: '172.16.0.200',  event_type: 'logout'   },
  { event_id: 4, user_email: 'park@test.org',      ip_address: '192.168.2.10',  event_type: 'login'    },
  { event_id: 5, user_email: 'choi@example.com',   ip_address: '10.10.0.1',     event_type: 'view'     },
]);

// ── hr.employees ──────────────────────────────────────────────────────────────
db.createCollection('employees');
db.employees.insertMany([
  { employee_id: 'E001', full_name: '홍길동', email: 'hong@corp.com', phone: '010-1234-5678', resident_id: '900315-1234567', bank_account: '110-123-456789', salary: 5000000 },
  { employee_id: 'E002', full_name: '김영희', email: 'kim@corp.com',  phone: '010-9876-5432', resident_id: '850722-2345678', bank_account: '209-12-345678',  salary: 6500000 },
  { employee_id: 'E003', full_name: '이철수', email: 'lee@corp.com',  phone: '010-5555-1234', resident_id: '921108-1456789', bank_account: '301-0123-456789', salary: 4800000 },
]);

print('MongoDB sample data inserted successfully.');
