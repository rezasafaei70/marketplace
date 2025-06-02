from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('', views.ReviewViewSet)
router.register('replies', views.ReviewReplyViewSet)
router.register('reports', views.ReviewReportViewSet)

urlpatterns = [
    path('', include(router.urls)),
]