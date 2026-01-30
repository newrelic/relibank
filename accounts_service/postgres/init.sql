-- Create a UUID extension for generating UUIDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create the user account table
CREATE TABLE IF NOT EXISTS user_account (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    alert_preferences JSONB,
    phone VARCHAR(20),
    email VARCHAR(255) UNIQUE NOT NULL,
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
INSERT INTO user_account (id, name, email, phone) VALUES
('b2a5c9f1-3d7f-4b0d-9a8c-9c7b5a1f2e4d', 'Alice Johnson', 'alice.j@relibank.com', '555-123-4567'),
('f5e8d1c6-2a9b-4c3e-8f1a-6e5b0d2c9f1a', 'Bob Williams', 'bob.w@relibank.com', '555-987-6543'),
('e1f2b3c4-5d6a-7e8f-9a0b-1c2d3e4f5a6b', 'Charlie Brown', 'charlie.b@relibank.com', '555-555-5555'),
('f47ac10b-58cc-4372-a567-0e02b2c3d471', 'Solaire Astora', 'solaire.a@sunlight.com', '555-248-1911'),
('d9b1e2a3-f4c5-4d6e-8f7a-9b0c1d2e3f4a', 'Malenia Miquella', 'malenia.m@haligtree.org', '555-001-9090'),
('8c7d6e5f-4a3b-2c1d-0e9f-8a7b6c5d4e3f', 'Artorias Abyss', 'artorias.a@darksouls.net', '555-777-0001'),
('7f6e5d4c-3b2a-1c0d-9e8f-7a6b5c4d3e2f', 'Priscilla Painted', 'priscilla.p@paintedworld.com', '555-111-2233'),
('6e5d4c3b-2a1c-0d9e-8f7a-6b5c4d3e2f1a', 'Gwyn Cinder', 'gwyn.c@kiln.org', '555-999-0000'),
('5d4c3b2a-1c0d-9e8f-7a6b-5c4d3e2f1a0b', 'Siegmeyer Catarina', 'siegmeyer.c@onionknight.com', '555-444-5566'),
('4c3b2a1c-0d9e-8f7a-6b5c-4d3e2f1a0b9c', 'Ornstein Dragon', 'ornstein.d@anor.org', '555-222-7788'),
('3b2a1c0d-9e8f-7a6b-5c4d-3e2f1a0b9c8d', 'Smough Executioner', 'smough.e@anor.org', '555-333-9900'),
('2a1c0d9e-8f7a-6b5c-4d3e-2f1a0b9c8d7e', 'Sif Greywolf', 'sif.g@forest.net', '555-666-1122'),
('1c0d9e8f-7a6b-5c4d-3e2f-1a0b9c8d7e6f', 'Patches Spider', 'patches.s@trustworthy.com', '555-888-3344'),
('0d9e8f7a-6b5c-4d3e-2f1a-0b9c8d7e6f50', 'Radahn Starscourge', 'radahn.s@redmane.org', '555-123-9999'),
('9e8f7a6b-5c4d-3e2f-1a0b-9c8d7e6f5041', 'Ranni Witch', 'ranni.w@moonlight.net', '555-456-7890'),
('8f7a6b5c-4d3e-2f1a-0b9c-8d7e6f504032', 'Godrick Grafted', 'godrick.g@stormveil.com', '555-789-0123'),
('7a6b5c4d-3e2f-1a0b-9c8d-7e6f50403021', 'Rennala Moon', 'rennala.m@academy.org', '555-012-3456'),
('6b5c4d3e-2f1a-0b9c-8d7e-6f5040302010', 'Morgott King', 'morgott.k@erdtree.net', '555-345-6789'),
('5c4d3e2f-1a0b-9c8d-7e6f-504030201001', 'Godfrey Warrior', 'godfrey.w@elden.com', '555-678-9012'),
('4d3e2f1a-0b9c-8d7e-6f50-403020100102', 'Maliketh Beast', 'maliketh.b@destined.org', '555-901-2345'),
('3e2f1a0b-9c8d-7e6f-5040-302010010203', 'Mohg Lord', 'mohg.l@dynasty.net', '555-234-5678'),
('2f1a0b9c-8d7e-6f50-4030-201001020304', 'Placidusax Dragon', 'placidusax.d@time.com', '555-567-8901'),
('1a0b9c8d-7e6f-5040-3020-100102030405', 'Blaidd Half', 'blaidd.h@mistwood.org', '555-890-1234'),
('0b9c8d7e-6f50-4030-2010-010203040506', 'Gehrman Hunter', 'gehrman.h@dream.net', '555-123-4567'),
('9c8d7e6f-5040-3020-1001-020304050607', 'Maria Astral', 'maria.a@clocktower.com', '555-456-7890'),
('8d7e6f50-4030-2010-0102-030405060708', 'Ludwig Holy', 'ludwig.h@healing.org', '555-789-0123'),
('7e6f5040-3020-1001-0203-040506070809', 'Laurence Beast', 'laurence.b@byrgenwerth.net', '555-012-3456'),
('6f504030-2010-0102-0304-05060708090a', 'Gascoigne Father', 'gascoigne.f@yharnam.com', '555-345-6789'),
('50403020-1001-0203-0405-0607080910ab', 'Eileen Crow', 'eileen.c@hunters.org', '555-678-9012'),
('40302010-0102-0304-0506-070809101112', 'Djura Powder', 'djura.p@oldyharnam.net', '555-901-2345'),
('30201001-0203-0405-0607-080910111213', 'Henryk Hunter', 'henryk.h@tomb.com', '555-234-5678'),
('20100102-0304-0506-0708-091011121314', 'Valtr Master', 'valtr.m@league.org', '555-567-8901'),
('10010203-0405-0607-0809-101112131415', 'Alfred Executioner', 'alfred.e@martyr.net', '555-890-1234'),
('01020304-0506-0708-0910-111213141516', 'Isshin Sword', 'isshin.s@ashina.com', '555-123-4567'),
('02030405-0607-0809-1011-121314151617', 'Genichiro Way', 'genichiro.w@castle.org', '555-456-7890'),
('03040506-0708-0910-1112-131415161718', 'Emma Gentle', 'emma.g@physician.net', '555-789-0123'),
('04050607-0809-1011-1213-141516171819', 'Sculptor Dilapidated', 'sculptor.d@temple.com', '555-012-3456'),
('05060708-0910-1112-1314-15161718191a', 'Kuro Divine', 'kuro.d@heir.org', '555-345-6789'),
('06070809-1011-1213-1415-161718191a1b', 'Owl Great', 'owl.g@shinobi.net', '555-678-9012'),
('07080910-1112-1314-1516-1718191a1b1c', 'Guardian Ape', 'guardian.a@forest.com', '555-901-2345'),
('08091011-1213-1415-1617-18191a1b1c1d', 'Corrupted Monk', 'corrupted.m@mibu.org', '555-234-5678'),
('09101112-1314-1516-1718-191a1b1c1d1e', 'Divine Dragon', 'divine.d@palace.net', '555-567-8901'),
('0a111213-1415-1617-1819-1a1b1c1d1e1f', 'Demon Fire', 'demon.f@hatred.com', '555-890-1234');

-- Insert test accounts with integer IDs
INSERT INTO checking_accounts (id, name, balance, routing_number, interest_rate) VALUES
(12345, 'Alice Checking', 1500.50, '0123456789', 0.001),
(67890, 'Charlie Checking', 750.25, '9876543210', 0.001),
(10001, 'Solaire Checking', 2500.00, '0123456790', 0.001),
(10002, 'Malenia Checking', 8750.50, '0123456790', 0.001),
(10003, 'Artorias Checking', 1200.75, '0123456791', 0.001),
(10004, 'Priscilla Checking', 3400.25, '0123456792', 0.001),
(10005, 'Gwyn Checking', 15000.00, '0123456793', 0.001),
(10006, 'Siegmeyer Checking', 950.50, '0123456794', 0.001),
(10007, 'Ornstein Checking', 6200.00, '0123456795', 0.001),
(10008, 'Smough Checking', 5800.75, '0123456796', 0.001),
(10009, 'Sif Checking', 1100.25, '0123456797', 0.001),
(10010, 'Patches Checking', 450.00, '0123456798', 0.001),
(10011, 'Radahn Checking', 9500.00, '0123456799', 0.001),
(10012, 'Ranni Checking', 12000.50, '0123456800', 0.001),
(10013, 'Godrick Checking', 3700.75, '0123456801', 0.001),
(10014, 'Rennala Checking', 11200.00, '0123456802', 0.001),
(10015, 'Morgott Checking', 8900.25, '0123456803', 0.001);

INSERT INTO savings_accounts (id, name, balance, routing_number, interest_rate) VALUES
(56789, 'Alice Savings', 5000.00, '1122334455', 0.015),
(20001, 'Solaire Savings', 15000.00, '1122334456', 0.015),
(20002, 'Malenia Savings', 25000.00, '1122334456', 0.020),
(20003, 'Gwyn Savings', 50000.00, '1122334457', 0.025),
(20004, 'Ornstein Savings', 18000.00, '1122334458', 0.015),
(20005, 'Radahn Savings', 30000.00, '1122334459', 0.020),
(20006, 'Ranni Savings', 40000.00, '1122334460', 0.025),
(20007, 'Rennala Savings', 35000.00, '1122334461', 0.020),
(20008, 'Godfrey Savings', 28000.00, '1122334462', 0.018),
(20009, 'Maliketh Savings', 22000.00, '1122334463', 0.017),
(20010, 'Gehrman Savings', 19000.00, '1122334464', 0.016);

INSERT INTO credit_accounts (id, name, balance, outstanding_balance, routing_number, interest_rate, payment_schedule, automatic_pay) VALUES
(98765, 'Bob Credit Card', 1200.00, 500.00, '5566778899', 0.1899, 'monthly', TRUE),
(10111, 'Charlie Credit Card', 5000.00, 2500.00, '5566778900', 0.1500, 'monthly', FALSE),
(30001, 'Artorias Credit Card', 5000.00, 1200.00, '5566778901', 0.1899, 'monthly', TRUE),
(30002, 'Priscilla Credit Card', 3000.00, 800.00, '5566778900', 0.1750, 'monthly', FALSE),
(30003, 'Siegmeyer Credit Card', 2000.00, 500.00, '5566778901', 0.1650, 'monthly', TRUE),
(30004, 'Smough Credit Card', 4000.00, 1500.00, '5566778902', 0.1899, 'monthly', FALSE),
(30005, 'Sif Credit Card', 1500.00, 300.00, '5566778903', 0.1599, 'monthly', TRUE),
(30006, 'Patches Credit Card', 1000.00, 950.00, '5566778904', 0.2199, 'monthly', FALSE),
(30007, 'Godrick Credit Card', 3500.00, 1000.00, '5566778905', 0.1799, 'monthly', TRUE),
(30008, 'Morgott Credit Card', 6000.00, 2000.00, '5566778906', 0.1899, 'monthly', TRUE),
(30009, 'Mohg Credit Card', 4500.00, 1800.00, '5566778907', 0.1950, 'monthly', FALSE),
(30010, 'Blaidd Credit Card', 2500.00, 600.00, '5566778908', 0.1699, 'monthly', TRUE),
(30011, 'Maria Credit Card', 3500.00, 900.00, '5566778909', 0.1750, 'monthly', TRUE),
(30012, 'Ludwig Credit Card', 5000.00, 2500.00, '5566778910', 0.1899, 'monthly', FALSE),
(30013, 'Gascoigne Credit Card', 2000.00, 700.00, '5566778911', 0.1650, 'monthly', TRUE),
(30014, 'Isshin Credit Card', 4000.00, 1100.00, '5566778912', 0.1799, 'monthly', TRUE),
(30015, 'Genichiro Credit Card', 3000.00, 1200.00, '5566778913', 0.1850, 'monthly', FALSE);

-- Link users to accounts with the correct IDs
INSERT INTO account_user (user_id, account_id) VALUES
('b2a5c9f1-3d7f-4b0d-9a8c-9c7b5a1f2e4d', 12345), -- Alice's checking
('b2a5c9f1-3d7f-4b0d-9a8c-9c7b5a1f2e4d', 56789), -- Alice's savings
('f5e8d1c6-2a9b-4c3e-8f1a-6e5b0d2c9f1a', 98765), -- Bob's credit
('e1f2b3c4-5d6a-7e8f-9a0b-1c2d3e4f5a6b', 67890), -- Charlie's checking
('e1f2b3c4-5d6a-7e8f-9a0b-1c2d3e4f5a6b', 10111), -- Charlie's credit card
('f47ac10b-58cc-4372-a567-0e02b2c3d471', 10001), -- Solaire's checking
('f47ac10b-58cc-4372-a567-0e02b2c3d471', 20001), -- Solaire's savings
('d9b1e2a3-f4c5-4d6e-8f7a-9b0c1d2e3f4a', 10002), -- Malenia's checking
('d9b1e2a3-f4c5-4d6e-8f7a-9b0c1d2e3f4a', 20002), -- Malenia's savings
('8c7d6e5f-4a3b-2c1d-0e9f-8a7b6c5d4e3f', 10003), -- Artorias's checking
('8c7d6e5f-4a3b-2c1d-0e9f-8a7b6c5d4e3f', 30001), -- Artorias's credit
('7f6e5d4c-3b2a-1c0d-9e8f-7a6b5c4d3e2f', 10004), -- Priscilla's checking
('7f6e5d4c-3b2a-1c0d-9e8f-7a6b5c4d3e2f', 30002), -- Priscilla's credit
('6e5d4c3b-2a1c-0d9e-8f7a-6b5c4d3e2f1a', 10005), -- Gwyn's checking
('6e5d4c3b-2a1c-0d9e-8f7a-6b5c4d3e2f1a', 20003), -- Gwyn's savings
('5d4c3b2a-1c0d-9e8f-7a6b-5c4d3e2f1a0b', 10006), -- Siegmeyer's checking
('5d4c3b2a-1c0d-9e8f-7a6b-5c4d3e2f1a0b', 30003), -- Siegmeyer's credit
('4c3b2a1c-0d9e-8f7a-6b5c-4d3e2f1a0b9c', 10007), -- Ornstein's checking
('4c3b2a1c-0d9e-8f7a-6b5c-4d3e2f1a0b9c', 20004), -- Ornstein's savings
('3b2a1c0d-9e8f-7a6b-5c4d-3e2f1a0b9c8d', 10008), -- Smough's checking
('3b2a1c0d-9e8f-7a6b-5c4d-3e2f1a0b9c8d', 30004), -- Smough's credit
('2a1c0d9e-8f7a-6b5c-4d3e-2f1a0b9c8d7e', 10009), -- Sif's checking
('2a1c0d9e-8f7a-6b5c-4d3e-2f1a0b9c8d7e', 30005), -- Sif's credit
('1c0d9e8f-7a6b-5c4d-3e2f-1a0b9c8d7e6f', 10010), -- Patches's checking
('1c0d9e8f-7a6b-5c4d-3e2f-1a0b9c8d7e6f', 30006), -- Patches's credit
('0d9e8f7a-6b5c-4d3e-2f1a-0b9c8d7e6f50', 10011), -- Radahn's checking
('0d9e8f7a-6b5c-4d3e-2f1a-0b9c8d7e6f50', 20005), -- Radahn's savings
('9e8f7a6b-5c4d-3e2f-1a0b-9c8d7e6f5041', 10012), -- Ranni's checking
('9e8f7a6b-5c4d-3e2f-1a0b-9c8d7e6f5041', 20006), -- Ranni's savings
('8f7a6b5c-4d3e-2f1a-0b9c-8d7e6f504032', 10013), -- Godrick's checking
('8f7a6b5c-4d3e-2f1a-0b9c-8d7e6f504032', 30007), -- Godrick's credit
('7a6b5c4d-3e2f-1a0b-9c8d-7e6f50403021', 10014), -- Rennala's checking
('7a6b5c4d-3e2f-1a0b-9c8d-7e6f50403021', 20007), -- Rennala's savings
('6b5c4d3e-2f1a-0b9c-8d7e-6f5040302010', 10015), -- Morgott's checking
('6b5c4d3e-2f1a-0b9c-8d7e-6f5040302010', 30008), -- Morgott's credit
('5c4d3e2f-1a0b-9c8d-7e6f-504030201001', 20008), -- Godfrey's savings
('4d3e2f1a-0b9c-8d7e-6f50-403020100102', 20009), -- Maliketh's savings
('3e2f1a0b-9c8d-7e6f-5040-302010010203', 30009), -- Mohg's credit
('1a0b9c8d-7e6f-5040-3020-100102030405', 30010), -- Blaidd's credit
('0b9c8d7e-6f50-4030-2010-010203040506', 20010), -- Gehrman's savings
('9c8d7e6f-5040-3020-1001-020304050607', 30011), -- Maria's credit
('8d7e6f50-4030-2010-0102-030405060708', 30012), -- Ludwig's credit
('6f504030-2010-0102-0304-05060708090a', 30013), -- Gascoigne's credit
('01020304-0506-0708-0910-111213141516', 30014), -- Isshin's credit
('02030405-0607-0809-1011-121314151617', 30015); -- Genichiro's credit
