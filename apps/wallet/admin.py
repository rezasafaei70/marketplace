from django.contrib import admin
from .models import Wallet, WalletTransaction, WalletTransfer


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    list_editable = ('is_active',)


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ('wallet', 'amount', 'transaction_type', 'status', 'created_at')
    list_filter = ('transaction_type', 'status', 'created_at')
    search_fields = ('wallet__user__username', 'wallet__user__email', 'reference_id', 'description')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'
    actions = ['mark_as_completed', 'mark_as_failed', 'mark_as_cancelled']
    
    def mark_as_completed(self, request, queryset):
        updated = queryset.update(status='completed')
        self.message_user(request, f'{updated} تراکنش به عنوان تکمیل شده علامت‌گذاری شد.')
    mark_as_completed.short_description = 'علامت‌گذاری به عنوان تکمیل شده'
    
    def mark_as_failed(self, request, queryset):
        updated = queryset.update(status='failed')
        self.message_user(request, f'{updated} تراکنش به عنوان ناموفق علامت‌گذاری شد.')
    mark_as_failed.short_description = 'علامت‌گذاری به عنوان ناموفق'
    
    def mark_as_cancelled(self, request, queryset):
        updated = queryset.update(status='cancelled')
        self.message_user(request, f'{updated} تراکنش به عنوان لغو شده علامت‌گذاری شد.')
    mark_as_cancelled.short_description = 'علامت‌گذاری به عنوان لغو شده'


@admin.register(WalletTransfer)
class WalletTransferAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'amount', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('sender__user__username', 'sender__user__email', 'receiver__user__username', 'receiver__user__email', 'description')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
