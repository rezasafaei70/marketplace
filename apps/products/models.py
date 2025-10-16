from itertools import product
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify
from django.conf import settings
import uuid


class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    seller = models.ForeignKey('sellers.Seller', on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey('categories.Category', on_delete=models.CASCADE, related_name='products')
    name = models.CharField(_('نام محصول'), max_length=200)
    slug = models.SlugField(_('اسلاگ'), max_length=200, unique=True)
    description = models.TextField(_('توضیحات'))
    short_description = models.CharField(_('توضیحات کوتاه'), max_length=300, blank=True)
    price = models.DecimalField(_('قیمت'), max_digits=15, decimal_places=0)
    discount_price = models.DecimalField(_('قیمت با تخفیف'), max_digits=15, decimal_places=0, blank=True, null=True)
    stock = models.PositiveIntegerField(_('موجودی'), default=0)
    is_active = models.BooleanField(_('فعال'), default=True)
    is_featured = models.BooleanField(_('ویژه'), default=False)
    is_approved = models.BooleanField(_('تایید شده'), default=False)
    rating = models.DecimalField(_('امتیاز'), max_digits=3, decimal_places=2, default=0)
    review_count = models.PositiveIntegerField(_('تعداد نظرات'), default=0)
    sales_count = models.PositiveIntegerField(_('تعداد فروش'), default=0)
    view_count = models.PositiveIntegerField(_('تعداد بازدید'), default=0)
    sku = models.CharField(_('کد محصول'), max_length=50, blank=True, null=True)
    weight = models.DecimalField(_('وزن (گرم)'), max_digits=10, decimal_places=2, blank=True, null=True)
    width = models.DecimalField(_('عرض (سانتی‌متر)'), max_digits=10, decimal_places=2, blank=True, null=True)
    height = models.DecimalField(_('ارتفاع (سانتی‌متر)'), max_digits=10, decimal_places=2, blank=True, null=True)
    length = models.DecimalField(_('طول (سانتی‌متر)'), max_digits=10, decimal_places=2, blank=True, null=True)
    meta_title = models.CharField(_('عنوان متا'), max_length=100, blank=True, null=True)
    meta_description = models.TextField(_('توضیحات متا'), blank=True, null=True)
    meta_keywords = models.CharField(_('کلمات کلیدی متا'), max_length=200, blank=True, null=True)
    created_at = models.DateTimeField(_('تاریخ ایجاد'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاریخ به‌روزرسانی'), auto_now=True)
    
    class Meta:
        verbose_name = _('محصول')
        verbose_name_plural = _('محصولات')
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            # اضافه کردن شناسه یکتا برای جلوگیری از تکرار اسلاگ
            if Product.objects.filter(slug=self.slug).exists():
                self.slug = f"{self.slug}-{str(uuid.uuid4())[:8]}"
        super().save(*args, **kwargs)
    
    @property
    def discount_percentage(self):
        if self.discount_price and self.price > 0:
            return int(100 - (self.discount_price * 100 / self.price))
        return 0
    
    @property
    def final_price(self):
        return self.discount_price if self.discount_price else self.price
    
    @property
    def is_in_stock(self):
        return self.stock > 0


class ProductImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(_('تصویر'), upload_to='products/')
    alt_text = models.CharField(_('متن جایگزین'), max_length=100, blank=True)
    is_primary = models.BooleanField(_('تصویر اصلی'), default=False)
    order = models.PositiveIntegerField(_('ترتیب'), default=0)
    
    class Meta:
        verbose_name = _('تصویر محصول')
        verbose_name_plural = _('تصاویر محصول')
        ordering = ['order']
    
    def __str__(self):
        return f"تصویر {self.order} محصول {self.product.name}"


class ProductAttribute(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='attributes')
    attribute = models.ForeignKey('categories.CategoryAttribute', on_delete=models.CASCADE, related_name='product_attributes')
    value = models.CharField(_('مقدار'), max_length=255)
    
    class Meta:
        verbose_name = _('ویژگی محصول')
        verbose_name_plural = _('ویژگی‌های محصول')
        unique_together = ('product', 'attribute')
    
    def __str__(self):
        return f"{self.attribute.name}: {self.value}"


class ProductVariant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    name = models.CharField(_('نام تنوع'), max_length=100)
    sku = models.CharField(_('کد محصول'), max_length=50, blank=True, null=True)
    price_adjustment = models.DecimalField(_('تغییر قیمت'), max_digits=15, decimal_places=0, default=0)
    stock = models.PositiveIntegerField(_('موجودی'), default=0)
    image = models.ImageField(_('تصویر'), upload_to='product_variants/', blank=True, null=True)
    is_default = models.BooleanField(_('پیش‌فرض'), default=False)
    
    class Meta:
        verbose_name = _('تنوع محصول')
        verbose_name_plural = _('تنوع‌های محصول')
    
    def __str__(self):
        return f"{self.product.name} - {self.name}"
    
    @property
    def final_price(self):
        base_price = self.product.discount_price if self.product.discount_price else self.product.price
        return base_price + self.price_adjustment


class ProductVariantAttribute(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='attributes')
    attribute = models.ForeignKey('categories.CategoryAttribute', on_delete=models.CASCADE)
    value = models.CharField(_('مقدار'), max_length=100)
    
    class Meta:
        verbose_name = _('ویژگی تنوع محصول')
        verbose_name_plural = _('ویژگی‌های تنوع محصول')
        unique_together = ('variant', 'attribute')
    
    def __str__(self):
        return f"{self.variant.name} - {self.attribute.name}: {self.value}"


class ProductTag(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('نام'), max_length=100, unique=True)
    slug = models.SlugField(_('اسلاگ'), max_length=100, unique=True)
    
    class Meta:
        verbose_name = _('برچسب محصول')
        verbose_name_plural = _('برچسب‌های محصول')
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class ProductTagRelation(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='tags')
    tag = models.ForeignKey(ProductTag, on_delete=models.CASCADE, related_name='products')
    
    class Meta:
        verbose_name = _('رابطه محصول و برچسب')
        verbose_name_plural = _('روابط محصول و برچسب')
        unique_together = ('product', 'tag')
    
    def __str__(self):
        return f"{self.product.name} - {self.tag.name}"


class ProductReview(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='product_reviews')
    rating = models.PositiveSmallIntegerField(_('امتیاز'), choices=[(i, i) for i in range(1, 6)])
    title = models.CharField(_('عنوان'), max_length=100, blank=True)
    comment = models.TextField(_('نظر'))
    is_approved = models.BooleanField(_('تایید شده'), default=False)
    created_at = models.DateTimeField(_('تاریخ ایجاد'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاریخ به‌روزرسانی'), auto_now=True)
    
    class Meta:
        verbose_name = _('نظر محصول')
        verbose_name_plural = _('نظرات محصول')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.product.name} - {self.rating}"


class ProductReviewImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    review = models.ForeignKey(ProductReview, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(_('تصویر'), upload_to='review_images/')
    
    class Meta:
        verbose_name = _('تصویر نظر')
        verbose_name_plural = _('تصاویر نظر')
    
    def __str__(self):
        return f"تصویر نظر {self.review.id}"


class ProductReviewComment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    review = models.ForeignKey(ProductReview, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='review_comments')
    comment = models.TextField(_('نظر'))
    is_seller = models.BooleanField(_('پاسخ فروشنده'), default=False)
    is_approved = models.BooleanField(_('تایید شده'), default=False)
    created_at = models.DateTimeField(_('تاریخ ایجاد'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('پاسخ به نظر')
        verbose_name_plural = _('پاسخ‌های به نظرات')
        ordering = ['created_at']
    
    def __str__(self):
        return f"پاسخ {self.user.get_full_name()} به نظر {self.review.id}"


class ProductReviewReport(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    review = models.ForeignKey(ProductReview, on_delete=models.CASCADE, related_name='reports')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='review_reports')
    reason = models.TextField(_('دلیل گزارش'))
    is_resolved = models.BooleanField(_('حل شده'), default=False)
    created_at = models.DateTimeField(_('تاریخ ایجاد'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('گزارش نظر نامناسب')
        verbose_name_plural = _('گزارش‌های نظرات نامناسب')
        unique_together = ('review', 'user')
    
    def __str__(self):
        return f"گزارش {self.user.get_full_name()} برای نظر {self.review.id}"


class ProductQuestion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='questions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='product_questions')
    question = models.TextField(_('پرسش'))
    is_approved = models.BooleanField(_('تایید شده'), default=False)
    created_at = models.DateTimeField(_('تاریخ ایجاد'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('پرسش محصول')
        verbose_name_plural = _('پرسش‌های محصول')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"پرسش {self.user.get_full_name()} درباره {self.product.name}"


class ProductAnswer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey(ProductQuestion, on_delete=models.CASCADE, related_name='answers')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='product_answers')
    answer = models.TextField(_('پاسخ'))
    is_seller = models.BooleanField(_('پاسخ فروشنده'), default=False)
    is_approved = models.BooleanField(_('تایید شده'), default=False)
    created_at = models.DateTimeField(_('تاریخ ایجاد'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('پاسخ به پرسش محصول')
        verbose_name_plural = _('پاسخ‌های به پرسش‌های محصول')
        ordering = ['created_at']
    
    def __str__(self):
        return f"پاسخ {self.user.get_full_name()} به پرسش {self.question.id}"


class RelatedProduct(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='related_products')
    related_product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='related_to_products')
    
    class Meta:
        verbose_name = _('محصول مرتبط')
        verbose_name_plural = _('محصولات مرتبط')
        unique_together = ('product', 'related_product')
    
    def __str__(self):
        return f"{self.product.name} -> {self.related_product.name}"


class ProductInventoryLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='inventory_logs')
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, 
                              related_name='inventory_logs', blank=True, null=True)
    previous_stock = models.PositiveIntegerField(_('موجودی قبلی'))
    new_stock = models.PositiveIntegerField(_('موجودی جدید'))
    change_reason = models.CharField(_('دلیل تغییر'), max_length=100)
    reference = models.CharField(_('مرجع'), max_length=100, blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, 
                                 related_name='inventory_logs', blank=True, null=True)
    created_at = models.DateTimeField(_('تاریخ ایجاد'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('لاگ موجودی محصول')
        verbose_name_plural = _('لاگ‌های موجودی محصول')
        ordering = ['-created_at']
    
    def __str__(self):
        product_name = self.product.name
        if self.variant:
            product_name += f" - {self.variant.name}"
        return f"{product_name} - {self.previous_stock} به {self.new_stock}"