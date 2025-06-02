from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.common.models import BaseModel

User = get_user_model()


class Review(BaseModel):
    """Product reviews model"""
    RATING_CHOICES = [
        (1, '1 ستاره'),
        (2, '2 ستاره'),
        (3, '3 ستاره'),
        (4, '4 ستاره'),
        (5, '5 ستاره'),
    ]

    STATUS_CHOICES = [
        ('pending', 'در انتظار بررسی'),
        ('approved', 'تایید شده'),
        ('rejected', 'رد شده'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='کاربر')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='product_detailed_reviews', verbose_name='محصول')
    order_item = models.ForeignKey('orders.OrderItem', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='آیتم سفارش')
    
    rating = models.PositiveSmallIntegerField(
        choices=RATING_CHOICES,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='امتیاز'
    )
    title = models.CharField(max_length=200, verbose_name='عنوان نظر')
    comment = models.TextField(verbose_name='متن نظر')
    
    # Review aspects
    quality_rating = models.PositiveSmallIntegerField(
        choices=RATING_CHOICES,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True, blank=True,
        verbose_name='امتیاز کیفیت'
    )
    value_rating = models.PositiveSmallIntegerField(
        choices=RATING_CHOICES,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True, blank=True,
        verbose_name='امتیاز ارزش خرید'
    )
    delivery_rating = models.PositiveSmallIntegerField(
        choices=RATING_CHOICES,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True, blank=True,
        verbose_name='امتیاز ارسال'
    )
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='وضعیت')
    admin_notes = models.TextField(blank=True, verbose_name='یادداشت مدیر')
    
    # Helpful votes
    helpful_count = models.PositiveIntegerField(default=0, verbose_name='تعداد مفید بودن')
    not_helpful_count = models.PositiveIntegerField(default=0, verbose_name='تعداد مفید نبودن')
    
    # Verification
    is_verified_purchase = models.BooleanField(default=False, verbose_name='خرید تایید شده')
    
    class Meta:
        verbose_name = 'نظر'
        verbose_name_plural = 'نظرات'
        ordering = ['-created_at']
        unique_together = ['user', 'product']  # One review per user per product

    def __str__(self):
        return f"{self.user.phone} - {self.product.name} - {self.rating} ستاره"

    @property
    def average_aspect_rating(self):
        """Calculate average of aspect ratings"""
        ratings = [r for r in [self.quality_rating, self.value_rating, self.delivery_rating] if r]
        return sum(ratings) / len(ratings) if ratings else self.rating

    @property
    def helpful_percentage(self):
        """Calculate helpful percentage"""
        total_votes = self.helpful_count + self.not_helpful_count
        if total_votes == 0:
            return 0
        return (self.helpful_count / total_votes) * 100

    def save(self, *args, **kwargs):
        # Check if this is a verified purchase
        if self.order_item and self.order_item.order.user == self.user:
            self.is_verified_purchase = True
        super().save(*args, **kwargs)


class ReviewImage(BaseModel):
    """Review images model"""
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='images', verbose_name='نظر')
    image = models.ImageField(upload_to='reviews/', verbose_name='تصویر')
    caption = models.CharField(max_length=200, blank=True, verbose_name='توضیح تصویر')

    class Meta:
        verbose_name = 'تصویر نظر'
        verbose_name_plural = 'تصاویر نظرات'

    def __str__(self):
        return f"تصویر نظر {self.review.id}"


