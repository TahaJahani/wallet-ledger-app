# Wallet Ledger Project
## Introduction
This program is a simulation of a wallet ledger system, where users can commit different transactions on their wallets.
The program is written in Django and uses simple SQLite database. Several API endpoints are exposed for procedures such as authentication and submitting transactions.
## How to run
1. First, you need to create a database and migrate all tables into it. to do so, run:
```shell
python3 manage.py migrate
```
2. After that, you need to create a super user to access admin page:
```shell
python3 manage.py createsuperuser
```
you will be prompted to enter username, email address and password.
3. If running on a production server, you should add cron jobs:
```shell
python3 manage.py crontab add
```
3. Next, run the project:
```shell
python3 manage.py runserver
```
You can visit the admin page in [localhost:8000/admin](http://localhost:8000/admin)
5. If you want to run system tests, you can use this command:
```shell
python3 manage.py test apps
```
## How to use (APIs)
There are 9 API endpoints implemented in this project. An example of each API request and response is included in a postman collection, available in [project repository](./Wallet%20Ledger.postman_collection.json). Note that all protected APIs need a valid `API token` inside `AUTHORIZATION` header in order to authenticate current user. A brief explanation of each endpoint is as follows:
1. `POST /api/auth/login`: This endpoint requires a valid username and password, and if correct, returns an access token with which you can use your wallet APIs.
2. `POST /api/auth/logout`: This endpoint accepts a valid token inside `AUTHORIZATION` header, and deletes the active session.
3. `GET /api/auth/profile`: This endpoint returns the current logged in user profile info, containing id, username, email, first name and last name.
4. `POST /api/auth/register`: This endpoint requires username, email, password, password confirmation, first name and last name. If the username is unique, it creates a new user and binds a wallet to that user.
5. `GET /api/wallets/me`: This endpoint returns current user's wallet data, containing id, balance and ten recent transactions.
6. `POST /api/wallets/me/deposit`: This endpoint accepts a reference and an amount number. If the reference is unique for the user, it commits a deposit transaction for user's wallet.
7. `POST /api/wallets/me/withdraw`: Same as `deposit`, if user's wallet has sufficient balance, a withdrawal transaction is submitted.
8. `POST /api/wallets/me/transfer`: In addition to amount and reference, this endpoint required `to_user_id`, which is the user id of the destination wallet. Again, if reference is unique for sender and sender has sufficient balance, two transactions are committed: a transfer out for sender and a transfer in for receiver.
9. `GET /api/wallets/me/transactions`: This endpoint does not require any input, but `limit` and `offset` are optional inputs to control pagination. This endpoint returns the requested transactions data for the current user.

## Technical notes
Based on the requirements document that was provided to implement this application, several technical notes are important and should be considered.

First of all, it is required that each user has exactly ***one*** wallet. With this requirement, it is best to have all wallet info inside the user table. Doing so will apply many limitations on further feature development. So, I decided to use a foreign key. If a foreign key to the user is stored inside wallets table, then the requirement may break and a user could have several wallets registered. As a conclusion, It was best to put a foreign key to the wallet inside users table. In addition, I had to define my own user model and I could not use Django's default user management methods.
After defining a custom user model, I could override the `UserManager` class and create a wallet whenever a new user is added to the database.
It is good to mention that this task could be done using Django `signals`. The main pitfall of this method is the hidden data flow; i.e. when a user is created, a signal is fired and caught inside another part of the program, leading to misunderstanding of how exactly data is being modified. But overriding the `UserManager` class clearly shows how a wallet is created when the user is saved to the database.

Secondly, all delete and update permissions on wallet and transaction models are limited in admin page. Also, with the definition of `TransactionsManager`, updating and deleting transactions in application level are prohibited. With these tools, I can have a better control on data consistency and business logic. If other developers work on this project, they will not be able to mistakenly update or delete transactions inside their code.
Note that when writing codes in Django, all limitations are applied at application level; This means that one can separately connect to the database and apply raw queries on transaction data. To prevent that, database-level mechanism should be used, which is outside the scope of this application and cannot be applied on simple database systems like `sqlite`

Thirdly, there are some technical explanation about how wallet `balance` is managed in this system. Saving balance as a database field inside wallets can lead to data inconsistency, alongside numerous database queries needed to keep the balance updated.
On the other hand, calculating balance each time from the transactions is too slow. Specially when the number of transactions increase.
So, a middle approach is used. Wallets have two fields called `last_balance` and `last_balance_update`. These fields hold the last calculated balance value and the time this value was calculated, respectively. Every night, these two values are updated for all wallets with a cron job. (Note that during running this job, accessing to database is limited and no new transactions can be applied) Then, during each day, when accessing wallet balance, the last balance value is added to the net amount of the transactions that are committed that day.

Finally, concurrency is handled with Django's transactions library. Every time a new transaction is going to be committed, the source and destination wallets are locked and no new transaction can be committed on those wallets. Also, the whole transaction is atomic; e.g. in transfer transactions, if one of the transactions causes an error, the the other transaction is rolled back too.
It is good to mention that SQLite database does not handle data locking so well. So it is normal that the concurrency test fails on this project. If the setting is changed to use a more advanced DBMS, like PostgreSQL, this test will pass too.
