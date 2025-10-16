from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import User, UserProfile, Address, OTP, UserSession, LoginAttempt

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('phone_number', 'get_full_name', 'email', 'is_active', 'is_staff', 'date_joined')
    list_filter = ('is_active', 'is_staff', 'date_joined')
    search_fields = ('phone_number', 'first_name', 'last_name', 'email')
    ordering = ('-date_joined',)
    
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('phone_number', 'email', 'password')
        }),
        ('اطلاعات شخصی', {
            'fields': ('first_name', 'last_name', 'national_id'),
            'classes': ('collapse',)
        }),
        ('دسترسی‌ها', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('تاریخ‌ها', {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = (
        ('ایجاد کاربر جدید', {
            'classes': ('wide',),
            'fields': ('phone_number', 'password1', 'password2'),
        }),
    )
    
    def get_full_name(self, obj):
        return obj.get_full_name() or 'نام وارد نشده'
    get_full_name.short_description = 'نام کامل'

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'پروفایل'
    
    def avatar_preview(self, obj):
        if obj.avatar:
            return format_html('<img src="{}" width="50" height="50" style="border-radius: 50%;" />', obj.avatar.url)
        return "بدون تصویر"
    avatar_preview.short_description = 'پیش‌نمایش'

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'avatar_preview', 'birth_date', 'loyalty_points')
    list_filter = ('birth_date',)
    search_fields = ('user__phone_number', 'user__first_name', 'user__last_name')
    
    def avatar_preview(self, obj):
        if obj.avatar:
            return format_html('<img src="{}" width="40" height="40" style="border-radius: 50%;" />', obj.avatar.url)
        return "❌"
    avatar_preview.short_description = 'تصویر'

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'city', 'province', 'is_default', 'receiver_name')
    list_filter = ('province', 'city', 'is_default')
    search_fields = ('user__phone_number', 'title', 'city', 'receiver_name')
    list_editable = ('is_default',)

@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'code', 'created_at', 'expires_at', 'is_used', 'status')
    list_filter = ('is_used', 'created_at')
    search_fields = ('phone_number', 'code')
    readonly_fields = ('created_at', 'expires_at')
    
    def status(self, obj):
        if obj.is_used:
            return format_html('<span style="color: green;">✅ استفاده شده</span>')
        elif obj.is_expired():
            return format_html('<span style="color: red;">❌ منقضی شده</span>')
        else:
            return format_html('<span style="color: orange;">⏳ در انتظار</span>')
    status.short_description = 'وضعیت'

@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'device', 'ip_address', 'location', 'last_activity', 'is_active', 'status_badge')
    list_filter = ('is_active', 'device', 'last_activity')
    search_fields = ('user__phone_number', 'ip_address', 'device')
    readonly_fields = ('created_at', 'last_activity')
    
    def status_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="background: green; color: white; padding: 2px 8px; border-radius: 10px;">🟢 فعال</span>')
        else:
            return format_html('<span style="background: red; color: white; padding: 2px 8px; border-radius: 10px;">🔴 غیرفعال</span>')
    status_badge.short_description = 'وضعیت'

@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'ip_address', 'timestamp', 'success', 'status_icon')
    list_filter = ('success', 'timestamp')
    search_fields = ('phone_number', 'ip_address')
    readonly_fields = ('timestamp',)
    
    def status_icon(self, obj):
        if obj.success:
            return format_html('<span style="color: green; font-size: 16px;">✅</span>')
        else:
            return format_html('<span style="color: red; font-size: 16px;">❌</span>')
    status_icon.short_description = 'نتیجه'