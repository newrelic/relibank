TODOs

DB interface python with endpoints for auth service
Add Transaction types:
shopping | credit_card | loan | entertainment | utilities | groceries | gas | etc

Check that to/fromaccount is valid, check balance on each before initiating payment or cancel if it's impossible

In Accounts, add an account for Relibank that will handle all loan payments. Build out loan payments in the code

Convert logging.info calls to json instead of flat logs



Completed items (not comprehensive)

DONE placeholder for posts/puts, so we can implement adding new accounts later
DONE In Transactions, add a DB table that stores outstanding balance on a loan/credit account, amount on a checking/savings account
DONE In Bill Pay, add from/to account
DONE Enforce uniqueness on BillIDs