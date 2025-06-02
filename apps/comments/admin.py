from django.contrib import admin
from .models import Comment, CommentVote, CommentReport


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'content_type', 'object_id', 'text_preview', 'status', 'created_at']
    list_filter = ['status', 'content_type', 'created_at']
    search_fields = ['text', 'user__phone', 'user__first_name', 'user__last_name']
    readonly_fields = ['likes_count', 'dislikes_count', 'created_at', 'updated_at']
    actions = ['approve_comments', 'reject_comments']
    
    def text_preview(self, obj):
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
    text_preview.short_description = 'متن نظر'
    
    def approve_comments(self, request, queryset):
        queryset.update(status='approved')
        self.message_user(request, f'{queryset.count()} نظر تایید شد')
    approve_comments.short_description = 'تایید نظرات انتخاب شده'
    
    def reject_comments(self, request, queryset):
        queryset.update(status='rejected')
        self.message_user(request, f'{queryset.count()} نظر رد شد')
    reject_comments.short_description = 'رد نظرات انتخاب شده'


@admin.register(CommentVote)
class CommentVoteAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'comment', 'vote_type', 'created_at']
    list_filter = ['vote_type', 'created_at']
    search_fields = ['user__phone', 'comment__text']


@admin.register(CommentReport)
class CommentReportAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'comment', 'reason', 'status', 'created_at']
    list_filter = ['reason', 'status', 'created_at']
    search_fields = ['user__phone', 'comment__text', 'description']
    actions = ['mark_as_resolved', 'mark_as_dismissed']
    
    def mark_as_resolved(self, request, queryset):
        queryset.update(status='resolved')
        self.message_user(request, f'{queryset.count()} گزارش به عنوان حل شده علامت‌گذاری شد')
    mark_as_resolved.short_description = 'علامت‌گذاری به عنوان حل شده'
    
    def mark_as_dismissed(self, request, queryset):
        queryset.update(status='dismissed')
        self.message_user(request, f'{queryset.count()} گزارش به عنوان رد شده علامت‌گذاری شد')
    mark_as_dismissed.short_description = 'علامت‌گذاری به عنوان رد شده'