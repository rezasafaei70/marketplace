from rest_framework import viewsets, permissions, status, generics, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Avg, Count
from django.db.transaction import atomic
from django_filters.rest_framework import DjangoFilterBackend
from .models import (
    Seller, SellerCategory, SellerReview, TieredCommission, SellerWithdrawal
)
from .serializers import (
    SellerListSerializer, SellerDetailSerializer, SellerRegistrationSerializer,
    SellerCategorySerializer, SellerReviewSerializer, TieredCommissionSerializer,
    SellerWithdrawalSerializer, AdminSellerUpdateSerializer, AdminSellerWithdrawalUpdateSerializer
)
from .permissions import IsSellerOwner, IsAdminUser


class IsSellerOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return hasattr(request.user, 'seller')


class SellerViewSet(viewsets.ModelViewSet):
    queryset = Seller.objects.all()
    serializer_class = SellerListSerializer
    lookup_field = 'slug'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'is_featured']
    search_fields = ['shop_name', 'description']
    ordering_fields = ['created_at', 'rating', 'sales_count']
    
    def get_permissions(self):
        if self.action == 'create':
            return [permissions.IsAuthenticated()]
        elif self.action in ['update', 'partial_update']:
            return [IsSellerOwner()]
        elif self.action == 'admin_update':
            return [IsAdminUser()]
        return [permissions.AllowAny()]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return SellerRegistrationSerializer
        elif self.action in ['retrieve', 'update', 'partial_update']:
            return SellerDetailSerializer
        elif self.action == 'admin_update':
            return AdminSellerUpdateSerializer
        return SellerListSerializer
    
    def get_queryset(self):
        queryset = Seller.objects.all()
        if self.action in ['list', 'retrieve']:
            queryset = queryset.filter(status='approved')
        return queryset
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def add_review(self, request, slug=None):
        seller = self.get_object()
        user = request.user
        
        # بررسی اینکه کاربر قبلاً نظر نداده باشد
        if SellerReview.objects.filter(seller=seller, user=user).exists():
            return Response(
                {'error': 'شما قبلاً برای این فروشنده نظر ثبت کرده‌اید'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = SellerReviewSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(seller=seller, user=user)
            
            # به‌روزرسانی امتیاز و تعداد نظرات فروشنده
            avg_rating = SellerReview.objects.filter(seller=seller).aggregate(Avg('rating'))['rating__avg'] or 0
            review_count = SellerReview.objects.filter(seller=seller).count()
            
            seller.rating = avg_rating
            seller.review_count = review_count
            seller.save()
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def reviews(self, request, slug=None):
        seller = self.get_object()
        reviews = SellerReview.objects.filter(seller=seller, is_approved=True)
        page = self.paginate_queryset(reviews)
        if page is not None:
            serializer = SellerReviewSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = SellerReviewSerializer(reviews, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'], permission_classes=[IsSellerOwner])
    def dashboard(self, request, slug=None):
        seller = self.get_object()
        
        # آمار فروش، درآمد و محصولات
        data = {
            'total_revenue': seller.total_revenue,
            'sales_count': seller.sales_count,
            'products_count': seller.products.count(),
            'balance': seller.balance,
            'rating': seller.rating,
            'review_count': seller.review_count,
            # سایر آمار مورد نیاز
        }
        
        return Response(data)
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def my_shop(self, request):
        try:
            seller = request.user.seller
            serializer = SellerDetailSerializer(seller)
            return Response(serializer.data)
        except:
            return Response({'error': 'شما هنوز فروشگاهی ندارید'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['patch'], permission_classes=[IsAdminUser])
    def admin_update(self, request, pk=None):
        seller_id = request.data.get('seller_id')
        if not seller_id:
            return Response({'error': 'شناسه فروشنده الزامی است'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            seller = Seller.objects.get(id=seller_id)
        except Seller.DoesNotExist:
            return Response({'error': 'فروشنده یافت نشد'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = AdminSellerUpdateSerializer(seller, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SellerCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = SellerCategorySerializer
    permission_classes = [IsSellerOwner]
    
    def get_queryset(self):
        return SellerCategory.objects.filter(seller=self.request.user.seller)
    
    def perform_create(self, serializer):
        serializer.save(seller=self.request.user.seller, is_approved=False)


class TieredCommissionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TieredCommissionSerializer
    permission_classes = [IsSellerOwner]
    
    def get_queryset(self):
        return TieredCommission.objects.filter(seller=self.request.user.seller)


class SellerWithdrawalViewSet(viewsets.ModelViewSet):
    serializer_class = SellerWithdrawalSerializer
    permission_classes = [IsSellerOwner]
    
    def get_queryset(self):
        return SellerWithdrawal.objects.filter(seller=self.request.user.seller)
    
    @atomic
    def perform_create(self, serializer):
        seller = self.request.user.seller
        amount = serializer.validated_data['amount']
        
        # کم کردن مبلغ از موجودی فروشنده
        seller.balance -= amount
        seller.save()
        
        serializer.save(seller=seller)
    
    @action(detail=True, methods=['patch'], permission_classes=[IsAdminUser])
    def admin_update(self, request, pk=None):
        withdrawal = self.get_object()
        serializer = AdminSellerWithdrawalUpdateSerializer(withdrawal, data=request.data, partial=True)
        
        if serializer.is_valid():
            # اگر درخواست رد شد، مبلغ به حساب فروشنده برگردانده شود
            if 'status' in request.data and request.data['status'] == 'rejected' and withdrawal.status != 'rejected':
                seller = withdrawal.seller
                seller.balance += withdrawal.amount
                seller.save()
            
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)