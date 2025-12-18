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
**Purpose:** Successful funds transfer flow

**What it does:**
- Logs in to ReliBank
- Transfers $100 from checking to savings
- Validates success message appears
- Clicks "Show All" and "Show Less" transaction buttons
- Reverses the transfer (transfers $100 back to checking)
- Validates second transfer completes

**Errors generated:**
- None (happy path validation)
- Monitor fails if transfer functionality breaks

**Use case:** Validates end-to-end transfer functionality and UI interactions

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

## Configuration Notes

**Base URL:** All scripts use `http://relibank.westus2.cloudapp.azure.com/`
- Update this URL if deploying to a different environment, change later to use environment variables for lower environments

**Default Credentials:** Scripts use default login (form auto-filled)


