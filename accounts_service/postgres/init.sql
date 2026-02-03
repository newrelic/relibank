-- Create a UUID extension for generating UUIDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create the user account table
CREATE TABLE IF NOT EXISTS user_account (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    alert_preferences JSONB,
    phone VARCHAR(20),
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255),
    address TEXT,
    income DECIMAL(19, 4),
    preferred_language VARCHAR(50),
    marketing_preferences JSONB,
    privacy_preferences JSONB
);

-- Create a table for checking accounts
CREATE TABLE IF NOT EXISTS checking_accounts (
    id INT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    balance DECIMAL(19, 4) NOT NULL,
    routing_number VARCHAR(255),
    interest_rate DECIMAL(5, 4),
    last_statement_date TIMESTAMP
);

-- Create a table for savings accounts
CREATE TABLE IF NOT EXISTS savings_accounts (
    id INT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    balance DECIMAL(19, 4) NOT NULL,
    routing_number VARCHAR(255),
    interest_rate DECIMAL(5, 4),
    last_statement_date TIMESTAMP
);

-- Create a table for loan and credit accounts
CREATE TABLE IF NOT EXISTS credit_accounts (
    id INT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    balance DECIMAL(19, 4) NOT NULL,
    outstanding_balance DECIMAL(19, 4) NOT NULL,
    routing_number VARCHAR(255),
    interest_rate DECIMAL(5, 4),
    last_statement_date TIMESTAMP,
    payment_schedule VARCHAR(255),
    last_payment_date TIMESTAMP,
    automatic_pay BOOLEAN
);

-- Create the relationship table to link users and accounts
CREATE TABLE IF NOT EXISTS account_user (
    account_id INT NOT NULL,
    user_id UUID NOT NULL REFERENCES user_account(id),
    PRIMARY KEY (account_id, user_id)
);

--
-- Populate with test data
--

-- Insert test users
-- NOTE: Passwords are stored in plain text for demo purposes only.
-- In production, use proper password hashing (bcrypt, argon2, etc.)
INSERT INTO user_account (id, name, email, phone, password) VALUES
('b2a5c9f1-3d7f-4b0d-9a8c-9c7b5a1f2e4d', 'Alice Johnson', 'alice.j@relibank.com', '555-123-4567', 'lightm0deisthebest'),
('f5e8d1c6-2a9b-4c3e-8f1a-6e5b0d2c9f1a', 'Bob Williams', 'bob.w@relibank.com', '555-987-6543', 'lightm0deisthebest'),
('e1f2b3c4-5d6a-7e8f-9a0b-1c2d3e4f5a6b', 'Charlie Brown', 'charlie.b@relibank.com', '555-555-5555', 'lightm0deisthebest');

-- Insert test accounts with integer IDs
INSERT INTO checking_accounts (id, name, balance, routing_number, interest_rate) VALUES
(12345, 'Alice Checking', 1500.50, '0123456789', 0.001),
(54321, 'Bob Checking', 2500.75, '5544332211', 0.001),
(67890, 'Charlie Checking', 750.25, '9876543210', 0.001);

INSERT INTO savings_accounts (id, name, balance, routing_number, interest_rate) VALUES
(56789, 'Alice Savings', 5000.00, '1122334455', 0.015),
(98766, 'Bob Savings', 3200.00, '6677889900', 0.020),
(67891, 'Charlie Savings', 1500.00, '9988776655', 0.018);

INSERT INTO credit_accounts (id, name, balance, outstanding_balance, routing_number, interest_rate, payment_schedule, automatic_pay) VALUES
(98765, 'Bob Credit Card', 1200.00, 500.00, '5566778899', 0.1899, 'monthly', TRUE),
(10111, 'Charlie Credit Card', 5000.00, 2500.00, '000111222', 0.1500, 'monthly', FALSE);

-- Link users to accounts with the correct IDs
INSERT INTO account_user (user_id, account_id) VALUES
('b2a5c9f1-3d7f-4b0d-9a8c-9c7b5a1f2e4d', 12345), -- Alice's checking
('b2a5c9f1-3d7f-4b0d-9a8c-9c7b5a1f2e4d', 56789), -- Alice's savings
('f5e8d1c6-2a9b-4c3e-8f1a-6e5b0d2c9f1a', 54321), -- Bob's checking
('f5e8d1c6-2a9b-4c3e-8f1a-6e5b0d2c9f1a', 98766), -- Bob's savings
('f5e8d1c6-2a9b-4c3e-8f1a-6e5b0d2c9f1a', 98765), -- Bob's credit
('e1f2b3c4-5d6a-7e8f-9a0b-1c2d3e4f5a6b', 67890), -- Charlie's checking
('e1f2b3c4-5d6a-7e8f-9a0b-1c2d3e4f5a6b', 67891), -- Charlie's savings
('e1f2b3c4-5d6a-7e8f-9a0b-1c2d3e4f5a6b', 10111); -- Charlie's credit card
