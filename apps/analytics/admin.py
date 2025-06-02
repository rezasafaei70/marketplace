from django.contrib import admin
from .models import PageView, ProductView, SearchQuery, CartEvent, UserActivity, SalesReport, ProductPerformance


@admin.register(PageView)
class PageViewAdmin(admin.ModelAdmin):
    list_display = ('user', 'url', 'created_at', 'ip_address', 'user_agent', 'referrer')
    list_filter = ('created_at', 'device_type', 'browser')
    search_fields = ('user__username', 'user__email', 'url', 'ip_address')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'ip_address', 'user_agent')


@admin.register(ProductView)
class ProductViewAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'created_at', 'ip_address')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'user__email', 'product__name', 'ip_address')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'ip_address')


@admin.register(SearchQuery)
class SearchQueryAdmin(admin.ModelAdmin):
    list_display = ('user', 'query', 'created_at', 'results_count')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'user__email', 'query')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)


@admin.register(CartEvent)
class CartEventAdmin(admin.ModelAdmin):
    list_display = ('user', 'cart', 'event_type', 'product', 'quantity', 'created_at')
    list_filter = ('created_at', 'event_type')
    search_fields = ('user__username', 'user__email', 'product__name')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ('user', 'activity_type', 'created_at', 'ip_address')
    list_filter = ('created_at', 'activity_type')
    search_fields = ('user__username', 'user__email', 'ip_address')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'ip_address', 'user_agent')


@admin.register(SalesReport)
class SalesReportAdmin(admin.ModelAdmin):
    list_display = ('date', 'total_sales', 'total_orders', 'average_order_value')
    list_filter = ('date',)
    date_hierarchy = 'date'
    readonly_fields = ('date',)


@admin.register(ProductPerformance)
class ProductPerformanceAdmin(admin.ModelAdmin):
    list_display = ('product', 'views', 'add_to_carts', 'purchases', 'conversion_rate', 'date')
    list_filter = ('date',)
    search_fields = ('product__name',)
    date_hierarchy = 'date'
    readonly_fields = ('date',)
