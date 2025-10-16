from django.urls import path, include

urlpatterns = [
    path('auth/', include('apps.accounts.urls')),
    path('categories/', include('apps.categories.urls')),
    path('products/', include('apps.products.urls')),
    path('sellers/', include('apps.sellers.urls')),
    path('orders/', include('apps.orders.urls')),
    path('payments/', include('apps.payments.urls')),
    path('wallet/', include('apps.wallet.urls')),
    path('discounts/', include('apps.discounts.urls')),
    path('shipping/', include('apps.shipping.urls')),
    path('analytics/', include('apps.analytics.urls')),
    path('comments/', include('apps.comments.urls')),
    path('notifications/', include('apps.notifications.urls')),
    path('reviews/', include('apps.reviews.urls')),
    path('common', include('apps.common.urls')),
]