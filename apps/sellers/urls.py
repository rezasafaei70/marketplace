from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'sellers', views.SellerViewSet)
router.register(r'categories', views.SellerCategoryViewSet, basename='seller-categories')
router.register(r'commissions', views.TieredCommissionViewSet, basename='seller-commissions')
router.register(r'withdrawals', views.SellerWithdrawalViewSet, basename='seller-withdrawals')

urlpatterns = [
    path('', include(router.urls)),
]