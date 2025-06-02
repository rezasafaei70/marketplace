from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'carts', views.CartViewSet, basename='cart')
router.register(r'orders', views.OrderViewSet, basename='order')
router.register(r'returns', views.OrderReturnViewSet, basename='return')
router.register(r'admin/orders', views.AdminOrderViewSet, basename='admin-order')
router.register(r'admin/returns', views.AdminOrderReturnViewSet, basename='admin-return')

urlpatterns = [
    path('', include(router.urls)),
    path('checkout/', views.CheckoutView.as_view(), name='checkout'),
]