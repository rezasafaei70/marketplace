from rest_framework import viewsets, permissions, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Sum, F
import uuid

from .models import (
    ShippingMethod, ShippingZone, ShippingRate, ShippingLocation,
    Warehouse, WarehouseProduct, WarehouseTransfer, WarehouseTransferItem
)
from .serializers import (
    ShippingMethodSerializer, ShippingZoneSerializer, ShippingRateSerializer,
    ShippingLocationSerializer, WarehouseSerializer, WarehouseProductSerializer,
    WarehouseTransferSerializer, WarehouseTransferItemSerializer,
    ShippingCalculatorSerializer
)
from apps.sellers.permissions import IsAdminUser


class ShippingMethodViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ShippingMethod.objects.filter(is_active=True)
    serializer_class = ShippingMethodSerializer
    permission_classes = [permissions.AllowAny]


class ShippingCalculatorView(generics.GenericAPIView):
    serializer_class = ShippingCalculatorSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        zone = serializer.validated_data['zone']
        cart = serializer.validated_data['cart']
        
        # محاسبه مجموع وزن محصولات
        total_weight = sum(item.product.weight * item.quantity for item in cart.items.all() if item.product.weight)
        
        # محاسبه مجموع قیمت محصولات
        cart_total = sum(item.total_price for item in cart.items.all())
        
        # دریافت روش‌های ارسال مناسب برای این منطقه
        shipping_methods = []
        
        for method in ShippingMethod.objects.filter(is_active=True):
            # بررسی وجود نرخ خاص برای این منطقه
            zone_rate = ShippingRate.objects.filter(shipping_method=method, zone=zone).first()
            
            if zone_rate:
                cost = zone_rate.cost
                delivery_days = zone_rate.estimated_delivery_days
            else:
                cost = method.cost
                delivery_days = method.estimated_delivery_days
            
            # بررسی ارسال رایگان برای خریدهای بالای مبلغ خاص
            if hasattr(method, 'free_shipping_threshold') and method.free_shipping_threshold:
                if cart_total >= method.free_shipping_threshold:
                    cost = 0
            
            shipping_methods.append({
                'id': method.id,
                'name': method.name,
                'description': method.description,
                'cost': cost,
                'estimated_delivery_days': delivery_days,
                'icon': method.icon.url if method.icon else None
            })
        
        return Response({
            'shipping_methods': shipping_methods,
            'cart_total': cart_total,
            'total_weight': total_weight
        })


class AdminShippingMethodViewSet(viewsets.ModelViewSet):
    queryset = ShippingMethod.objects.all()
    serializer_class = ShippingMethodSerializer
    permission_classes = [IsAdminUser]


class AdminShippingZoneViewSet(viewsets.ModelViewSet):
    queryset = ShippingZone.objects.all()
    serializer_class = ShippingZoneSerializer
    permission_classes = [IsAdminUser]


class AdminShippingRateViewSet(viewsets.ModelViewSet):
    queryset = ShippingRate.objects.all()
    serializer_class = ShippingRateSerializer
    permission_classes = [IsAdminUser]


class AdminShippingLocationViewSet(viewsets.ModelViewSet):
    queryset = ShippingLocation.objects.all()
    serializer_class = ShippingLocationSerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # فیلتر بر اساس منطقه
        zone_id = self.request.query_params.get('zone_id')
        if zone_id:
            queryset = queryset.filter(zone_id=zone_id)
        
        # فیلتر بر اساس استان
        province = self.request.query_params.get('province')
        if province:
            queryset = queryset.filter(province=province)
        
        return queryset


class WarehouseViewSet(viewsets.ModelViewSet):
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer
    permission_classes = [IsAdminUser]


class WarehouseProductViewSet(viewsets.ModelViewSet):
    queryset = WarehouseProduct.objects.all()
    serializer_class = WarehouseProductSerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # فیلتر بر اساس انبار
        warehouse_id = self.request.query_params.get('warehouse_id')
        if warehouse_id:
            queryset = queryset.filter(warehouse_id=warehouse_id)
        
        # فیلتر بر اساس محصول
