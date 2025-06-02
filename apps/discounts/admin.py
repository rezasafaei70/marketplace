from django.contrib import admin
from django.utils import timezone
from .models import Discount, DiscountUsage, LoyaltyPoint, LoyaltyReward, LoyaltyRewardClaim


class DiscountUsageInline(admin.TabularInline):
    model = DiscountUsage
    extra = 0
    readonly_fields = ('used_at',)


@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_type', 'value', 'max_discount', 'min_purchase', 'start_date', 'end_date', 'usage_count', 'usage_limit', 'is_active', 'is_valid')
    list_filter = ('discount_type', 'is_active', 'is_first_purchase_only', 'is_one_time_per_user', 'is_for_specific_users', 'is_for_specific_products', 'start_date', 'end_date')
    search_fields = ('code', 'description')
    readonly_fields = ('usage_count', 'created_at', 'updated_at')
    filter_horizontal = ('specific_users', 'specific_products', 'specific_categories')
    inlines = [DiscountUsageInline]
    date_hierarchy = 'created_at'
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('code', 'discount_type', 'value', 'max_discount', 'min_purchase', 'description')
        }),
        ('زمان‌بندی و محدودیت‌ها', {
            'fields': ('start_date', 'end_date', 'usage_limit', 'usage_count', 'is_active')
        }),
        ('محدودیت‌های اضافی', {
            'fields': ('is_first_purchase_only', 'is_one_time_per_user')
        }),
        ('محدودیت‌های کاربری', {
            'fields': ('is_for_specific_users', 'specific_users')
        }),
        ('محدودیت‌های محصول', {
            'fields': ('is_for_specific_products', 'specific_products', 'specific_categories')
        }),
        ('زمان‌بندی', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    actions = ['activate_discounts', 'deactivate_discounts', 'extend_expiry']
    
    def is_valid(self, obj):
        return obj.is_valid
    is_valid.boolean = True
    is_valid.short_description = 'معتبر'
    
    def activate_discounts(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} کد تخفیف فعال شد.')
    activate_discounts.short_description = 'فعال کردن کدهای تخفیف انتخاب شده'
    
    def deactivate_discounts(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} کد تخفیف غیرفعال شد.')
    deactivate_discounts.short_description = 'غیرفعال کردن کدهای تخفیف انتخاب شده'
    
    def extend_expiry(self, request, queryset):
        for discount in queryset:
            if discount.end_date:
                discount.end_date = discount.end_date + timezone.timedelta(days=30)
            else:
                discount.end_date = timezone.now() + timezone.timedelta(days=30)
            discount.save()
        self.message_user(request, f'{queryset.count()} کد تخفیف به مدت 30 روز تمدید شد.')
    extend_expiry.short_description = 'تمدید 30 روزه کدهای تخفیف انتخاب شده'


@admin.register(DiscountUsage)
class DiscountUsageAdmin(admin.ModelAdmin):
    list_display = ('discount', 'user', 'order', 'amount', 'used_at')
    list_filter = ('used_at',)
    search_fields = ('discount__code', 'user__username', 'user__email', 'order__order_number')
    readonly_fields = ('used_at',)
    date_hierarchy = 'used_at'


@admin.register(LoyaltyPoint)
class LoyaltyPointAdmin(admin.ModelAdmin):
    list_display = ('user', 'points', 'reason', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'user__email', 'reason', 'reference_id')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'


@admin.register(LoyaltyReward)
class LoyaltyRewardAdmin(admin.ModelAdmin):
    list_display = ('name', 'points_required', 'reward_type', 'is_active', 'created_at')
    list_filter = ('reward_type', 'is_active', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    list_editable = ('is_active',)


@admin.register(LoyaltyRewardClaim)
class LoyaltyRewardClaimAdmin(admin.ModelAdmin):
    list_display = ('user', 'reward', 'status', 'claimed_at')
    list_filter = ('status', 'claimed_at')
    search_fields = ('user__username', 'user__email', 'reward__name', 'discount_code')
    readonly_fields = ('claimed_at',)
    date_hierarchy = 'claimed_at'
    actions = ['approve_claims', 'reject_claims', 'mark_as_delivered']
    
    def approve_claims(self, request, queryset):
        updated = queryset.update(status='approved')
        self.message_user(request, f'{updated} درخواست جایزه تایید شد.')
    approve_claims.short_description = 'تایید درخ'
