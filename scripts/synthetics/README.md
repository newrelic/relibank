# ReliBank Synthetics Scripts

These scripts are designed to be copied into **New Relic Synthetics** as Scripted Browser monitors to simulate user journeys and validate application behavior.

## Setup

1. Navigate to **New Relic � Synthetics � Create monitor**
2. Select **Scripted browser** monitor type
3. Copy and paste one of the scripts below
4. Configure monitor settings (frequency, locations, alerts)

## Available Scripts

### 1. `selenium_login.js`
**Purpose:** Basic login flow validation

**What it does:**
- Navigates to ReliBank homepage
- Enters username and password
- Clicks Sign In button
- Validates successful redirect to dashboard

**Errors generated:**
- None (happy path validation)
- Monitor fails if login doesn't work

**Use case:** Validates core authentication functionality

---

### 2. `selenium_transfer.js`
**Purpose:** Successful funds transfer flow with randomized amounts

**What it does:**
- Generates a random transfer amount between $1-$100
- Logs in to ReliBank
- Transfers the random amount from checking to savings
- Validates success message appears
- Clicks "Show All" and "Show Less" transaction buttons
- Reverses the transfer (transfers the same amount back to checking)
- Validates second transfer completes
- Account balances return to original state

**Errors generated:**
- None (happy path validation)
- Monitor fails if transfer functionality breaks

**Use case:**
- Validates end-to-end transfer functionality and UI interactions
- Creates varied transaction data in New Relic for more realistic demos
- Tests transfer logic with different dollar amounts on each run

---

### 3. `selenium_chatbot.js`
**Purpose:** Insufficient funds error flow with support interaction

**What it does:**
- Logs in to ReliBank
- Attempts to transfer $10,000 from checking (balance: $8,500.25)
- Validates "Insufficient funds" error message appears
- Navigates to Support page
- Submits support question about failed transfer
- Validates support interaction completes

**Errors generated:**
- **InsufficientFundsError** in New Relic Errors Inbox for Browser
- Captured from `bill-pay-service` backend with attributes:
  - `account_type`: checking
  - `requested_amount`: 10000.00
  - `available_balance`: 8500.25
  - `error.class`: InsufficientFundsError

**Use case:**
- Validates error handling works correctly
- Generates realistic error data in Errors Inbox for demos
- Tests support flow integration

---

### 4. `selenium_brute_force_login_charlie.js`
**Purpose:** Brute force attack simulation and security monitoring

**What it does:**
- Simulates a brute force attack on Charlie's account (charlie.b@relibank.com)
- Attempts 65 different incorrect passwords from an expanded rainbow table including:
  - Common passwords (password123, Password123!, admin, root, etc.)
  - Charlie-specific attempts (charlie123, Charlie2024!, charliebaker, etc.)
  - Bank-related passwords (relibank123, banking123, finance123, etc.)
  - Common patterns (P@ssw0rd, Passw0rd!, Summer2024, etc.)
  - Keyboard patterns (qwerty123, qazwsx123, asdfgh123, etc.)
  - Date/number patterns (01011990, 123456, 2024, etc.)
- Validates each login attempt fails (stays on login page)
- Mimics realistic brute force timing with 2.5-second delays between attempts

**Errors generated:**
- **65x FailedLoginInvalidPassword** errors in New Relic Errors Inbox for APM
- Each error captured from `auth-service` backend with attributes:
  - `email`: charlie.b@relibank.com
  - `reason`: invalid_password
  - `login_status`: failed
  - `actor_ip`: [Synthetic monitor IP]
  - `actor_user_agent`: [New Relic Synthetics user agent]
  - `actor_origin`: unknown
  - `error.class`: auth_service.FailedLoginInvalidPassword

**Use case:**
- Simulates real-world brute force attack patterns
- Generates multiple security-related errors for demo scenarios
- Tests failed login tracking and analytics at scale
- Validates New Relic APM security monitoring dashboards
- Demonstrates error grouping and pattern detection capabilities

**Security Note:** This is a controlled synthetic test against your own application. Do not use this script against systems you don't own or have permission to test.

---

## Configuration Notes

**Base URL:** All scripts use `http://relibank.westus2.cloudapp.azure.com/`
- Update this URL if deploying to a different environment, change later to use environment variables for lower environments

**Default Credentials:** Scripts use default login (form auto-filled)


