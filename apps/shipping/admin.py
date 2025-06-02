from django.contrib import admin
from .models import ShippingMethod, ShippingZone, ShippingRate, ShippingLocation, Warehouse, WarehouseProduct, WarehouseTransfer, WarehouseTransferItem


class ShippingRateInline(admin.TabularInline):
    model = ShippingRate
    extra = 1


@admin.register(ShippingMethod)
class ShippingMethodAdmin(admin.ModelAdmin):
    list_display = ('name', 'cost', 'estimated_delivery_days', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [ShippingRateInline]
    list_editable = ('is_active',)


class ShippingLocationInline(admin.TabularInline):
    model = ShippingLocation
    extra = 1


@admin.register(ShippingZone)
class ShippingZoneAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    inlines = [ShippingLocationInline, ShippingRateInline]
    list_editable = ('is_active',)


@admin.register(ShippingRate)
class ShippingRateAdmin(admin.ModelAdmin):
    list_display = ('shipping_method', 'zone', 'cost', 'estimated_delivery_days')
    list_filter = ('shipping_method', 'zone')
    search_fields = ('shipping_method__name', 'zone__name')
    list_editable = ('cost', 'estimated_delivery_days')


@admin.register(ShippingLocation)
class ShippingLocationAdmin(admin.ModelAdmin):
    list_display = ('province', 'city', 'zone')
    list_filter = ('zone', 'province')
    search_fields = ('province', 'city', 'zone__name')
    list_editable = ('zone',)


class WarehouseProductInline(admin.TabularInline):
    model = WarehouseProduct
    extra = 0


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'province', 'manager', 'is_active', 'created_at')
    list_filter = ('is_active', 'province', 'city')
    search_fields = ('name', 'address', 'postal_code', 'phone')
    readonly_fields = ('created_at',)
    inlines = [WarehouseProductInline]
    list_editable = ('is_active',)


@admin.register(WarehouseProduct)
class WarehouseProductAdmin(admin.ModelAdmin):
    list_display = ('warehouse', 'product', 'variant', 'stock', 'location', 'updated_at')
    list_filter = ('warehouse', 'updated_at')
    search_fields = ('warehouse__name', 'product__name', 'variant__name', 'location')
    readonly_fields = ('updated_at',)
    list_editable = ('stock', 'location')


class WarehouseTransferItemInline(admin.TabularInline):
    model = WarehouseTransferItem
    extra = 1


@admin.register(WarehouseTransfer)
class WarehouseTransferAdmin(admin.ModelAdmin):
    list_display = ('source_warehouse', 'destination_warehouse', 'status', 'created_by', 'created_at')
    list_filter = ('status', 'source_warehouse', 'destination_warehouse', 'created_at')
    search_fields = ('source_warehouse__name', 'destination_warehouse__name', 'notes')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [WarehouseTransferItemInline]
    date_hierarchy = 'created_at'
    actions = ['mark_as_in_transit', 'mark_as_completed', 'mark_as_cancelled']
    
    def mark_as_in_transit(self, request, queryset):
        updated = queryset.update(status='in_transit')
        self.message_user(request, f'{updated} انتقال به عنوان در حال انتقال علامت‌گذاری شد.')
    mark_as_in_transit.short_description = 'علامت‌گذاری به عنوان در حال انتقال'
    
    def mark_as_completed(self, request, queryset):
        updated = queryset.update(status='completed')
        self.message_user(request, f'{updated} انتقال به عنوان تکمیل شده علامت‌گذاری شد.')
    mark_as_completed.short_description = 'علامت‌گذاری به عنوان تکمیل شده'
    
    def mark_as_cancelled(self, request, queryset):
        updated = queryset.update(status='cancelled')
        self.message_user(request, f'{updated} انتقال به عنوان لغو شده علامت‌گذاری شد.')
    mark_as_cancelled.short_description = 'علامت‌گذاری به عنوان لغو شده'
