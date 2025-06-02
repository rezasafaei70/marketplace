from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, F, Avg, Count, Sum
from django.db.transaction import atomic
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
import uuid

from .models import (
    Product, ProductImage, ProductAttribute, ProductVariant, ProductVariantAttribute,
    ProductTag, ProductTagRelation, ProductReview, ProductReviewImage, ProductReviewComment,
    ProductQuestion, ProductAnswer, RelatedProduct, ProductInventoryLog
)
from .serializers import (
    ProductListSerializer, ProductDetailSerializer, ProductCreateUpdateSerializer,
    ProductReviewSerializer, ProductReviewCommentSerializer, ProductQuestionSerializer,
    ProductAnswerSerializer, ProductInventoryLogSerializer, ProductTagSerializer
)
from apps.sellers.permissions import IsSellerOwner, IsAdminUser


class IsProductSellerOrReadOnly(permissions.BasePermission):
    """
    فقط فروشنده محصول می‌تواند آن را ویرایش کند
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # بررسی اینکه کاربر فروشنده محصول باشد
        if hasattr(request.user, 'seller'):
            return obj.seller == request.user.seller
        return False


class IsProductSellerOrAdmin(permissions.BasePermission):
    """
    فقط فروشنده محصول یا مدیر سیستم می‌تواند به این دسترسی داشته باشد
    """
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        
        if hasattr(request.user, 'seller'):
            return obj.seller == request.user.seller
        return False


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductListSerializer
    lookup_field = 'slug'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'seller', 'is_featured', 'is_active']
    search_fields = ['name', 'description', 'short_description', 'sku', 'meta_keywords']
    ordering_fields = ['created_at', 'price', 'rating', 'sales_count', 'view_count']
    
    def get_permissions(self):
        if self.action in ['create']:
            return [permissions.IsAuthenticated(), IsSellerOwner()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsProductSellerOrReadOnly()]
        elif self.action in ['admin_approve', 'admin_feature']:
            return [permissions.IsAuthenticated(), IsAdminUser()]
        return [permissions.AllowAny()]
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ProductDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ProductCreateUpdateSerializer
        return ProductListSerializer
    
    def get_queryset(self):
        queryset = Product.objects.all()
        
        if self.action in ['list', 'retrieve']:
            # فقط محصولات فعال و تایید شده را به کاربران عادی نمایش می‌دهیم
            if not self.request.user.is_staff and not hasattr(self.request.user, 'seller'):
                queryset = queryset.filter(is_active=True, is_approved=True)
        
        # فیلتر بر اساس قیمت
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        
        if min_price:
            queryset = queryset.filter(Q(discount_price__gte=min_price) | 
                                      (Q(discount_price__isnull=True) & Q(price__gte=min_price)))
        
        if max_price:
            queryset = queryset.filter(Q(discount_price__lte=max_price) | 
                                      (Q(discount_price__isnull=True) & Q(price__lte=max_price)))
        
        # فیلتر بر اساس برچسب
        tag = self.request.query_params.get('tag')
        if tag:
            queryset = queryset.filter(tags__tag__slug=tag)
        
        # فیلتر بر اساس موجودی
        in_stock = self.request.query_params.get('in_stock')
        if in_stock == 'true':
            queryset = queryset.filter(stock__gt=0)
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(seller=self.request.user.seller, is_approved=False)
    
    @action(detail=True, methods=['post'])
    def increment_view(self, request, slug=None):
        product = self.get_object()
        product.view_count = F('view_count') + 1
        product.save(update_fields=['view_count'])
        return Response({'status': 'view count incremented'})
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def add_review(self, request, slug=None):
        product = self.get_object()
        user = request.user
        
        # بررسی اینکه کاربر قبلاً نظر نداده باشد
        if ProductReview.objects.filter(product=product, user=user).exists():
            return Response(
                {'error': 'شما قبلاً برای این محصول نظر ثبت کرده‌اید'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = ProductReviewSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(product=product, user=user)
            
            # به‌روزرسانی امتیاز و تعداد نظرات محصول
            avg_rating = ProductReview.objects.filter(product=product).aggregate(Avg('rating'))['rating__avg'] or 0
            review_count = ProductReview.objects.filter(product=product).count()
            
            product.rating = avg_rating
            product.review_count = review_count
            product.save(update_fields=['rating', 'review_count'])
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def add_review_comment(self, request, slug=None):
        product = self.get_object()
        review_id = request.data.get('review_id')
        
        try:
            review = ProductReview.objects.get(id=review_id, product=product)
        except ProductReview.DoesNotExist:
            return Response(
                {'error': 'نظر مورد نظر یافت نشد'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = ProductReviewCommentSerializer(data=request.data)
        if serializer.is_valid():
            # بررسی اینکه آیا کاربر فروشنده محصول است
            is_seller = False
            if hasattr(request.user, 'seller') and request.user.seller == product.seller:
                is_seller = True
            
            serializer.save(review=review, user=request.user, is_seller=is_seller)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def add_question(self, request, slug=None):
        product = self.get_object()
        serializer = ProductQuestionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(product=product, user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def add_answer(self, request, slug=None):
        product = self.get_object()
        question_id = request.data.get('question_id')
        
        try:
            question = ProductQuestion.objects.get(id=question_id, product=product)
        except ProductQuestion.DoesNotExist:
            return Response(
                {'error': 'پرسش مورد نظر یافت نشد'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = ProductAnswerSerializer(data=request.data)
        if serializer.is_valid():
            # بررسی اینکه آیا کاربر فروشنده محصول است
            is_seller = False
            if hasattr(request.user, 'seller') and request.user.seller == product.seller:
                is_seller = True
            
            serializer.save(question=question, user=request.user, is_seller=is_seller)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], permission_classes=[IsProductSellerOrAdmin])
    def update_inventory(self, request, slug=None):
        product = self.get_object()
        new_stock = request.data.get('stock')
        variant_id = request.data.get('variant_id')
        change_reason = request.data.get('change_reason', 'بروزرسانی دستی')
        
        with atomic():
            if variant_id:
                try:
                    variant = ProductVariant.objects.get(id=variant_id, product=product)
                    previous_stock = variant.stock
                    variant.stock = new_stock
                    variant.save()
                    
                    # ثبت لاگ تغییر موجودی
                    ProductInventoryLog.objects.create(
                        product=product,
                        variant=variant,
                        previous_stock=previous_stock,
                        new_stock=new_stock,
                        change_reason=change_reason,
                        created_by=request.user
                    )
                    
                    return Response({'status': 'موجودی تنوع به‌روزرسانی شد'})
                except ProductVariant.DoesNotExist:
                    return Response(
                        {'error': 'تنوع مورد نظر یافت نشد'},
                        status=status.HTTP_404_NOT_FOUND
                    )
            else:
                previous_stock = product.stock
                product.stock = new_stock
                product.save()
                
                # ثبت لاگ تغییر موجودی
                ProductInventoryLog.objects.create(
                    product=product,
                    previous_stock=previous_stock,
                    new_stock=new_stock,
                    change_reason=change_reason,
                    created_by=request.user
                )
                
                return Response({'status': 'موجودی محصول به‌روزرسانی شد'})
    
    @action(detail=True, methods=['post'], permission_classes=[IsProductSellerOrAdmin])
    def related_products(self, request, slug=None):
        product = self.get_object()
        related_product_ids = request.data.get('related_product_ids', [])
        
        # حذف روابط قبلی
        RelatedProduct.objects.filter(product=product).delete()
        
        # ایجاد روابط جدید
        for related_id in related_product_ids:
            try:
                related_product = Product.objects.get(id=related_id)
                RelatedProduct.objects.create(
                    product=product,
                    related_product=related_product
                )
            except Product.DoesNotExist:
                pass
        
        return Response({'status': 'محصولات مرتبط به‌روزرسانی شدند'})
    
    @action(detail=True, methods=['patch'], permission_classes=[IsAdminUser])
    def admin_approve(self, request, slug=None):
        product = self.get_object()
        product.is_approved = request.data.get('is_approved', True)
        product.save(update_fields=['is_approved'])
        return Response({'status': 'وضعیت تایید محصول به‌روزرسانی شد'})
    
    @action(detail=True, methods=['patch'], permission_classes=[IsAdminUser])
    def admin_feature(self, request, slug=None):
        product = self.get_object()
        product.is_featured = request.data.get('is_featured', True)
        product.save(update_fields=['is_featured'])
        return Response({'status': 'وضعیت ویژه بودن محصول به‌روزرسانی شد'})
    
    @action(detail=False, methods=['get'])
    def featured(self, request):
        featured_products = Product.objects.filter(is_featured=True, is_active=True, is_approved=True)
        page = self.paginate_queryset(featured_products)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(featured_products, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def best_selling(self, request):
        best_selling = Product.objects.filter(is_active=True, is_approved=True).order_by('-sales_count')
        page = self.paginate_queryset(best_selling)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(best_selling, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def new_arrivals(self, request):
        new_arrivals = Product.objects.filter(is_active=True, is_approved=True).order_by('-created_at')
        page = self.paginate_queryset(new_arrivals)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(new_arrivals, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def discounted(self, request):
        discounted = Product.objects.filter(
            is_active=True, is_approved=True, discount_price__isnull=False
        ).exclude(discount_price=0)
        
        page = self.paginate_queryset(discounted)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(discounted, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[IsSellerOwner])
    def my_products(self, request):
        products = Product.objects.filter(seller=request.user.seller)
        page = self.paginate_queryset(products)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)


class ProductTagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ProductTag.objects.all()
    serializer_class = ProductTagSerializer
    lookup_field = 'slug'
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']


class ProductInventoryLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProductInventoryLogSerializer
    permission_classes = [IsProductSellerOrAdmin]
    
    def get_queryset(self):
        user = self.request.user
        
        if user.is_staff:
            return ProductInventoryLog.objects.all()
        
        if hasattr(user, 'seller'):
            return ProductInventoryLog.objects.filter(product__seller=user.seller)
        
        return ProductInventoryLog.objects.none()