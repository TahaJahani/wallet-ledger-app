from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.deletion import ProtectedError

from .wallet import Wallet


class UserManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError("Username is required")
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.wallet = Wallet()
        user.wallet.save()
        user.save()
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        return self.create_user(username, password, **extra_fields)


class User(AbstractUser):
    email = models.EmailField(blank=True, null=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    wallet = models.OneToOneField(Wallet, on_delete=models.PROTECT, related_name='user')
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    def delete(self, *args, **kwargs):
        if self.wallet_id:
            raise ProtectedError(
                "Cannot delete user",
                self
            )
        super().delete(*args, **kwargs)

    def __str__(self):
        return self.username
