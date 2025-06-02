from django.contrib import admin
from .models import Notification, NotificationSetting, DeviceToken


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'type', 'title', 'is_read', 'priority', 'created_at']
    list_filter = ['type', 'is_read', 'priority', 'created_at']
    search_fields = ['user__phone', 'title', 'message']
    readonly_fields = ['created_at', 'read_at']
    actions = ['mark_as_read', 'mark_as_unread']
    
    def mark_as_read(self, request, queryset):
        from django.utils import timezone
        queryset.update(is_read=True, read_at=timezone.now())
        self.message_user(request, f'{queryset.count()} اعلان به عنوان خوانده شده علامت‌گذاری شد')
    mark_as_read.short_description = 'علامت‌گذاری به عنوان خوانده شده'
    
    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False, read_at=None)
        self.message_user(request, f'{queryset.count()} اعلان به عنوان خوانده نشده علامت‌گذاری شد')
    mark_as_unread.short_description = 'علامت‌گذاری به عنوان خوانده نشده'


@admin.register(NotificationSetting)
class NotificationSettingAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'created_at', 'updated_at']
    search_fields = ['user__phone', 'user__first_name', 'user__last_name']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('کاربر', {
            'fields': ('user',)
        }),
        ('اعلان‌های ایمیل', {
            'fields': (
                'email_order', 'email_payment', 'email_product',
                'email_comment', 'email_review', 'email_account',
                'email_system', 'email_promotion',
            )
        }),
        ('اعلان‌های پیامک', {
            'fields': (
                'sms_order', 'sms_payment', 'sms_product',
                'sms_comment', 'sms_review', 'sms_account',
                'sms_system', 'sms_promotion',
            )
        }),
        ('اعلان‌های پوش', {
            'fields': (
                'push_order', 'push_payment', 'push_product',
                'push_comment', 'push_review', 'push_account',
                'push_system', 'push_promotion',
            )
        }),
        ('زمان‌ها', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'platform', 'device_name', 'is_active', 'created_at', 'last_used_at']
    list_filter = ['platform', 'is_active', 'created_at']
    search_fields = ['user__phone', 'device_name', 'token']
    readonly_fields = ['created_at', 'last_used_at']
    actions = ['activate_tokens', 'deactivate_tokens']
    
    def activate_tokens(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f'{queryset.count()} توکن دستگاه فعال شد')
    activate_tokens.short_description = 'فعال‌سازی توکن‌های انتخاب شده'
    
    def deactivate_tokens(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f'{queryset.count()} توکن دستگاه غیرفعال شد')
    deactivate_tokens.short_description = 'غیرفعال‌سازی توکن‌های انتخاب شده'