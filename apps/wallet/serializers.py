from rest_framework import serializers
from django.db import transaction
from .models import Wallet, WalletTransaction, WalletTransfer, TransactionType, TransactionStatus


class WalletSerializer(serializers.ModelSerializer):
    user_full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Wallet
        fields = ('id', 'user', 'user_full_name', 'balance', 'is_active', 'created_at', 'updated_at')
        read_only_fields = fields
    
    def get_user_full_name(self, obj):
        return obj.user.get_full_name()


class WalletTransactionSerializer(serializers.ModelSerializer):
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = WalletTransaction
        fields = ('id', 'wallet', 'amount', 'transaction_type', 'transaction_type_display',
                 'status', 'status_display', 'description', 'reference_id', 'created_at')
        read_only_fields = fields


class WalletTransferSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    receiver_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = WalletTransfer
        fields = ('id', 'sender', 'sender_name', 'receiver', 'receiver_name',
                 'amount', 'status', 'status_display', 'description', 'created_at')
        read_only_fields = ('id', 'sender', 'sender_name', 'status', 'status_display', 'created_at')
    
    def get_sender_name(self, obj):
        return obj.sender.user.get_full_name()
    
    def get_receiver_name(self, obj):
        return obj.receiver.user.get_full_name()


class TransferRequestSerializer(serializers.Serializer):
    receiver_id = serializers.CharField()
    amount = serializers.DecimalField(max_digits=15, decimal_places=0)
    description = serializers.CharField(required=False, allow_blank=True)
    
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('مبلغ باید بزرگتر از صفر باشد')
        return value
    
    def validate(self, data):
        receiver_id = data.get('receiver_id')
        amount = data.get('amount')
        
        # بررسی وجود کیف پول گیرنده
        try:
            receiver_wallet = Wallet.objects.get(user__id=receiver_id, is_active=True)
            data['receiver_wallet'] = receiver_wallet
        except Wallet.DoesNotExist:
            raise serializers.ValidationError('کیف پول گیرنده یافت نشد یا غیرفعال است')
        
        # بررسی کافی بودن موجودی فرستنده
        sender_wallet = self.context['request'].user.wallet
        if sender_wallet.balance < amount:
            raise serializers.ValidationError('موجودی کیف پول شما کافی نیست')
        
# اطمینان از اینکه کاربر به خودش انتقال نمی‌دهد
        if sender_wallet.user.id == receiver_wallet.user.id:
            raise serializers.ValidationError('نمی‌توانید به کیف پول خودتان انتقال دهید')
        
        data['sender_wallet'] = sender_wallet
        return data
    
    @transaction.atomic
    def create(self, validated_data):
        sender_wallet = validated_data['sender_wallet']
        receiver_wallet = validated_data['receiver_wallet']
        amount = validated_data['amount']
        description = validated_data.get('description', '')
        
        # کاهش موجودی فرستنده
        sender_wallet.balance -= amount
        sender_wallet.save()
        
        # افزایش موجودی گیرنده
        receiver_wallet.balance += amount
        receiver_wallet.save()
        
        # ثبت تراکنش برای فرستنده
        sender_transaction = WalletTransaction.objects.create(
            wallet=sender_wallet,
            amount=amount,
            transaction_type=TransactionType.TRANSFER,
            status=TransactionStatus.COMPLETED,
            description=f"انتقال به {receiver_wallet.user.get_full_name()}: {description}"
        )
        
        # ثبت تراکنش برای گیرنده
        receiver_transaction = WalletTransaction.objects.create(
            wallet=receiver_wallet,
            amount=amount,
            transaction_type=TransactionType.DEPOSIT,
            status=TransactionStatus.COMPLETED,
            description=f"دریافت از {sender_wallet.user.get_full_name()}: {description}"
        )
        
        # ثبت انتقال
        transfer = WalletTransfer.objects.create(
            sender=sender_wallet,
            receiver=receiver_wallet,
            amount=amount,
            description=description
        )
        
        return transfer


class WithdrawalRequestSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=15, decimal_places=0)
    bank_account = serializers.CharField()
    description = serializers.CharField(required=False, allow_blank=True)
    
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('مبلغ باید بزرگتر از صفر باشد')
        
        # حداقل مبلغ برداشت
        if value < 50000:
            raise serializers.ValidationError('حداقل مبلغ برداشت 50,000 تومان است')
        
        return value
    
    def validate(self, data):
        amount = data.get('amount')
        
        # بررسی کافی بودن موجودی
        wallet = self.context['request'].user.wallet
        if wallet.balance < amount:
            raise serializers.ValidationError('موجودی کیف پول شما کافی نیست')
        
        return data
    
    @transaction.atomic
    def create(self, validated_data):
        wallet = self.context['request'].user.wallet
        amount = validated_data['amount']
        bank_account = validated_data['bank_account']
        description = validated_data.get('description', '')
        
        # کاهش موجودی کیف پول
        wallet.balance -= amount
        wallet.save()
        
        # ثبت تراکنش برداشت
        transaction = WalletTransaction.objects.create(
            wallet=wallet,
            amount=amount,
            transaction_type=TransactionType.WITHDRAWAL,
            status=TransactionStatus.PENDING,
            description=f"درخواست برداشت به شماره حساب {bank_account}: {description}"
        )
        
        return transaction