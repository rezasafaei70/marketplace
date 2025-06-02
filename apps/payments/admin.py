from django.contrib import admin
from .models import PaymentGateway, Payment, PaymentLog


class PaymentLogInline(admin.TabularInline):
    model = PaymentLog
    extra = 0
    readonly_fields = ('created_at',)


@admin.register(PaymentGateway)
class PaymentGatewayAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'code', 'description')
    readonly_fields = ('created_at', 'updated_at')
    list_editable = ('is_active',)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'amount', 'gateway', 'status', 'payment_date', 'created_at')
    list_filter = ('status', 'gateway', 'created_at', 'payment_date')
    search_fields = ('user__username', 'user__email', 'tracking_code', 'reference_id', 'transaction_id')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [PaymentLogInline]
    date_hierarchy = 'created_at'
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('user', 'amount', 'gateway', 'status')
        }),
        ('اطلاعات مرتبط', {
            'fields': ('order', 'installment', 'wallet_transaction')
        }),
        ('اطلاعات تراکنش', {
            'fields': ('tracking_code', 'reference_id', 'transaction_id', 'payment_date')
        }),
        ('اطلاعات اضافی', {
            'fields': ('description', 'meta_data', 'created_at', 'updated_at')
        }),
    )
    actions = ['mark_as_completed', 'mark_as_failed', 'mark_as_refunded']
    
    def mark_as_completed(self, request, queryset):
        updated = queryset.update(status='completed', payment_date=timezone.now())
        for payment in queryset:
            PaymentLog.objects.create(
                payment=payment,
                status='completed',
                description='پرداخت با موفقیت انجام شد',
                meta_data={'admin_user': request.user.username}
            )
        self.message_user(request, f'{updated} پرداخت به عنوان موفق علامت‌گذاری شد.')
    mark_as_completed.short_description = 'علامت‌گذاری به عنوان پرداخت موفق'
    
    def mark_as_failed(self, request, queryset):
        updated = queryset.update(status='failed')
        for payment in queryset:
            PaymentLog.objects.create(
                payment=payment,
                status='failed',
                description='پرداخت ناموفق بود',
                meta_data={'admin_user': request.user.username}
            )
        self.message_user(request, f'{updated} پرداخت به عنوان ناموفق علامت‌گذاری شد.')
    mark_as_failed.short_description = 'علامت‌گذاری به عنوان پرداخت ناموفق'
    
    def mark_as_refunded(self, request, queryset):
        updated = queryset.update(status='refunded')
        for payment in queryset:
            PaymentLog.objects.create(
                payment=payment,
                status='refunded',
                description='مبلغ پرداخت بازگردانده شد',
                meta_data={'admin_user': request.user.username}
            )
        self.message_user(request, f'{updated} پرداخت به عنوان بازگردانده شده علامت‌گذاری شد.')
    mark_as_refunded.short_description = 'علامت‌گذاری به عنوان بازگردانده شده'


@admin.register(PaymentLog)
class PaymentLogAdmin(admin.ModelAdmin):
    list_display = ('payment', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('payment__user__username', 'payment__user__email', 'description')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
