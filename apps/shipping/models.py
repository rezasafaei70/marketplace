from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
import uuid


class ShippingMethod(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('نام روش ارسال'), max_length=100)
    description = models.TextField(_('توضیحات'), blank=True)
    cost = models.DecimalField(_('هزینه ارسال'), max_digits=15, decimal_places=0)
    is_active = models.BooleanField(_('فعال'), default=True)
    estimated_delivery_days = models.PositiveIntegerField(_('تخمین روزهای تحویل'), default=3)
    icon = models.ImageField(_('آیکون'), upload_to='shipping_icons/', blank=True, null=True)
    created_at = models.DateTimeField(_('تاریخ ایجاد'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاریخ به‌روزرسانی'), auto_now=True)
    
    class Meta:
        verbose_name = _('روش ارسال')
        verbose_name_plural = _('روش‌های ارسال')
        ordering = ['cost']
    
    def __str__(self):
        return f"{self.name} - {self.cost} تومان"


class ShippingZone(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('نام منطقه'), max_length=100)
    description = models.TextField(_('توضیحات'), blank=True)
    is_active = models.BooleanField(_('فعال'), default=True)
    
    class Meta:
        verbose_name = _('منطقه ارسال')
        verbose_name_plural = _('مناطق ارسال')
    
    def __str__(self):
        return self.name


class ShippingRate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shipping_method = models.ForeignKey(ShippingMethod, on_delete=models.CASCADE, related_name='rates')
    zone = models.ForeignKey(ShippingZone, on_delete=models.CASCADE, related_name='rates')
    cost = models.DecimalField(_('هزینه ارسال'), max_digits=15, decimal_places=0)
    estimated_delivery_days = models.PositiveIntegerField(_('تخمین روزهای تحویل'), default=3)
    
    class Meta:
        verbose_name = _('نرخ ارسال')
        verbose_name_plural = _('نرخ‌های ارسال')
        unique_together = ('shipping_method', 'zone')
    
    def __str__(self):
        return f"{self.shipping_method.name} - {self.zone.name} - {self.cost} تومان"


class ShippingLocation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    zone = models.ForeignKey(ShippingZone, on_delete=models.CASCADE, related_name='locations')
    province = models.CharField(_('استان'), max_length=100)
    city = models.CharField(_('شهر'), max_length=100)
    
    class Meta:
        verbose_name = _('موقعیت ارسال')
        verbose_name_plural = _('موقعیت‌های ارسال')
        unique_together = ('zone', 'province', 'city')
    
    def __str__(self):
        return f"{self.province} - {self.city} ({self.zone.name})"


class Warehouse(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('نام انبار'), max_length=100)
    address = models.TextField(_('آدرس'))
    province = models.CharField(_('استان'), max_length=100)
    city = models.CharField(_('شهر'), max_length=100)
    postal_code = models.CharField(_('کد پستی'), max_length=10)
    phone = models.CharField(_('تلفن'), max_length=20)
    manager = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, 
                              related_name='managed_warehouses', null=True, blank=True)
    is_active = models.BooleanField(_('فعال'), default=True)
    created_at = models.DateTimeField(_('تاریخ ایجاد'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('انبار')
        verbose_name_plural = _('انبارها')
    
    def __str__(self):
        return f"{self.name} - {self.city}"


class WarehouseProduct(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='products')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='warehouse_stocks')
    variant = models.ForeignKey('products.ProductVariant', on_delete=models.CASCADE, 
                              related_name='warehouse_stocks', null=True, blank=True)
    stock = models.PositiveIntegerField(_('موجودی'))
    location = models.CharField(_('موقعیت در انبار'), max_length=100, blank=True)
    updated_at = models.DateTimeField(_('تاریخ به‌روزرسانی'), auto_now=True)
    
    class Meta:
        verbose_name = _('موجودی محصول در انبار')
        verbose_name_plural = _('موجودی محصولات در انبار')
        unique_together = ('warehouse', 'product', 'variant')
    
    def __str__(self):
        variant_name = f" - {self.variant.name}" if self.variant else ""
        return f"{self.warehouse.name} - {self.product.name}{variant_name} - {self.stock}"


class WarehouseTransfer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, 
                                       related_name='outgoing_transfers')
    destination_warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, 
                                           related_name='incoming_transfers')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, 
                                 related_name='created_transfers')
    status_choices = [
        ('pending', _('در انتظار')),
        ('in_transit', _('در حال انتقال')),
        ('completed', _('تکمیل شده')),
        ('cancelled', _('لغو شده')),
    ]
    status = models.CharField(_('وضعیت'), max_length=20, choices=status_choices, default='pending')
    notes = models.TextField(_('یادداشت‌ها'), blank=True)
    created_at = models.DateTimeField(_('تاریخ ایجاد'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاریخ به‌روزرسانی'), auto_now=True)
    
    class Meta:
        verbose_name = _('انتقال بین انبار')
        verbose_name_plural = _('انتقالات بین انبار')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"انتقال از {self.source_warehouse.name} به {self.destination_warehouse.name} - {self.get_status_display()}"


class WarehouseTransferItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transfer = models.ForeignKey(WarehouseTransfer, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    variant = models.ForeignKey('products.ProductVariant', on_delete=models.CASCADE, 
                              null=True, blank=True)
    quantity = models.PositiveIntegerField(_('تعداد'))
    
    class Meta:
        verbose_name = _('آیتم انتقال بین انبار')
        verbose_name_plural = _('آیتم‌های انتقال بین انبار')
    
    def __str__(self):
        variant_name = f" - {self.variant.name}" if self.variant else ""
        return f"{self.product.name}{variant_name} - {self.quantity}"