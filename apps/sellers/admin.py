from django.contrib import admin
from django.utils.html import format_html
from .models import Seller, SellerCategory, SellerReview, TieredCommission, SellerWithdrawal


class SellerCategoryInline(admin.TabularInline):
    model = SellerCategory
    extra = 1


class TieredCommissionInline(admin.TabularInline):
    model = TieredCommission
    extra = 1


@admin.register(Seller)
class SellerAdmin(admin.ModelAdmin):
    list_display = ('shop_name', 'user', 'status', 'rating', 'sales_count', 'total_revenue', 'balance', 'is_featured', 'created_at')
    list_filter = ('status', 'is_featured', 'created_at')
    search_fields = ('shop_name', 'user__username', 'user__email', 'description')
    readonly_fields = ('rating', 'review_count', 'sales_count', 'total_revenue', 'created_at', 'updated_at', 'logo_preview', 'banner_preview', 'identification_image_preview', 'business_license_preview')
    inlines = [SellerCategoryInline, TieredCommissionInline]
    date_hierarchy = 'created_at'
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('user', 'shop_name', 'slug', 'description', 'status', 'is_featured')
        }),
        ('تصاویر', {
            'fields': ('logo', 'logo_preview', 'banner', 'banner_preview')
        }),
        ('احراز هویت', {
            'fields': ('identification_type', 'identification_number', 'identification_image', 'identification_image_preview', 'business_license', 'business_license_preview')
        }),
        ('اطلاعات بانکی', {
            'fields': ('bank_account_number', 'bank_sheba', 'bank_card_number', 'bank_name')
        }),
        ('اطلاعات تماس', {
            'fields': ('address', 'postal_code', 'phone_number', 'email', 'website', 'instagram', 'telegram')
        }),
        ('آمار', {
            'fields': ('rating', 'review_count', 'sales_count', 'total_revenue')
        }),
        ('کمیسیون و مالی', {
            'fields': ('commission_type', 'commission_value', 'balance')
        }),
        ('زمان‌بندی', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    actions = ['approve_sellers', 'reject_sellers', 'suspend_sellers', 'mark_as_featured', 'unmark_as_featured']
    
    def logo_preview(self, obj):
        if obj.logo:
            return format_html('<img src="{}" width="100" height="100" />', obj.logo.url)
        return "-"
    logo_preview.short_description = 'پیش‌نمایش لوگو'
    
    def banner_preview(self, obj):
        if obj.banner:
            return format_html('<img src="{}" width="200" height="100" />', obj.banner.url)
        return "-"
    banner_preview.short_description = 'پیش‌نمایش بنر'
    
    def identification_image_preview(self, obj):
        if obj.identification_image:
            return format_html('<img src="{}" width="200" height="100" />', obj.identification_image.url)
        return "-"
    identification_image_preview.short_description = 'پیش‌نمایش مدرک شناسایی'
    
    def business_license_preview(self, obj):
        if obj.business_license:
            return format_html('<img src="{}" width="200" height="100" />', obj.business_license.url)
        return "-"
    business_license_preview.short_description = 'پیش‌نمایش مجوز کسب'
    
    def approve_sellers(self, request, queryset):
        updated = queryset.update(status='approved')
        self.message_user(request, f'{updated} فروشنده تایید شد.')
    approve_sellers.short_description = 'تایید فروشندگان انتخاب شده'
    
    def reject_sellers(self, request, queryset):
        updated = queryset.update(status='rejected')
        self.message_user(request, f'{updated} فروشنده رد شد.')
    reject_sellers.short_description = 'رد فروشندگان انتخاب شده'
    
    def suspend_sellers(self, request, queryset):
        updated = queryset.update(status='suspended')
        self.message_user(request, f'{updated} فروشنده تعلیق شد.')
    suspend_sellers.short_description = 'تعلیق فروشندگان انتخاب شده'
    
    def mark_as_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} فروشنده به عنوان ویژه علامت‌گذاری شد.')
    mark_as_featured.short_description = 'علامت‌گذاری به عنوان فروشنده ویژه'
    
    def unmark_as_featured(self, request, queryset):
        updated = queryset.update(is_featured=False)
        self.message_user(request, f'{updated} فروشنده از حالت ویژه خارج شد.')
    unmark_as_featured.short_description = 'حذف علامت فروشنده ویژه'


@admin.register(SellerCategory)
class SellerCategoryAdmin(admin.ModelAdmin):
    list_display = ('seller', 'category', 'is_approved', 'created_at')
    list_filter = ('is_approved', 'category', 'created_at')
    search_fields = ('seller__shop_name', 'category__name')
    readonly_fields = ('created_at',)
    list_editable = ('is_approved',)


@admin.register(SellerReview)
class SellerReviewAdmin(admin.ModelAdmin):
    list_display = ('seller', 'user', 'rating', 'is_approved', 'created_at')
    list_filter = ('rating', 'is_approved', 'created_at')
    search_fields = ('seller__shop_name', 'user__username', 'user__email', 'comment')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'
    actions = ['approve_reviews', 'unapprove_reviews']
    
    def approve_reviews(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f'{updated} نظر تایید شد.')
    approve_reviews.short_description = 'تایید نظرات انتخاب شده'
    
    def unapprove_reviews(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, f'{updated} نظر از حالت تایید خارج شد.')
    unapprove_reviews.short_description = 'لغو تایید نظرات انتخاب شده'


@admin.register(SellerWithdrawal)
class SellerWithdrawalAdmin(admin.ModelAdmin):
    list_display = ('seller', 'amount', 'status', 'created_at', 'updated_at')
    list_filter = ('status', 'created_at')
    search_fields = ('seller__shop_name', 'transaction_id', 'description')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'
    actions = ['approve_withdrawals', 'reject_withdrawals', 'mark_as_paid']
    
    def approve_withdrawals(self, request, queryset):
        updated = queryset.update(status='approved')
        self.message_user(request, f'{updated} درخواست برداشت تایید شد.')
    approve_withdrawals.short_description = 'تایید درخواست‌های برداشت انتخاب شده'
    
    def reject_withdrawals(self, request, queryset):
        updated = queryset.update(status='rejected')
        self.message_user(request, f'{updated} درخواست برداشت رد شد.')
    reject_withdrawals.short_description = 'رد درخواست‌های برداشت انتخاب شده'
    
    def mark_as_paid(self, request, queryset):
        updated = queryset.update(status='paid')
        self.message_user(request, f'{updated} درخواست برداشت به عنوان پرداخت شده علامت‌گذاری شد.')
    mark_as_paid.short_description = 'علامت‌گذاری به عنوان پرداخت شده'
