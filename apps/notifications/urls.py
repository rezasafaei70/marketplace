from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('', views.NotificationViewSet, basename='notification')
router.register('settings', views.NotificationSettingViewSet, basename='notification-settings')
router.register('devices', views.DeviceTokenViewSet, basename='device-token')

urlpatterns = [
    path('', include(router.urls)),
]