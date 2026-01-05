import uuid

from django.db import models
from django.db.models.aggregates import Sum
from django.db.models.expressions import Case, When, F
from django.db.models.fields import IntegerField
from django.utils import timezone


class Wallet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    last_balance = models.PositiveBigIntegerField(default=0)
    last_balance_update = models.DateTimeField(auto_now_add=True)

    def update_balance(self):
        result = self.__get_transactions_after_balance_update()
        self.last_balance_update = timezone.now()
        self.last_balance += (result["balance"] or 0)
        self.save()

    @property
    def balance(self):
        result = self.__get_transactions_after_balance_update()
        return self.last_balance + (result["balance"] or 0)

    def __get_transactions_after_balance_update(self):
        from .transaction import Transaction
        return self.transactions.filter(
            created_at__gt=self.last_balance_update
        ).aggregate(
            balance=Sum(
                Case(
                    When(
                        type__in=[
                            Transaction.Type.deposit,
                            Transaction.Type.transfer_in,
                        ],
                        then=F("amount"),
                    ),
                    When(
                        type__in=[
                            Transaction.Type.withdrawal,
                            Transaction.Type.transfer_out,
                        ],
                        then=-F("amount"),
                    ),
                    output_field=IntegerField(),
                )
            )
        )
