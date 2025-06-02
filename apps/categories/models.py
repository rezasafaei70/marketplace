from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify
from mptt.models import MPTTModel, TreeForeignKey
import uuid


class Category(MPTTModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('نام'), max_length=100)
    slug = models.SlugField(_('اسلاگ'), max_length=100, unique=True)
    description = models.TextField(_('توضیحات'), blank=True)
    parent = TreeForeignKey('self', on_delete=models.CASCADE, null=True, blank=True,
                           related_name='children', verbose_name=_('دسته والد'))
    image = models.ImageField(_('تصویر'), upload_to='categories/', blank=True, null=True)
    is_active = models.BooleanField(_('فعال'), default=True)
    created_at = models.DateTimeField(_('تاریخ ایجاد'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاریخ به‌روزرسانی'), auto_now=True)
    order = models.PositiveIntegerField(_('ترتیب نمایش'), default=0)
    
    class MPTTMeta:
        order_insertion_by = ['order', 'name']
    
    class Meta:
        verbose_name = _('دسته‌بندی')
        verbose_name_plural = _('دسته‌بندی‌ها')
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class CategoryAttribute(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='attributes',
                               verbose_name=_('دسته‌بندی'))
    name = models.CharField(_('نام ویژگی'), max_length=100)
    slug = models.SlugField(_('اسلاگ'), max_length=100)
    is_required = models.BooleanField(_('اجباری'), default=False)
    is_filter = models.BooleanField(_('قابل فیلتر'), default=False)
    is_color = models.BooleanField(_('ویژگی رنگ'), default=False)
    is_size = models.BooleanField(_('ویژگی سایز'), default=False)
    order = models.PositiveIntegerField(_('ترتیب نمایش'), default=0)
    
    class Meta:
        verbose_name = _('ویژگی دسته‌بندی')
        verbose_name_plural = _('ویژگی‌های دسته‌بندی')
        ordering = ['order', 'name']
        unique_together = ('category', 'slug')
    
    def __str__(self):
        return f"{self.name} - {self.category.name}"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class CategoryAttributeValue(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attribute = models.ForeignKey(CategoryAttribute, on_delete=models.CASCADE,
                                related_name='values', verbose_name=_('ویژگی'))
    value = models.CharField(_('مقدار'), max_length=100)
    color_code = models.CharField(_('کد رنگ'), max_length=7, blank=True, null=True)
    order = models.PositiveIntegerField(_('ترتیب نمایش'), default=0)
    
    class Meta:
        verbose_name = _('مقدار ویژگی دسته‌بندی')
        verbose_name_plural = _('مقادیر ویژگی دسته‌بندی')
        ordering = ['order', 'value']
        unique_together = ('attribute', 'value')
    
    def __str__(self):
        return f"{self.attribute.name}: {self.value}"