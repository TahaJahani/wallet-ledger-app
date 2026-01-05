from django.db import transaction

from apps.wallets.models import Wallet


@transaction.atomic
def update_wallet_balances():
    wallets = Wallet.objects.all()
    for wallet in wallets:
        wallet.update_balance()
