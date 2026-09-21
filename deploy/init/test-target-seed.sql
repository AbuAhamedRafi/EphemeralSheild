-- =============================================================================
-- EphemeralShield — Test Target Database Seed Data
-- =============================================================================
-- This script seeds the DISPOSABLE test target with realistic synthetic data.
-- It simulates a production database that teams need JIT access to.
--
-- Tables created:
--   customers — Fake customer records (PII simulation)
--   orders    — Order history linked to customers
--   payments  — Payment records linked to orders
--
-- WHY synthetic data?
--   Integration tests need to verify that ephemeral credentials can SELECT
--   from these tables (read-only) but CANNOT INSERT/UPDATE/DELETE.
--   Using realistic table structures ensures the adapter handles real-world
--   schemas, not trivial single-column test tables.
--
-- WARNING: This is ONLY for the test-target-db container.
-- NEVER run this against your real production database.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Schema: Create a dedicated application schema
-- ---------------------------------------------------------------------------
-- WHY a named schema instead of 'public'?
--   Real applications use dedicated schemas. Our adapter must handle
--   schema-qualified access grants (USAGE + SELECT), not just public.
-- ---------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS app;

-- ---------------------------------------------------------------------------
-- Table: customers
-- ---------------------------------------------------------------------------
-- Simulates PII data (names, emails) — exactly the kind of data that
-- justifies JIT access controls and audit trails.
-- ---------------------------------------------------------------------------
CREATE TABLE app.customers (
    id          SERIAL PRIMARY KEY,
    first_name  VARCHAR(100) NOT NULL,
    last_name   VARCHAR(100) NOT NULL,
    email       VARCHAR(255) NOT NULL UNIQUE,
    phone       VARCHAR(20),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- Table: orders
-- ---------------------------------------------------------------------------
CREATE TABLE app.orders (
    id           SERIAL PRIMARY KEY,
    customer_id  INTEGER NOT NULL REFERENCES app.customers(id),
    order_number VARCHAR(20) NOT NULL UNIQUE,
    status       VARCHAR(20) NOT NULL DEFAULT 'pending'
                 CHECK (status IN ('pending', 'confirmed', 'shipped', 'delivered', 'cancelled')),
    total_amount NUMERIC(12, 2) NOT NULL CHECK (total_amount >= 0),
    currency     VARCHAR(3) NOT NULL DEFAULT 'USD',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- Table: payments
-- ---------------------------------------------------------------------------
CREATE TABLE app.payments (
    id             SERIAL PRIMARY KEY,
    order_id       INTEGER NOT NULL REFERENCES app.orders(id),
    payment_method VARCHAR(20) NOT NULL
                   CHECK (payment_method IN ('credit_card', 'bank_transfer', 'paypal')),
    amount         NUMERIC(12, 2) NOT NULL CHECK (amount >= 0),
    currency       VARCHAR(3) NOT NULL DEFAULT 'USD',
    status         VARCHAR(20) NOT NULL DEFAULT 'pending'
                   CHECK (status IN ('pending', 'completed', 'failed', 'refunded')),
    processed_at   TIMESTAMPTZ,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- Indexes for realistic query patterns
-- ---------------------------------------------------------------------------
CREATE INDEX idx_orders_customer_id ON app.orders(customer_id);
CREATE INDEX idx_orders_status ON app.orders(status);
CREATE INDEX idx_payments_order_id ON app.payments(order_id);
CREATE INDEX idx_payments_status ON app.payments(status);

-- ---------------------------------------------------------------------------
-- Seed: Insert synthetic data
-- ---------------------------------------------------------------------------
-- 10 customers, 20 orders, 20 payments — enough to verify SELECT works
-- without making integration tests slow.
-- ---------------------------------------------------------------------------
INSERT INTO app.customers (first_name, last_name, email, phone) VALUES
    ('Alice',   'Smith',    'alice.smith@example.com',    '+1-555-0101'),
    ('Bob',     'Johnson',  'bob.johnson@example.com',    '+1-555-0102'),
    ('Charlie', 'Williams', 'charlie.williams@example.com', '+1-555-0103'),
    ('Diana',   'Brown',    'diana.brown@example.com',    '+1-555-0104'),
    ('Eve',     'Jones',    'eve.jones@example.com',      '+1-555-0105'),
    ('Frank',   'Garcia',   'frank.garcia@example.com',   '+1-555-0106'),
    ('Grace',   'Miller',   'grace.miller@example.com',   '+1-555-0107'),
    ('Hank',    'Davis',    'hank.davis@example.com',     '+1-555-0108'),
    ('Ivy',     'Rodriguez','ivy.rodriguez@example.com',  '+1-555-0109'),
    ('Jack',    'Wilson',   'jack.wilson@example.com',    '+1-555-0110');

INSERT INTO app.orders (customer_id, order_number, status, total_amount, currency) VALUES
    (1, 'ORD-2026-0001', 'delivered',  149.99, 'USD'),
    (1, 'ORD-2026-0002', 'shipped',    89.50,  'USD'),
    (2, 'ORD-2026-0003', 'confirmed',  234.00, 'USD'),
    (2, 'ORD-2026-0004', 'pending',    67.25,  'USD'),
    (3, 'ORD-2026-0005', 'delivered',  512.00, 'USD'),
    (3, 'ORD-2026-0006', 'cancelled',  45.99,  'USD'),
    (4, 'ORD-2026-0007', 'shipped',    178.50, 'EUR'),
    (4, 'ORD-2026-0008', 'delivered',  92.00,  'EUR'),
    (5, 'ORD-2026-0009', 'confirmed',  310.75, 'USD'),
    (5, 'ORD-2026-0010', 'pending',    55.00,  'USD'),
    (6, 'ORD-2026-0011', 'delivered',  425.00, 'USD'),
    (6, 'ORD-2026-0012', 'shipped',    199.99, 'USD'),
    (7, 'ORD-2026-0013', 'confirmed',  78.50,  'GBP'),
    (7, 'ORD-2026-0014', 'delivered',  156.00, 'GBP'),
    (8, 'ORD-2026-0015', 'pending',    340.00, 'USD'),
    (8, 'ORD-2026-0016', 'cancelled',  22.99,  'USD'),
    (9, 'ORD-2026-0017', 'delivered',  567.50, 'USD'),
    (9, 'ORD-2026-0018', 'shipped',    88.00,  'USD'),
    (10, 'ORD-2026-0019', 'confirmed', 245.00, 'USD'),
    (10, 'ORD-2026-0020', 'delivered', 134.75, 'USD');

INSERT INTO app.payments (order_id, payment_method, amount, currency, status, processed_at) VALUES
    (1,  'credit_card',   149.99, 'USD', 'completed', NOW() - INTERVAL '30 days'),
    (2,  'credit_card',   89.50,  'USD', 'completed', NOW() - INTERVAL '15 days'),
    (3,  'bank_transfer', 234.00, 'USD', 'completed', NOW() - INTERVAL '10 days'),
    (4,  'paypal',        67.25,  'USD', 'pending',   NULL),
    (5,  'credit_card',   512.00, 'USD', 'completed', NOW() - INTERVAL '45 days'),
    (6,  'credit_card',   45.99,  'USD', 'refunded',  NOW() - INTERVAL '40 days'),
    (7,  'bank_transfer', 178.50, 'EUR', 'completed', NOW() - INTERVAL '20 days'),
    (8,  'credit_card',   92.00,  'EUR', 'completed', NOW() - INTERVAL '25 days'),
    (9,  'paypal',        310.75, 'USD', 'completed', NOW() - INTERVAL '5 days'),
    (10, 'credit_card',   55.00,  'USD', 'pending',   NULL),
    (11, 'credit_card',   425.00, 'USD', 'completed', NOW() - INTERVAL '35 days'),
    (12, 'bank_transfer', 199.99, 'USD', 'completed', NOW() - INTERVAL '12 days'),
    (13, 'paypal',        78.50,  'GBP', 'completed', NOW() - INTERVAL '8 days'),
    (14, 'credit_card',   156.00, 'GBP', 'completed', NOW() - INTERVAL '22 days'),
    (15, 'bank_transfer', 340.00, 'USD', 'pending',   NULL),
    (16, 'credit_card',   22.99,  'USD', 'refunded',  NOW() - INTERVAL '18 days'),
    (17, 'credit_card',   567.50, 'USD', 'completed', NOW() - INTERVAL '50 days'),
    (18, 'paypal',        88.00,  'USD', 'completed', NOW() - INTERVAL '7 days'),
    (19, 'bank_transfer', 245.00, 'USD', 'completed', NOW() - INTERVAL '3 days'),
    (20, 'credit_card',   134.75, 'USD', 'completed', NOW() - INTERVAL '28 days');
