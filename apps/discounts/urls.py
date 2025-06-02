from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'admin/discounts', views.DiscountViewSet)
router.register(r'admin/discount-usages', views.DiscountUsageViewSet)
router.register(r'rewards', views.LoyaltyRewardViewSet)
router.register(r'loyalty-points', views.LoyaltyPointViewSet, basename='loyalty-points')
router.register(r'reward-claims', views.LoyaltyRewardClaimViewSet, basename='reward-claims')
router.register(r'admin/rewards', views.AdminLoyaltyRewardViewSet, basename='admin-rewards')
router.register(r'admin/loyalty-points', views.AdminLoyaltyPointViewSet, basename='admin-loyalty-points')
router.register(r'admin/reward-claims', views.AdminLoyaltyRewardClaimViewSet, basename='admin-reward-claims')

urlpatterns = [
    path('', include(router.urls)),
    path('apply-discount/', views.ApplyDiscountView.as_view(), name='apply-discount'),
    path('admin/manual-points/', views.AdminManualPointsView.as_view(), name='admin-manual-points'),
]