# فیلتر بر اساس محصول
        product_id = self.request.query_params.get('product_id')
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        
        # فیلتر بر اساس موجودی
        low_stock = self.request.query_params.get('low_stock')
        if low_stock:
            try:
                threshold = int(low_stock)
                queryset = queryset.filter(stock__lte=threshold)
            except ValueError:
                pass
        
        return queryset
    
    @action(detail=False, methods=['post'])
    def adjust_stock(self, request):
        warehouse_id = request.data.get('warehouse_id')
        product_id = request.data.get('product_id')
        variant_id = request.data.get('variant_id')
        quantity = request.data.get('quantity')
        reason = request.data.get('reason', 'تنظیم دستی موجودی')
        
        if not warehouse_id or not product_id or not quantity:
            return Response(
                {'error': 'انبار، محصول و تعداد الزامی هستند'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            quantity = int(quantity)
        except ValueError:
            return Response(
                {'error': 'تعداد باید عددی باشد'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            # دریافت یا ایجاد رکورد موجودی انبار
            warehouse_product, created = WarehouseProduct.objects.get_or_create(
                warehouse_id=warehouse_id,
                product_id=product_id,
                variant_id=variant_id,
                defaults={'stock': 0}
            )
            
            previous_stock = warehouse_product.stock
            warehouse_product.stock += quantity
            
            if warehouse_product.stock < 0:
                return Response(
                    {'error': 'موجودی نمی‌تواند منفی باشد'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            warehouse_product.save()
            
            # ثبت لاگ تغییر موجودی
            from apps.products.models import ProductInventoryLog
            ProductInventoryLog.objects.create(
                product_id=product_id,
                variant_id=variant_id,
                previous_stock=previous_stock,
                new_stock=warehouse_product.stock,
                warehouse_id=warehouse_id,
                change_reason=reason,
                reference=f"MANUAL-{uuid.uuid4().hex[:8]}"
            )
            
            # به‌روزرسانی موجودی کلی محصول
            if variant_id:
                from apps.products.models import ProductVariant
                variant = ProductVariant.objects.get(id=variant_id)
                total_stock = WarehouseProduct.objects.filter(
                    product_id=product_id,
                    variant_id=variant_id
                ).aggregate(total=Sum('stock'))['total'] or 0
                
                variant.stock = total_stock
                variant.save()
            else:
                from apps.products.models import Product
                product = Product.objects.get(id=product_id)
                total_stock = WarehouseProduct.objects.filter(
                    product_id=product_id,
                    variant_id__isnull=True
                ).aggregate(total=Sum('stock'))['total'] or 0
                
                product.stock = total_stock
                product.save()
        
        return Response({
            'status': 'موجودی با موفقیت به‌روزرسانی شد',
            'product_id': product_id,
            'variant_id': variant_id,
            'warehouse_id': warehouse_id,
            'previous_stock': previous_stock,
            'new_stock': warehouse_product.stock,
            'change': quantity
        })


class WarehouseTransferViewSet(viewsets.ModelViewSet):
    queryset = WarehouseTransfer.objects.all().order_by('-created_at')
    serializer_class = WarehouseTransferSerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # فیلتر بر اساس انبار مبدأ
        source_id = self.request.query_params.get('source_id')
        if source_id:
            queryset = queryset.filter(source_warehouse_id=source_id)
        
        # فیلتر بر اساس انبار مقصد
        destination_id = self.request.query_params.get('destination_id')
        if destination_id:
            queryset = queryset.filter(destination_warehouse_id=destination_id)
        
        # فیلتر بر اساس وضعیت
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        transfer = self.get_object()
        new_status = request.data.get('status')
        notes = request.data.get('notes', '')
        
        if new_status not in ['pending', 'in_transit', 'completed', 'cancelled']:
            return Response({'error': 'وضعیت نامعتبر است'}, status=status.HTTP_400_BAD_REQUEST)
        
        with transaction.atomic():
            # به‌روزرسانی وضعیت انتقال
            transfer.status = new_status
            
            if notes:
                transfer.notes = (transfer.notes + "\n\n" + notes).strip()
            
            transfer.save()
            
            # اگر انتقال تکمیل شده، موجودی انبارها را به‌روزرسانی کنیم
            if new_status == 'completed':
                for item in transfer.items.all():
                    # کاهش موجودی انبار مبدأ
                    source_product, created = WarehouseProduct.objects.get_or_create(
                        warehouse=transfer.source_warehouse,
                        product=item.product,
                        variant=item.variant,
                        defaults={'stock': 0}
                    )
                    
                    source_product.stock -= item.quantity
                    source_product.save()
                    
                    # افزایش موجودی انبار مقصد
                    dest_product, created = WarehouseProduct.objects.get_or_create(
                        warehouse=transfer.destination_warehouse,
                        product=item.product,
                        variant=item.variant,
                        defaults={'stock': 0}
                    )
                    
                    dest_product.stock += item.quantity
                    dest_product.save()
                    
                    # ثبت لاگ تغییر موجودی برای انبار مبدأ
                    from apps.products.models import ProductInventoryLog
                    ProductInventoryLog.objects.create(
                        product=item.product,
                        variant=item.variant,
                        previous_stock=source_product.stock + item.quantity,
                        new_stock=source_product.stock,
                        warehouse=transfer.source_warehouse,
                        change_reason=f'انتقال به انبار {transfer.destination_warehouse.name}',
                        reference=str(transfer.id)
                    )
                    
                    # ثبت لاگ تغییر موجودی برای انبار مقصد
                    ProductInventoryLog.objects.create(
                        product=item.product,
                        variant=item.variant,
                        previous_stock=dest_product.stock - item.quantity,
                        new_stock=dest_product.stock,
                        warehouse=transfer.destination_warehouse,
                        change_reason=f'دریافت از انبار {transfer.source_warehouse.name}',
                        reference=str(transfer.id)
                    )
            
            # اگر انتقال لغو شده، هیچ تغییری در موجودی ایجاد نمی‌کنیم
        
        return Response({'status': 'وضعیت انتقال با موفقیت به‌روزرسانی شد'})