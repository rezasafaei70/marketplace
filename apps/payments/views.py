from rest_framework import viewsets, permissions, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.utils import timezone
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
import uuid
import json
import requests
import logging

from .models import PaymentGateway, Payment, PaymentLog, PaymentStatus
from .serializers import (
    PaymentGatewaySerializer, PaymentSerializer, PaymentInitSerializer,
    PaymentCallbackSerializer
)
from apps.sellers.permissions import IsAdminUser

logger = logging.getLogger(__name__)


class PaymentGatewayViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PaymentGateway.objects.filter(is_active=True)
    serializer_class = PaymentGatewaySerializer
    permission_classes = [permissions.IsAuthenticated]


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user).order_by('-created_at')


class PaymentInitView(generics.GenericAPIView):
    serializer_class = PaymentInitSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        order = serializer.validated_data.get('order')
        installment = serializer.validated_data.get('installment')
        wallet_amount = serializer.validated_data.get('wallet_amount')
        gateway = serializer.validated_data['gateway']
        amount = serializer.validated_data['amount']
        return_url = serializer.validated_data['return_url']
        
        # ایجاد رکورد پرداخت
        payment = Payment.objects.create(
            user=request.user,
            order=order,
            installment=installment,
            gateway=gateway,
            amount=amount,
            description='پرداخت آنلاین'
        )
        
        # اگر شارژ کیف پول است، ایجاد تراکنش کیف پول
        if wallet_amount:
            from apps.wallet.models import Wallet, WalletTransaction
            wallet, created = Wallet.objects.get_or_create(user=request.user)
            wallet_transaction = WalletTransaction.objects.create(
                wallet=wallet,
                amount=wallet_amount,
                transaction_type='deposit',
                description='شارژ کیف پول',
                status='pending',
                reference_id=str(payment.id)
            )
            payment.wallet_transaction = wallet_transaction
            payment.save()
        
        # ثبت لاگ پرداخت
        PaymentLog.objects.create(
            payment=payment,
            status=PaymentStatus.PENDING,
            description='درخواست پرداخت ایجاد شد'
        )
        
        # فراخوانی API درگاه پرداخت بر اساس نوع درگاه
        gateway_response = None
        
        try:
            if gateway.code == 'zarinpal':
                gateway_response = self._init_zarinpal_payment(payment, return_url)
            elif gateway.code == 'payir':
                gateway_response = self._init_payir_payment(payment, return_url)
            else:
                return Response(
                    {'error': 'درگاه پرداخت پشتیبانی نمی‌شود'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if gateway_response.get('success'):
                # به‌روزرسانی اطلاعات پرداخت
                payment.reference_id = gateway_response.get('reference_id')
                payment.meta_data = gateway_response.get('meta_data', {})
                payment.save()
                
                # ثبت لاگ پرداخت
                PaymentLog.objects.create(
                    payment=payment,
                    status=PaymentStatus.PENDING,
                    description='درخواست پرداخت به درگاه ارسال شد',
                    meta_data=gateway_response.get('meta_data', {})
                )
                
                return Response({
                    'payment_id': payment.id,
                    'redirect_url': gateway_response.get('redirect_url')
                })
            else:
                # ثبت لاگ خطا
                PaymentLog.objects.create(
                    payment=payment,
                    status=PaymentStatus.FAILED,
                    description=f"خطا در اتصال به درگاه: {gateway_response.get('error')}",
                    meta_data=gateway_response.get('meta_data', {})
                )
                
                return Response(
                    {'error': gateway_response.get('error', 'خطا در اتصال به درگاه پرداخت')},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        except Exception as e:
            logger.error(f"Payment gateway error: {str(e)}")
            
            # ثبت لاگ خطا
            PaymentLog.objects.create(
                payment=payment,
                status=PaymentStatus.FAILED,
                description=f"خطا در اتصال به درگاه: {str(e)}"
            )
            
            return Response(
                {'error': 'خطا در اتصال به درگاه پرداخت'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _init_zarinpal_payment(self, payment, return_url):
        # تنظیمات درگاه زرین‌پال
        merchant_id = payment.gateway.config.get('merchant_id')
        zarinpal_url = "https://api.zarinpal.com/pg/v4/payment/request.json"
        
        callback_url = f"{return_url}?payment_id={payment.id}"
        
        # آماده‌سازی داده‌های ارسال به درگاه
        data = {
            "merchant_id": merchant_id,
            "amount": int(payment.amount),
            "currency": "IRT",  # تومان
            "description": payment.description,
            "callback_url": callback_url,
            "metadata": {
                "mobile": payment.user.phone_number,
                "email": payment.user.email or ""
            }
        }
        
        # ارسال درخواست به درگاه
        try:
            response = requests.post(zarinpal_url, json=data, timeout=10)
            result = response.json()
            
            if response.status_code == 200 and result.get('data', {}).get('code') == 100:
                authority = result['data']['authority']
                redirect_url = f"https://www.zarinpal.com/pg/StartPay/{authority}"
                
                return {
                    'success': True,
                    'reference_id': authority,
                    'redirect_url': redirect_url,
                    'meta_data': result
                }
            else:
                return {
                    'success': False,
                    'error': f"خطای زرین‌پال: {result.get('errors', {}).get('message', 'خطای نامشخص')}",
                    'meta_data': result
                }
        
        except Exception as e:
            return {
                'success': False,
                'error': f"خطا در ارتباط با زرین‌پال: {str(e)}"
            }
    
    def _init_payir_payment(self, payment, return_url):
        # تنظیمات درگاه pay.ir
        api_key = payment.gateway.config.get('api_key')
        payir_url = "https://pay.ir/pg/send"
        
        callback_url = f"{return_url}?payment_id={payment.id}"
        
        # آماده‌سازی داده‌های ارسال به درگاه
        data = {
            "api": api_key,
            "amount": int(payment.amount),
            "redirect": callback_url,
            "factorNumber": str(payment.id)[:8],
            "mobile": payment.user.phone_number,
            "description": payment.description
        }
        
        # ارسال درخواست به درگاه
        try:
            response = requests.post(payir_url, data=data, timeout=10)
            result = response.json()
            
            if response.status_code == 200 and result.get('status') == 1:
                token = result['token']
                redirect_url = f"https://pay.ir/pg/{token}"
                
                return {
                    'success': True,
                    'reference_id': token,
                    'redirect_url': redirect_url,
                    'meta_data': result
                }
            else:
                return {
                    'success': False,
                    'error': f"خطای pay.ir: {result.get('errorMessage', 'خطای نامشخص')}",
                    'meta_data': result
                }
        
        except Exception as e:
            return {
                'success': False,
                'error': f"خطا در ارتباط با pay.ir: {str(e)}"
            }


class PaymentCallbackView(generics.GenericAPIView):
    serializer_class = PaymentCallbackSerializer
    permission_classes = [permissions.AllowAny]  # درگاه پرداخت به این آدرس دسترسی دارد
    
    def get(self, request, *args, **kwargs):
        payment_id = request.query_params.get('payment_id')
        
        if not payment_id:
            return Response({'error': 'شناسه پرداخت الزامی است'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            payment = Payment.objects.get(id=payment_id)
        except Payment.DoesNotExist:
            return Response({'error': 'پرداخت یافت نشد'}, status=status.HTTP_404_NOT_FOUND)
        
        # بررسی نتیجه پرداخت بر اساس نوع درگاه
        verification_result = None
        
        try:
            if payment.gateway.code == 'zarinpal':
                verification_result = self._verify_zarinpal_payment(payment, request)
            elif payment.gateway.code == 'payir':
                verification_result = self._verify_payir_payment(payment, request)
            else:
                # ثبت لاگ خطا
                PaymentLog.objects.create(
                    payment=payment,
                    status=PaymentStatus.FAILED,
                    description='درگاه پرداخت پشتیبانی نمی‌شود'
                )
                
                return redirect(f"/payment/result?status=error&message=درگاه پرداخت پشتیبانی نمی‌شود")
            
            if verification_result.get('success'):
                # پرداخت موفق
                with transaction.atomic():
                    # به‌روزرسانی اطلاعات پرداخت
                    payment.status = PaymentStatus.COMPLETED
                    payment.payment_date = timezone.now()
                    payment.tracking_code = verification_result.get('tracking_code')
                    payment.transaction_id = verification_result.get('transaction_id')
                    payment.meta_data = verification_result.get('meta_data', {})
                    payment.save()
                    
                    # ثبت لاگ پرداخت
                    PaymentLog.objects.create(
                        payment=payment,
                        status=PaymentStatus.COMPLETED,
                        description='پرداخت با موفقیت انجام شد',
                        meta_data=verification_result.get('meta_data', {})
                    )
                    
                    # به‌روزرسانی وضعیت سفارش یا قسط یا کیف پول
                    if payment.order:
                        self._update_order_status(payment)
                    elif payment.installment:
                        self._update_installment_status(payment)
                    elif payment.wallet_transaction:
                        self._update_wallet_transaction(payment)
                
                return redirect(f"/payment/result?status=success&payment_id={payment.id}")
            else:
                # پرداخت ناموفق
                payment.status = PaymentStatus.FAILED
                payment.meta_data = verification_result.get('meta_data', {})
                payment.save()
                
                # ثبت لاگ پرداخت
                PaymentLog.objects.create(
                    payment=payment,
                    status=PaymentStatus.FAILED,
                    description=f"پرداخت ناموفق: {verification_result.get('error')}",
                    meta_data=verification_result.get('meta_data', {})
                )
                
                return redirect(f"/payment/result?status=error&message={verification_result.get('error')}")
        
        except Exception as e:
            logger.error(f"Payment verification error: {str(e)}")
            
            # ثبت لاگ خطا
            PaymentLog.objects.create(
                payment=payment,
                status=PaymentStatus.FAILED,
                description=f"خطا در تایید پرداخت: {str(e)}"
            )
            
            return redirect(f"/payment/result?status=error&message=خطا در تایید پرداخت")
    
    def _verify_zarinpal_payment(self, payment, request):
        authority = request.query_params.get('Authority')
        status = request.query_params.get('Status')
        
        if not authority or status != 'OK':
            return {
                'success': False,
                'error': 'پرداخت توسط کاربر لغو شد',
                'meta_data': {'authority': authority, 'status': status}
            }
        
        # تنظیمات درگاه زرین‌پال
        merchant_id = payment.gateway.config.get('merchant_id')
        verify_url = "https://api.zarinpal.com/pg/v4/payment/verify.json"
        
        # آماده‌سازی داده‌های تایید پرداخت
        data = {
            "merchant_id": merchant_id,
            "authority": authority,
            "amount": int(payment.amount)
        }
        
        # ارسال درخواست تایید به درگاه
        try:
            response = requests.post(verify_url, json=data, timeout=10)
            result = response.json()
            
            if response.status_code == 200 and result.get('data', {}).get('code') == 100:
                ref_id = result['data']['ref_id']
                
                return {
                    'success': True,
                    'tracking_code': authority,
                    'transaction_id': ref_id,
                    'meta_data': result
                }
            else:
                return {
                    'success': False,
                    'error': f"خطای تایید زرین‌پال: {result.get('errors', {}).get('message', 'خطای نامشخص')}",
                    'meta_data': result
                }
        
        except Exception as e:
            return {
                'success': False,
                'error': f"خطا در ارتباط با زرین‌پال: {str(e)}"
            }
    
    def _verify_payir_payment(self, payment, request):
        token = request.query_params.get('token')
        status = request.query_params.get('status')
        
        if not token or status != '1':
            return {
                'success': False,
                'error': 'پرداخت توسط کاربر لغو شد',
                'meta_data': {'token': token, 'status': status}
            }
        
        # تنظیمات درگاه pay.ir
        api_key = payment.gateway.config.get('api_key')
        verify_url = "https://pay.ir/pg/verify"
        
        # آماده‌سازی داده‌های تایید پرداخت
        data = {
            "api": api_key,
            "token": token
        }
        
        # ارسال درخواست تایید به درگاه
        try:
            response = requests.post(verify_url, data=data, timeout=10)
            result = response.json()
            
            if response.status_code == 200 and result.get('status') == 1:
                transaction_id = result['transId']
                
                return {
                    'success': True,
                    'tracking_code': token,
                    'transaction_id': transaction_id,
                    'meta_data': result
                }
            else:
                return {
                    'success': False,
                    'error': f"خطای تایید pay.ir: {result.get('errorMessage', 'خطای نامشخص')}",
                    'meta_data': result
                }
        
        except Exception as e:
            return {
                'success': False,
                'error': f"خطا در ارتباط با pay.ir: {str(e)}"
            }
    
    def _update_order_status(self, payment):
        from apps.orders.models import Order, OrderStatus, OrderHistory
        
        order = payment.order
        order.status = OrderStatus.PAID
        order.payment_date = payment.payment_date
        order.payment_ref_id = payment.transaction_id
        order.save()
        
        # به‌روزرسانی وضعیت آیتم‌های سفارش
        order.items.update(status=OrderStatus.PROCESSING)
        
        # ثبت در تاریخچه سفارش
        OrderHistory.objects.create(
            order=order,
            status=OrderStatus.PAID,
            description=f'پرداخت با موفقیت انجام شد. کد پیگیری: {payment.transaction_id}',
            created_by=payment.user
        )
        
        # به‌روزرسانی فاکتور
        invoice = order.invoice
        invoice.is_paid = True
        invoice.payment_date = payment.payment_date
        invoice.save()
        
        # به‌روزرسانی موجودی محصولات
        self._update_product_inventory(order)
    
    def _update_installment_status(self, payment):
        installment = payment.installment
        installment.is_paid = True
        installment.payment_date = payment.payment_date
        installment.payment_ref_id = payment.transaction_id
        installment.save()
        
        # بررسی وضعیت طرح اقساطی
        plan = installment.plan
        all_paid = plan.installments.filter(is_paid=False).count() == 0
        
        if all_paid:
            plan.status = 'completed'
            plan.save()
    
    def _update_wallet_transaction(self, payment):
        wallet_transaction = payment.wallet_transaction
        wallet_transaction.status = 'completed'
        wallet_transaction.reference_id = payment.transaction_id
        wallet_transaction.save()
        
        # افزایش موجودی کیف پول
        wallet = wallet_transaction.wallet
        wallet.balance += wallet_transaction.amount
        wallet.save()
    
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
                from django.db.models import Q
                
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


class AdminPaymentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Payment.objects.all().order_by('-created_at')
    serializer_class = PaymentSerializer
    permission_classes = [IsAdminUser]
    
    @action(detail=True, methods=['post'])
    def refund(self, request, pk=None):
        payment = self.get_object()
        
        if payment.status != PaymentStatus.COMPLETED:
            return Response({'error': 'فقط پرداخت‌های موفق قابل استرداد هستند'}, status=status.HTTP_400_BAD_REQUEST)
        
        reason = request.data.get('reason', 'استرداد توسط مدیر')
        
        with transaction.atomic():
            # به‌روزرسانی وضعیت پرداخت
            payment.status = PaymentStatus.REFUNDED
            payment.save()
            
            # ثبت لاگ پرداخت
            PaymentLog.objects.create(
                payment=payment,
                status=PaymentStatus.REFUNDED,
                description=f'استرداد وجه: {reason}'
            )
            
            # اگر پرداخت مربوط به سفارش است
            if payment.order:
                from apps.orders.models import OrderStatus, OrderHistory
                
                order = payment.order
                order.status = OrderStatus.REFUNDED
                order.save()
                
                # به‌روزرسانی وضعیت آیتم‌های سفارش
                order.items.update(status=OrderStatus.REFUNDED)
                
                # ثبت در تاریخچه سفارش
                OrderHistory.objects.create(
                    order=order,
                    status=OrderStatus.REFUNDED,
                    description=f'استرداد وجه: {reason}',
                    created_by=request.user
                )
                
                # برگشت وجه به کیف پول کاربر
                from apps.wallet.models import Wallet, WalletTransaction
                wallet, created = Wallet.objects.get_or_create(user=payment.user)
                wallet.balance += payment.amount
                wallet.save()
                
                # ثبت تراکنش کیف پول
                wallet_transaction = WalletTransaction.objects.create(
                    wallet=wallet,
                    amount=payment.amount,
                    transaction_type='refund',
                    description=f'استرداد وجه سفارش {order.order_number}: {reason}',
                    status='completed',
                    reference_id=str(payment.id)
                )
                
                # به‌روزرسانی فاکتور
                invoice = order.invoice
                invoice.is_paid = False
                invoice.save()
            
            # اگر پرداخت مربوط به شارژ کیف پول است
            elif payment.wallet_transaction:
                wallet_transaction = payment.wallet_transaction
                wallet = wallet_transaction.wallet
                
                # کاهش موجودی کیف پول
                wallet.balance -= payment.amount
                wallet.save()
                
                # به‌روزرسانی تراکنش کیف پول
                wallet_transaction.status = 'refunded'
                wallet_transaction.description += f' (استرداد: {reason})'
                wallet_transaction.save()
        
        return Response({'status': 'وجه با موفقیت استرداد شد'})