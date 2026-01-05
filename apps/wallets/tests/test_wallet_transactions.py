from django.core.exceptions import ValidationError
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.wallets.models import Transaction

User = get_user_model()


class WalletTransactionTestCase(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            username='user1',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            password='testpass123'
        )
        self.wallet1 = self.user1.wallet
        self.wallet2 = self.user2.wallet

    def test_deposit_increases_balance(self):
        initial_balance = self.wallet1.balance
        deposit_amount = 100

        txn = Transaction.objects.deposit(
            wallet=self.wallet1,
            amount=deposit_amount,
            reference='DEP001',
            metadata={"description": 'Test deposit'}
        )

        self.wallet1.refresh_from_db()

        self.assertEqual(txn.type, Transaction.Type.deposit)
        self.assertEqual(txn.amount, deposit_amount)
        self.assertEqual(txn.wallet, self.wallet1)
        self.assertEqual(txn.reference, 'DEP001')

        self.assertEqual(self.wallet1.balance, initial_balance + deposit_amount)

    def test_withdrawal_fails_on_insufficient_funds(self):
        Transaction.objects.deposit(
            wallet=self.wallet1,
            amount=50,
            reference='DEP002',
            metadata={"description": 'Initial deposit'}
        )

        self.wallet1.refresh_from_db()
        initial_balance = self.wallet1.balance

        with self.assertRaises(ValidationError) as context:
            Transaction.objects.withdraw(
                wallet=self.wallet1,
                amount=100,
                reference='WTH001',
                metadata={"description": 'Overdraft attempt'}
            )

        self.assertIn('Insufficient funds', str(context.exception))

        self.wallet1.refresh_from_db()
        self.assertEqual(self.wallet1.balance, initial_balance)

        self.assertFalse(Transaction.objects.filter(reference='WTH001').exists())

    def test_transfer_creates_two_entries_and_updates_balances(self):
        Transaction.objects.deposit(
            wallet=self.wallet1,
            amount=200,
            reference='DEP003',
            metadata={"description": 'Initial balance'}
        )

        self.wallet1.refresh_from_db()
        self.wallet2.refresh_from_db()

        initial_balance1 = self.wallet1.balance
        initial_balance2 = self.wallet2.balance
        transfer_amount = 75

        withdraw_txn, deposit_txn = Transaction.objects.transfer(
            from_wallet=self.wallet1,
            to_wallet=self.wallet2,
            amount=transfer_amount,
            reference='TRF001',
            metadata={"description": 'Test transfer'}
        )

        self.wallet1.refresh_from_db()
        self.wallet2.refresh_from_db()

        self.assertEqual(withdraw_txn.type, Transaction.Type.transfer_out)
        self.assertEqual(withdraw_txn.amount, transfer_amount)
        self.assertEqual(withdraw_txn.wallet, self.wallet1)
        self.assertEqual(withdraw_txn.reference, 'TRF001')

        self.assertEqual(deposit_txn.type, Transaction.Type.transfer_in)
        self.assertEqual(deposit_txn.amount, transfer_amount)
        self.assertEqual(deposit_txn.wallet, self.wallet2)
        self.assertEqual(deposit_txn.reference, 'TRF001')

        self.assertEqual(
            self.wallet1.balance,
            initial_balance1 - transfer_amount
        )
        self.assertEqual(
            self.wallet2.balance,
            initial_balance2 + transfer_amount
        )

        self.assertEqual(withdraw_txn.amount, initial_balance1 - self.wallet1.balance)
        self.assertEqual(deposit_txn.amount, self.wallet2.balance - initial_balance2)

    def test_idempotency_same_reference_does_not_duplicate(self):
        reference = 'IDEMPOTENT001'
        amount = 100

        txn1 = Transaction.objects.deposit(
            wallet=self.wallet1,
            amount=amount,
            reference=reference,
            metadata={"description": 'First attempt'}
        )

        self.wallet1.refresh_from_db()
        balance_after_first = self.wallet1.balance

        txn2 = Transaction.objects.deposit(
            wallet=self.wallet1,
            amount=amount,
            reference=reference,
            metadata={"description": 'Second attempt'}
        )

        self.wallet1.refresh_from_db()

        self.assertEqual(txn1.id, txn2.id)
        self.assertEqual(self.wallet1.balance, balance_after_first)

        txn_count = Transaction.objects.filter(
            reference=reference,
            type=Transaction.Type.deposit
        ).count()
        self.assertEqual(txn_count, 1)

    def test_transactions_are_immutable(self):
        txn = Transaction.objects.deposit(
            wallet=self.wallet1,
            amount=100,
            reference='IMM001',
            metadata={"description": 'Immutable test'}
        )

        original_amount = txn.amount
        original_balance = self.wallet1.balance

        txn.amount = 200

        with self.assertRaises(RuntimeError) as context:
            txn.save()

        self.assertIn('Transactions are immutable', str(context.exception))

        txn.refresh_from_db()
        self.assertEqual(txn.amount, original_amount)
        self.assertEqual(self.wallet1.balance, original_balance)

        with self.assertRaises(RuntimeError) as context:
            Transaction.objects.filter(id=txn.id).update(
                amount=300
            )

        self.assertIn('Transactions are immutable and cannot be updated', str(context.exception))

        txn.refresh_from_db()
        self.assertEqual(txn.amount, original_amount)
