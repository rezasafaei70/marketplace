from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from apps.common.models import BaseModel

User = get_user_model()


class Notification(BaseModel):
    """Notification model for user notifications"""
    TYPE_CHOICES = [
        ('order', 'سفارش'),
        ('payment', 'پرداخت'),
        ('product', 'محصول'),
        ('comment', 'نظر'),
        ('review', 'بررسی'),
        ('account', 'حساب کاربری'),
        ('system', 'سیستمی'),
        ('promotion', 'تبلیغاتی'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'کم'),
        ('medium', 'متوسط'),
        ('high', 'زیاد'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications', verbose_name='کاربر')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name='نوع')
    title = models.CharField(max_length=255, verbose_name='عنوان')
    message = models.TextField(verbose_name='پیام')
    is_read = models.BooleanField(default=False, verbose_name='خوانده شده')
    read_at = models.DateTimeField(null=True, blank=True, verbose_name='زمان خواندن')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium', verbose_name='اولویت')
    
    # Link to related object (optional)
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='نوع محتوا')
    object_id = models.CharField(max_length=50, null=True, blank=True, verbose_name='شناسه محتوا')
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Additional data as JSON
    data = models.JSONField(default=dict, blank=True, verbose_name='داده‌های اضافی')
    
    # Action URL
    action_url = models.CharField(max_length=255, blank=True, verbose_name='لینک عمل')
    
    class Meta:
        verbose_name = 'اعلان'
        verbose_name_plural = 'اعلان‌ها'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'is_read']),
        ]
    
    def __str__(self):
        return f"{self.user.phone} - {self.title}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        from django.utils import timezone
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])


class NotificationSetting(models.Model):
    """User notification preferences"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='notification_settings', verbose_name='کاربر')
    
    # Email notifications
    email_order = models.BooleanField(default=True, verbose_name='اعلان سفارش از طریق ایمیل')
    email_payment = models.BooleanField(default=True, verbose_name='اعلان پرداخت از طریق ایمیل')
    email_product = models.BooleanField(default=True, verbose_name='اعلان محصول از طریق ایمیل')
    email_comment = models.BooleanField(default=True, verbose_name='اعلان نظر از طریق ایمیل')
    email_review = models.BooleanField(default=True, verbose_name='اعلان بررسی از طریق ایمیل')
    email_account = models.BooleanField(default=True, verbose_name='اعلان حساب کاربری از طریق ایمیل')
    email_system = models.BooleanField(default=True, verbose_name='اعلان سیستمی از طریق ایمیل')
    email_promotion = models.BooleanField(default=False, verbose_name='اعلان تبلیغاتی از طریق ایمیل')
    
    # SMS notifications
    sms_order = models.BooleanField(default=True, verbose_name='اعلان سفارش از طریق پیامک')
    sms_payment = models.BooleanField(default=True, verbose_name='اعلان پرداخت از طریق پیامک')
    sms_product = models.BooleanField(default=False, verbose_name='اعلان محصول از طریق پیامک')
    sms_comment = models.BooleanField(default=False, verbose_name='اعلان نظر از طریق پیامک')
    sms_review = models.BooleanField(default=False, verbose_name='اعلان بررسی از طریق پیامک')
    sms_account = models.BooleanField(default=True, verbose_name='اعلان حساب کاربری از طریق پیامک')
    sms_system = models.BooleanField(default=True, verbose_name='اعلان سیستمی از طریق پیامک')
    sms_promotion = models.BooleanField(default=False, verbose_name='اعلان تبلیغاتی از طریق پیامک')
    
    # Push notifications
    push_order = models.BooleanField(default=True, verbose_name='اعلان سفارش از طریق نوتیفیکیشن')
    push_payment = models.BooleanField(default=True, verbose_name='اعلان پرداخت از طریق نوتیفیکیشن')
    push_product = models.BooleanField(default=True, verbose_name='اعلان محصول از طریق نوتیفیکیشن')
    push_comment = models.BooleanField(default=True, verbose_name='اعلان نظر از طریق نوتیفیکیشن')
    push_review = models.BooleanField(default=True, verbose_name='اعلان بررسی از طریق نوتیفیکیشن')
    push_account = models.BooleanField(default=True, verbose_name='اعلان حساب کاربری از طریق نوتیفیکیشن')
    push_system = models.BooleanField(default=True, verbose_name='اعلان سیستمی از طریق نوتیفیکیشن')
    push_promotion = models.BooleanField(default=False, verbose_name='اعلان تبلیغاتی از طریق نوتیفیکیشن')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاریخ بروزرسانی')
    
    class Meta:
        verbose_name = 'تنظیمات اعلان'
        verbose_name_plural = 'تنظیمات اعلان‌ها'
    
    def __str__(self):
        return f"تنظیمات اعلان {self.user.phone}"
    
    @classmethod
    def get_or_create_settings(cls, user):
        """Get or create notification settings for a user"""
        settings, created = cls.objects.get_or_create(user=user)
        return settings


class DeviceToken(models.Model):
    """Device tokens for push notifications"""
    PLATFORM_CHOICES = [
        ('android', 'Android'),
        ('ios', 'iOS'),
        ('web', 'Web'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='device_tokens', verbose_name='کاربر')
    token = models.TextField(verbose_name='توکن دستگاه')
    platform = models.CharField(max_length=10, choices=PLATFORM_CHOICES, verbose_name='پلتفرم')
    device_name = models.CharField(max_length=255, blank=True, verbose_name='نام دستگاه')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    last_used_at = models.DateTimeField(auto_now=True, verbose_name='آخرین استفاده')
    
    class Meta:
        verbose_name = 'توکن دستگاه'
        verbose_name_plural = 'توکن‌های دستگاه'
        unique_together = ['user', 'token']
    
    def __str__(self):
        return f"{self.user.phone} - {self.get_platform_display()} - {self.device_name}"