import uuid

from django.db import models
from django.db.models.aggregates import Sum
from django.db.models.expressions import Case, When, F
from django.db.models.fields import IntegerField


class Wallet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    @property
    def balance(self):
        from .transaction import Transaction
        result = self.transactions.aggregate(
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
        return result["balance"] or 0
