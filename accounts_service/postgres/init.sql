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
    privacy_preferences JSONB,
    stripe_customer_id          VARCHAR(255),
    stripe_payment_method_id    VARCHAR(255),
    stripe_payment_method_name  VARCHAR(255)
);

-- Add Stripe columns if they don't exist (for databases created before commit c6079b1, March 25 2026)
ALTER TABLE user_account ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR(255);
ALTER TABLE user_account ADD COLUMN IF NOT EXISTS stripe_payment_method_id VARCHAR(255);
ALTER TABLE user_account ADD COLUMN IF NOT EXISTS stripe_payment_method_name VARCHAR(255);

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
INSERT INTO user_account (id, name, email, phone, password, stripe_customer_id, stripe_payment_method_id, stripe_payment_method_name) VALUES
('b2a5c9f1-3d7f-4b0d-9a8c-9c7b5a1f2e4d', 'Alice Johnson', 'alice.j@relibank.com', '555-123-4567', 'aJ7#kQ9mP2wX', 'cus_UDJUKtOkn6XoOB', 'pm_1TExyFFGyca1lOb8OuCAwtEn', 'pm_card_visa'),
('f5e8d1c6-2a9b-4c3e-8f1a-6e5b0d2c9f1a', 'Bob Williams', 'bob.w@relibank.com', '555-987-6543', 'bW3$nL8vR5yT', 'cus_UDJWbyD8V585Ov', 'pm_1TEyJiFGyca1lOb8mXJNWULT', 'pm_card_visa'),
('e1f2b3c4-5d6a-7e8f-9a0b-1c2d3e4f5a6b', 'Charlie Brown', 'charlie.b@relibank.com', '555-555-5555', 'cB9@hN4zD7fK', 'cus_UDJXmCEDzJLVQT', 'pm_1TEyJjFGyca1lOb8FQmcbDbn', 'pm_card_mastercard'),
('f47ac10b-58cc-4372-a567-0e02b2c3d471', 'Solaire Astora', 'solaire.a@sunlight.com', '555-248-1911', 'sA4%pR8mV3xJ', 'cus_UDONEXRz6FuSOJ', 'pm_1TEyJkFGyca1lOb89A11DMOY', 'pm_card_discover'),
('d9b1e2a3-f4c5-4d6e-8f7a-9b0c1d2e3f4a', 'Malenia Miquella', 'malenia.m@haligtree.org', '555-001-9090', 'mM6&tY2nQ9wL', 'cus_UDONja6tdPGNBu', 'pm_1TEyJmFGyca1lOb8Osa182qe', 'pm_card_visa'),
('8c7d6e5f-4a3b-2c1d-0e9f-8a7b6c5d4e3f', 'Artorias Abyss', 'artorias.a@darksouls.net', '555-777-0001', 'aA8#fG5kS1bN', 'cus_UDOO7Am0C4id4y', 'pm_1TEyJnFGyca1lOb8ACxhFv4I', 'pm_card_mastercard'),
('7f6e5d4c-3b2a-1c0d-9e8f-7a6b5c4d3e2f', 'Priscilla Painted', 'priscilla.p@paintedworld.com', '555-111-2233', 'pP2$mH7vC4xR', 'cus_UDOOCvDNMRi7ms', 'pm_1TEyJpFGyca1lOb81c0sji5L', 'pm_card_discover'),
('6e5d4c3b-2a1c-0d9e-8f7a-6b5c4d3e2f1a', 'Gwyn Cinder', 'gwyn.c@kiln.org', '555-999-0000', 'gC5@nK9zL3wT', 'cus_UDOOXEjO6FUexG', 'pm_1TEyJqFGyca1lOb8UzrfjPs2', 'pm_card_visa'),
('5d4c3b2a-1c0d-9e8f-7a6b-5c4d3e2f1a0b', 'Siegmeyer Catarina', 'siegmeyer.c@onionknight.com', '555-444-5566', 'sC7#qJ4mP8yD', 'cus_UDOO4JRW7eTKxr', 'pm_1TEyJsFGyca1lOb8NAHbKMWj', 'pm_card_mastercard'),
('4c3b2a1c-0d9e-8f7a-6b5c-4d3e2f1a0b9c', 'Ornstein Dragon', 'ornstein.d@anor.org', '555-222-7788', 'oD3$wN6vR2fK', 'cus_UDOPeiXsu2M1Gu', 'pm_1TEyJtFGyca1lOb893U5efaJ', 'pm_card_discover'),
('3b2a1c0d-9e8f-7a6b-5c4d-3e2f1a0b9c8d', 'Smough Executioner', 'smough.e@anor.org', '555-333-9900', 'sE9@hL5xT7bM', 'cus_UDOPteQJOTyk5s', 'pm_1TEyJuFGyca1lOb84YC9kGRa', 'pm_card_visa'),
('2a1c0d9e-8f7a-6b5c-4d3e-2f1a0b9c8d7e', 'Sif Greywolf', 'sif.g@forest.net', '555-666-1122', 'sG4%pQ8nV1cJ', 'cus_UDOPLhBCElG1HZ', 'pm_1TEyJwFGyca1lOb8oL1zdMXe', 'pm_card_mastercard'),
('1c0d9e8f-7a6b-5c4d-3e2f-1a0b9c8d7e6f', 'Patches Spider', 'patches.s@trustworthy.com', '555-888-3344', 'pS6&tR2mW9xL', 'cus_UDOPc8SQ8xIuhE', 'pm_1TEyJxFGyca1lOb8SELK4OMO', 'pm_card_discover'),
('0d9e8f7a-6b5c-4d3e-2f1a-0b9c8d7e6f50', 'Radahn Starscourge', 'radahn.s@redmane.org', '555-123-9999', 'rS8#fY5kD3bN', 'cus_UDOQ7OvIRYchrw', 'pm_1TEyJyFGyca1lOb8pIvSaLV0', 'pm_card_visa'),
('9e8f7a6b-5c4d-3e2f-1a0b-9c8d7e6f5041', 'Ranni Witch', 'ranni.w@moonlight.net', '555-456-7890', 'rW2$mG7vS4xR', 'cus_UDOQCRMHk2I7gb', 'pm_1TEyK0FGyca1lOb8rLLhwMNl', 'pm_card_mastercard'),
('8f7a6b5c-4d3e-2f1a-0b9c-8d7e6f504032', 'Godrick Grafted', 'godrick.g@stormveil.com', '555-789-0123', 'gG5@nH9zC3wT', 'cus_UDOQCRMFI8zKWU', 'pm_1TEyK1FGyca1lOb8eK1D2FDJ', 'pm_card_discover'),
('7a6b5c4d-3e2f-1a0b-9c8d-7e6f50403021', 'Rennala Moon', 'rennala.m@academy.org', '555-012-3456', 'rM7#qK4mL8yD', 'cus_UDORftTZgWGeZV', 'pm_1TEyK2FGyca1lOb8HVx7vYrf', 'pm_card_visa'),
('6b5c4d3e-2f1a-0b9c-8d7e-6f5040302010', 'Morgott King', 'morgott.k@erdtree.net', '555-345-6789', 'mK3$wJ6vP2fK', 'cus_UDORZMSaVjHGOU', 'pm_1TEyK4FGyca1lOb83qWai2QO', 'pm_card_mastercard'),
('5c4d3e2f-1a0b-9c8d-7e6f-504030201001', 'Godfrey Warrior', 'godfrey.w@elden.com', '555-678-9012', 'gW9@hN5xR7bM', 'cus_UDORPkAgjHyrsz', 'pm_1TEyK5FGyca1lOb8N0gkaQ3k', 'pm_card_discover'),
('4d3e2f1a-0b9c-8d7e-6f50-403020100102', 'Maliketh Beast', 'maliketh.b@destined.org', '555-901-2345', 'mB4%pL8nT1cJ', 'cus_UDORQrer29Mh7N', 'pm_1TEyK7FGyca1lOb8qXpwaFyK', 'pm_card_visa'),
('3e2f1a0b-9c8d-7e6f-5040-302010010203', 'Mohg Lord', 'mohg.l@dynasty.net', '555-234-5678', 'mL6&tQ2mV9xL', 'cus_UDOSlLTPkHtvyT', 'pm_1TEyK8FGyca1lOb8b2K6a1LF', 'pm_card_mastercard'),
('2f1a0b9c-8d7e-6f50-4030-201001020304', 'Placidusax Dragon', 'placidusax.d@time.com', '555-567-8901', 'pD8#fR5kW3bN', 'cus_UDOSgv8r2K6AgY', 'pm_1TEyK9FGyca1lOb8EP4Cjg8B', 'pm_card_discover'),
('1a0b9c8d-7e6f-5040-3020-100102030405', 'Blaidd Half', 'blaidd.h@mistwood.org', '555-890-1234', 'bH2$mY7vD4xR', 'cus_UDOSzILQZNYh7c', 'pm_1TEyKBFGyca1lOb8OY3d0eaL', 'pm_card_visa'),
('0b9c8d7e-6f50-4030-2010-010203040506', 'Gehrman Hunter', 'gehrman.h@dream.net', '555-123-4567', 'gH5@nG9zS3wT', 'cus_UDOTQ5b1qjYQTW', 'pm_1TEyKCFGyca1lOb8LpW8693L', 'pm_card_mastercard'),
('9c8d7e6f-5040-3020-1001-020304050607', 'Maria Astral', 'maria.a@clocktower.com', '555-456-7890', 'mA7#qK4mC8yD', 'cus_UDOTcXaPe48TmT', 'pm_1TEyKDFGyca1lOb8Ty79UKBj', 'pm_card_discover'),
('8d7e6f50-4030-2010-0102-030405060708', 'Ludwig Holy', 'ludwig.h@healing.org', '555-789-0123', 'lH3$wJ6vL2fK', 'cus_UDOTuw7j2C0AGf', 'pm_1TEyKFFGyca1lOb8RvC0g7e1', 'pm_card_visa'),
('7e6f5040-3020-1001-0203-040506070809', 'Laurence Beast', 'laurence.b@byrgenwerth.net', '555-012-3456', 'lB9@hP5xR7bM', 'cus_UDOTF7pbrUU45t', 'pm_1TEyKGFGyca1lOb872FOfEp3', 'pm_card_mastercard'),
('6f504030-2010-0102-0304-05060708090a', 'Gascoigne Father', 'gascoigne.f@yharnam.com', '555-345-6789', 'gF4%pN8nT1cJ', 'cus_UDOTT01jjBDXsj', 'pm_1TEyKHFGyca1lOb8NTS26on3', 'pm_card_discover'),
('50403020-1001-0203-0405-0607080910ab', 'Eileen Crow', 'eileen.c@hunters.org', '555-678-9012', 'eC6&tL2mV9xL', 'cus_UDOUWKHgpSyKB0', 'pm_1TEyKJFGyca1lOb8unmSkbq2', 'pm_card_visa'),
('40302010-0102-0304-0506-070809101112', 'Djura Powder', 'djura.p@oldyharnam.net', '555-901-2345', 'dP8#fQ5kW3bN', 'cus_UDOUveeuxWP3vX', 'pm_1TEyKKFGyca1lOb8TAgQNR0a', 'pm_card_mastercard'),
('30201001-0203-0405-0607-080910111213', 'Henryk Hunter', 'henryk.h@tomb.com', '555-234-5678', 'hH2$mR7vD4xR', 'cus_UDOUwVX2pvB0ad', 'pm_1TEyKMFGyca1lOb8poNtG8jO', 'pm_card_discover'),
('20100102-0304-0506-0708-091011121314', 'Valtr Master', 'valtr.m@league.org', '555-567-8901', 'vM5@nY9zS3wT', 'cus_UDOVtzg112Mksw', 'pm_1TEyKNFGyca1lOb8On2brUpu', 'pm_card_visa'),
('10010203-0405-0607-0809-101112131415', 'Alfred Executioner', 'alfred.e@martyr.net', '555-890-1234', 'aE7#qG4mC8yD', 'cus_UDOVOIyVGH99ti', 'pm_1TEyKOFGyca1lOb8SHK3VMw0', 'pm_card_mastercard'),
('01020304-0506-0708-0910-111213141516', 'Isshin Sword', 'isshin.s@ashina.com', '555-123-4567', 'iS3$wK6vL2fK', 'cus_UDOVd3mqyS2pxE', 'pm_1TEyKQFGyca1lOb8jqORJEI2', 'pm_card_discover'),
('02030405-0607-0809-1011-121314151617', 'Genichiro Way', 'genichiro.w@castle.org', '555-456-7890', 'gW9@hJ5xR7bM', 'cus_UDOVfMaBsiouzb', 'pm_1TEyKRFGyca1lOb839hipslU', 'pm_card_visa'),
('03040506-0708-0910-1112-131415161718', 'Emma Gentle', 'emma.g@physician.net', '555-789-0123', 'eG4%pP8nT1cJ', 'cus_UDOWQq6JppJPxS', 'pm_1TEyKTFGyca1lOb8k5lyycUn', 'pm_card_mastercard'),
('04050607-0809-1011-1213-141516171819', 'Sculptor Dilapidated', 'sculptor.d@temple.com', '555-012-3456', 'sD6&tN2mV9xL', 'cus_UDOW9JYOLm6JIa', 'pm_1TEyKUFGyca1lOb8OqDwHwHd', 'pm_card_discover'),
('05060708-0910-1112-1314-15161718191a', 'Kuro Divine', 'kuro.d@heir.org', '555-345-6789', 'kD8#fL5kW3bN', 'cus_UDOW6HKSWeaqF1', 'pm_1TEyKVFGyca1lOb8Vq4LfgB4', 'pm_card_visa'),
('06070809-1011-1213-1415-161718191a1b', 'Owl Great', 'owl.g@shinobi.net', '555-678-9012', 'oG2$mQ7vD4xR', 'cus_UDOXM6Lqg5ia63', 'pm_1TEyKXFGyca1lOb8DrWJ9izF', 'pm_card_mastercard'),
('07080910-1112-1314-1516-1718191a1b1c', 'Guardian Ape', 'guardian.a@forest.com', '555-901-2345', 'gA5@nR9zS3wT', 'cus_UDOX2ej64dsYqh', 'pm_1TEyKYFGyca1lOb8oQUI8lj0', 'pm_card_discover'),
('08091011-1213-1415-1617-18191a1b1c1d', 'Corrupted Monk', 'corrupted.m@mibu.org', '555-234-5678', 'cM7#qY4mC8yD', 'cus_UDOXOcVFbiJdbn', 'pm_1TEyKaFGyca1lOb8ttY5xdHG', 'pm_card_visa'),
('09101112-1314-1516-1718-191a1b1c1d1e', 'Divine Dragon', 'divine.d@palace.net', '555-567-8901', 'dD3$wH6vL2fK', 'cus_UDOXtiXOGv79Q6', 'pm_1TEyKbFGyca1lOb8ZQ6lQePK', 'pm_card_mastercard'),
('0a111213-1415-1617-1819-1a1b1c1d1e1f', 'Demon Fire', 'demon.f@hatred.com', '555-890-1234', 'dF9@hK5xR7bM', 'cus_UDOXRJ4v1UVdYJ', 'pm_1TEyKcFGyca1lOb8XkkcaCFY', 'pm_card_discover');

