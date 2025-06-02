from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid


class CartStatus(models.TextChoices):
    OPEN = 'open', _('باز')
    CHECKOUT = 'checkout', _('در حال تسویه')
    ABANDONED = 'abandoned', _('رها شده')
    CONVERTED = 'converted', _('تبدیل شده به سفارش')


class Cart(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, 
                           related_name='carts', null=True, blank=True)
    session_key = models.CharField(_('کلید نشست'), max_length=40, null=True, blank=True)
    status = models.CharField(_('وضعیت'), max_length=20, choices=CartStatus.choices, default=CartStatus.OPEN)
    created_at = models.DateTimeField(_('تاریخ ایجاد'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاریخ به‌روزرسانی'), auto_now=True)
    
    class Meta:
        verbose_name = _('سبد خرید')
        verbose_name_plural = _('سبدهای خرید')
        ordering = ['-updated_at']
    
    def __str__(self):
        if self.user:
            return f"سبد خرید {self.user.get_full_name()}"
        return f"سبد خرید مهمان {self.session_key}"
    
    @property
    def total_price(self):
        return sum(item.total_price for item in self.items.all())
    
    @property
    def total_discount(self):
        return sum(item.total_discount for item in self.items.all())
    
    @property
    def total_items_count(self):
        return sum(item.quantity for item in self.items.all())


class CartItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    variant = models.ForeignKey('products.ProductVariant', on_delete=models.CASCADE, 
                              null=True, blank=True)
    quantity = models.PositiveIntegerField(_('تعداد'), default=1)
    unit_price = models.DecimalField(_('قیمت واحد'), max_digits=15, decimal_places=0)
    created_at = models.DateTimeField(_('تاریخ ایجاد'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاریخ به‌روزرسانی'), auto_now=True)
    
    class Meta:
        verbose_name = _('آیتم سبد خرید')
        verbose_name_plural = _('آیتم‌های سبد خرید')
        unique_together = ('cart', 'product', 'variant')
    
    def __str__(self):
        variant_name = f" - {self.variant.name}" if self.variant else ""
        return f"{self.product.name}{variant_name} x {self.quantity}"
    
    @property
    def total_price(self):
        return self.unit_price * self.quantity
    
    @property
    def total_discount(self):
        if self.product.discount_price:
            return (self.product.price - self.product.discount_price) * self.quantity
        return 0


class OrderStatus(models.TextChoices):
    PENDING = 'pending', _('در انتظار پرداخت')
    PAID = 'paid', _('پرداخت شده')
    PROCESSING = 'processing', _('در حال پردازش')
    SHIPPED = 'shipped', _('ارسال شده')
    DELIVERED = 'delivered', _('تحویل داده شده')
    CANCELLED = 'cancelled', _('لغو شده')
    REFUNDED = 'refunded', _('مسترد شده')


class Order(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    order_number = models.CharField(_('شماره سفارش'), max_length=20, unique=True)
    status = models.CharField(_('وضعیت'), max_length=20, choices=OrderStatus.choices, default=OrderStatus.PENDING)
    total_price = models.DecimalField(_('مبلغ کل'), max_digits=15, decimal_places=0)
    total_discount = models.DecimalField(_('تخفیف کل'), max_digits=15, decimal_places=0, default=0)
    shipping_cost = models.DecimalField(_('هزینه ارسال'), max_digits=15, decimal_places=0, default=0)
    tax = models.DecimalField(_('مالیات'), max_digits=15, decimal_places=0, default=0)
    final_price = models.DecimalField(_('مبلغ نهایی'), max_digits=15, decimal_places=0)
    description = models.TextField(_('توضیحات'), blank=True)
    shipping_address = models.ForeignKey('accounts.Address', on_delete=models.PROTECT, 
                                       related_name='orders')
    shipping_method = models.ForeignKey('shipping.ShippingMethod', on_delete=models.PROTECT,
                                      related_name='orders')
    tracking_code = models.CharField(_('کد پیگیری'), max_length=100, blank=True, null=True)
    payment_method = models.CharField(_('روش پرداخت'), max_length=50)
    payment_ref_id = models.CharField(_('شناسه پرداخت'), max_length=100, blank=True, null=True)
    payment_date = models.DateTimeField(_('تاریخ پرداخت'), blank=True, null=True)
    created_at = models.DateTimeField(_('تاریخ ایجاد'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاریخ به‌روزرسانی'), auto_now=True)
    
    class Meta:
        verbose_name = _('سفارش')
        verbose_name_plural = _('سفارشات')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"سفارش {self.order_number} - {self.user.get_full_name()}"


class OrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.PROTECT)
    variant = models.ForeignKey('products.ProductVariant', on_delete=models.PROTECT, 
                              null=True, blank=True)
    seller = models.ForeignKey('sellers.Seller', on_delete=models.PROTECT)
    product_name = models.CharField(_('نام محصول'), max_length=200)
    variant_name = models.CharField(_('نام تنوع'), max_length=100, blank=True, null=True)
    quantity = models.PositiveIntegerField(_('تعداد'))
    unit_price = models.DecimalField(_('قیمت واحد'), max_digits=15, decimal_places=0)
    discount = models.DecimalField(_('تخفیف واحد'), max_digits=15, decimal_places=0, default=0)
    final_price = models.DecimalField(_('قیمت نهایی واحد'), max_digits=15, decimal_places=0)
    total_price = models.DecimalField(_('قیمت کل'), max_digits=15, decimal_places=0)
    commission = models.DecimalField(_('کمیسیون'), max_digits=15, decimal_places=0, default=0)
    status = models.CharField(_('وضعیت'), max_length=20, choices=OrderStatus.choices, 
                            default=OrderStatus.PENDING)
    
    class Meta:
        verbose_name = _('آیتم سفارش')
        verbose_name_plural = _('آیتم‌های سفارش')
    
    def __str__(self):
        variant_name = f" - {self.variant_name}" if self.variant_name else ""
        return f"{self.product_name}{variant_name} x {self.quantity}"


class OrderHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='history')
    status = models.CharField(_('وضعیت'), max_length=20, choices=OrderStatus.choices)
    description = models.TextField(_('توضیحات'), blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                 null=True, blank=True, related_name='order_status_changes')
    created_at = models.DateTimeField(_('تاریخ ایجاد'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('تاریخچه سفارش')
        verbose_name_plural = _('تاریخچه سفارشات')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"سفارش {self.order.order_number} - {self.get_status_display()}"


class OrderReturn(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE, related_name='returns')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='returns')
    reason = models.TextField(_('دلیل مرجوعی'))
    quantity = models.PositiveIntegerField(_('تعداد'))
    status_choices = [
        ('pending', _('در انتظار بررسی')),
        ('approved', _('تایید شده')),
        ('rejected', _('رد شده')),
        ('returned', _('بازگشت داده شده')),
        ('refunded', _('مسترد شده')),
    ]
    status = models.CharField(_('وضعیت'), max_length=20, choices=status_choices, default='pending')
    admin_note = models.TextField(_('یادداشت مدیر'), blank=True)
    created_at = models.DateTimeField(_('تاریخ ایجاد'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاریخ به‌روزرسانی'), auto_now=True)
    
    class Meta:
        verbose_name = _('مرجوعی سفارش')
        verbose_name_plural = _('مرجوعی‌های سفارش')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"مرجوعی {self.order_item.product_name} - {self.user.get_full_name()}"


class OrderReturnImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_return = models.ForeignKey(OrderReturn, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(_('تصویر'), upload_to='return_images/')
    
    class Meta:
        verbose_name = _('تصویر مرجوعی')
        verbose_name_plural = _('تصاویر مرجوعی')
    
    def __str__(self):
        return f"تصویر مرجوعی {self.order_return.id}"


class Invoice(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='invoice')
    invoice_number = models.CharField(_('شماره فاکتور'), max_length=20, unique=True)
    issue_date = models.DateTimeField(_('تاریخ صدور'), auto_now_add=True)
    due_date = models.DateTimeField(_('تاریخ سررسید'), blank=True, null=True)
    is_paid = models.BooleanField(_('پرداخت شده'), default=False)
    payment_date = models.DateTimeField(_('تاریخ پرداخت'), blank=True, null=True)
    
    class Meta:
        verbose_name = _('فاکتور')
        verbose_name_plural = _('فاکتورها')
    
    def __str__(self):
        return f"فاکتور {self.invoice_number} - {self.order.order_number}"


class InstallmentPlan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='installment_plan')
    total_amount = models.DecimalField(_('مبلغ کل'), max_digits=15, decimal_places=0)
    down_payment = models.DecimalField(_('پیش پرداخت'), max_digits=15, decimal_places=0)
    number_of_installments = models.PositiveSmallIntegerField(_('تعداد اقساط'))
    installment_amount = models.DecimalField(_('مبلغ هر قسط'), max_digits=15, decimal_places=0)
    interest_rate = models.DecimalField(_('نرخ سود'), max_digits=5, decimal_places=2, default=0)
    start_date = models.DateField(_('تاریخ شروع'))
    status_choices = [
        ('active', _('فعال')),
        ('completed', _('تکمیل شده')),
        ('defaulted', _('معوق')),
        ('cancelled', _('لغو شده')),
    ]
    status = models.CharField(_('وضعیت'), max_length=20, choices=status_choices, default='active')
    created_at = models.DateTimeField(_('تاریخ ایجاد'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('طرح اقساطی')
        verbose_name_plural = _('طرح‌های اقساطی')
    
    def __str__(self):
        return f"طرح اقساطی {self.order.order_number} - {self.number_of_installments} قسط"


class Installment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(InstallmentPlan, on_delete=models.CASCADE, related_name='installments')
    amount = models.DecimalField(_('مبلغ'), max_digits=15, decimal_places=0)
    due_date = models.DateField(_('تاریخ سررسید'))
    is_paid = models.BooleanField(_('پرداخت شده'), default=False)
    payment_date = models.DateTimeField(_('تاریخ پرداخت'), blank=True, null=True)
    payment_ref_id = models.CharField(_('شناسه پرداخت'), max_length=100, blank=True, null=True)
    
    class Meta:
        verbose_name = _('قسط')
        verbose_name_plural = _('اقساط')
        ordering = ['due_date']
    
    def __str__(self):
        status = 'پرداخت شده' if self.is_paid else 'پرداخت نشده'
        return f"قسط {self.due_date} - {self.amount} - {status}"