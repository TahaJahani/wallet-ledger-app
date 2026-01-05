from django.urls import path
from . import views

urlpatterns = [
    path('auth/login/', views.login_view, name='login'),
    path('auth/logout/', views.logout_view, name='logout'),
    path('auth/profile/', views.user_profile_view, name='user-profile'),
    path('auth/register/', views.create_user, name='create-user'),

    path('wallets/me/', views.wallet_detail, name='wallet-detail'),
    path('wallets/me/deposit', views.deposit, name='deposit'),
    path('wallets/me/withdraw', views.withdraw, name='withdraw'),
    path('wallets/me/transfer', views.transfer, name='transfer'),
    path('wallets/me/transactions', views.transaction_list, name='transaction-list'),
]
