# user flows

### loan payments
Reduces outstanding balance on user account's loan account
Reduces remaining balance on a loan's account if we keep separate accounts for that

UI flow:
1) User account screen, click outstanding loans
2) Loan account screen, click pay or click set up recurring payment
3) Payment screen, enter amount, click finalize payment
4) If recurring, enter the schedule and click schedule payment

Backend flow:
1) Payment or scheduled payment initiated on Bill Pay service
2) Payment or scheduled payment sent to kafka
3) Transaction service sees payment or schedule
4) If payment, Transaction service updates amounts on user's account on the Account service and the Loan account
5) Notification service sees payment and sends SMS/email to user
6) If recurring, Transaction service updates the DB and it's later picked up by the Event Scheduler

### credit card payments
Reduces outstanding balance on user account's credit card on their account
UI flow:
1) User account screen, click credit
2) Credit card account screen shows minimum payment, due date. User clicks pay
3) Payment screen, enter amount, click finalize payment

Backend flow:
1) Payment initiated on Bill Pay service
2) Payment sent to kafka
3) Transaction service sees payment
4) Transaction service updates amounts on user's account on the Account service
5) Notification service sees payment and sends SMS/email to user