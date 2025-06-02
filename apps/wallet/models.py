from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
import uuid


class Wallet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(_('موجودی'), max_digits=15, decimal_places=0, default=0)
    is_active = models.BooleanField(_('فعال'), default=True)
    created_at = models.DateTimeField(_('تاریخ ایجاد'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاریخ به‌روزرسانی'), auto_now=True)
    
    class Meta:
        verbose_name = _('کیف پول')
        verbose_name_plural = _('کیف‌های پول')
    
    def __str__(self):
        return f"کیف پول {self.user.get_full_name()}"


class TransactionType(models.TextChoices):
    DEPOSIT = 'deposit', _('واریز')
    WITHDRAWAL = 'withdrawal', _('برداشت')
    PAYMENT = 'payment', _('پرداخت')
    REFUND = 'refund', _('استرداد')
    TRANSFER = 'transfer', _('انتقال')
    REWARD = 'reward', _('پاداش')


class TransactionStatus(models.TextChoices):
    PENDING = 'pending', _('در انتظار')
    COMPLETED = 'completed', _('تکمیل شده')
    FAILED = 'failed', _('ناموفق')
    CANCELLED = 'cancelled', _('لغو شده')
    REFUNDED = 'refunded', _('مسترد شده')


class WalletTransaction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(_('مبلغ'), max_digits=15, decimal_places=0)
    transaction_type = models.CharField(_('نوع تراکنش'), max_length=20, choices=TransactionType.choices)
    status = models.CharField(_('وضعیت'), max_length=20, choices=TransactionStatus.choices, default=TransactionStatus.PENDING)
    description = models.TextField(_('توضیحات'), blank=True)
    reference_id = models.CharField(_('شناسه مرجع'), max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(_('تاریخ ایجاد'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاریخ به‌روزرسانی'), auto_now=True)
    
    class Meta:
        verbose_name = _('تراکنش کیف پول')
        verbose_name_plural = _('تراکنش‌های کیف پول')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_transaction_type_display()} {self.amount} - {self.wallet.user.get_full_name()}"


class WalletTransfer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sender = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='sent_transfers')
    receiver = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='received_transfers')
    amount = models.DecimalField(_('مبلغ'), max_digits=15, decimal_places=0)
    status = models.CharField(_('وضعیت'), max_length=20, choices=TransactionStatus.choices, default=TransactionStatus.COMPLETED)
    description = models.TextField(_('توضیحات'), blank=True)
    created_at = models.DateTimeField(_('تاریخ ایجاد'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('انتقال کیف پول')
        verbose_name_plural = _('انتقال‌های کیف پول')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"انتقال {self.amount} از {self.sender.user.get_full_name()} به {self.receiver.user.get_full_name()}"