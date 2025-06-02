from django.contrib import admin
from .models import Review, ReviewImage, ReviewHelpful, ReviewReply, ReviewReport, ReviewSummary


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'product', 'rating', 'status', 'is_verified_purchase', 'created_at']
    list_filter = ['status', 'rating', 'is_verified_purchase', 'created_at']
    search_fields = ['user__phone', 'product__name', 'title', 'comment']
    readonly_fields = ['helpful_count', 'not_helpful_count', 'created_at', 'updated_at']
    actions = ['approve_reviews', 'reject_reviews']

    def approve_reviews(self, request, queryset):
        queryset.update(status='approved')
        self.message_user(request, f'{queryset.count()} نظر تایید شد')
    approve_reviews.short_description = 'تایید نظرات انتخاب شده'

    def reject_reviews(self, request, queryset):
        queryset.update(status='rejected')
        self.message_user(request, f'{queryset.count()} نظر رد شد')
    reject_reviews.short_description = 'رد نظرات انتخاب شده'


@admin.register(ReviewImage)
class ReviewImageAdmin(admin.ModelAdmin):
    list_display = ['id', 'review', 'image', 'created_at']
    list_filter = ['created_at']


@admin.register(ReviewHelpful)
class ReviewHelpfulAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'review', 'is_helpful', 'created_at']
    list_filter = ['is_helpful', 'created_at']


@admin.register(ReviewReply)
class ReviewReplyAdmin(admin.ModelAdmin):
    list_display = ['id', 'review', 'seller', 'created_at']
    list_filter = ['created_at']


@admin.register(ReviewReport)
class ReviewReportAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'review', 'reason', 'status', 'created_at']
    list_filter = ['reason', 'status', 'created_at']
    actions = ['mark_as_reviewed']

    def mark_as_reviewed(self, request, queryset):
        queryset.update(status='reviewed')
        self.message_user(request, f'{queryset.count()} گزارش بررسی شد')
    mark_as_reviewed.short_description = 'علامت‌گذاری به عنوان بررسی شده'


@admin.register(ReviewSummary)
class ReviewSummaryAdmin(admin.ModelAdmin):
    list_display = ['product', 'total_reviews', 'average_rating', 'last_updated']
    readonly_fields = ['last_updated']
    actions = ['update_summaries']

    def update_summaries(self, request, queryset):
        for summary in queryset:
            ReviewSummary.update_for_product(summary.product)
        self.message_user(request, f'{queryset.count()} خلاصه بروزرسانی شد')
    update_summaries.short_description = 'بروزرسانی خلاصه‌ها'