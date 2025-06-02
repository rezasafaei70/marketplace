from rest_framework import serializers
from django.db import transaction
from .models import (
    ShippingMethod, ShippingZone, ShippingRate, ShippingLocation,
    Warehouse, WarehouseProduct, WarehouseTransfer, WarehouseTransferItem
)


class ShippingLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShippingLocation
        fields = ('id', 'zone', 'province', 'city')


class ShippingZoneSerializer(serializers.ModelSerializer):
    locations = ShippingLocationSerializer(many=True, read_only=True)
    
    class Meta:
        model = ShippingZone
        fields = ('id', 'name', 'description', 'is_active', 'locations')


class ShippingRateSerializer(serializers.ModelSerializer):
    zone_name = serializers.CharField(source='zone.name', read_only=True)
    
    class Meta:
        model = ShippingRate
        fields = ('id', 'shipping_method', 'zone', 'zone_name', 'cost', 'estimated_delivery_days')


class ShippingMethodSerializer(serializers.ModelSerializer):
    rates = ShippingRateSerializer(many=True, read_only=True)
    
    class Meta:
        model = ShippingMethod
        fields = ('id', 'name', 'description', 'cost', 'is_active',
                 'estimated_delivery_days', 'icon', 'created_at', 'updated_at', 'rates')
        read_only_fields = ('id', 'created_at', 'updated_at')


class WarehouseProductSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    variant_name = serializers.CharField(source='variant.name', read_only=True)
    
    class Meta:
        model = WarehouseProduct
        fields = ('id', 'warehouse', 'product', 'product_name', 'variant',
                 'variant_name', 'stock', 'location', 'updated_at')


class WarehouseSerializer(serializers.ModelSerializer):
    manager_name = serializers.CharField(source='manager.get_full_name', read_only=True)
    products_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Warehouse
        fields = ('id', 'name', 'address', 'province', 'city', 'postal_code',
                 'phone', 'manager', 'manager_name', 'is_active', 'created_at',
                 'products_count')
        read_only_fields = ('id', 'created_at', 'products_count')
    
    def get_products_count(self, obj):
        return obj.products.count()


class WarehouseTransferItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    variant_name = serializers.CharField(source='variant.name', read_only=True)
    
    class Meta:
        model = WarehouseTransferItem
        fields = ('id', 'product', 'product_name', 'variant', 'variant_name', 'quantity')


class WarehouseTransferSerializer(serializers.ModelSerializer):
    source_warehouse_name = serializers.CharField(source='source_warehouse.name', read_only=True)
    destination_warehouse_name = serializers.CharField(source='destination_warehouse.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    items = WarehouseTransferItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = WarehouseTransfer
        fields = ('id', 'source_warehouse', 'source_warehouse_name',
                 'destination_warehouse', 'destination_warehouse_name',
                 'created_by', 'created_by_name', 'status', 'status_display',
                 'notes', 'created_at', 'updated_at', 'items')
        read_only_fields = ('id', 'created_by', 'created_by_name', 'created_at', 'updated_at')
    
    def create(self, validated_data):
        items_data = self.context['request'].data.get('items', [])
        
        if not items_data:
            raise serializers.ValidationError('حداقل یک آیتم برای انتقال الزامی است')
        
        validated_data['created_by'] = self.context['request'].user
        
        with transaction.atomic():
            transfer = WarehouseTransfer.objects.create(**validated_data)
            
            for item_data in items_data:
                product_id = item_data.get('product')
                variant_id = item_data.get('variant')
                quantity = item_data.get('quantity')
                
                if not product_id or not quantity:
                    continue
                
                # بررسی موجودی در انبار مبدأ
                source_stock = WarehouseProduct.objects.filter(
                    warehouse=transfer.source_warehouse,
                    product_id=product_id,
                    variant_id=variant_id
                ).first()
                
                if not source_stock or source_stock.stock < quantity:
                    raise serializers.ValidationError(f'موجودی محصول {product_id} در انبار مبدأ کافی نیست')
                
                # ایجاد آیتم انتقال
                WarehouseTransferItem.objects.create(
                    transfer=transfer,
                    product_id=product_id,
                    variant_id=variant_id,
                    quantity=quantity
                )
        
        return transfer


class ShippingCalculatorSerializer(serializers.Serializer):
    province = serializers.CharField()
    city = serializers.CharField()
    cart_id = serializers.UUIDField()
    
    def validate(self, data):
        province = data.get('province')
        city = data.get('city')
        cart_id = data.get('cart_id')
        
        # بررسی سبد خرید
        from apps.orders.models import Cart, CartStatus
        try:
            cart = Cart.objects.get(id=cart_id, status=CartStatus.OPEN)
            data['cart'] = cart
        except Cart.DoesNotExist:
            raise serializers.ValidationError('سبد خرید نامعتبر است')
        
        # بررسی منطقه ارسال
        try:
            location = ShippingLocation.objects.get(province=province, city=city)
            data['zone'] = location.zone
        except ShippingLocation.DoesNotExist:
            # اگر موقعیت دقیق پیدا نشد، فقط استان را بررسی می‌کنیم
            try:
                location = ShippingLocation.objects.filter(province=province).first()
                if location:
                    data['zone'] = location.zone
                else:
                    # اگر استان هم پیدا نشد، از منطقه پیش‌فرض استفاده می‌کنیم
                    default_zone = ShippingZone.objects.filter(is_active=True).first()
                    if default_zone:
                        data['zone'] = default_zone
                    else:
                        raise serializers.ValidationError('منطقه ارسال برای این آدرس یافت نشد')
            except Exception:
                raise serializers.ValidationError('منطقه ارسال برای این آدرس یافت نشد')
        
        return data