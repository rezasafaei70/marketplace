from rest_framework import viewsets, permissions, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
import uuid

from .models import Wallet, WalletTransaction, WalletTransfer, TransactionType, TransactionStatus
from .serializers import (
    WalletSerializer, WalletTransactionSerializer, WalletTransferSerializer,
    TransferRequestSerializer, WithdrawalRequestSerializer
)
from apps.sellers.permissions import IsAdminUser


class WalletViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = WalletSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Wallet.objects.filter(user=self.request.user)
    
    def get_object(self):
        # ایجاد کیف پول در صورت عدم وجود
        wallet, created = Wallet.objects.get_or_create(user=self.request.user)
        return wallet
    
    @action(detail=False, methods=['get'])
    def balance(self, request):
        wallet = self.get_object()
        return Response({'balance': wallet.balance})
    
    @action(detail=False, methods=['get'])
    def transactions(self, request):
        wallet = self.get_object()
        transactions = wallet.transactions.all().order_by('-created_at')
        
        # فیلتر بر اساس نوع تراکنش
        transaction_type = request.query_params.get('type')
        if transaction_type:
            transactions = transactions.filter(transaction_type=transaction_type)
        
        # فیلتر بر اساس وضعیت
        status = request.query_params.get('status')
        if status:
            transactions = transactions.filter(status=status)
        
        # فیلتر بر اساس تاریخ
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            transactions = transactions.filter(created_at__gte=start_date)
        if end_date:
            transactions = transactions.filter(created_at__lte=end_date)
        
        # صفحه‌بندی
        page = self.paginate_queryset(transactions)
        if page is not None:
            serializer = WalletTransactionSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = WalletTransactionSerializer(transactions, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def transfers(self, request):
        wallet = self.get_object()
        transfers = WalletTransfer.objects.filter(
            sender=wallet
        ) | WalletTransfer.objects.filter(
            receiver=wallet
        )
        transfers = transfers.order_by('-created_at')
        
        # صفحه‌بندی
        page = self.paginate_queryset(transfers)
        if page is not None:
            serializer = WalletTransferSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = WalletTransferSerializer(transfers, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def transfer(self, request):
        serializer = TransferRequestSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            transfer = serializer.save()
            return Response(WalletTransferSerializer(transfer).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def withdraw(self, request):
        serializer = WithdrawalRequestSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            transaction = serializer.save()
            return Response(WalletTransactionSerializer(transaction).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        wallet = self.get_object()
        
        # محاسبه مجموع تراکنش‌ها بر اساس نوع
        deposits = wallet.transactions.filter(
            transaction_type=TransactionType.DEPOSIT,
            status=TransactionStatus.COMPLETED
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        withdrawals = wallet.transactions.filter(
            transaction_type=TransactionType.WITHDRAWAL,
            status=TransactionStatus.COMPLETED
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        payments = wallet.transactions.filter(
            transaction_type=TransactionType.PAYMENT,
            status=TransactionStatus.COMPLETED
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        refunds = wallet.transactions.filter(
            transaction_type=TransactionType.REFUND,
            status=TransactionStatus.COMPLETED
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # محاسبه تعداد تراکنش‌ها
        transaction_count = wallet.transactions.count()
        
        # محاسبه تراکنش‌های اخیر
        recent_transactions = wallet.transactions.order_by('-created_at')[:5]
        
        return Response({
            'balance': wallet.balance,
            'deposits': deposits,
            'withdrawals': withdrawals,
            'payments': payments,
            'refunds': refunds,
            'transaction_count': transaction_count,
            'recent_transactions': WalletTransactionSerializer(recent_transactions, many=True).data
        })


class AdminWalletViewSet(viewsets.ModelViewSet):
    queryset = Wallet.objects.all()
    serializer_class = WalletSerializer
    permission_classes = [IsAdminUser]
    
    @action(detail=True, methods=['post'])
    def adjust_balance(self, request, pk=None):
        wallet = self.get_object()
        amount = request.data.get('amount')
        reason = request.data.get('reason', 'تنظیم توسط مدیر')
        
        if not amount:
            return Response({'error': 'مبلغ الزامی است'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            amount = int(amount)
        except ValueError:
            return Response({'error': 'مبلغ باید عددی باشد'}, status=status.HTTP_400_BAD_REQUEST)
        
        with transaction.atomic():
            # به‌روزرسانی موجودی کیف پول
            previous_balance = wallet.balance
            wallet.balance += amount
            wallet.save()
            
            # ثبت تراکنش
            if amount > 0:
                transaction_type = TransactionType.DEPOSIT
                description = f"افزایش موجودی توسط مدیر: {reason}"
            else:
                transaction_type = TransactionType.WITHDRAWAL
                description = f"کاهش موجودی توسط مدیر: {reason}"
                amount = abs(amount)
            
            WalletTransaction.objects.create(
                wallet=wallet,
                amount=amount,
                transaction_type=transaction_type,
                status=TransactionStatus.COMPLETED,
                description=description,
                reference_id=f"ADMIN-{uuid.uuid4().hex[:8]}"
            )
        
        return Response({
            'status': 'موجودی با موفقیت تنظیم شد',
            'previous_balance': previous_balance,
            'new_balance': wallet.balance,
            'change': amount
        })
    
    @action(detail=True, methods=['post'])
    def process_withdrawal(self, request, pk=None):
        wallet = self.get_object()
        transaction_id = request.data.get('transaction_id')
        action = request.data.get('action')  # 'approve' یا 'reject'
        note = request.data.get('note', '')
        
        if not transaction_id or not action:
            return Response({'error': 'شناسه تراکنش و عملیات الزامی هستند'}, status=status.HTTP_400_BAD_REQUEST)
        
        if action not in ['approve', 'reject']:
            return Response({'error': 'عملیات باید یکی از مقادیر "approve" یا "reject" باشد'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            transaction = WalletTransaction.objects.get(
                id=transaction_id,
                wallet=wallet,
                transaction_type=TransactionType.WITHDRAWAL,
                status=TransactionStatus.PENDING
            )
        except WalletTransaction.DoesNotExist:
            return Response({'error': 'تراکنش مورد نظر یافت نشد'}, status=status.HTTP_404_NOT_FOUND)
        
        with transaction.atomic():
            if action == 'approve':
                # تایید برداشت
                transaction.status = TransactionStatus.COMPLETED
                transaction.description += f" | تایید شده: {note}"
                transaction.save()
                
                return Response({'status': 'درخواست برداشت با موفقیت تایید شد'})
            else:
                # رد برداشت و برگشت وجه
                transaction.status = TransactionStatus.CANCELLED
                transaction.description += f" | رد شده: {note}"
                transaction.save()
                
                # برگشت وجه به کیف پول
                wallet.balance += transaction.amount
                wallet.save()
                
                # ثبت تراکنش برگشت وجه
                WalletTransaction.objects.create(
                    wallet=wallet,
                    amount=transaction.amount,
                    transaction_type=TransactionType.DEPOSIT,
                    status=TransactionStatus.COMPLETED,
                    description=f"برگشت وجه برداشت رد شده: {note}",
                    reference_id=str(transaction.id)
                )
                
                return Response({'status': 'درخواست برداشت رد شد و وجه به کیف پول برگشت داده شد'})


class AdminWalletTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = WalletTransaction.objects.all().order_by('-created_at')
    serializer_class = WalletTransactionSerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # فیلتر بر اساس کاربر
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(wallet__user__id=user_id)
        
        # فیلتر بر اساس نوع تراکنش
        transaction_type = self.request.query_params.get('type')
        if transaction_type:
            queryset = queryset.filter(transaction_type=transaction_type)
        
        # فیلتر بر اساس وضعیت
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # فیلتر بر اساس تاریخ
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        
        return queryset


class AdminWalletTransferViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = WalletTransfer.objects.all().order_by('-created_at')
    serializer_class = WalletTransferSerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # فیلتر بر اساس فرستنده
        sender_id = self.request.query_params.get('sender_id')
        if sender_id:
            queryset = queryset.filter(sender__user__id=sender_id)
        
        # فیلتر بر اساس گیرنده
        receiver_id = self.request.query_params.get('receiver_id')
        if receiver_id:
            queryset = queryset.filter(receiver__user__id=receiver_id)
        
        # فیلتر بر اساس تاریخ
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        
        return queryset