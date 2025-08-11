# dev notes

## Transaction Types
- Bill payment/ledger transactions
- Credit card transactions w/ merchant involvement
- Transactions involving Stripe or some external connection


## misc notes

Go with MSSQL Express

The transaction-service is currently designed to directly insert data from Kafka messages into the MSSQL database. While the bill-pay service validates the initial request, the consumer should re-validate the data before inserting it into the database. This prevents bad or malformed data from corrupting your transaction ledger.

Can use this to cause issues for a demo scenario later.