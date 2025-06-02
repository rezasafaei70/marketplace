from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
import uuid


class PageView(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                           related_name='page_views', null=True, blank=True)
    session_id = models.CharField(_('شناسه نشست'), max_length=100)
    url = models.URLField(_('آدرس صفحه'))
    page_title = models.CharField(_('عنوان صفحه'), max_length=255, blank=True)
    referrer = models.URLField(_('ارجاع‌دهنده'), blank=True, null=True)
    user_agent = models.TextField(_('مرورگر کاربر'), blank=True)
    ip_address = models.GenericIPAddressField(_('آدرس IP'))
    device_type = models.CharField(_('نوع دستگاه'), max_length=50, blank=True)
    os = models.CharField(_('سیستم عامل'), max_length=50, blank=True)
    browser = models.CharField(_('مرورگر'), max_length=50, blank=True)
    created_at = models.DateTimeField(_('تاریخ بازدید'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('بازدید صفحه')
        verbose_name_plural = _('بازدیدهای صفحه')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.url} - {self.created_at}"


class ProductView(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='views')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                           related_name='product_views', null=True, blank=True)
    session_id = models.CharField(_('شناسه نشست'), max_length=100)
    ip_address = models.GenericIPAddressField(_('آدرس IP'))
    referrer = models.URLField(_('ارجاع‌دهنده'), blank=True, null=True)
    created_at = models.DateTimeField(_('تاریخ بازدید'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('بازدید محصول')
        verbose_name_plural = _('بازدیدهای محصول')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.product.name} - {self.created_at}"


class SearchQuery(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    query = models.CharField(_('عبارت جستجو'), max_length=255)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                           related_name='search_queries', null=True, blank=True)
    session_id = models.CharField(_('شناسه نشست'), max_length=100)
    results_count = models.IntegerField(_('تعداد نتایج'), default=0)
    category = models.ForeignKey('categories.Category', on_delete=models.SET_NULL,
                               related_name='search_queries', null=True, blank=True)
    created_at = models.DateTimeField(_('تاریخ جستجو'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('جستجو')
        verbose_name_plural = _('جستجوها')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.query} - {self.created_at}"


class CartEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart = models.ForeignKey('orders.Cart', on_delete=models.CASCADE, related_name='events')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                           related_name='cart_events', null=True, blank=True)
    session_id = models.CharField(_('شناسه نشست'), max_length=100)
    event_type_choices = [
        ('create', _('ایجاد سبد')),
        ('add', _('افزودن محصول')),
        ('remove', _('حذف محصول')),
        ('update', _('به‌روزرسانی تعداد')),
        ('clear', _('خالی کردن سبد')),
        ('checkout', _('تکمیل خرید')),
        ('abandon', _('رها کردن سبد')),
    ]
    event_type = models.CharField(_('نوع رویداد'), max_length=20, choices=event_type_choices)
    product = models.ForeignKey('products.Product', on_delete=models.SET_NULL,
                              related_name='cart_events', null=True, blank=True)
    quantity = models.PositiveIntegerField(_('تعداد'), null=True, blank=True)
    created_at = models.DateTimeField(_('تاریخ رویداد'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('رویداد سبد خرید')
        verbose_name_plural = _('رویدادهای سبد خرید')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_event_type_display()} - {self.created_at}"


class UserActivity(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='activities')
    activity_type_choices = [
        ('login', _('ورود')),
        ('logout', _('خروج')),
        ('register', _('ثبت نام')),
        ('password_change', _('تغییر رمز عبور')),
        ('profile_update', _('به‌روزرسانی پروفایل')),
        ('order_create', _('ایجاد سفارش')),
        ('order_payment', _('پرداخت سفارش')),
        ('review_submit', _('ثبت نظر')),
        ('wishlist_add', _('افزودن به علاقه‌مندی‌ها')),
        ('wishlist_remove', _('حذف از علاقه‌مندی‌ها')),
    ]
    activity_type = models.CharField(_('نوع فعالیت'), max_length=20, choices=activity_type_choices)
    ip_address = models.GenericIPAddressField(_('آدرس IP'))
    user_agent = models.TextField(_('مرورگر کاربر'), blank=True)
    object_id = models.CharField(_('شناسه شیء'), max_length=100, blank=True, null=True)
    description = models.TextField(_('توضیحات'), blank=True)
    created_at = models.DateTimeField(_('تاریخ فعالیت'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('فعالیت کاربر')
        verbose_name_plural = _('فعالیت‌های کاربر')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_activity_type_display()} - {self.created_at}"


class SalesReport(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date = models.DateField(_('تاریخ'))
    total_sales = models.DecimalField(_('مجموع فروش'), max_digits=15, decimal_places=0, default=0)
    total_orders = models.PositiveIntegerField(_('تعداد سفارش‌ها'), default=0)
    average_order_value = models.DecimalField(_('میانگین ارزش سفارش'), max_digits=15, decimal_places=0, default=0)
    total_discount = models.DecimalField(_('مجموع تخفیف'), max_digits=15, decimal_places=0, default=0)
    total_shipping = models.DecimalField(_('مجموع هزینه ارسال'), max_digits=15, decimal_places=0, default=0)
    total_tax = models.DecimalField(_('مجموع مالیات'), max_digits=15, decimal_places=0, default=0)
    total_refund = models.DecimalField(_('مجموع برگشتی'), max_digits=15, decimal_places=0, default=0)
    net_sales = models.DecimalField(_('فروش خالص'), max_digits=15, decimal_places=0, default=0)
    
    class Meta:
        verbose_name = _('گزارش فروش')
        verbose_name_plural = _('گزارش‌های فروش')
        ordering = ['-date']
        unique_together = ('date',)
    
    def __str__(self):
        return f"گزارش فروش {self.date}"


class ProductPerformance(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='performances')
    date = models.DateField(_('تاریخ'))
    views = models.PositiveIntegerField(_('بازدیدها'), default=0)
    add_to_carts = models.PositiveIntegerField(_('افزودن به سبد'), default=0)
    purchases = models.PositiveIntegerField(_('خریدها'), default=0)
    revenue = models.DecimalField(_('درآمد'), max_digits=15, decimal_places=0, default=0)
    conversion_rate = models.FloatField(_('نرخ تبدیل'), default=0)
    
    class Meta:
        verbose_name = _('عملکرد محصول')
        verbose_name_plural = _('عملکرد محصولات')
        ordering = ['-date']
        unique_together = ('product', 'date')
    
    def __str__(self):
        return f"عملکرد {self.product.name} - {self.date}"