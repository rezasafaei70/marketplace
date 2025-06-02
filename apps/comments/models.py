from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from apps.common.models import BaseModel

User = get_user_model()


class Comment(BaseModel):
    """Comment model for products, blog posts, etc."""
    STATUS_CHOICES = [
        ('pending', 'در انتظار بررسی'),
        ('approved', 'تایید شده'),
        ('rejected', 'رد شده'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments', verbose_name='کاربر')
    
    # Generic foreign key for linking to any model
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, verbose_name='نوع محتوا')
    object_id = models.UUIDField(verbose_name='شناسه محتوا')
    content_object = GenericForeignKey('content_type', 'object_id')
    
    text = models.TextField(verbose_name='متن نظر')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending', verbose_name='وضعیت')
    
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, 
                              related_name='replies', verbose_name='نظر والد')
    
    likes_count = models.PositiveIntegerField(default=0, verbose_name='تعداد لایک‌ها')
    dislikes_count = models.PositiveIntegerField(default=0, verbose_name='تعداد دیسلایک‌ها')
    
    admin_note = models.TextField(blank=True, verbose_name='یادداشت مدیر')
    
    class Meta:
        verbose_name = 'نظر'
        verbose_name_plural = 'نظرات'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
        ]

    def __str__(self):
        return f"{self.user.phone} - {self.text[:50]}"
    
    @property
    def is_reply(self):
        """Check if comment is a reply"""
        return self.parent is not None
    
    @property
    def replies_count(self):
        """Get replies count"""
        return self.replies.count()


class CommentVote(BaseModel):
    """Model for comment likes/dislikes"""
    VOTE_CHOICES = [
        ('like', 'لایک'),
        ('dislike', 'دیسلایک'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='کاربر')
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='votes', verbose_name='نظر')
    vote_type = models.CharField(max_length=10, choices=VOTE_CHOICES, verbose_name='نوع رای')
    
    class Meta:
        verbose_name = 'رای نظر'
        verbose_name_plural = 'آرای نظرات'
        unique_together = ['user', 'comment']
        
    def __str__(self):
        return f"{self.user.phone} - {self.get_vote_type_display()} - {self.comment.id}"
    
    def save(self, *args, **kwargs):
        # Check if this is a new vote or update
        is_new = self.pk is None
        
        # Get old vote if exists
        old_vote_type = None
        if not is_new:
            old_vote = CommentVote.objects.get(pk=self.pk)
            old_vote_type = old_vote.vote_type
        
        super().save(*args, **kwargs)
        
        # Update comment vote counts
        if is_new:
            # New vote
            if self.vote_type == 'like':
                self.comment.likes_count += 1
            else:
                self.comment.dislikes_count += 1
        elif old_vote_type != self.vote_type:
            # Changed vote
            if self.vote_type == 'like':
                self.comment.likes_count += 1
                self.comment.dislikes_count -= 1
            else:
                self.comment.likes_count -= 1
                self.comment.dislikes_count += 1
        
        self.comment.save()
    
    def delete(self, *args, **kwargs):
        # Update comment vote counts
        if self.vote_type == 'like':
            self.comment.likes_count = max(0, self.comment.likes_count - 1)
        else:
            self.comment.dislikes_count = max(0, self.comment.dislikes_count - 1)
        self.comment.save()
        
        super().delete(*args, **kwargs)


class CommentReport(BaseModel):
    """Model for reporting inappropriate comments"""
    REASON_CHOICES = [
        ('spam', 'اسپم'),
        ('offensive', 'توهین‌آمیز'),
        ('irrelevant', 'غیرمرتبط'),
        ('advertising', 'تبلیغاتی'),
        ('other', 'سایر'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'در انتظار بررسی'),
        ('resolved', 'بررسی شده'),
        ('dismissed', 'رد شده'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='گزارش‌دهنده')
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='reports', verbose_name='نظر')
    reason = models.CharField(max_length=20, choices=REASON_CHOICES, verbose_name='دلیل گزارش')
    description = models.TextField(blank=True, verbose_name='توضیحات')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending', verbose_name='وضعیت')
    admin_note = models.TextField(blank=True, verbose_name='یادداشت مدیر')
    
    class Meta:
        verbose_name = 'گزارش نظر'
        verbose_name_plural = 'گزارش‌های نظرات'
        unique_together = ['user', 'comment']
        
    def __str__(self):
        return f"{self.user.phone} - {self.get_reason_display()} - {self.comment.id}"