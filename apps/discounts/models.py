from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid


class DiscountType(models.TextChoices):
    FIXED = 'fixed', _('مبلغ ثابت')
    PERCENTAGE = 'percentage', _('درصدی')


class Discount(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(_('کد تخفیف'), max_length=50, unique=True)
    discount_type = models.CharField(_('نوع تخفیف'), max_length=20, choices=DiscountType.choices)
    value = models.DecimalField(_('مقدار تخفیف'), max_digits=15, decimal_places=0)
    max_discount = models.DecimalField(_('حداکثر تخفیف'), max_digits=15, decimal_places=0, blank=True, null=True)
    min_purchase = models.DecimalField(_('حداقل خرید'), max_digits=15, decimal_places=0, default=0)
    start_date = models.DateTimeField(_('تاریخ شروع'), default=timezone.now)
    end_date = models.DateTimeField(_('تاریخ پایان'), blank=True, null=True)
    usage_limit = models.PositiveIntegerField(_('محدودیت استفاده'), blank=True, null=True)
    usage_count = models.PositiveIntegerField(_('تعداد استفاده'), default=0)
    is_active = models.BooleanField(_('فعال'), default=True)
    description = models.TextField(_('توضیحات'), blank=True)
    created_at = models.DateTimeField(_('تاریخ ایجاد'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاریخ به‌روزرسانی'), auto_now=True)
    
    # محدودیت‌های اضافی
    is_first_purchase_only = models.BooleanField(_('فقط اولین خرید'), default=False)
    is_one_time_per_user = models.BooleanField(_('یک بار برای هر کاربر'), default=False)
    
    # محدودیت‌های کاربری
    specific_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='specific_discounts',
        blank=True,
        verbose_name=_('کاربران خاص')
    )
    is_for_specific_users = models.BooleanField(_('فقط برای کاربران خاص'), default=False)
    
    # محدودیت‌های محصول و دسته‌بندی
    specific_products = models.ManyToManyField(
        'products.Product',
        related_name='specific_discounts',
        blank=True,
        verbose_name=_('محصولات خاص')
    )
    specific_categories = models.ManyToManyField(
        'categories.Category',
        related_name='specific_discounts',
        blank=True,
        verbose_name=_('دسته‌بندی‌های خاص')
    )
    is_for_specific_products = models.BooleanField(_('فقط برای محصولات خاص'), default=False)
    
    class Meta:
        verbose_name = _('کد تخفیف')
        verbose_name_plural = _('کدهای تخفیف')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.code} - {self.get_discount_type_display()} {self.value}"
    
    @property
    def is_expired(self):
        if not self.end_date:
            return False
        return timezone.now() > self.end_date
    
    @property
    def is_started(self):
        return timezone.now() >= self.start_date
    
    @property
    def is_exhausted(self):
        if not self.usage_limit:
            return False
        return self.usage_count >= self.usage_limit
    
    @property
    def is_valid(self):
        return (
            self.is_active and
            self.is_started and
            not self.is_expired and
            not self.is_exhausted
        )


class DiscountUsage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    discount = models.ForeignKey(Discount, on_delete=models.CASCADE, related_name='usages')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='discount_usages')
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, related_name='discount_usages')
    used_at = models.DateTimeField(_('تاریخ استفاده'), auto_now_add=True)
    amount = models.DecimalField(_('مقدار تخفیف'), max_digits=15, decimal_places=0)
    
    class Meta:
        verbose_name = _('استفاده از تخفیف')
        verbose_name_plural = _('استفاده‌های تخفیف')
        ordering = ['-used_at']
        unique_together = ('discount', 'order')
    
    def __str__(self):
        return f"{self.discount.code} - {self.user.get_full_name()} - {self.amount}"


class LoyaltyPoint(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='loyalty_points')
    points = models.PositiveIntegerField(_('امتیاز'))
    reason = models.CharField(_('دلیل'), max_length=100)
    reference_id = models.CharField(_('شناسه مرجع'), max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(_('تاریخ ایجاد'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('امتیاز وفاداری')
        verbose_name_plural = _('امتیازهای وفاداری')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.points} امتیاز - {self.reason}"


class LoyaltyReward(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('نام جایزه'), max_length=100)
    description = models.TextField(_('توضیحات'))
    points_required = models.PositiveIntegerField(_('امتیاز مورد نیاز'))
    reward_type_choices = [
        ('discount', _('کد تخفیف')),
        ('product', _('محصول رایگان')),
        ('shipping', _('ارسال رایگان')),
    ]
    reward_type = models.CharField(_('نوع جایزه'), max_length=20, choices=reward_type_choices)
    discount_value = models.DecimalField(_('مقدار تخفیف'), max_digits=15, decimal_places=0, blank=True, null=True)
    discount_type = models.CharField(_('نوع تخفیف'), max_length=20, choices=DiscountType.choices, blank=True, null=True)
    product = models.ForeignKey('products.Product', on_delete=models.SET_NULL, blank=True, null=True, related_name='loyalty_rewards')
    is_active = models.BooleanField(_('فعال'), default=True)
    created_at = models.DateTimeField(_('تاریخ ایجاد'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاریخ به‌روزرسانی'), auto_now=True)
    
    class Meta:
        verbose_name = _('جایزه وفاداری')
        verbose_name_plural = _('جوایز وفاداری')
        ordering = ['points_required']
    
    def __str__(self):
        return f"{self.name} - {self.points_required} امتیاز"


class LoyaltyRewardClaim(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='loyalty_reward_claims')
    reward = models.ForeignKey(LoyaltyReward, on_delete=models.CASCADE, related_name='claims')
    claimed_at = models.DateTimeField(_('تاریخ درخواست'), auto_now_add=True)
    status_choices = [
        ('pending', _('در انتظار')),
        ('approved', _('تایید شده')),
        ('rejected', _('رد شده')),
        ('delivered', _('تحویل داده شده')),
    ]
    status = models.CharField(_('وضعیت'), max_length=20, choices=status_choices, default='pending')
    discount_code = models.CharField(_('کد تخفیف'), max_length=50, blank=True, null=True)
    order = models.ForeignKey('orders.Order', on_delete=models.SET_NULL, blank=True, null=True, related_name='loyalty_reward_claims')
    notes = models.TextField(_('یادداشت‌ها'), blank=True)
    
    class Meta:
        verbose_name = _('درخواست جایزه وفاداری')
        verbose_name_plural = _('درخواست‌های جایزه وفاداری')
        ordering = ['-claimed_at']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.reward.name} - {self.get_status_display()}"