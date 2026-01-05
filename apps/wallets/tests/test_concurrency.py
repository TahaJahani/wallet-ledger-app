import threading
from decimal import Decimal

from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from apps.wallets.models import Wallet, Transaction

User = get_user_model()


class ConcurrencyTestCase(TransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='concurrent_user',
            password='testpass123'
        )
        self.wallet = self.user.wallet

        Transaction.objects.deposit(
            wallet=self.wallet,
            amount=100,
            reference='INITIAL',
            metadata={"description": 'Initial balance for concurrency test'}
        )

    def test_concurrent_withdrawals_prevent_overdraft(self):
        errors = []
        successes = []

        def withdraw_50(ref_suffix):
            try:
                wallet = Wallet.objects.get(id=self.wallet.id)

                txn = Transaction.objects.withdraw(
                    wallet=wallet,
                    amount=50,
                    reference=f'CONCURRENT_{ref_suffix}',
                    metadata={"description" : f'Concurrent withdrawal {ref_suffix}'}
                )
                successes.append(txn)
            except ValueError as e:
                errors.append(str(e))
            except Exception as e:
                errors.append(f'Unexpected: {str(e)}')

        thread1 = threading.Thread(target=withdraw_50, args=('T1',))
        thread2 = threading.Thread(target=withdraw_50, args=('T2',))

        thread1.start()
        thread2.start()

        thread1.join()
        thread2.join()

        self.assertEqual(len(successes), 1,
                         "Only one withdrawal should succeed")
        self.assertEqual(len(errors), 1,
                         "One withdrawal should fail with insufficient funds")

        self.assertTrue(
            any('Insufficient funds' in err for err in errors),
            f"Expected insufficient funds error, got: {errors}"
        )

        self.wallet.refresh_from_db()
        self.assertEqual(
            self.wallet.balance,
            Decimal('50'),
            "Final balance should be 50 (one successful 50 withdrawal)"
        )

        txn_count = Transaction.objects.filter(wallet=self.wallet).count()
        self.assertEqual(txn_count, 2,
                         "Should have initial deposit + one successful withdrawal")


class TransactionQuerySetTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='queryset_user',
            password='testpass123'
        )
        self.wallet = self.user.wallet

    def test_bulk_update_blocked(self):
        txn1 = Transaction.objects.deposit(
            wallet=self.wallet,
            amount=100,
            reference='BULK1',
            metadata={"description": 'Bulk test 1'}
        )
        txn2 = Transaction.objects.deposit(
            wallet=self.wallet,
            amount=200,
            reference='BULK2',
            metadata={"description": 'Bulk test 2'}
        )

        txn1.metadata = {"description": 'Modified'}
        txn2.metadata = {"description": 'Modified'}

        with self.assertRaises(RuntimeError) as context:
            Transaction.objects.bulk_update([txn1, txn2], ['description'])

        self.assertIn('Transactions are immutable and cannot be updated', str(context.exception))

        txn1.refresh_from_db()
        txn2.refresh_from_db()
        self.assertEqual(txn1.metadata["description"], 'Bulk test 1')
        self.assertEqual(txn2.metadata["description"], 'Bulk test 2')
