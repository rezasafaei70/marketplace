from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('', views.CommentViewSet)
router.register('reports', views.CommentReportViewSet)

urlpatterns = [
    path('', include(router.urls)),
]