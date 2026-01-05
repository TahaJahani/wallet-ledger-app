import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.query_utils import Q

from .wallet import Wallet


class TransactionQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise RuntimeError("Transactions are immutable and cannot be updated")

    def bulk_update(self, objs, fields, **kwargs):
        raise RuntimeError("Transactions are immutable and cannot be updated")

    def delete(self):
        raise RuntimeError("Transactions are immutable and cannot be deleted")

    def bulk_create(self, objs, **kwargs):
        raise RuntimeError("Use factory methods to create transactions")


class TransactionManager(models.Manager):
    def get_queryset(self):
        return TransactionQuerySet(self.model, using=self._db)

    def update(self, **kwargs):
        raise RuntimeError("Transactions are immutable and cannot be updated")

    def bulk_update(self, objs, fields, batch_size=None):
        raise RuntimeError(
            "Transactions are immutable and cannot be updated"
        )

    def __create_transaction(self, *, wallet, type, amount, reference, metadata=None):
        from django.db import transaction

        if amount <= 0:
            raise ValidationError("Amount must be positive")

        existing_transaction = Transaction.objects.filter(reference=reference, wallet=wallet, type=type).first()
        if existing_transaction is not None:
            return existing_transaction

        with transaction.atomic():
            wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)

            if type in (
                    Transaction.Type.withdrawal,
                    Transaction.Type.transfer_out,
            ):
                if wallet.balance < amount:
                    raise ValidationError("Insufficient funds")

            t = Transaction(
                wallet=wallet,
                type=type,
                amount=amount,
                reference=reference,
                metadata=metadata or {},
            )
            t._safely_created = True
            t.save()
            t._safely_created = False
            return t

    def deposit(self, wallet, amount, reference, metadata=None):
        return self.__create_transaction(
            wallet=wallet,
            type=Transaction.Type.deposit,
            amount=amount,
            reference=reference,
            metadata=metadata,
        )

    def withdraw(self, wallet, amount, reference, metadata=None):
        return self.__create_transaction(
            wallet=wallet,
            type=Transaction.Type.withdrawal,
            amount=amount,
            reference=reference,
            metadata=metadata,
        )

    def transfer(self, from_wallet, to_wallet, amount, reference, metadata=None):
        from django.db import transaction

        if from_wallet.pk == to_wallet.pk:
            raise ValidationError("Cannot transfer to the same wallet")

        if amount <= 0:
            raise ValidationError("Amount must be positive")

        existing_transaction = Transaction.objects.filter(
            reference=reference,
            wallet=from_wallet,
            type=Transaction.Type.transfer_out
        ).first()

        if existing_transaction is not None:
            return existing_transaction

        with transaction.atomic():
            wallets = (
                Wallet.objects
                .select_for_update()
                .filter(pk__in=[from_wallet.pk, to_wallet.pk])
                .order_by('pk')
            )

            wallets_map = {w.pk: w for w in wallets}
            from_wallet = wallets_map[from_wallet.pk]
            to_wallet = wallets_map[to_wallet.pk]

            if from_wallet.balance < amount:
                raise ValidationError("Insufficient funds in source wallet")

            withdrawal = Transaction(
                wallet=from_wallet,
                type=Transaction.Type.transfer_out,
                amount=amount,
                reference=reference,
                metadata=metadata or {},
            )
            withdrawal._safely_created = True
            withdrawal.save()
            withdrawal._safely_created = False

            deposit = Transaction(
                wallet=to_wallet,
                type=Transaction.Type.transfer_in,
                amount=amount,
                reference=reference,
                metadata=metadata or {},
            )
            deposit._safely_created = True
            deposit.save()
            deposit._safely_created = False

            return withdrawal, deposit


class Transaction(models.Model):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._safely_created = False

    class Type(models.TextChoices):
        deposit = "DEPOSIT", "Deposit"
        withdrawal = "WITHDRAWAL", "Withdrawal"
        transfer_in = "TRANSFER_IN", "Transfer in"
        transfer_out = "TRANSFER_OUT", "Transfer out"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(Wallet, on_delete=models.PROTECT, related_name='transactions', null=False, blank=False)
    type = models.CharField(choices=Type.choices, max_length=15, null=False, blank=False)
    amount = models.PositiveBigIntegerField(null=False, blank=False)
    reference = models.CharField(null=False, blank=False, max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict)

    objects = TransactionManager()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name="amount_greater_than_zero",
            ),
            models.UniqueConstraint(
                fields=["wallet", "reference", "type"],
                name="unique_wallet_reference_type"
            )
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise RuntimeError("Transactions are immutable and cannot be updated")
        if not self._safely_created:
            raise RuntimeError("Use factory methods to create transactions")
        super(Transaction, self).save(*args, **kwargs)
