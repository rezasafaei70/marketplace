from rest_framework import serializers
from .models import PaymentGateway, Payment, PaymentLog


class PaymentGatewaySerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentGateway
        fields = ('id', 'name', 'code', 'description', 'is_active')


class PaymentLogSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = PaymentLog
        fields = ('id', 'status', 'status_display', 'description', 'meta_data', 'created_at')


class PaymentSerializer(serializers.ModelSerializer):
    gateway_name = serializers.CharField(source='gateway.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    logs = PaymentLogSerializer(many=True, read_only=True)
    
    class Meta:
        model = Payment
        fields = ('id', 'order', 'installment', 'wallet_transaction', 'gateway', 
                 'gateway_name', 'amount', 'status', 'status_display', 'tracking_code',
                 'reference_id', 'transaction_id', 'payment_date', 'description',
                 'meta_data', 'created_at', 'updated_at', 'logs')
        read_only_fields = fields


class PaymentInitSerializer(serializers.Serializer):
    order_id = serializers.UUIDField(required=False)
    installment_id = serializers.UUIDField(required=False)
    wallet_amount = serializers.DecimalField(required=False, max_digits=15, decimal_places=0)
    gateway_code = serializers.CharField()
    return_url = serializers.URLField()
    
    def validate(self, data):
        order_id = data.get('order_id')
        installment_id = data.get('installment_id')
        wallet_amount = data.get('wallet_amount')
        
        # حداقل یکی از موارد باید وجود داشته باشد
        if not any([order_id, installment_id, wallet_amount]):
            raise serializers.ValidationError('حداقل یکی از موارد سفارش، قسط یا شارژ کیف پول باید مشخص شود')
        
        # بررسی درگاه پرداخت
        gateway_code = data.get('gateway_code')
        try:
            gateway = PaymentGateway.objects.get(code=gateway_code, is_active=True)
            data['gateway'] = gateway
        except PaymentGateway.DoesNotExist:
            raise serializers.ValidationError('درگاه پرداخت نامعتبر است')
        
        # بررسی سفارش
        if order_id:
            from apps.orders.models import Order, OrderStatus
            try:
                order = Order.objects.get(id=order_id, status=OrderStatus.PENDING)
                data['order'] = order
                data['amount'] = order.final_price
            except Order.DoesNotExist:
                raise serializers.ValidationError('سفارش نامعتبر است یا قبلاً پرداخت شده است')
        
        # بررسی قسط
        if installment_id:
            from apps.orders.models import Installment
            try:
                installment = Installment.objects.get(id=installment_id, is_paid=False)
                data['installment'] = installment
                data['amount'] = installment.amount
            except Installment.DoesNotExist:
                raise serializers.ValidationError('قسط نامعتبر است یا قبلاً پرداخت شده است')
        
        # بررسی شارژ کیف پول
        if wallet_amount:
            if wallet_amount < 10000:
                raise serializers.ValidationError('حداقل مبلغ شارژ کیف پول 10,000 تومان است')
            data['amount'] = wallet_amount
        
        return data


class PaymentCallbackSerializer(serializers.Serializer):
    payment_id = serializers.UUIDField()
    status = serializers.CharField()
    tracking_code = serializers.CharField(required=False, allow_blank=True)
    reference_id = serializers.CharField(required=False, allow_blank=True)
    transaction_id = serializers.CharField(required=False, allow_blank=True)