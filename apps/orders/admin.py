from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from django.db.models import Sum, Count
from .models import (
    CartStatus, Cart, CartItem, OrderStatus, Order, OrderItem, 
    OrderHistory, OrderReturn, OrderReturnImage, Invoice, 
    InstallmentPlan, Installment
)


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ('created_at', 'total_price_display')
    fields = ('product', 'variant', 'quantity', 'unit_price', 'total_price_display', 'created_at')
    
    def total_price_display(self, obj):
        return obj.total_price
    total_price_display.short_description = 'قیمت کل'


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = (
        'user_display', 'status', 'created_at', 'updated_at', 
        'get_total_items', 'get_total_price'
    )
    list_filter = ('status', 'created_at')
    search_fields = ('user__phone', 'user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('created_at', 'updated_at', 'total_price_display', 'total_items_display')
    inlines = [CartItemInline]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('user', 'session_key', 'status')
        }),
        ('آمار', {
            'fields': ('total_items_display', 'total_price_display'),
            'classes': ('collapse',)
        }),
        ('تاریخ‌ها', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user').prefetch_related('items')
    
    def user_display(self, obj):
        if obj.user:
            return f"{obj.user.get_full_name()} ({obj.user.phone})"
        return f"مهمان ({obj.session_key})"
    user_display.short_description = 'کاربر'
    
    def get_total_items(self, obj):
        return obj.total_items_count
    get_total_items.short_description = 'تعداد آیتم‌ها'
    
    def get_total_price(self, obj):
        return f"{obj.total_price:,} تومان"
    get_total_price.short_description = 'قیمت کل'
    
    def total_price_display(self, obj):
        return f"{obj.total_price:,} تومان"
    total_price_display.short_description = 'قیمت کل'
    
    def total_items_display(self, obj):
        return obj.total_items_count
    total_items_display.short_description = 'تعداد آیتم‌ها'
    
    actions = ['convert_to_order', 'mark_as_abandoned']
    
    def convert_to_order(self, request, queryset):
        count = queryset.filter(status=CartStatus.OPEN).update(status=CartStatus.CONVERTED)
        self.message_user(request, f'{count} سبد خرید به سفارش تبدیل شد.')
    convert_to_order.short_description = 'تبدیل به سفارش'
    
    def mark_as_abandoned(self, request, queryset):
        count = queryset.filter(status=CartStatus.OPEN).update(status=CartStatus.ABANDONED)
        self.message_user(request, f'{count} سبد خرید به عنوان رها شده علامت‌گذاری شد.')
    mark_as_abandoned.short_description = 'علامت‌گذاری به عنوان رها شده'


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = (
        'cart', 'product', 'variant', 'quantity', 
        'unit_price', 'total_price_display', 'created_at'
    )
    list_filter = ('created_at', 'updated_at')
    search_fields = (
        'cart__user__phone', 'product__name', 'variant__name'
    )
    readonly_fields = ('created_at', 'updated_at', 'total_price_display')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'cart__user', 'product', 'variant'
        )
    
    def total_price_display(self, obj):
        return f"{obj.total_price:,} تومان"
    total_price_display.short_description = 'قیمت کل'


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('unit_price', 'discount', 'final_price', 'total_price')
    fields = (
        'product', 'variant', 'seller', 'product_name', 'variant_name',
        'quantity', 'unit_price', 'discount', 'final_price', 'total_price', 'status'
    )


