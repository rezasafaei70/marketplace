from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'shipping-methods', views.ShippingMethodViewSet)
router.register(r'admin/shipping-methods', views.AdminShippingMethodViewSet, basename='admin-shipping-methods')
router.register(r'admin/shipping-zones', views.AdminShippingZoneViewSet, basename='admin-shipping-zones')
router.register(r'admin/shipping-rates', views.AdminShippingRateViewSet, basename='admin-shipping-rates')
router.register(r'admin/shipping-locations', views.AdminShippingLocationViewSet, basename='admin-shipping-locations')
router.register(r'admin/warehouses', views.WarehouseViewSet, basename='admin-warehouses')
router.register(r'admin/warehouse-products', views.WarehouseProductViewSet, basename='admin-warehouse-products')
router.register(r'admin/warehouse-transfers', views.WarehouseTransferViewSet, basename='admin-warehouse-transfers')

urlpatterns = [
    path('', include(router.urls)),
    path('calculate-shipping/', views.ShippingCalculatorView.as_view(), name='calculate-shipping'),
]