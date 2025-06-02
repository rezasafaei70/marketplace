from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'wallet', views.WalletViewSet, basename='wallet')
router.register(r'admin/wallets', views.AdminWalletViewSet, basename='admin-wallet')
router.register(r'admin/transactions', views.AdminWalletTransactionViewSet, basename='admin-transaction')
router.register(r'admin/transfers', views.AdminWalletTransferViewSet, basename='admin-transfer')

urlpatterns = [
    path('', include(router.urls)),
]