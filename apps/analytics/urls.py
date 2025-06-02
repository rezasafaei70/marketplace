from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'admin/page-views', views.AdminPageViewViewSet)
router.register(r'admin/search-queries', views.AdminSearchQueryViewSet)
router.register(r'admin/user-activities', views.AdminUserActivityViewSet)
router.register(r'admin/sales-reports', views.AdminSalesReportViewSet)
router.register(r'admin/product-performances', views.AdminProductPerformanceViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('track/page-view/', views.TrackPageViewView.as_view(), name='track-page-view'),
    path('track/product-view/', views.TrackProductViewView.as_view(), name='track-product-view'),
    path('track/search-query/', views.TrackSearchQueryView.as_view(), name='track-search-query'),
    path('track/cart-event/', views.TrackCartEventView.as_view(), name='track-cart-event'),
    path('admin/dashboard/', views.AdminDashboardView.as_view(), name='admin-dashboard'),
]