-- Update all users with Stripe credentials if they exist but don't have them
-- This handles the case where the database was created before Stripe columns were added (commit c6079b1, March 25 2026)
-- Note: These UPDATEs will only affect rows where stripe_customer_id IS NULL
UPDATE user_account SET stripe_customer_id = 'cus_UDJUKtOkn6XoOB', stripe_payment_method_id = 'pm_1TExyFFGyca1lOb8OuCAwtEn', stripe_payment_method_name = 'pm_card_visa' WHERE id = 'b2a5c9f1-3d7f-4b0d-9a8c-9c7b5a1f2e4d' AND stripe_customer_id IS NULL;
UPDATE user_account SET stripe_customer_id = 'cus_UDJWbyD8V585Ov', stripe_payment_method_id = 'pm_1TEyJiFGyca1lOb8mXJNWULT', stripe_payment_method_name = 'pm_card_visa' WHERE id = 'f5e8d1c6-2a9b-4c3e-8f1a-6e5b0d2c9f1a' AND stripe_customer_id IS NULL;
UPDATE user_account SET stripe_customer_id = 'cus_UDJXmCEDzJLVQT', stripe_payment_method_id = 'pm_1TEyJjFGyca1lOb8FQmcbDbn', stripe_payment_method_name = 'pm_card_mastercard' WHERE id = 'e1f2b3c4-5d6a-7e8f-9a0b-1c2d3e4f5a6b' AND stripe_customer_id IS NULL;
UPDATE user_account SET stripe_customer_id = 'cus_UDONEXRz6FuSOJ', stripe_payment_method_id = 'pm_1TEyJkFGyca1lOb89A11DMOY', stripe_payment_method_name = 'pm_card_discover' WHERE id = 'f47ac10b-58cc-4372-a567-0e02b2c3d471' AND stripe_customer_id IS NULL;
UPDATE user_account SET stripe_customer_id = 'cus_UDONja6tdPGNBu', stripe_payment_method_id = 'pm_1TEyJmFGyca1lOb8Osa182qe', stripe_payment_method_name = 'pm_card_visa' WHERE id = 'd9b1e2a3-f4c5-4d6e-8f7a-9b0c1d2e3f4a' AND stripe_customer_id IS NULL;
UPDATE user_account SET stripe_customer_id = 'cus_UDOO7Am0C4id4y', stripe_payment_method_id = 'pm_1TEyJnFGyca1lOb8ACxhFv4I', stripe_payment_method_name = 'pm_card_mastercard' WHERE id = '8c7d6e5f-4a3b-2c1d-0e9f-8a7b6c5d4e3f' AND stripe_customer_id IS NULL;
UPDATE user_account SET stripe_customer_id = 'cus_UDOOCvDNMRi7ms', stripe_payment_method_id = 'pm_1TEyJpFGyca1lOb81c0sji5L', stripe_payment_method_name = 'pm_card_discover' WHERE id = '7f6e5d4c-3b2a-1c0d-9e8f-7a6b5c4d3e2f' AND stripe_customer_id IS NULL;
UPDATE user_account SET stripe_customer_id = 'cus_UDOOXEjO6FUexG', stripe_payment_method_id = 'pm_1TEyJqFGyca1lOb8UzrfjPs2', stripe_payment_method_name = 'pm_card_visa' WHERE id = '6e5d4c3b-2a1c-0d9e-8f7a-6b5c4d3e2f1a' AND stripe_customer_id IS NULL;
UPDATE user_account SET stripe_customer_id = 'cus_UDOO4JRW7eTKxr', stripe_payment_method_id = 'pm_1TEyJsFGyca1lOb8NAHbKMWj', stripe_payment_method_name = 'pm_card_mastercard' WHERE id = '5d4c3b2a-1c0d-9e8f-7a6b-5c4d3e2f1a0b' AND stripe_customer_id IS NULL;
UPDATE user_account SET stripe_customer_id = 'cus_UDOPeiXsu2M1Gu', stripe_payment_method_id = 'pm_1TEyJtFGyca1lOb893U5efaJ', stripe_payment_method_name = 'pm_card_discover' WHERE id = '4c3b2a1c-0d9e-8f7a-6b5c-4d3e2f1a0b9c' AND stripe_customer_id IS NULL;
UPDATE user_account SET stripe_customer_id = 'cus_UDOPteQJOTyk5s', stripe_payment_method_id = 'pm_1TEyJuFGyca1lOb84YC9kGRa', stripe_payment_method_name = 'pm_card_visa' WHERE id = '3b2a1c0d-9e8f-7a6b-5c4d-3e2f1a0b9c8d' AND stripe_customer_id IS NULL;
UPDATE user_account SET stripe_customer_id = 'cus_UDOPLhBCElG1HZ', stripe_payment_method_id = 'pm_1TEyJwFGyca1lOb8oL1zdMXe', stripe_payment_method_name = 'pm_card_mastercard' WHERE id = '2a1c0d9e-8f7a-6b5c-4d3e-2f1a0b9c8d7e' AND stripe_customer_id IS NULL;
UPDATE user_account SET stripe_customer_id = 'cus_UDOPc8SQ8xIuhE', stripe_payment_method_id = 'pm_1TEyJxFGyca1lOb8SELK4OMO', stripe_payment_method_name = 'pm_card_discover' WHERE id = '1c0d9e8f-7a6b-5c4d-3e2f-1a0b9c8d7e6f' AND stripe_customer_id IS NULL;
UPDATE user_account SET stripe_customer_id = 'cus_UDOQ7OvIRYchrw', stripe_payment_method_id = 'pm_1TEyJyFGyca1lOb8pIvSaLV0', stripe_payment_method_name = 'pm_card_visa' WHERE id = '0d9e8f7a-6b5c-4d3e-2f1a-0b9c8d7e6f50' AND stripe_customer_id IS NULL;
UPDATE user_account SET stripe_customer_id = 'cus_UDOQCRMHk2I7gb', stripe_payment_method_id = 'pm_1TEyK0FGyca1lOb8rLLhwMNl', stripe_payment_method_name = 'pm_card_mastercard' WHERE id = '9e8f7a6b-5c4d-3e2f-1a0b-9c8d7e6f5041' AND stripe_customer_id IS NULL;
UPDATE user_account SET stripe_customer_id = 'cus_UDOQCRMFI8zKWU', stripe_payment_method_id = 'pm_1TEyK1FGyca1lOb8eK1D2FDJ', stripe_payment_method_name = 'pm_card_discover' WHERE id = '8f7a6b5c-4d3e-2f1a-0b9c-8d7e6f504032' AND stripe_customer_id IS NULL;
UPDATE user_account SET stripe_customer_id = 'cus_UDORftTZgWGeZV', stripe_payment_method_id = 'pm_1TEyK2FGyca1lOb8HVx7vYrf', stripe_payment_method_name = 'pm_card_visa' WHERE id = '7a6b5c4d-3e2f-1a0b-9c8d-7e6f50403021' AND stripe_customer_id IS NULL;
UPDATE user_account SET stripe_customer_id = 'cus_UDORZMSaVjHGOU', stripe_payment_method_id = 'pm_1TEyK4FGyca1lOb83qWai2QO', stripe_payment_method_name = 'pm_card_mastercard' WHERE id = '6b5c4d3e-2f1a-0b9c-8d7e-6f5040302010' AND stripe_customer_id IS NULL;
UPDATE user_account SET stripe_customer_id = 'cus_UDORPkAgjHyrsz', stripe_payment_method_id = 'pm_1TEyK5FGyca1lOb8N0gkaQ3k', stripe_payment_method_name = 'pm_card_discover' WHERE id = '5c4d3e2f-1a0b-9c8d-7e6f-504030201001' AND stripe_customer_id IS NULL;
UPDATE user_account SET stripe_customer_id = 'cus_UDORQrer29Mh7N', stripe_payment_method_id = 'pm_1TEyK7FGyca1lOb8qXpwaFyK', stripe_payment_method_name = 'pm_card_visa' WHERE id = '4d3e2f1a-0b9c-8d7e-6f50-403020100102' AND stripe_customer_id IS NULL;
UPDATE user_account SET stripe_customer_id = 'cus_UDOSlLTPkHtvyT', stripe_payment_method_id = 'pm_1TEyK8FGyca1lOb8b2K6a1LF', stripe_payment_method_name = 'pm_card_mastercard' WHERE id = '3e2f1a0b-9c8d-7e6f-5040-302010010203' AND stripe_customer_id IS NULL;
UPDATE user_account SET stripe_customer_id = 'cus_UDOSgv8r2K6AgY', stripe_payment_method_id = 'pm_1TEyK9FGyca1lOb8EP4Cjg8B', stripe_payment_method_name = 'pm_card_discover' WHERE id = '2f1a0b9c-8d7e-6f50-4030-201001020304' AND stripe_customer_id IS NULL;
UPDATE user_account SET stripe_customer_id = 'cus_UDOSzILQZNYh7c', stripe_payment_method_id = 'pm_1TEyKBFGyca1lOb8OY3d0eaL', stripe_payment_method_name = 'pm_card_visa' WHERE id = '1a0b9c8d-7e6f-5040-3020-100102030405' AND stripe_customer_id IS NULL;
UPDATE user_account SET stripe_customer_id = 'cus_UDOTQ5b1qjYQTW', stripe_payment_method_id = 'pm_1TEyKCFGyca1lOb8LpW8693L', stripe_payment_method_name = 'pm_card_mastercard' WHERE id = '0b9c8d7e-6f50-4030-2010-010203040506' AND stripe_customer_id IS NULL;
UPDATE user_account SET stripe_customer_id = 'cus_UDOTcXaPe48TmT', stripe_payment_method_id = 'pm_1TEyKDFGyca1lOb8Ty79UKBj', stripe_payment_method_name = 'pm_card_discover' WHERE id = '9c8d7e6f-5040-3020-1001-020304050607' AND stripe_customer_id IS NULL;
UPDATE user_account SET stripe_customer_id = 'cus_UDOTuw7j2C0AGf', stripe_payment_method_id = 'pm_1TEyKFFGyca1lOb8RvC0g7e1', stripe_payment_method_name = 'pm_card_visa' WHERE id = '8d7e6f50-4030-2010-0102-030405060708' AND stripe_customer_id IS NULL;
UPDATE user_account SET stripe_customer_id = 'cus_UDOTF7pbrUU45t', stripe_payment_method_id = 'pm_1TEyKGFGyca1lOb872FOfEp3', stripe_payment_method_name = 'pm_card_mastercard' WHERE id = '7e6f5040-3020-1001-0203-040506070809' AND stripe_customer_id IS NULL;
UPDATE user_account SET stripe_customer_id = 'cus_UDOTT01jjBDXsj', stripe_payment_method_id = 'pm_1TEyKHFGyca1lOb8NTS26on3', stripe_payment_method_name = 'pm_card_discover' WHERE id = '6f504030-2010-0102-0304-05060708090a' AND stripe_customer_id IS NULL;
UPDATE user_account SET stripe_customer_id = 'cus_UDOUWKHgpSyKB0', stripe_payment_method_id = 'pm_1TEyKJFGyca1lOb8unmSkbq2', stripe_payment_method_name = 'pm_card_visa' WHERE id = '50403020-1001-0203-0405-0607080910ab' AND stripe_customer_id IS NULL;
UPDATE user_account SET stripe_customer_id = 'cus_UDOUveeuxWP3vX', stripe_payment_method_id = 'pm_1TEyKKFGyca1lOb8TAgQNR0a', stripe_payment_method_name = 'pm_card_mastercard' WHERE id = '40302010-0102-0304-0506-070809101112' AND stripe_customer_id IS NULL;
UPDATE user_account SET stripe_customer_id = 'cus_UDOUwVX2pvB0ad', stripe_payment_method_id = 'pm_1TEyKMFGyca1lOb8poNtG8jO', stripe_payment_method_name = 'pm_card_discover' WHERE id = '30201001-0203-0405-0607-080910111213' AND stripe_customer_id IS NULL;
UPDATE user_account SET stripe_customer_id = 'cus_UDOVtzg112Mksw', stripe_payment_method_id = 'pm_1TEyKNFGyca1lOb8On2brUpu', stripe_payment_method_name = 'pm_card_visa' WHERE id = '20100102-0304-0506-0708-091011121314' AND stripe_customer_id IS NULL;
UPDATE user_account SET stripe_customer_id = 'cus_UDOVOIyVGH99ti', stripe_payment_method_id = 'pm_1TEyKOFGyca1lOb8SHK3VMw0', stripe_payment_method_name = 'pm_card_mastercard' WHERE id = '10010203-0405-0607-0809-101112131415' AND stripe_customer_id IS NULL;
UPDATE user_account SET stripe_customer_id = 'cus_UDOVd3mqyS2pxE', stripe_payment_method_id = 'pm_1TEyKQFGyca1lOb8jqORJEI2', stripe_payment_method_name = 'pm_card_discover' WHERE id = '01020304-0506-0708-0910-111213141516' AND stripe_customer_id IS NULL;
UPDATE user_account SET stripe_customer_id = 'cus_UDOVfMaBsiouzb', stripe_payment_method_id = 'pm_1TEyKRFGyca1lOb839hipslU', stripe_payment_method_name = 'pm_card_visa' WHERE id = '02030405-0607-0809-1011-121314151617' AND stripe_customer_id IS NULL;
UPDATE user_account SET stripe_customer_id = 'cus_UDOWQq6JppJPxS', stripe_payment_method_id = 'pm_1TEyKTFGyca1lOb8k5lyycUn', stripe_payment_method_name = 'pm_card_mastercard' WHERE id = '03040506-0708-0910-1112-131415161718' AND stripe_customer_id IS NULL;
UPDATE user_account SET stripe_customer_id = 'cus_UDOW9JYOLm6JIa', stripe_payment_method_id = 'pm_1TEyKUFGyca1lOb8OqDwHwHd', stripe_payment_method_name = 'pm_card_discover' WHERE id = '04050607-0809-1011-1213-141516171819' AND stripe_customer_id IS NULL;
UPDATE user_account SET stripe_customer_id = 'cus_UDOW6HKSWeaqF1', stripe_payment_method_id = 'pm_1TEyKVFGyca1lOb8Vq4LfgB4', stripe_payment_method_name = 'pm_card_visa' WHERE id = '05060708-0910-1112-1314-15161718191a' AND stripe_customer_id IS NULL;
UPDATE user_account SET stripe_customer_id = 'cus_UDOXM6Lqg5ia63', stripe_payment_method_id = 'pm_1TEyKXFGyca1lOb8DrWJ9izF', stripe_payment_method_name = 'pm_card_mastercard' WHERE id = '06070809-1011-1213-1415-161718191a1b' AND stripe_customer_id IS NULL;
UPDATE user_account SET stripe_customer_id = 'cus_UDOX2ej64dsYqh', stripe_payment_method_id = 'pm_1TEyKYFGyca1lOb8oQUI8lj0', stripe_payment_method_name = 'pm_card_discover' WHERE id = '07080910-1112-1314-1516-1718191a1b1c' AND stripe_customer_id IS NULL;
UPDATE user_account SET stripe_customer_id = 'cus_UDOXOcVFbiJdbn', stripe_payment_method_id = 'pm_1TEyKaFGyca1lOb8ttY5xdHG', stripe_payment_method_name = 'pm_card_visa' WHERE id = '08091011-1213-1415-1617-18191a1b1c1d' AND stripe_customer_id IS NULL;
UPDATE user_account SET stripe_customer_id = 'cus_UDOXtiXOGv79Q6', stripe_payment_method_id = 'pm_1TEyKbFGyca1lOb8ZQ6lQePK', stripe_payment_method_name = 'pm_card_mastercard' WHERE id = '09101112-1314-1516-1718-191a1b1c1d1e' AND stripe_customer_id IS NULL;
UPDATE user_account SET stripe_customer_id = 'cus_UDOXRJ4v1UVdYJ', stripe_payment_method_id = 'pm_1TEyKcFGyca1lOb8XkkcaCFY', stripe_payment_method_name = 'pm_card_discover' WHERE id = '0a111213-1415-1617-1819-1a1b1c1d1e1f' AND stripe_customer_id IS NULL;

-- Insert test accounts with integer IDs
INSERT INTO checking_accounts (id, name, balance, routing_number, interest_rate) VALUES
(12345, 'Alice Checking', 1500.50, '0123456789', 0.001),
(54321, 'Bob Checking', 2500.75, '5544332211', 0.001),
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
(98766, 'Bob Savings', 3200.00, '6677889900', 0.020),
(67891, 'Charlie Savings', 1500.00, '9988776655', 0.018),
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
('f5e8d1c6-2a9b-4c3e-8f1a-6e5b0d2c9f1a', 54321), -- Bob's checking
('f5e8d1c6-2a9b-4c3e-8f1a-6e5b0d2c9f1a', 98766), -- Bob's savings
('f5e8d1c6-2a9b-4c3e-8f1a-6e5b0d2c9f1a', 98765), -- Bob's credit
('e1f2b3c4-5d6a-7e8f-9a0b-1c2d3e4f5a6b', 67890), -- Charlie's checking
('e1f2b3c4-5d6a-7e8f-9a0b-1c2d3e4f5a6b', 67891), -- Charlie's savings
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