class OrderHistoryInline(admin.TabularInline):
    model = OrderHistory
    extra = 0
    readonly_fields = ('created_at', 'created_by')
    fields = ('status', 'description', 'created_by', 'created_at')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'order_number', 'user', 'status', 'final_price_display',
        'payment_method', 'created_at', 'items_count'
    )
    list_filter = ('status', 'payment_method', 'created_at', 'updated_at')
    search_fields = (
        'order_number', 'user__phone', 'user__email', 
        'user__first_name', 'user__last_name'
    )
    readonly_fields = (
        'order_number', 'created_at', 'updated_at', 'final_price',
        'total_price', 'total_discount'
    )
    inlines = [OrderItemInline, OrderHistoryInline]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': (
                'order_number', 'user', 'status', 'description'
            )
        }),
        ('مبالغ', {
            'fields': (
                'total_price', 'total_discount', 'shipping_cost',
                'tax', 'final_price'
            )
        }),
        ('حمل و نقل', {
            'fields': (
                'shipping_address', 'shipping_method', 'tracking_code'
            )
        }),
        ('پرداخت', {
            'fields': (
                'payment_method', 'payment_ref_id', 'payment_date'
            )
        }),
        ('تاریخ‌ها', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'user', 'shipping_address', 'shipping_method'
        ).prefetch_related('items').annotate(
            items_count=Count('items')
        )
    
    def final_price_display(self, obj):
        return f"{obj.final_price:,} تومان"
    final_price_display.short_description = 'مبلغ نهایی'
    final_price_display.admin_order_field = 'final_price'
    
    def items_count(self, obj):
        return obj.items_count
    items_count.short_description = 'تعداد آیتم‌ها'
    items_count.admin_order_field = 'items_count'
    
    actions = [
        'mark_as_paid', 'mark_as_processing', 'mark_as_shipped', 
        'mark_as_delivered', 'cancel_orders'
    ]
    
    def mark_as_paid(self, request, queryset):
        count = queryset.filter(status=OrderStatus.PENDING).update(
            status=OrderStatus.PAID, payment_date=timezone.now()
        )
        self.message_user(request, f'{count} سفارش به عنوان پرداخت شده علامت‌گذاری شد.')
    mark_as_paid.short_description = 'علامت‌گذاری به عنوان پرداخت شده'
    
    def mark_as_processing(self, request, queryset):
        count = queryset.update(status=OrderStatus.PROCESSING)
        self.message_user(request, f'{count} سفارش در حال پردازش قرار گرفت.')
    mark_as_processing.short_description = 'تغییر وضعیت به در حال پردازش'
    
    def mark_as_shipped(self, request, queryset):
        count = queryset.update(status=OrderStatus.SHIPPED)
        self.message_user(request, f'{count} سفارش ارسال شد.')
    mark_as_shipped.short_description = 'تغییر وضعیت به ارسال شده'
    
    def mark_as_delivered(self, request, queryset):
        count = queryset.update(status=OrderStatus.DELIVERED)
        self.message_user(request, f'{count} سفارش تحویل داده شد.')
    mark_as_delivered.short_description = 'تغییر وضعیت به تحویل داده شده'
    
    def cancel_orders(self, request, queryset):
        count = queryset.exclude(
            status__in=[OrderStatus.DELIVERED, OrderStatus.CANCELLED]
        ).update(status=OrderStatus.CANCELLED)
        self.message_user(request, f'{count} سفارش لغو شد.')
    cancel_orders.short_description = 'لغو سفارشات انتخاب شده'


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = (
        'order', 'product_name', 'variant_name', 'seller',
        'quantity', 'unit_price', 'total_price_display', 'status'
    )
    list_filter = ('status', 'order__created_at')
    search_fields = (
        'order__order_number', 'product_name', 'variant_name',
        'seller__business_name'
    )
    readonly_fields = ('total_price', 'commission')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'order', 'product', 'variant', 'seller'
        )
    
    def total_price_display(self, obj):
        return f"{obj.total_price:,} تومان"
    total_price_display.short_description = 'قیمت کل'


@admin.register(OrderHistory)
class OrderHistoryAdmin(admin.ModelAdmin):
    list_display = (
        'order', 'status', 'description_preview', 'created_by', 'created_at'
    )
    list_filter = ('status', 'created_at')
    search_fields = ('order__order_number', 'description')
    readonly_fields = ('created_at',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('order', 'created_by')
    
    def description_preview(self, obj):
        return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
    description_preview.short_description = 'توضیحات'


class OrderReturnImageInline(admin.TabularInline):
    model = OrderReturnImage
    extra = 1
    readonly_fields = ('image_preview',)
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="100" height="100" style="border-radius: 5px;" />',
                obj.image.url
            )
        return '-'
    image_preview.short_description = 'پیش‌نمایش'


@admin.register(OrderReturn)
class OrderReturnAdmin(admin.ModelAdmin):
    list_display = (
        'order_item', 'user', 'status', 'quantity', 'created_at'
    )
    list_filter = ('status', 'created_at')
    search_fields = (
        'user__phone', 'user__email', 'order_item__product_name'
    )
    readonly_fields = ('created_at', 'updated_at')
    inlines = [OrderReturnImageInline]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('order_item', 'user', 'quantity', 'reason')
        }),
        ('وضعیت', {
            'fields': ('status', 'admin_note')
        }),
        ('تاریخ‌ها', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'order_item__order', 'user'
        )
    
    actions = ['approve_return', 'reject_return', 'mark_as_refunded']
    
    def approve_return(self, request, queryset):
        count = queryset.filter(status='pending').update(
            status='approved', updated_at=timezone.now()
        )
        self.message_user(request, f'{count} درخواست مرجوعی تایید شد.')
    approve_return.short_description = 'تایید درخواست مرجوعی'
    
    def reject_return(self, request, queryset):
        count = queryset.filter(status='pending').update(
            status='rejected', updated_at=timezone.now()
        )
        self.message_user(request, f'{count} درخواست مرجوعی رد شد.')
    reject_return.short_description = 'رد درخواست مرجوعی'
    
    def mark_as_refunded(self, request, queryset):
        count = queryset.filter(status='approved').update(
            status='refunded', updated_at=timezone.now()
        )
        self.message_user(request, f'{count} درخواست مرجوعی به عنوان بازپرداخت شده علامت‌گذاری شد.')
    mark_as_refunded.short_description = 'علامت‌گذاری به عنوان بازپرداخت شده'


