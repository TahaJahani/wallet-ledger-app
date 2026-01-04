import uuid

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models


# Create your models here.
class Wallet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.PROTECT, related_name='wallet')


class Transaction(models.Model):
    class Type(models.TextChoices):
        deposit = "DEPOSIT", "Deposit"
        withdrawal = "WITHDRAWAL", "Withdrawal"
        transfer_in = "TRANSFER_IN", "Transfer in"
        transfer_out = "TRANSFER_OUT", "Transfer out"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(Wallet, on_delete=models.PROTECT, related_name='transactions', null=False, blank=False)
    type = models.CharField(choices=Type.choices, max_length=15, null=False, blank=False)
    amount = models.PositiveBigIntegerField(null=False, blank=False)
    reference = models.CharField(null=False, blank=False, max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default={})

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("UPDATING IMMUTABLE OBJECT")
        super(Transaction, self).save(*args, **kwargs)
