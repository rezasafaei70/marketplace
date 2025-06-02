from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'products', views.ProductViewSet)
router.register(r'tags', views.ProductTagViewSet)
router.register(r'inventory-logs', views.ProductInventoryLogViewSet, basename='inventory-logs')

urlpatterns = [
    path('', include(router.urls)),
]