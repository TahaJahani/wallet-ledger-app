from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import Wallet
from .serializers import (
    WalletSerializer,
    DepositSerializer,
    WithdrawSerializer,
    TransferSerializer,
    TransactionSerializer,
    TransactionListSerializer
)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def deposit(request):
    wallet = get_object_or_404(Wallet, user=request.user)

    serializer = DepositSerializer(
        data=request.data,
        context={'wallet': wallet}
    )

    if serializer.is_valid():
        transaction = serializer.save()
        is_idempotent = serializer.context.get('is_idempotent', False)

        return Response(
            TransactionSerializer(transaction).data,
            status=status.HTTP_200_OK if is_idempotent else status.HTTP_201_CREATED
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def withdraw(request):
    wallet = get_object_or_404(Wallet, user=request.user)

    serializer = WithdrawSerializer(
        data=request.data,
        context={'wallet': wallet}
    )

    if serializer.is_valid():
        transaction = serializer.save()
        is_idempotent = serializer.context.get('is_idempotent', False)

        return Response(
            TransactionSerializer(transaction).data,
            status=status.HTTP_200_OK if is_idempotent else status.HTTP_201_CREATED
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def transfer(request):
    wallet = get_object_or_404(Wallet, user=request.user)

    serializer = TransferSerializer(
        data=request.data,
        context={'wallet': wallet}
    )

    if serializer.is_valid():
        withdrawal, deposit = serializer.save()
        is_idempotent = serializer.context.get('is_idempotent', False)

        return Response(
            {
                'transfer_out': TransactionSerializer(withdrawal).data,
                'transfer_in': TransactionSerializer(deposit).data
            },
            status=status.HTTP_200_OK if is_idempotent else status.HTTP_201_CREATED
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def wallet_detail(request):
    wallet = get_object_or_404(Wallet, user=request.user)
    serializer = WalletSerializer(wallet)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def transaction_list(request):
    wallet = get_object_or_404(Wallet, user=request.user)

    query_serializer = TransactionListSerializer(data=request.query_params)

    if not query_serializer.is_valid():
        return Response(
            query_serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    limit = query_serializer.validated_data['limit']
    offset = query_serializer.validated_data['offset']

    transactions = (
        wallet.transactions
        .order_by('-created_at')
        [offset:offset + limit]
    )

    total_count = wallet.transactions.count()

    serializer = TransactionSerializer(transactions, many=True)

    return Response({
        'count': total_count,
        'limit': limit,
        'offset': offset,
        'results': serializer.data
    })
