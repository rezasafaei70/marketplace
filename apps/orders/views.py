from rest_framework import viewsets, permissions, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Sum, F, Q
from django.utils import timezone
from django.shortcuts import get_object_or_404
import uuid

from .models import (
    Cart, CartItem, Order, OrderItem, OrderHistory, OrderReturn,
    OrderReturnImage, Invoice, InstallmentPlan, Installment, CartStatus, OrderStatus
)
from .serializers import (
    CartSerializer, CartItemSerializer, OrderListSerializer, OrderDetailSerializer,
    CheckoutSerializer, OrderReturnSerializer, OrderHistorySerializer
)
from apps.products.models import Product, ProductVariant
from apps.sellers.permissions import IsAdminUser


class CartPermission(permissions.BasePermission):
    """
    اجازه دسترسی به سبد خرید فقط برای صاحب سبد
    """
    def has_object_permission(self, request, view, obj):
        if obj.user:
            return obj.user == request.user
        return obj.session_key == request.session.session_key


class CartViewSet(viewsets.ModelViewSet):
    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated, CartPermission]
    
    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user, status=CartStatus.OPEN)
    
    def create(self, request, *args, **kwargs):
        # بررسی وجود سبد خرید فعال
        active_cart = Cart.objects.filter(user=request.user, status=CartStatus.OPEN).first()
        if active_cart:
            serializer = self.get_serializer(active_cart)
            return Response(serializer.data)
        
        # ایجاد سبد خرید جدید
        cart = Cart.objects.create(user=request.user)
        serializer = self.get_serializer(cart)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def add_item(self, request, pk=None):
        cart = self.get_object()
        serializer = CartItemSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            product = serializer.validated_data['product']
            variant = serializer.validated_data.get('variant')
            quantity = serializer.validated_data.get('quantity', 1)
            
            # تعیین قیمت واحد
            unit_price = product.discount_price if product.discount_price else product.price
            if variant:
                unit_price += variant.price_adjustment
            
            # بررسی وجود آیتم مشابه در سبد
            try:
                cart_item = CartItem.objects.get(
                    cart=cart,
                    product=product,
                    variant=variant
                )
                # به‌روزرسانی تعداد
                cart_item.quantity += quantity
                cart_item.save()
            except CartItem.DoesNotExist:
                # ایجاد آیتم جدید
                cart_item = CartItem.objects.create(
                    cart=cart,
                    product=product,
                    variant=variant,
                    quantity=quantity,
                    unit_price=unit_price
                )
            
            # به‌روزرسانی زمان سبد خرید
            cart.save()
            
            return Response(CartItemSerializer(cart_item).data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def update_item(self, request, pk=None):
        cart = self.get_object()
        item_id = request.data.get('item_id')
        quantity = request.data.get('quantity')
        
        if not item_id or not quantity or int(quantity) < 1:
            return Response({'error': 'آیتم یا تعداد نامعتبر است'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            cart_item = CartItem.objects.get(cart=cart, id=item_id)
        except CartItem.DoesNotExist:
            return Response({'error': 'آیتم در سبد خرید یافت نشد'}, status=status.HTTP_404_NOT_FOUND)
        
        # بررسی موجودی
        if cart_item.variant:
            if cart_item.variant.stock < int(quantity):
                return Response({'error': 'موجودی کافی نیست'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            if cart_item.product.stock < int(quantity):
                return Response({'error': 'موجودی کافی نیست'}, status=status.HTTP_400_BAD_REQUEST)
        
        # به‌روزرسانی تعداد
        cart_item.quantity = int(quantity)
        cart_item.save()
        
        # به‌روزرسانی زمان سبد خرید
        cart.save()
        
        return Response(CartItemSerializer(cart_item).data)
    
    @action(detail=True, methods=['post'])
    def remove_item(self, request, pk=None):
        cart = self.get_object()
        item_id = request.data.get('item_id')
        
        if not item_id:
            return Response({'error': 'آیتم نامعتبر است'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            cart_item = CartItem.objects.get(cart=cart, id=item_id)
        except CartItem.DoesNotExist:
            return Response({'error': 'آیتم در سبد خرید یافت نشد'}, status=status.HTTP_404_NOT_FOUND)
        
        cart_item.delete()
        
        # به‌روزرسانی زمان سبد خرید
        cart.save()
        
        return Response({'status': 'آیتم با موفقیت حذف شد'})
    
    @action(detail=True, methods=['post'])
    def clear(self, request, pk=None):
        cart = self.get_object()
        cart.items.all().delete()
        
        # به‌روزرسانی زمان سبد خرید
        cart.save()
        
        return Response({'status': 'سبد خرید با موفقیت خالی شد'})
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        cart = Cart.objects.filter(user=request.user, status=CartStatus.OPEN).first()
        if cart:
            serializer = self.get_serializer(cart)
            return Response(serializer.data)
        else:
            # ایجاد سبد خرید جدید
            cart = Cart.objects.create(user=request.user)
            serializer = self.get_serializer(cart)
            return Response(serializer.data)


class CheckoutView(generics.GenericAPIView):
    serializer_class = CheckoutSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        
        # ایجاد پاسخ مناسب بر اساس روش پرداخت
        payment_method = serializer.validated_data['payment_method']
        
        if payment_method == 'online':
            # ارسال به درگاه پرداخت
            payment_url = self._get_payment_url(order)
            return Response({'order_id': order.id, 'payment_url': payment_url})
        elif payment_method == 'wallet':
            # پرداخت با کیف پول
            result = self._process_wallet_payment(order, request.user)
            if result['success']:
                return Response({
                    'order_id': order.id,
                    'status': 'پرداخت با موفقیت انجام شد',
                    'redirect_url': f'/orders/{order.id}'
                })
            else:
                return Response({'error': result['message']}, status=status.HTTP_400_BAD_REQUEST)
        elif payment_method == 'installment':
            # ایجاد طرح اقساطی
            installment_plan = self._create_installment_plan(order)
            return Response({
                'order_id': order.id,
                'installment_plan_id': installment_plan.id,
                'redirect_url': f'/orders/{order.id}/installment-plan'
            })
        else:  # COD - پرداخت در محل
            return Response({
                'order_id': order.id,
                'status': 'سفارش با موفقیت ثبت شد',
                'redirect_url': f'/orders/{order.id}'
            })
    
    def _get_payment_url(self, order):
        # در اینجا کد اتصال به درگاه پرداخت و دریافت URL پرداخت قرار می‌گیرد
        return f'/payments/process/{order.id}'
    
    def _process_wallet_payment(self, order, user):
        # بررسی موجودی کیف پول
        from apps.wallet.models import Wallet
        try:
            wallet = Wallet.objects.get(user=user)
            if wallet.balance >= order.final_price:
                # کسر از موجودی کیف پول
                wallet.balance -= order.final_price
                wallet.save()
                
                # به‌روزرسانی وضعیت سفارش
                order.status = OrderStatus.PAID
                order.payment_date = timezone.now()
                order.payment_ref_id = f"WALLET-{uuid.uuid4().hex[:8]}"
                order.save()
                
                # به‌روزرسانی وضعیت آیتم‌های سفارش
                order.items.update(status=OrderStatus.PROCESSING)
                
                # ثبت در تاریخچه سفارش
                OrderHistory.objects.create(
                    order=order,
                    status=OrderStatus.PAID,
                    description='پرداخت از طریق کیف پول انجام شد',
                    created_by=user
                )
                
                # به‌روزرسانی فاکتور
                invoice = order.invoice
                invoice.is_paid = True
                invoice.payment_date = timezone.now()
                invoice.save()
                
                # به‌روزرسانی موجودی محصولات
                self._update_product_inventory(order)
                
                return {'success': True}
            else:
                return {'success': False, 'message': 'موجودی کیف پول کافی نیست'}
        except Wallet.DoesNotExist:
            return {'success': False, 'message': 'کیف پول شما فعال نیست'}
    
    def _create_installment_plan(self, order):
        # ایجاد طرح اقساطی با پیش‌فرض‌های مناسب
        down_payment = order.final_price * 0.3  # 30% پیش پرداخت
        remaining = order.final_price - down_payment
        num_installments = 3  # تعداد اقساط
        installment_amount = remaining / num_installments
        
        plan = InstallmentPlan.objects.create(
            order=order,
            total_amount=order.final_price,
            down_payment=down_payment,
            number_of_installments=num_installments,
            installment_amount=installment_amount,
            start_date=timezone.now().date(),
            status='active'
        )
        
        # ایجاد اقساط
        for i in range(num_installments):
            due_date = timezone.now().date() + timezone.timedelta(days=30 * (i + 1))
            Installment.objects.create(
                plan=plan,
                amount=installment_amount,
                due_date=due_date
            )
        
        return plan
    
    def _update_product_inventory(self, order):
        # به‌روزرسانی موجودی محصولات
        for item in order.items.all():
            if item.variant:
                variant = item.variant
                variant.stock -= item.quantity
                variant.save()
                
                # ثبت لاگ تغییر موجودی
                from apps.products.models import ProductInventoryLog
                ProductInventoryLog.objects.create(
                    product=item.product,
                    variant=variant,
                    previous_stock=variant.stock + item.quantity,
                    new_stock=variant.stock,
                    change_reason=f'فروش - سفارش {order.order_number}',
                    reference=str(order.id)
                )
            else:
                product = item.product
                product.stock -= item.quantity
                product.save()
                
                # ثبت لاگ تغییر موجودی
                from apps.products.models import ProductInventoryLog
                ProductInventoryLog.objects.create(
                    product=product,
                    previous_stock=product.stock + item.quantity,
                    new_stock=product.stock,
                    change_reason=f'فروش - سفارش {order.order_number}',
                    reference=str(order.id)
                )
            
            # به‌روزرسانی تعداد فروش محصول
            product = item.product
            product.sales_count += item.quantity
            product.save()
            
            # به‌روزرسانی آمار فروشنده
            seller = item.seller
            seller.sales_count += item.quantity
            seller.total_revenue += item.total_price
            
            # محاسبه کمیسیون
            commission = 0
            if seller.commission_type == 'fixed':
                commission = seller.commission_value
            elif seller.commission_type == 'percentage':
                commission = item.total_price * (seller.commission_value / 100)
            elif seller.commission_type == 'tiered':
                # محاسبه کمیسیون پلکانی بر اساس میزان فروش
                from apps.sellers.models import TieredCommission
                tiered_commission = TieredCommission.objects.filter(
                    seller=seller,
                    min_sales__lte=seller.total_revenue
                ).filter(
                    Q(max_sales__gte=seller.total_revenue) | Q(max_sales__isnull=True)
                ).first()
                
                if tiered_commission:
                    commission = item.total_price * (tiered_commission.commission_percentage / 100)
                else:
                    commission = item.total_price * (seller.commission_value / 100)
            
            # ذخیره کمیسیون در آیتم سفارش
            item.commission = commission
            item.save()
            
            # به‌روزرسانی موجودی فروشنده (درآمد منهای کمیسیون)
            seller.balance += (item.total_price - commission)
            seller.save()


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OrderListSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).order_by('-created_at')
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return OrderDetailSerializer
        return OrderListSerializer
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        order = self.get_object()
        
        # بررسی امکان لغو سفارش
        if order.status not in [OrderStatus.PENDING, OrderStatus.PAID]:
            return Response(
                {'error': 'این سفارش قابل لغو نیست'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            # به‌روزرسانی وضعیت سفارش
            order.status = OrderStatus.CANCELLED
            order.save()
            
            # به‌روزرسانی وضعیت آیتم‌های سفارش
            order.items.update(status=OrderStatus.CANCELLED)
            
            # ثبت در تاریخچه سفارش
            reason = request.data.get('reason', 'لغو توسط مشتری')
            OrderHistory.objects.create(
                order=order,
                status=OrderStatus.CANCELLED,
                description=reason,
                created_by=request.user
            )
            
            # اگر سفارش پرداخت شده بود، برگشت وجه
            if order.payment_method == 'wallet' and order.payment_date:
                from apps.wallet.models import Wallet, WalletTransaction
                wallet = Wallet.objects.get(user=request.user)
                wallet.balance += order.final_price
                wallet.save()
                
                # ثبت تراکنش کیف پول
                WalletTransaction.objects.create(
                    wallet=wallet,
                    amount=order.final_price,
                    transaction_type='refund',
                    description=f'برگشت وجه سفارش {order.order_number}',
                    reference_id=str(order.id)
                )
            
            # برگشت موجودی محصولات
            for item in order.items.all():
                if item.variant:
                    variant = item.variant
                    variant.stock += item.quantity
                    variant.save()
                    
                    # ثبت لاگ تغییر موجودی
                    from apps.products.models import ProductInventoryLog
                    ProductInventoryLog.objects.create(
                        product=item.product,
                        variant=variant,
                        previous_stock=variant.stock - item.quantity,
                        new_stock=variant.stock,
                        change_reason=f'لغو سفارش {order.order_number}',
                        reference=str(order.id)
                    )
                else:
                    product = item.product
                    product.stock += item.quantity
                    product.save()
                    
                    # ثبت لاگ تغییر موجودی
                    from apps.products.models import ProductInventoryLog
                    ProductInventoryLog.objects.create(
                        product=product,
                        previous_stock=product.stock - item.quantity,
                        new_stock=product.stock,
                        change_reason=f'لغو سفارش {order.order_number}',
                        reference=str(order.id)
                    )
                
                # به‌روزرسانی تعداد فروش محصول
                product = item.product
                product.sales_count -= item.quantity
                product.save()
                
                # به‌روزرسانی آمار فروشنده
                seller = item.seller
                seller.sales_count -= item.quantity
                seller.total_revenue -= item.total_price
                
                # برگشت کمیسیون و درآمد
                seller.balance -= (item.total_price - item.commission)
                seller.save()
        
        return Response({'status': 'سفارش با موفقیت لغو شد'})
    
    @action(detail=True, methods=['get'])
    def track(self, request, pk=None):
        order = self.get_object()
        
        tracking_info = {
            'order_number': order.order_number,
            'status': order.status,
            'status_display': order.get_status_display(),
            'tracking_code': order.tracking_code,
            'history': OrderHistorySerializer(order.history.all(), many=True).data
        }
        
        return Response(tracking_info)


class OrderReturnViewSet(viewsets.ModelViewSet):
    serializer_class = OrderReturnSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return OrderReturn.objects.filter(user=self.request.user).order_by('-created_at')
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class AdminOrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all().order_by('-created_at')
    serializer_class = OrderDetailSerializer
    permission_classes = [IsAdminUser]
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        order = self.get_object()
        new_status = request.data.get('status')
        description = request.data.get('description', '')
        
        if new_status not in dict(OrderStatus.choices).keys():
            return Response({'error': 'وضعیت نامعتبر است'}, status=status.HTTP_400_BAD_REQUEST)
        
        with transaction.atomic():
            # به‌روزرسانی وضعیت سفارش
            order.status = new_status
            order.save()
            
            # به‌روزرسانی وضعیت آیتم‌های سفارش
            order.items.update(status=new_status)
            
            # ثبت در تاریخچه سفارش
            OrderHistory.objects.create(
                order=order,
                status=new_status,
                description=description,
                created_by=request.user
            )
            
            # اگر وضعیت "تحویل داده شده" باشد، افزایش امتیاز وفاداری
            if new_status == OrderStatus.DELIVERED:
                user_profile = order.user.profile
                loyalty_points = int(order.final_price / 10000)  # هر 10 هزار تومان 1 امتیاز
                user_profile.loyalty_points += loyalty_points
                user_profile.save()
        
        return Response({'status': 'وضعیت سفارش با موفقیت به‌روزرسانی شد'})
    
    @action(detail=True, methods=['post'])
    def update_tracking(self, request, pk=None):
        order = self.get_object()
        tracking_code = request.data.get('tracking_code')
        
        if not tracking_code:
            return Response({'error': 'کد پیگیری الزامی است'}, status=status.HTTP_400_BAD_REQUEST)
        
        order.tracking_code = tracking_code
        order.save()
        
        # ثبت در تاریخچه سفارش
        OrderHistory.objects.create(
            order=order,
            status=order.status,
            description=f'کد پیگیری به {tracking_code} تغییر یافت',
            created_by=request.user
        )
        
        return Response({'status': 'کد پیگیری با موفقیت به‌روزرسانی شد'})


class AdminOrderReturnViewSet(viewsets.ModelViewSet):
    queryset = OrderReturn.objects.all().order_by('-created_at')
    serializer_class = OrderReturnSerializer
    permission_classes = [IsAdminUser]
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        order_return = self.get_object()
        new_status = request.data.get('status')
        admin_note = request.data.get('admin_note', '')
        
        valid_statuses = ['pending', 'approved', 'rejected', 'returned', 'refunded']
        if new_status not in valid_statuses:
            return Response({'error': 'وضعیت نامعتبر است'}, status=status.HTTP_400_BAD_REQUEST)
        
        with transaction.atomic():
            # به‌روزرسانی وضعیت مرجوعی
            order_return.status = new_status
            order_return.admin_note = admin_note
            order_return.save()
            
            # اگر وضعیت "تایید شده" باشد، به‌روزرسانی موجودی محصول
            if new_status == 'approved':
                order_item = order_return.order_item
                
                if order_item.variant:
                    variant = order_item.variant
                    variant.stock += order_return.quantity
                    variant.save()
                    
                    # ثبت لاگ تغییر موجودی
                    from apps.products.models import ProductInventoryLog
                    ProductInventoryLog.objects.create(
                        product=order_item.product,
                        variant=variant,
                        previous_stock=variant.stock - order_return.quantity,
                        new_stock=variant.stock,
                        change_reason=f'مرجوعی سفارش {order_item.order.order_number}',
                        reference=str(order_return.id)
                    )
                else:
                    product = order_item.product
                    product.stock += order_return.quantity
                    product.save()
                    
                    # ثبت لاگ تغییر موجودی
                    from apps.products.models import ProductInventoryLog
                    ProductInventoryLog.objects.create(
                        product=product,
                        previous_stock=product.stock - order_return.quantity,
                        new_stock=product.stock,
                        change_reason=f'مرجوعی سفارش {order_item.order.order_number}',
                        reference=str(order_return.id)
                    )
            
            # اگر وضعیت "مسترد شده" باشد، برگشت وجه به کاربر
            if new_status == 'refunded':
                order_item = order_return.order_item
                refund_amount = order_item.final_price * order_return.quantity
                
                # برگشت وجه به کیف پول کاربر
                from apps.wallet.models import Wallet, WalletTransaction
                wallet, created = Wallet.objects.get_or_create(user=order_return.user)
                wallet.balance += refund_amount
                wallet.save()
                
                # ثبت تراکنش کیف پول
                WalletTransaction.objects.create(
                    wallet=wallet,
                    amount=refund_amount,
                    transaction_type='refund',
                    description=f'برگشت وجه مرجوعی سفارش {order_item.order.order_number}',
                    reference_id=str(order_return.id)
                )
                
                # کسر از موجودی فروشنده
                seller = order_item.seller
                seller.balance -= refund_amount
                seller.save()
        
        return Response({'status': 'وضعیت مرجوعی با موفقیت به‌روزرسانی شد'})