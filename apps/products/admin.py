from django.contrib import admin
from django.utils.html import format_html
from .models import (Product, ProductImage, ProductAttribute, ProductVariant, 
                     ProductVariantAttribute, ProductTag, ProductTagRelation, 
                     ProductReview, ProductReviewImage, ProductReviewComment, 
                     ProductReviewReport, ProductQuestion, ProductAnswer, 
                     RelatedProduct, ProductInventoryLog)


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    readonly_fields = ('image_preview',)
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="100" height="100" />', obj.image.url)
        return "-"
    image_preview.short_description = 'پیش‌نمایش تصویر'


class ProductAttributeInline(admin.TabularInline):
    model = ProductAttribute
    extra = 1


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0


class ProductTagRelationInline(admin.TabularInline):
    model = ProductTagRelation
    extra = 1


class RelatedProductInline(admin.TabularInline):
    model = RelatedProduct
    fk_name = 'product'
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'seller', 'category', 'price', 'discount_price', 'stock', 
                   'is_active', 'is_approved', 'rating', 'sales_count', 'created_at')
    list_filter = ('is_active', 'is_approved', 'is_featured', 'category', 'created_at')
    search_fields = ('name', 'description', 'sku', 'seller__shop_name')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('rating', 'review_count', 'sales_count', 'view_count', 'created_at', 'updated_at')
    inlines = [ProductImageInline, ProductAttributeInline, ProductVariantInline, ProductTagRelationInline, RelatedProductInline]
    date_hierarchy = 'created_at'
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('name', 'slug', 'seller', 'category', 'description', 'short_description')
        }),
        ('قیمت و موجودی', {
            'fields': ('price', 'discount_price', 'stock')
        }),
        ('وضعیت', {
            'fields': ('is_active', 'is_approved', 'is_featured')
        }),
        ('آمار', {
            'fields': ('rating', 'review_count', 'sales_count', 'view_count')
        }),
        ('مشصات فیزیکی', {
            'fields': ('sku', 'weight', 'width', 'height', 'length')
        }),
        ('سئو', {
            'fields': ('meta_title', 'meta_description', 'meta_keywords')
        }),
        ('زمان‌بندی', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    actions = ['approve_products', 'unapprove_products', 'mark_as_featured', 'unmark_as_featured']
    
    def approve_products(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f'{updated} محصول تایید شد.')
    approve_products.short_description = 'تایید محصولات انتخاب شده'
    
    def unapprove_products(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, f'{updated} محصول از حالت تایید خارج شد.')
    unapprove_products.short_description = 'لغو تایید محصولات انتخاب شده'
    
    def mark_as_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} محصول به عنوان ویژه علامت‌گذاری شد.')
    mark_as_featured.short_description = 'علامت‌گذاری به عنوان محصول ویژه'
    
    def unmark_as_featured(self, request, queryset):
        updated = queryset.update(is_featured=False)
        self.message_user(request, f'{updated} محصول از حالت ویژه خارج شد.')
    unmark_as_featured.short_description = 'حذف علامت محصول ویژه'


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ('name', 'product', 'sku', 'price_adjustment', 'stock', 'is_default')
    list_filter = ('is_default', 'product')
    search_fields = ('name', 'sku', 'product__name')
    list_editable = ('price_adjustment', 'stock', 'is_default')


class ProductVariantAttributeInline(admin.TabularInline):
    model = ProductVariantAttribute
    extra = 1


@admin.register(ProductTag)
class ProductTagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


class ProductReviewImageInline(admin.TabularInline):
    model = ProductReviewImage
    extra = 1


class ProductReviewCommentInline(admin.TabularInline):
    model = ProductReviewComment
    extra = 0


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'title', 'is_approved', 'created_at')
    list_filter = ('rating', 'is_approved', 'created_at')
    search_fields = ('product__name', 'user__username', 'user__email', 'title', 'comment')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [ProductReviewImageInline, ProductReviewCommentInline]
    date_hierarchy = 'created_at'
    actions = ['approve_reviews', 'unapprove_reviews']
    
    def approve_reviews(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f'{updated} نظر تایید شد.')
    approve_reviews.short_description = 'تایید نظرات انتخاب شده'
    
    def unapprove_reviews(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, f'{updated} نظر از حالت تایید خارج شد.')
    unapprove_reviews.short_description = 'لغو تایید نظرات انتخاب شده'


@admin.register(ProductReviewReport)
class ProductReviewReportAdmin(admin.ModelAdmin):
    list_display = ('review', 'user', 'is_resolved', 'created_at')
    list_filter = ('is_resolved', 'created_at')
    search_fields = ('review__product__name', 'user__username', 'user__email', 'reason')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
    actions = ['mark_as_resolved', 'mark_as_unresolved']
    
    def mark_as_resolved(self, request, queryset):
        updated = queryset.update(is_resolved=True)
        self.message_user(request, f'{updated} گزارش به عنوان حل شده علامت‌گذاری شد.')
    mark_as_resolved.short_description = 'علامت‌گذاری به عنوان حل شده'
    
    def mark_as_unresolved(self, request, queryset):
        updated = queryset.update(is_resolved=False)
        self.message_user(request, f'{updated} گزارش به عنوان حل نشده علامت‌گذاری شد.')
    mark_as_unresolved.short_description = 'علامت‌گذاری به عنوان حل نشده'


class ProductAnswerInline(admin.TabularInline):
    model = ProductAnswer
    extra = 0


@admin.register(ProductQuestion)
class ProductQuestionAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'question', 'is_approved', 'created_at')
    list_filter = ('is_approved', 'created_at')
    search_fields = ('product__name', 'user__username', 'user__email', 'question')
    readonly_fields = ('created_at',)
    inlines = [ProductAnswerInline]
    date_hierarchy = 'created_at'
    actions = ['approve_questions', 'unapprove_questions']
    
    def approve_questions(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f'{updated} پرسش تایید شد.')
    approve_questions.short_description = 'تایید پرسش‌های انتخاب شده'
    
    def unapprove_questions(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, f'{updated} پرسش از حالت تایید خارج شد.')
    unapprove_questions.short_description = 'لغو تایید پرسش‌های انتخاب شده'


@admin.register(ProductAnswer)
class ProductAnswerAdmin(admin.ModelAdmin):
    list_display = ('question', 'user', 'is_seller', 'is_approved', 'created_at')
    list_filter = ('is_seller', 'is_approved', 'created_at')
    search_fields = ('question__product__name', 'user__username', 'user__email', 'answer')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
    actions = ['approve_answers', 'unapprove_answers']
    
    def approve_answers(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f'{updated} پاسخ تایید شد.')
    approve_answers.short_description = 'تایید پاسخ‌های انتخاب شده'
    
    def unapprove_answers(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, f'{updated} پاسخ از حالت تایید خارج شد.')
    unapprove_answers.short_description = 'لغو تایید پاسخ‌های انتخاب شده'


@admin.register(ProductInventoryLog)
class ProductInventoryLogAdmin(admin.ModelAdmin):
    list_display = ('product', 'variant', 'previous_stock', 'new_stock', 'change_reason', 'created_by', 'created_at')
    list_filter = ('change_reason', 'created_at')
    search_fields = ('product__name', 'variant__name', 'reference', 'created_by__username')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
