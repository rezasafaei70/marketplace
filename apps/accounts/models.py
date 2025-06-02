from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import uuid


class UserManager(BaseUserManager):
    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError(_('شماره موبایل الزامی است'))
        
        user = self.model(phone_number=phone_number, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        
        return self.create_user(phone_number, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone_number = models.CharField(_('شماره موبایل'), max_length=11, unique=True)
    email = models.EmailField(_('ایمیل'), blank=True, null=True)
    first_name = models.CharField(_('نام'), max_length=30, blank=True)
    last_name = models.CharField(_('نام خانوادگی'), max_length=30, blank=True)
    national_id = models.CharField(_('کد ملی'), max_length=10, blank=True, null=True)
    is_active = models.BooleanField(_('فعال'), default=True)
    is_staff = models.BooleanField(_('کارمند'), default=False)
    date_joined = models.DateTimeField(_('تاریخ عضویت'), default=timezone.now)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = []
    
    class Meta:
        verbose_name = _('کاربر')
        verbose_name_plural = _('کاربران')
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    def get_short_name(self):
        return self.first_name
    
    def __str__(self):
        return self.phone_number


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(_('تصویر پروفایل'), upload_to='avatars/', blank=True, null=True)
    birth_date = models.DateField(_('تاریخ تولد'), blank=True, null=True)
    loyalty_points = models.PositiveIntegerField(_('امتیازهای وفاداری'), default=0)
    
    class Meta:
        verbose_name = _('پروفایل کاربر')
        verbose_name_plural = _('پروفایل‌های کاربران')
    
    def __str__(self):
        return f"پروفایل {self.user.phone_number}"


class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    title = models.CharField(_('عنوان آدرس'), max_length=100)
    province = models.CharField(_('استان'), max_length=100)
    city = models.CharField(_('شهر'), max_length=100)
    postal_code = models.CharField(_('کد پستی'), max_length=10)
    address = models.TextField(_('آدرس کامل'))
    receiver_name = models.CharField(_('نام گیرنده'), max_length=100)
    receiver_phone = models.CharField(_('شماره تماس گیرنده'), max_length=11)
    is_default = models.BooleanField(_('آدرس پیش‌فرض'), default=False)
    
    class Meta:
        verbose_name = _('آدرس')
        verbose_name_plural = _('آدرس‌ها')
    
    def __str__(self):
        return f"{self.title} - {self.user.phone_number}"


class OTP(models.Model):
    phone_number = models.CharField(_('شماره موبایل'), max_length=11)
    code = models.CharField(_('کد یکبار مصرف'), max_length=6)
    created_at = models.DateTimeField(_('تاریخ ایجاد'), auto_now_add=True)
    expires_at = models.DateTimeField(_('تاریخ انقضا'))
    is_used = models.BooleanField(_('استفاده شده'), default=False)
    
    class Meta:
        verbose_name = _('کد یکبار مصرف')
        verbose_name_plural = _('کدهای یکبار مصرف')
    
    def __str__(self):
        return f"{self.phone_number} - {self.code}"
    
    def is_expired(self):
        return timezone.now() > self.expires_at


class UserSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    session_key = models.CharField(_('کلید نشست'), max_length=255)
    ip_address = models.GenericIPAddressField(_('آدرس IP'))
    user_agent = models.TextField(_('مرورگر کاربر'))
    device = models.CharField(_('دستگاه'), max_length=100)
    location = models.CharField(_('موقعیت'), max_length=255, blank=True, null=True)
    last_activity = models.DateTimeField(_('آخرین فعالیت'), auto_now=True)
    created_at = models.DateTimeField(_('تاریخ ایجاد'), auto_now_add=True)
    is_active = models.BooleanField(_('فعال'), default=True)
    
    class Meta:
        verbose_name = _('نشست کاربر')
        verbose_name_plural = _('نشست‌های کاربران')
    
    def __str__(self):
        return f"{self.user.phone_number} - {self.device}"


class LoginAttempt(models.Model):
    phone_number = models.CharField(_('شماره موبایل'), max_length=11)
    ip_address = models.GenericIPAddressField(_('آدرس IP'))
    user_agent = models.TextField(_('مرورگر کاربر'))
    timestamp = models.DateTimeField(_('زمان'), auto_now_add=True)
    success = models.BooleanField(_('موفق'), default=False)
    
    class Meta:
        verbose_name = _('تلاش ورود')
        verbose_name_plural = _('تلاش‌های ورود')
    
    def __str__(self):
        status = 'موفق' if self.success else 'ناموفق'
        return f"{self.phone_number} - {status} - {self.timestamp}"