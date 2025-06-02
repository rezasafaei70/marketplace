from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Q, Avg
from .models import Review, ReviewHelpful, ReviewReply, ReviewReport, ReviewSummary
from .serializers import (
    ReviewSerializer, ReviewCreateSerializer, ReviewHelpfulSerializer,
    ReviewReplySerializer, ReviewReportSerializer, ReviewSummarySerializer,
    ReviewAdminSerializer
)
from apps.common.pagination import StandardResultsSetPagination


class ReviewViewSet(viewsets.ModelViewSet):
    """Reviews viewset"""
    queryset = Review.objects.filter(status='approved')
    serializer_class = ReviewSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['product', 'rating', 'is_verified_purchase']
    search_fields = ['title', 'comment']
    ordering_fields = ['created_at', 'rating', 'helpful_count']
    ordering = ['-created_at']

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        if self.action == 'create':
            return ReviewCreateSerializer
        elif self.action in ['update', 'partial_update'] and self.request.user.is_staff:
            return ReviewAdminSerializer
        return ReviewSerializer

    def get_queryset(self):
        queryset = Review.objects.all()
        
        if not self.request.user.is_staff:
            if self.action in ['list', 'retrieve']:
                queryset = queryset.filter(status='approved')
            elif self.action in ['update', 'partial_update', 'destroy']:
                queryset = queryset.filter(user=self.request.user)
        
        # Filter by product
        product_id = self.request.query_params.get('product')
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        
        # Filter by rating range
        min_rating = self.request.query_params.get('min_rating')
        max_rating = self.request.query_params.get('max_rating')
        if min_rating:
            queryset = queryset.filter(rating__gte=min_rating)
        if max_rating:
            queryset = queryset.filter(rating__lte=max_rating)
        
        return queryset

    def perform_create(self, serializer):
        review = serializer.save()
        # Update product review summary
        ReviewSummary.update_for_product(review.product)

    def perform_update(self, serializer):
        review = serializer.save()
        # Update product review summary
        ReviewSummary.update_for_product(review.product)

    def perform_destroy(self, instance):
        product = instance.product
        instance.delete()
        # Update product review summary
        ReviewSummary.update_for_product(product)

    @action(detail=False, methods=['get'])
    def my_reviews(self, request):
        """Get current user's reviews"""
        if not request.user.is_authenticated:
            return Response({'error': 'احراز هویت الزامی است'}, status=status.HTTP_401_UNAUTHORIZED)
        
        reviews = Review.objects.filter(user=request.user)
        page = self.paginate_queryset(reviews)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(reviews, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def vote_helpful(self, request, pk=None):
        """Vote if review is helpful or not"""
        review = self.get_object()
        is_helpful = request.data.get('is_helpful', True)
        
        # Check if user already voted
        existing_vote = ReviewHelpful.objects.filter(user=request.user, review=review).first()
        if existing_vote:
            if existing_vote.is_helpful != is_helpful:
                existing_vote.is_helpful = is_helpful
                existing_vote.save()
                return Response({'message': 'رای شما بروزرسانی شد'})
            else:
                return Response({'message': 'شما قبلاً رای داده‌اید'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Create new vote
        ReviewHelpful.objects.create(user=request.user, review=review, is_helpful=is_helpful)
        return Response({'message': 'رای شما ثبت شد'})

    @action(detail=True, methods=['post'])
    def report(self, request, pk=None):
        """Report a review"""
        review = self.get_object()
        serializer = ReviewReportSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(review=review)
            return Response({'message': 'گزارش شما ثبت شد'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get review statistics"""
        product_id = request.query_params.get('product')
        if not product_id:
            return Response({'error': 'شناسه محصول الزامی است'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            summary = ReviewSummary.objects.get(product_id=product_id)
            serializer = ReviewSummarySerializer(summary)
            return Response(serializer.data)
        except ReviewSummary.DoesNotExist:
            # Create summary if it doesn't exist
            from apps.products.models import Product
            try:
                product = Product.objects.get(id=product_id)
                summary = ReviewSummary.update_for_product(product)
                serializer = ReviewSummarySerializer(summary)
                return Response(serializer.data)
            except Product.DoesNotExist:
                return Response({'error': 'محصول یافت نشد'}, status=status.HTTP_404_NOT_FOUND)


class ReviewReplyViewSet(viewsets.ModelViewSet):
    """Review replies viewset"""
    queryset = ReviewReply.objects.all()
    serializer_class = ReviewReplySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if hasattr(self.request.user, 'seller_profile'):
            return ReviewReply.objects.filter(seller=self.request.user.seller_profile)
        return ReviewReply.objects.none()


class ReviewReportViewSet(viewsets.ModelViewSet):
    """Review reports viewset (admin only)"""
    queryset = ReviewReport.objects.all()
    serializer_class = ReviewReportSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['status', 'reason']
    ordering = ['-created_at']

    def get_queryset(self):
        if self.request.user.is_staff:
            return ReviewReport.objects.all()
        return ReviewReport.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Resolve a report (admin only)"""
        if not request.user.is_staff:
            return Response({'error': 'دسترسی محدود'}, status=status.HTTP_403_FORBIDDEN)
        
        report = self.get_object()
        action_type = request.data.get('action')  # 'dismiss', 'remove_review', 'warn_user'
        admin_notes = request.data.get('admin_notes', '')
        
        if action_type == 'dismiss':
            report.status = 'dismissed'
        elif action_type == 'remove_review':
            report.review.status = 'rejected'
            report.review.save()
            report.status = 'resolved'
        elif action_type == 'warn_user':
            # Send warning to user
            report.status = 'resolved'
        else:
            return Response({'error': 'نوع عمل نامعتبر'}, status=status.HTTP_400_BAD_REQUEST)
        
        report.admin_notes = admin_notes
        report.save()
        
        return Response({'message': 'گزارش پردازش شد'})