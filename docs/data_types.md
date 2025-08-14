# data types

## transaction types - transaction DB

### loan payments


### credit card payments


### debit card payments
direct deposit?



## accounts - accounts DB

### user info - user account table
id (uuid16), name, alert_preferences, phone, email, address, income, preferred_language, marketing_preferences (blob), privacy_preferences (blob)

#### checking account, savings account
id (uuid16), name, balance, routing, interest rate, last_statement_date

#### loan account, credit account
id (uuid16), name, balance, outstanding_balance, routing, interest rate, last_statement_date, payment_schedule, last_payment_date, automatic_pay

### account_user (relationship table)
account_id, user_id


