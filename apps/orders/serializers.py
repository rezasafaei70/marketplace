from rest_framework import serializers
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import get_random_string
from .models import (
    Cart, CartItem, Order, OrderItem, OrderHistory, OrderReturn, OrderReturnImage,
    Invoice, InstallmentPlan, Installment
)
from apps.products.serializers import ProductListSerializer
from apps.accounts.serializers import AddressSerializer
from apps.shipping.serializers import ShippingMethodSerializer


class CartItemSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)
    product_id = serializers.UUIDField(write_only=True)
    variant_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    
    class Meta:
        model = CartItem
        fields = ('id', 'product', 'product_id', 'variant', 'variant_id', 'quantity', 
                 'unit_price', 'total_price', 'total_discount', 'created_at')
        read_only_fields = ('id', 'unit_price', 'total_price', 'total_discount', 'created_at')
    
    def validate(self, data):
        product_id = data.get('product_id')
        variant_id = data.get('variant_id')
        quantity = data.get('quantity', 1)
        
        from apps.products.models import Product, ProductVariant
        
        try:
            product = Product.objects.get(id=product_id, is_active=True, is_approved=True)
        except Product.DoesNotExist:
            raise serializers.ValidationError('محصول مورد نظر یافت نشد یا غیرفعال است')
        
        variant = None
        if variant_id:
            try:
                variant = ProductVariant.objects.get(id=variant_id, product=product)
            except ProductVariant.DoesNotExist:
                raise serializers.ValidationError('تنوع مورد نظر یافت نشد')
            
            if quantity > variant.stock:
                raise serializers.ValidationError('موجودی کافی نیست')
        else:
            if quantity > product.stock:
                raise serializers.ValidationError('موجودی کافی نیست')
        
        data['product'] = product
        data['variant'] = variant
        return data


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.DecimalField(max_digits=15, decimal_places=0, read_only=True)
    total_discount = serializers.DecimalField(max_digits=15, decimal_places=0, read_only=True)
    total_items_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Cart
        fields = ('id', 'status', 'created_at', 'updated_at', 'items', 
                 'total_price', 'total_discount', 'total_items_count')
        read_only_fields = ('id', 'status', 'created_at', 'updated_at')


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ('id', 'product', 'variant', 'seller', 'product_name', 'variant_name',
                 'quantity', 'unit_price', 'discount', 'final_price', 'total_price', 'status')
        read_only_fields = fields


class OrderHistorySerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    created_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderHistory
        fields = ('id', 'status', 'status_display', 'description', 
                 'created_by', 'created_by_name', 'created_at')
        read_only_fields = fields
    
    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name()
        return None


class OrderReturnImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderReturnImage
        fields = ('id', 'image')


class OrderReturnSerializer(serializers.ModelSerializer):
    images = OrderReturnImageSerializer(many=True, read_only=True)
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(max_length=1000000, allow_empty_file=False, use_url=False),
        write_only=True, required=False
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = OrderReturn
        fields = ('id', 'order_item', 'reason', 'quantity', 'status', 'status_display',
                 'admin_note', 'created_at', 'updated_at', 'images', 'uploaded_images')
        read_only_fields = ('id', 'status', 'admin_note', 'created_at', 'updated_at')
    
    def validate(self, data):
        order_item = data.get('order_item')
        quantity = data.get('quantity')
        
        # بررسی اینکه آیتم سفارش متعلق به کاربر باشد
        if order_item.order.user != self.context['request'].user:
            raise serializers.ValidationError('شما اجازه مرجوع کردن این آیتم را ندارید')
        
        # بررسی اینکه تعداد مرجوعی از تعداد خریداری شده بیشتر نباشد
        total_returned = OrderReturn.objects.filter(
            order_item=order_item
        ).exclude(status='rejected').aggregate(
            total=models.Sum('quantity')
        )['total'] or 0
        
        if total_returned + quantity > order_item.quantity:
            raise serializers.ValidationError('تعداد مرجوعی بیشتر از تعداد خریداری شده است')
        
        return data
    
    def create(self, validated_data):
        uploaded_images = validated_data.pop('uploaded_images', [])
        order_return = OrderReturn.objects.create(**validated_data)
        
        for image in uploaded_images:
            OrderReturnImage.objects.create(order_return=order_return, image=image)
        
        return order_return


class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = ('id', 'invoice_number', 'issue_date', 'due_date', 
                 'is_paid', 'payment_date')
        read_only_fields = fields


class InstallmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Installment
        fields = ('id', 'amount', 'due_date', 'is_paid', 'payment_date')
        read_only_fields = fields


class InstallmentPlanSerializer(serializers.ModelSerializer):
    installments = InstallmentSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = InstallmentPlan
        fields = ('id', 'total_amount', 'down_payment', 'number_of_installments',
                 'installment_amount', 'interest_rate', 'start_date', 'status',
                 'status_display', 'created_at', 'installments')
        read_only_fields = fields


class OrderListSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Order
        fields = ('id', 'order_number', 'status', 'status_display', 'final_price', 
                 'created_at', 'payment_method')
        read_only_fields = fields


class OrderDetailSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    history = OrderHistorySerializer(many=True, read_only=True)
    shipping_address = AddressSerializer(read_only=True)
    shipping_method = ShippingMethodSerializer(read_only=True)
    invoice = InvoiceSerializer(read_only=True)
    installment_plan = InstallmentPlanSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Order
        fields = ('id', 'order_number', 'status', 'status_display', 'total_price',
                 'total_discount', 'shipping_cost', 'tax', 'final_price', 'description',
                 'shipping_address', 'shipping_method', 'tracking_code', 'payment_method',
                 'payment_ref_id', 'payment_date', 'created_at', 'updated_at',
                 'items', 'history', 'invoice', 'installment_plan')
        read_only_fields = fields


class CheckoutSerializer(serializers.Serializer):
    cart_id = serializers.UUIDField()
    shipping_address_id = serializers.UUIDField()
    shipping_method_id = serializers.UUIDField()
    payment_method = serializers.CharField()
    description = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, data):
        cart_id = data.get('cart_id')
        shipping_address_id = data.get('shipping_address_id')
        shipping_method_id = data.get('shipping_method_id')
        payment_method = data.get('payment_method')
        
        # بررسی سبد خرید
        try:
            cart = Cart.objects.get(id=cart_id, status=CartStatus.OPEN)
        except Cart.DoesNotExist:
            raise serializers.ValidationError('سبد خرید معتبر نیست')
        
        # بررسی آدرس
        from apps.accounts.models import Address
        try:
            address = Address.objects.get(id=shipping_address_id, user=self.context['request'].user)
        except Address.DoesNotExist:
            raise serializers.ValidationError('آدرس ارسال معتبر نیست')
        
        # بررسی روش ارسال
        from apps.shipping.models import ShippingMethod
        try:
            shipping_method = ShippingMethod.objects.get(id=shipping_method_id, is_active=True)
        except ShippingMethod.DoesNotExist:
            raise serializers.ValidationError('روش ارسال معتبر نیست')
        
        # بررسی روش پرداخت
        valid_payment_methods = ['online', 'wallet', 'cod', 'installment']
        if payment_method not in valid_payment_methods:
            raise serializers.ValidationError('روش پرداخت معتبر نیست')
        
        # بررسی موجودی محصولات
        for item in cart.items.all():
            if item.variant:
                if item.variant.stock < item.quantity:
                    raise serializers.ValidationError(f'موجودی محصول {item.product.name} کافی نیست')
            else:
                if item.product.stock < item.quantity:
                    raise serializers.ValidationError(f'موجودی محصول {item.product.name} کافی نیست')
        
        data['cart'] = cart
        data['address'] = address
        data['shipping_method'] = shipping_method
        return data
    
    @transaction.atomic
    def create(self, validated_data):
        cart = validated_data['cart']
        address = validated_data['address']
        shipping_method = validated_data['shipping_method']
        payment_method = validated_data['payment_method']
        description = validated_data.get('description', '')
        
        user = self.context['request'].user
        
        # محاسبه مبالغ
        total_price = sum(item.unit_price * item.quantity for item in cart.items.all())
        total_discount = sum((item.product.price - item.unit_price) * item.quantity for item in cart.items.all() if item.product.discount_price)
        shipping_cost = shipping_method.cost
        
        # محاسبه مالیات (مثلاً 9%)
# محاسبه مالیات (مثلاً 9%)
        tax = int(total_price * 0.09)
        
        # محاسبه مبلغ نهایی
        final_price = total_price - total_discount + shipping_cost + tax
        
        # ایجاد شماره سفارش یکتا
        order_number = f"ORD-{get_random_string(8, '0123456789').upper()}"
        
        # ایجاد سفارش
        order = Order.objects.create(
            user=user,
            order_number=order_number,
            status=OrderStatus.PENDING,
            total_price=total_price,
            total_discount=total_discount,
            shipping_cost=shipping_cost,
            tax=tax,
            final_price=final_price,
            description=description,
            shipping_address=address,
            shipping_method=shipping_method,
            payment_method=payment_method
        )
        
        # ایجاد آیتم‌های سفارش
        for item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=item.product,
                variant=item.variant,
                seller=item.product.seller,
                product_name=item.product.name,
                variant_name=item.variant.name if item.variant else None,
                quantity=item.quantity,
                unit_price=item.product.price,
                discount=item.product.price - item.unit_price if item.product.discount_price else 0,
                final_price=item.unit_price,
                total_price=item.unit_price * item.quantity,
                status=OrderStatus.PENDING
            )
        
        # ایجاد تاریخچه سفارش
        OrderHistory.objects.create(
            order=order,
            status=OrderStatus.PENDING,
            description='سفارش ایجاد شد',
            created_by=user
        )
        
        # ایجاد فاکتور
        invoice_number = f"INV-{get_random_string(8, '0123456789').upper()}"
        Invoice.objects.create(
            order=order,
            invoice_number=invoice_number
        )
        
        # تغییر وضعیت سبد خرید
        cart.status = CartStatus.CONVERTED
        cart.save()
        
        return order