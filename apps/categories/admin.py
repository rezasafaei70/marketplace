from django.contrib import admin
from .models import Category, CategoryAttribute, CategoryAttributeValue


class CategoryAttributeInline(admin.TabularInline):
    model = CategoryAttribute
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'slug', 'is_active', 'order', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at')
    inlines = [CategoryAttributeInline]
    list_editable = ('is_active', 'order')


class CategoryAttributeValueInline(admin.TabularInline):
    model = CategoryAttributeValue
    extra = 1


@admin.register(CategoryAttribute)
class CategoryAttributeAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'is_color', 'is_required', 'is_filter')
    list_filter = ('is_color', 'is_required', 'is_filter', 'category')
    search_fields = ('name', 'category__name')
    inlines = [CategoryAttributeValueInline]
    list_editable = ('is_required', 'is_filter')


@admin.register(CategoryAttributeValue)
class CategoryAttributeValueAdmin(admin.ModelAdmin):
    list_display = ('value', 'attribute', 'order')
    list_filter = ('attribute',)
    search_fields = ('value', 'attribute__name')
    list_editable = ('order',)
