from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
import uuid


class PaymentGateway(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('نام درگاه'), max_length=100)
    code = models.CharField(_('کد درگاه'), max_length=50, unique=True)
    description = models.TextField(_('توضیحات'), blank=True)
    is_active = models.BooleanField(_('فعال'), default=True)
    config = models.JSONField(_('تنظیمات'), default=dict, blank=True)
    created_at = models.DateTimeField(_('تاریخ ایجاد'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاریخ به‌روزرسانی'), auto_now=True)
    
    class Meta:
        verbose_name = _('درگاه پرداخت')
        verbose_name_plural = _('درگاه‌های پرداخت')
    
    def __str__(self):
        return self.name


class PaymentStatus(models.TextChoices):
    PENDING = 'pending', _('در انتظار پرداخت')
    COMPLETED = 'completed', _('پرداخت موفق')
    FAILED = 'failed', _('پرداخت ناموفق')
    REFUNDED = 'refunded', _('برگشت داده شده')
    CANCELLED = 'cancelled', _('لغو شده')


class Payment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, 
                           related_name='payments')
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, 
                            related_name='payments', null=True, blank=True)
    installment = models.ForeignKey('orders.Installment', on_delete=models.CASCADE, 
                                  related_name='payments', null=True, blank=True)
    wallet_transaction = models.ForeignKey('wallet.WalletTransaction', on_delete=models.CASCADE, 
                                         related_name='payments', null=True, blank=True)
    gateway = models.ForeignKey(PaymentGateway, on_delete=models.PROTECT, related_name='payments')
    amount = models.DecimalField(_('مبلغ'), max_digits=15, decimal_places=0)
    status = models.CharField(_('وضعیت'), max_length=20, choices=PaymentStatus.choices, 
                            default=PaymentStatus.PENDING)
    tracking_code = models.CharField(_('کد پیگیری'), max_length=100, blank=True, null=True)
    reference_id = models.CharField(_('شناسه مرجع'), max_length=100, blank=True, null=True)
    transaction_id = models.CharField(_('شناسه تراکنش'), max_length=100, blank=True, null=True)
    payment_date = models.DateTimeField(_('تاریخ پرداخت'), blank=True, null=True)
    description = models.TextField(_('توضیحات'), blank=True)
    meta_data = models.JSONField(_('اطلاعات اضافی'), default=dict, blank=True)
    created_at = models.DateTimeField(_('تاریخ ایجاد'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاریخ به‌روزرسانی'), auto_now=True)
    
    class Meta:
        verbose_name = _('پرداخت')
        verbose_name_plural = _('پرداخت‌ها')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"پرداخت {self.id} - {self.amount} - {self.get_status_display()}"


class PaymentLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='logs')
    status = models.CharField(_('وضعیت'), max_length=20, choices=PaymentStatus.choices)
    description = models.TextField(_('توضیحات'), blank=True)
    meta_data = models.JSONField(_('اطلاعات اضافی'), default=dict, blank=True)
    created_at = models.DateTimeField(_('تاریخ ایجاد'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('لاگ پرداخت')
        verbose_name_plural = _('لاگ‌های پرداخت')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"لاگ پرداخت {self.payment.id} - {self.get_status_display()}"