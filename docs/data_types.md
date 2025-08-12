# data types

## transaction types - transaction DB

### loan payments


### credit card payments


### debit card payments
direct deposit?



## accounts - accounts DB

### example user info
id (uuid16), name, alert_preferences, phone, email, address, income, preferred_language, marketing_preferences, privacy_preferences

#### example accounts (checking/debit, savings)
id (uuid16), name, balance, routing, interest, last_statement_date

#### example accounts payable (credit, loans)
id (uuid16), name, balance, outstanding_balance, routing, interest rate, last_statement_date, payment_schedule, last_payment_date, automatic_pay

### account_user (relationship table)
account_id, user_id


