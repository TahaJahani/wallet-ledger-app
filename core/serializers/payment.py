from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError
from core.models import Wallet, Transaction


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['id', 'type', 'amount', 'reference', 'created_at', 'metadata']
        read_only_fields = ['id', 'type', 'amount', 'reference', 'created_at', 'metadata']


class WalletSerializer(serializers.ModelSerializer):
    recent_transactions = serializers.SerializerMethodField()

    class Meta:
        model = Wallet
        fields = ['id', 'balance', 'recent_transactions']
        read_only_fields = ['id', 'balance']

    def get_recent_transactions(self, obj):
        transactions = obj.transactions.order_by('-created_at')[:10]
        return TransactionSerializer(transactions, many=True).data


class DepositSerializer(serializers.Serializer):
    amount = serializers.IntegerField(min_value=1)
    reference = serializers.CharField(max_length=255)
    metadata = serializers.JSONField(required=False, default=dict)

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be positive")
        return value

    def validate(self, attrs):
        wallet = self.context['wallet']
        reference = attrs['reference']

        existing = Transaction.objects.filter(
            wallet=wallet,
            type=Transaction.Type.deposit,
            reference=reference
        ).first()

        if existing:
            self.context['existing_transaction'] = existing
            self.context['is_idempotent'] = True

        return attrs

    def create(self, validated_data):
        if self.context.get('is_idempotent'):
            return self.context['existing_transaction']

        wallet = self.context['wallet']
        try:
            transaction = Transaction.objects.deposit(
                wallet=wallet,
                amount=validated_data['amount'],
                reference=validated_data['reference'],
                metadata=validated_data.get('metadata', {})
            )
            return transaction
        except DjangoValidationError as e:
            raise serializers.ValidationError(str(e))


class WithdrawSerializer(serializers.Serializer):
    amount = serializers.IntegerField(min_value=1)
    reference = serializers.CharField(max_length=255)
    metadata = serializers.JSONField(required=False, default=dict)

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be positive")
        return value

    def validate(self, attrs):
        wallet = self.context['wallet']
        reference = attrs['reference']

        existing = Transaction.objects.filter(
            wallet=wallet,
            type=Transaction.Type.withdrawal,
            reference=reference
        ).first()

        if existing:
            self.context['existing_transaction'] = existing
            self.context['is_idempotent'] = True
            return attrs

        if wallet.balance < attrs['amount']:
            raise serializers.ValidationError({
                'amount': 'Insufficient funds'
            })

        return attrs

    def create(self, validated_data):
        if self.context.get('is_idempotent'):
            return self.context['existing_transaction']

        wallet = self.context['wallet']
        try:
            transaction = Transaction.objects.withdraw(
                wallet=wallet,
                amount=validated_data['amount'],
                reference=validated_data['reference'],
                metadata=validated_data.get('metadata', {})
            )
            return transaction
        except DjangoValidationError as e:
            raise serializers.ValidationError(str(e))


class TransferSerializer(serializers.Serializer):
    to_user_id = serializers.IntegerField()
    amount = serializers.IntegerField(min_value=1)
    reference = serializers.CharField(max_length=255)
    metadata = serializers.JSONField(required=False, default=dict)

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be positive")
        return value

    def validate_to_user_id(self, value):
        from_wallet = self.context['wallet']
        if from_wallet.user.id == value:
            raise serializers.ValidationError("Cannot transfer to yourself")

        try:
            to_wallet = Wallet.objects.get(user__id=value)
        except Wallet.DoesNotExist:
            raise serializers.ValidationError("Recipient wallet not found")

        return value

    def validate(self, attrs):
        wallet = self.context['wallet']
        reference = attrs['reference']

        existing_withdrawal = Transaction.objects.filter(
            wallet=wallet,
            type=Transaction.Type.withdrawal,
            reference=reference
        ).first()

        if existing_withdrawal:
            existing_deposit = Transaction.objects.filter(
                type=Transaction.Type.deposit,
                reference=reference
            ).first()

            self.context['existing_withdrawal'] = existing_withdrawal
            self.context['existing_deposit'] = existing_deposit
            self.context['is_idempotent'] = True
            return attrs

        if wallet.balance < attrs['amount']:
            raise serializers.ValidationError({
                'amount': 'Insufficient funds'
            })

        return attrs

    def create(self, validated_data):
        if self.context.get('is_idempotent'):
            return (
                self.context['existing_withdrawal'],
                self.context['existing_deposit']
            )

        from_wallet = self.context['wallet']
        to_wallet = Wallet.objects.get(user__id=validated_data['to_user_id'])

        try:
            withdrawal, deposit = Transaction.objects.transfer(
                from_wallet=from_wallet,
                to_wallet=to_wallet,
                amount=validated_data['amount'],
                reference=validated_data['reference'],
                metadata=validated_data.get('metadata', {})
            )
            return withdrawal, deposit
        except DjangoValidationError as e:
            raise serializers.ValidationError(str(e))


class TransactionListSerializer(serializers.Serializer):
    limit = serializers.IntegerField(default=20, min_value=1, max_value=100)
    offset = serializers.IntegerField(default=0, min_value=0)