@admin.register(OrderReturnImage)
class OrderReturnImageAdmin(admin.ModelAdmin):
    list_display = ('order_return', 'image_preview')
    search_fields = ('order_return__order_item__product_name',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('order_return')
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="100" height="100" style="border-radius: 5px;" />',
                obj.image.url
            )
        return '-'
    image_preview.short_description = 'پیش‌نمایش'


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        'invoice_number', 'order', 'issue_date', 'due_date', 
        'is_paid', 'payment_date'
    )
    list_filter = ('is_paid', 'issue_date', 'due_date')
    search_fields = ('invoice_number', 'order__order_number')
    readonly_fields = ('issue_date',)
    date_hierarchy = 'issue_date'
    
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('invoice_number', 'order')
        }),
        ('تاریخ‌ها', {
            'fields': ('issue_date', 'due_date')
        }),
        ('وضعیت پرداخت', {
            'fields': ('is_paid', 'payment_date')
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('order')
    
    actions = ['mark_as_paid']
    
    def mark_as_paid(self, request, queryset):
        count = queryset.filter(is_paid=False).update(
            is_paid=True, payment_date=timezone.now()
        )
        self.message_user(request, f'{count} فاکتور به عنوان پرداخت شده علامت‌گذاری شد.')
    mark_as_paid.short_description = 'علامت‌گذاری به عنوان پرداخت شده'


class InstallmentInline(admin.TabularInline):
    model = Installment
    extra = 0
    readonly_fields = ('payment_date',)
    fields = ('amount', 'due_date', 'is_paid', 'payment_date', 'payment_ref_id')


@admin.register(InstallmentPlan)
class InstallmentPlanAdmin(admin.ModelAdmin):
    list_display = (
        'order', 'total_amount_display', 'number_of_installments', 
        'installment_amount_display', 'status', 'start_date'
    )
    list_filter = ('status', 'start_date', 'created_at')
    search_fields = ('order__order_number',)
    readonly_fields = ('created_at',)
    inlines = [InstallmentInline]
    date_hierarchy = 'start_date'
    
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('order', 'status')
        }),
        ('مبالغ', {
            'fields': (
                'total_amount', 'down_payment', 'installment_amount', 'interest_rate'
            )
        }),
        ('اقساط', {
            'fields': ('number_of_installments', 'start_date')
        }),
        ('تاریخ‌ها', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('order')
    
    def total_amount_display(self, obj):
        return f"{obj.total_amount:,} تومان"
    total_amount_display.short_description = 'مبلغ کل'
    total_amount_display.admin_order_field = 'total_amount'
    
    def installment_amount_display(self, obj):
        return f"{obj.installment_amount:,} تومان"
    installment_amount_display.short_description = 'مبلغ هر قسط'
    installment_amount_display.admin_order_field = 'installment_amount'
    
    actions = ['activate_plans', 'complete_plans', 'cancel_plans']
    
    def activate_plans(self, request, queryset):
        count = queryset.update(status='active')
        self.message_user(request, f'{count} طرح اقساط فعال شد.')
    activate_plans.short_description = 'فعال کردن طرح‌های اقساط'
    
    def complete_plans(self, request, queryset):
        count = queryset.update(status='completed')
        self.message_user(request, f'{count} طرح اقساط تکمیل شد.')
    complete_plans.short_description = 'تکمیل طرح‌های اقساط'
    
    def cancel_plans(self, request, queryset):
        count = queryset.update(status='cancelled')
        self.message_user(request, f'{count} طرح اقساط لغو شد.')
    cancel_plans.short_description = 'لغو طرح‌های اقساط'


@admin.register(Installment)
class InstallmentAdmin(admin.ModelAdmin):
    list_display = (
        'plan', 'amount_display', 'due_date', 'is_paid', 'payment_date'
    )
    list_filter = ('is_paid', 'due_date', 'payment_date')
    search_fields = ('plan__order__order_number', 'payment_ref_id')
    readonly_fields = ('payment_date',)
    date_hierarchy = 'due_date'
    
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('plan', 'amount', 'due_date')
        }),
        ('وضعیت پرداخت', {
            'fields': ('is_paid', 'payment_date', 'payment_ref_id')
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('plan__order')
    
    def amount_display(self, obj):
        return f"{obj.amount:,} تومان"
    amount_display.short_description = 'مبلغ'
    amount_display.admin_order_field = 'amount'
    
    actions = ['mark_as_paid']
    
    def mark_as_paid(self, request, queryset):
        count = queryset.filter(is_paid=False).update(
            is_paid=True, payment_date=timezone.now()
        )
        self.message_user(request, f'{count} قسط به عنوان پرداخت شده علامت‌گذاری شد.')
    mark_as_paid.short_description = 'علامت‌گذاری به عنوان پرداخت شده'