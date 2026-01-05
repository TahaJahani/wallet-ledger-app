from django.urls import path
from . import views

urlpatterns = [
    path('me/', views.wallet_detail, name='wallet-detail'),
    path('me/deposit', views.deposit, name='deposit'),
    path('me/withdraw', views.withdraw, name='withdraw'),
    path('me/transfer', views.transfer, name='transfer'),
    path('me/transactions', views.transaction_list, name='transaction-list'),
]