class ReviewHelpful(BaseModel):
    """Review helpful votes model"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='کاربر')
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='helpful_votes', verbose_name='نظر')
    is_helpful = models.BooleanField(verbose_name='مفید است')

    class Meta:
        verbose_name = 'رای مفید بودن نظر'
        verbose_name_plural = 'آرای مفید بودن نظرات'
        unique_together = ['user', 'review']

    def __str__(self):
        return f"{self.user.phone} - {self.review.id} - {'مفید' if self.is_helpful else 'غیرمفید'}"

    def save(self, *args, **kwargs):
        # Update review helpful counts
        old_vote = None
        if self.pk:
            old_vote = ReviewHelpful.objects.get(pk=self.pk)
        
        super().save(*args, **kwargs)
        
        # Update counts
        if old_vote:
            if old_vote.is_helpful and not self.is_helpful:
                self.review.helpful_count -= 1
                self.review.not_helpful_count += 1
            elif not old_vote.is_helpful and self.is_helpful:
                self.review.helpful_count += 1
                self.review.not_helpful_count -= 1
        else:
            if self.is_helpful:
                self.review.helpful_count += 1
            else:
                self.review.not_helpful_count += 1
        
        self.review.save()

    def delete(self, *args, **kwargs):
        # Update review helpful counts
        if self.is_helpful:
            self.review.helpful_count -= 1
        else:
            self.review.not_helpful_count -= 1
        self.review.save()
        
        super().delete(*args, **kwargs)


class ReviewReply(BaseModel):
    """Seller replies to reviews"""
    review = models.OneToOneField(Review, on_delete=models.CASCADE, related_name='reply', verbose_name='نظر')
    seller = models.ForeignKey('sellers.Seller', on_delete=models.CASCADE, verbose_name='فروشنده')
    message = models.TextField(verbose_name='پیام پاسخ')

    class Meta:
        verbose_name = 'پاسخ به نظر'
        verbose_name_plural = 'پاسخ‌های نظرات'

    def __str__(self):
        return f"پاسخ به نظر {self.review.id}"


class ReviewReport(BaseModel):
    """Review reports model"""
    REPORT_REASONS = [
        ('spam', 'اسپم'),
        ('inappropriate', 'نامناسب'),
        ('fake', 'جعلی'),
        ('offensive', 'توهین‌آمیز'),
        ('irrelevant', 'غیرمرتبط'),
        ('other', 'سایر'),
    ]

    STATUS_CHOICES = [
        ('pending', 'در انتظار بررسی'),
        ('reviewed', 'بررسی شده'),
        ('resolved', 'حل شده'),
        ('dismissed', 'رد شده'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='گزارش‌دهنده')
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='reports', verbose_name='نظر')
    reason = models.CharField(max_length=20, choices=REPORT_REASONS, verbose_name='دلیل گزارش')
    description = models.TextField(blank=True, verbose_name='توضیحات')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='وضعیت')
    admin_notes = models.TextField(blank=True, verbose_name='یادداشت مدیر')

    class Meta:
        verbose_name = 'گزارش نظر'
        verbose_name_plural = 'گزارش‌های نظرات'
        unique_together = ['user', 'review']

    def __str__(self):
        return f"گزارش نظر {self.review.id} توسط {self.user.phone}"


class ReviewSummary(models.Model):
    """Review summary for products (cached data)"""
    product = models.OneToOneField('products.Product', on_delete=models.CASCADE, related_name='review_summary', verbose_name='محصول')
    
    total_reviews = models.PositiveIntegerField(default=0, verbose_name='تعداد کل نظرات')
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0, verbose_name='میانگین امتیاز')
    
    # Rating distribution
    rating_1_count = models.PositiveIntegerField(default=0, verbose_name='تعداد 1 ستاره')
    rating_2_count = models.PositiveIntegerField(default=0, verbose_name='تعداد 2 ستاره')
    rating_3_count = models.PositiveIntegerField(default=0, verbose_name='تعداد 3 ستاره')
    rating_4_count = models.PositiveIntegerField(default=0, verbose_name='تعداد 4 ستاره')
    rating_5_count = models.PositiveIntegerField(default=0, verbose_name='تعداد 5 ستاره')
    
    # Aspect ratings
    average_quality_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0, verbose_name='میانگین امتیاز کیفیت')
    average_value_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0, verbose_name='میانگین امتیاز ارزش')
    average_delivery_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0, verbose_name='میانگین امتیاز ارسال')
    
    verified_purchases_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='درصد خریدهای تایید شده')
    
    last_updated = models.DateTimeField(auto_now=True, verbose_name='آخرین بروزرسانی')

    class Meta:
        verbose_name = 'خلاصه نظرات'
        verbose_name_plural = 'خلاصه نظرات'

    def __str__(self):
        return f"خلاصه نظرات {self.product.name}"

    @classmethod
    def update_for_product(cls, product):
        """Update review summary for a product"""
        from django.db.models import Avg, Count, Q
        
        reviews = Review.objects.filter(product=product, status='approved')
        
        summary, created = cls.objects.get_or_create(product=product)
        
        # Basic stats
        summary.total_reviews = reviews.count()
        summary.average_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0
        
        # Rating distribution
        summary.rating_1_count = reviews.filter(rating=1).count()
        summary.rating_2_count = reviews.filter(rating=2).count()
        summary.rating_3_count = reviews.filter(rating=3).count()
        summary.rating_4_count = reviews.filter(rating=4).count()
        summary.rating_5_count = reviews.filter(rating=5).count()
        
        # Aspect ratings
        summary.average_quality_rating = reviews.aggregate(avg=Avg('quality_rating'))['avg'] or 0
        summary.average_value_rating = reviews.aggregate(avg=Avg('value_rating'))['avg'] or 0
        summary.average_delivery_rating = reviews.aggregate(avg=Avg('delivery_rating'))['avg'] or 0
        
        # Verified purchases
        if summary.total_reviews > 0:
            verified_count = reviews.filter(is_verified_purchase=True).count()
            summary.verified_purchases_percentage = (verified_count / summary.total_reviews) * 100
        else:
            summary.verified_purchases_percentage = 0
        
        summary.save()
        return summary