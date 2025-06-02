from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
import uuid


class SellerStatus(models.TextChoices):
    PENDING = 'pending', _('در انتظار بررسی')
    APPROVED = 'approved', _('تایید شده')
    REJECTED = 'rejected', _('رد شده')
    SUSPENDED = 'suspended', _('تعلیق شده')


class IdentificationType(models.TextChoices):
    NATIONAL_ID = 'national_id', _('کارت ملی')
    BUSINESS_LICENSE = 'business_license', _('مجوز کسب و کار')
    BOTH = 'both', _('هر دو')


class CommissionType(models.TextChoices):
    FIXED = 'fixed', _('ثابت')
    PERCENTAGE = 'percentage', _('درصدی')
    TIERED = 'tiered', _('پلکانی')


class Seller(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='seller')
    shop_name = models.CharField(_('نام فروشگاه'), max_length=100)
    slug = models.SlugField(_('اسلاگ'), max_length=100, unique=True)
    description = models.TextField(_('توضیحات'), blank=True)
    logo = models.ImageField(_('لوگو'), upload_to='seller_logos/', blank=True, null=True)
    banner = models.ImageField(_('بنر'), upload_to='seller_banners/', blank=True, null=True)
    status = models.CharField(_('وضعیت'), max_length=20, choices=SellerStatus.choices, default=SellerStatus.PENDING)
    identification_type = models.CharField(_('نوع احراز هویت'), max_length=20, 
                                         choices=IdentificationType.choices, default=IdentificationType.NATIONAL_ID)
    identification_number = models.CharField(_('شماره شناسایی'), max_length=20, blank=True, null=True)
    identification_image = models.ImageField(_('تصویر مدرک'), upload_to='seller_identification/', blank=True, null=True)
    business_license = models.ImageField(_('تصویر مجوز کسب'), upload_to='seller_licenses/', blank=True, null=True)
    bank_account_number = models.CharField(_('شماره حساب بانکی'), max_length=26, blank=True, null=True)
    bank_sheba = models.CharField(_('شماره شبا'), max_length=26, blank=True, null=True)
    bank_card_number = models.CharField(_('شماره کارت بانکی'), max_length=16, blank=True, null=True)
    bank_name = models.CharField(_('نام بانک'), max_length=50, blank=True, null=True)
    address = models.TextField(_('آدرس'), blank=True, null=True)
    postal_code = models.CharField(_('کد پستی'), max_length=10, blank=True, null=True)
    phone_number = models.CharField(_('شماره تلفن ثابت'), max_length=11, blank=True, null=True)
    email = models.EmailField(_('ایمیل'), blank=True, null=True)
    website = models.URLField(_('وب‌سایت'), blank=True, null=True)
    instagram = models.CharField(_('اینستاگرام'), max_length=100, blank=True, null=True)
    telegram = models.CharField(_('تلگرام'), max_length=100, blank=True, null=True)
    rating = models.DecimalField(_('امتیاز'), max_digits=3, decimal_places=2, default=0)
    review_count = models.PositiveIntegerField(_('تعداد نظرات'), default=0)
    sales_count = models.PositiveIntegerField(_('تعداد فروش'), default=0)
    total_revenue = models.DecimalField(_('درآمد کل'), max_digits=15, decimal_places=0, default=0)
    commission_type = models.CharField(_('نوع کمیسیون'), max_length=20, choices=CommissionType.choices, default=CommissionType.PERCENTAGE)
    commission_value = models.DecimalField(_('مقدار کمیسیون'), max_digits=5, decimal_places=2, default=10)
    balance = models.DecimalField(_('موجودی حساب'), max_digits=15, decimal_places=0, default=0)
    is_featured = models.BooleanField(_('ویژه'), default=False)
    created_at = models.DateTimeField(_('تاریخ ایجاد'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاریخ به‌روزرسانی'), auto_now=True)
    
    class Meta:
        verbose_name = _('فروشنده')
        verbose_name_plural = _('فروشندگان')
    
    def __str__(self):
        return self.shop_name


class SellerCategory(models.Model):
    seller = models.ForeignKey(Seller, on_delete=models.CASCADE, related_name='categories')
    category = models.ForeignKey('categories.Category', on_delete=models.CASCADE, related_name='sellers')
    is_approved = models.BooleanField(_('تایید شده'), default=False)
    created_at = models.DateTimeField(_('تاریخ ایجاد'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('دسته‌بندی فروشنده')
        verbose_name_plural = _('دسته‌بندی‌های فروشنده')
        unique_together = ('seller', 'category')
    
    def __str__(self):
        return f"{self.seller.shop_name} - {self.category.name}"


class SellerReview(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    seller = models.ForeignKey(Seller, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='seller_reviews')
    rating = models.PositiveSmallIntegerField(_('امتیاز'), choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField(_('نظر'))
    is_approved = models.BooleanField(_('تایید شده'), default=False)
    created_at = models.DateTimeField(_('تاریخ ایجاد'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاریخ به‌روزرسانی'), auto_now=True)
    
    class Meta:
        verbose_name = _('نظر فروشنده')
        verbose_name_plural = _('نظرات فروشنده')
        unique_together = ('seller', 'user')
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.seller.shop_name} - {self.rating}"


class TieredCommission(models.Model):
    seller = models.ForeignKey(Seller, on_delete=models.CASCADE, related_name='tiered_commissions')
    min_sales = models.DecimalField(_('حداقل فروش'), max_digits=15, decimal_places=0)
    max_sales = models.DecimalField(_('حداکثر فروش'), max_digits=15, decimal_places=0, blank=True, null=True)
    commission_percentage = models.DecimalField(_('درصد کمیسیون'), max_digits=5, decimal_places=2)
    
    class Meta:
        verbose_name = _('کمیسیون پلکانی')
        verbose_name_plural = _('کمیسیون‌های پلکانی')
        ordering = ['min_sales']
    
    def __str__(self):
        max_sales_str = f" تا {self.max_sales}" if self.max_sales else " به بالا"
        return f"{self.seller.shop_name} - از {self.min_sales}{max_sales_str} - {self.commission_percentage}%"


class SellerWithdrawal(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    seller = models.ForeignKey(Seller, on_delete=models.CASCADE, related_name='withdrawals')
    amount = models.DecimalField(_('مبلغ'), max_digits=15, decimal_places=0)
    status_choices = [
        ('pending', _('در انتظار بررسی')),
        ('approved', _('تایید شده')),
        ('rejected', _('رد شده')),
        ('paid', _('پرداخت شده')),
    ]
    status = models.CharField(_('وضعیت'), max_length=20, choices=status_choices, default='pending')
    transaction_id = models.CharField(_('شناسه تراکنش'), max_length=100, blank=True, null=True)
    description = models.TextField(_('توضیحات'), blank=True)
    admin_note = models.TextField(_('یادداشت مدیر'), blank=True)
    created_at = models.DateTimeField(_('تاریخ ایجاد'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاریخ به‌روزرسانی'), auto_now=True)
    
    class Meta:
        verbose_name = _('برداشت فروشنده')
        verbose_name_plural = _('برداشت‌های فروشنده')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.seller.shop_name} - {self.amount} - {self.get_status_display()}"