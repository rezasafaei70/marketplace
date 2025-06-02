from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
import uuid

User = get_user_model()


class TimeStampedModel(models.Model):
    """Abstract base class with created_at and updated_at fields"""
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاریخ بروزرسانی')

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    """Abstract base class with soft delete functionality"""
    is_deleted = models.BooleanField(default=False, verbose_name='حذف شده')
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name='تاریخ حذف')

    class Meta:
        abstract = True

    def soft_delete(self):
        from django.utils import timezone
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.save()


class BaseModel(TimeStampedModel, SoftDeleteModel):
    """Base model with timestamp and soft delete functionality"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class ActivityLog(TimeStampedModel):
    """Model to track user activities"""
    ACTION_CHOICES = [
        ('create', 'ایجاد'),
        ('update', 'بروزرسانی'),
        ('delete', 'حذف'),
        ('view', 'مشاهده'),
        ('login', 'ورود'),
        ('logout', 'خروج'),
        ('purchase', 'خرید'),
        ('payment', 'پرداخت'),
        ('review', 'نظر'),
        ('like', 'پسند'),
        ('follow', 'دنبال کردن'),
        ('search', 'جستجو'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='کاربر')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name='عمل')
    description = models.TextField(blank=True, verbose_name='توضیحات')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='آدرس IP')
    user_agent = models.TextField(blank=True, verbose_name='User Agent')
    
    # Generic foreign key for linking to any model
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        verbose_name = 'لاگ فعالیت'
        verbose_name_plural = 'لاگ‌های فعالیت'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.phone} - {self.get_action_display()} - {self.created_at}"


class Setting(models.Model):
    """System settings model"""
    SETTING_TYPES = [
        ('string', 'متن'),
        ('integer', 'عدد صحیح'),
        ('float', 'عدد اعشاری'),
        ('boolean', 'بولین'),
        ('json', 'JSON'),
        ('text', 'متن طولانی'),
    ]

    key = models.CharField(max_length=100, unique=True, verbose_name='کلید')
    value = models.TextField(verbose_name='مقدار')
    value_type = models.CharField(max_length=20, choices=SETTING_TYPES, default='string', verbose_name='نوع مقدار')
    description = models.TextField(blank=True, verbose_name='توضیحات')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاریخ بروزرسانی')

    class Meta:
        verbose_name = 'تنظیمات'
        verbose_name_plural = 'تنظیمات'

    def __str__(self):
        return self.key

    def get_value(self):
        """Return the value in its proper type"""
        if self.value_type == 'integer':
            return int(self.value)
        elif self.value_type == 'float':
            return float(self.value)
        elif self.value_type == 'boolean':
            return self.value.lower() in ['true', '1', 'yes']
        elif self.value_type == 'json':
            import json
            return json.loads(self.value)
        return self.value


class ContactMessage(TimeStampedModel):
    """Contact form messages"""
    name = models.CharField(max_length=100, verbose_name='نام')
    email = models.EmailField(verbose_name='ایمیل')
    phone = models.CharField(max_length=15, blank=True, verbose_name='تلفن')
    subject = models.CharField(max_length=200, verbose_name='موضوع')
    message = models.TextField(verbose_name='پیام')
    is_read = models.BooleanField(default=False, verbose_name='خوانده شده')
    replied = models.BooleanField(default=False, verbose_name='پاسخ داده شده')
    reply_message = models.TextField(blank=True, verbose_name='پیام پاسخ')
    replied_at = models.DateTimeField(null=True, blank=True, verbose_name='تاریخ پاسخ')

    class Meta:
        verbose_name = 'پیام تماس'
        verbose_name_plural = 'پیام‌های تماس'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.subject}"


class FAQ(models.Model):
    """Frequently Asked Questions"""
    question = models.CharField(max_length=500, verbose_name='سوال')
    answer = models.TextField(verbose_name='پاسخ')
    category = models.CharField(max_length=100, blank=True, verbose_name='دسته‌بندی')
    order = models.PositiveIntegerField(default=0, verbose_name='ترتیب')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاریخ بروزرسانی')

    class Meta:
        verbose_name = 'سوال متداول'
        verbose_name_plural = 'سوالات متداول'
        ordering = ['order', '-created_at']

    def __str__(self):
        return self.question


class Province(models.Model):
    """Iranian provinces"""
    name = models.CharField(max_length=100, verbose_name='نام استان')
    code = models.CharField(max_length=10, unique=True, verbose_name='کد استان')
    is_active = models.BooleanField(default=True, verbose_name='فعال')

    class Meta:
        verbose_name = 'استان'
        verbose_name_plural = 'استان‌ها'
        ordering = ['name']

    def __str__(self):
        return self.name


class City(models.Model):
    """Iranian cities"""
    name = models.CharField(max_length=100, verbose_name='نام شهر')
    province = models.ForeignKey(Province, on_delete=models.CASCADE, related_name='cities', verbose_name='استان')
    code = models.CharField(max_length=10, verbose_name='کد شهر')
    is_active = models.BooleanField(default=True, verbose_name='فعال')

    class Meta:
        verbose_name = 'شهر'
        verbose_name_plural = 'شهرها'
        ordering = ['name']
        unique_together = ['province', 'code']

    def __str__(self):
        return f"{self.name} - {self.province.name}"


class Banner(TimeStampedModel):
    """Website banners"""
    POSITION_CHOICES = [
        ('header', 'هدر'),
        ('sidebar', 'نوار کناری'),
        ('footer', 'فوتر'),
        ('homepage', 'صفحه اصلی'),
        ('category', 'صفحه دسته‌بندی'),
        ('product', 'صفحه محصول'),
    ]

    title = models.CharField(max_length=200, verbose_name='عنوان')
    image = models.ImageField(upload_to='banners/', verbose_name='تصویر')
    link = models.URLField(blank=True, verbose_name='لینک')
    position = models.CharField(max_length=20, choices=POSITION_CHOICES, verbose_name='موقعیت')
    order = models.PositiveIntegerField(default=0, verbose_name='ترتیب')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    start_date = models.DateTimeField(null=True, blank=True, verbose_name='تاریخ شروع')
    end_date = models.DateTimeField(null=True, blank=True, verbose_name='تاریخ پایان')

    class Meta:
        verbose_name = 'بنر'
        verbose_name_plural = 'بنرها'
        ordering = ['position', 'order']

    def __str__(self):
        return self.title

    @property
    def is_valid(self):
        from django.utils import timezone
        now = timezone.now()
        if self.start_date and now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False
        return self.is_active


class Newsletter(TimeStampedModel):
    """Newsletter subscriptions"""
    email = models.EmailField(unique=True, verbose_name='ایمیل')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    confirmed = models.BooleanField(default=False, verbose_name='تایید شده')
    confirmation_token = models.CharField(max_length=100, blank=True, verbose_name='توکن تایید')

    class Meta:
        verbose_name = 'خبرنامه'
        verbose_name_plural = 'خبرنامه‌ها'
        ordering = ['-created_at']

    def __str__(self):
        return self.email