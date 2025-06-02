from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'gateways', views.PaymentGatewayViewSet)
router.register(r'payments', views.PaymentViewSet, basename='payment')
router.register(r'admin/payments', views.AdminPaymentViewSet, basename='admin-payment')

urlpatterns = [
    path('', include(router.urls)),
    path('init/', views.PaymentInitView.as_view(), name='payment-init'),
    path('callback/', views.PaymentCallbackView.as_view(), name='payment-callback'),
]