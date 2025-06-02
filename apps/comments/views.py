from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from .models import Comment, CommentVote, CommentReport
from .serializers import (
    CommentSerializer, CommentVoteSerializer, CommentReportSerializer,
    ReplySerializer
)
from apps.common.pagination import StandardResultsSetPagination


class CommentViewSet(viewsets.ModelViewSet):
    """Comment viewset for CRUD operations"""
    queryset = Comment.objects.filter(status='approved', parent=None)
    serializer_class = CommentSerializer
    pagination_class = StandardResultsSetPagination
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'for_object']:
            permission_classes = [AllowAny]
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        queryset = Comment.objects.all()
        
        # Filter by status
        if self.request.user.is_staff:
            status_filter = self.request.query_params.get('status')
            if status_filter:
                queryset = queryset.filter(status=status_filter)
        else:
            # Regular users can only see approved comments or their own
            queryset = queryset.filter(
                Q(status='approved') | Q(user=self.request.user)
            )
        
        # Filter by parent (top-level comments)
        if self.action != 'replies':
            queryset = queryset.filter(parent=None)
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    def perform_update(self, serializer):
        comment = self.get_object()
        
        # Only allow users to edit their own comments or admins
        if comment.user != self.request.user and not self.request.user.is_staff:
            self.permission_denied(self.request, message="شما اجازه ویرایش این نظر را ندارید")
        
        serializer.save()
    
    def perform_destroy(self, instance):
        # Only allow users to delete their own comments or admins
        if instance.user != self.request.user and not self.request.user.is_staff:
            self.permission_denied(self.request, message="شما اجازه حذف این نظر را ندارید")
        
        instance.delete()
    
    @action(detail=False, methods=['get'])
    def for_object(self, request):
        """Get comments for a specific object"""
        content_type_name = request.query_params.get('content_type')
        object_id = request.query_params.get('object_id')
        
        if not content_type_name or not object_id:
            return Response(
                {"error": "نوع محتوا و شناسه محتوا الزامی است"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            app_label, model = content_type_name.split('.')
            content_type = ContentType.objects.get(app_label=app_label, model=model)
            
            queryset = self.get_queryset().filter(
                content_type=content_type,
                object_id=object_id
            )
            
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
            
        except (ValueError, ContentType.DoesNotExist):
            return Response(
                {"error": "نوع محتوا نامعتبر است"},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'])
    def replies(self, request, pk=None):
        """Get replies for a comment"""
        comment = self.get_object()
        replies = Comment.objects.filter(parent=comment, status='approved')
        
        page = self.paginate_queryset(replies)
        if page is not None:
            serializer = ReplySerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = ReplySerializer(replies, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def vote(self, request, pk=None):
        """Vote on a comment"""
        comment = self.get_object()
        vote_type = request.data.get('vote_type')
        
        if vote_type not in ['like', 'dislike']:
            return Response(
                {"error": "نوع رای باید 'like' یا 'dislike' باشد"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user is voting on their own comment
        if comment.user == request.user:
            return Response(
                {"error": "شما نمی‌توانید به نظر خود رای دهید"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create or update vote
        vote, created = CommentVote.objects.update_or_create(
            user=request.user,
            comment=comment,
            defaults={'vote_type': vote_type}
        )
        
        return Response({
            "message": "رای شما ثبت شد",
            "likes_count": comment.likes_count,
            "dislikes_count": comment.dislikes_count
        })
    
    @action(detail=True, methods=['post'])
    def report(self, request, pk=None):
        """Report a comment"""
        comment = self.get_object()
        reason = request.data.get('reason')
        description = request.data.get('description', '')
        
        if not reason:
            return Response(
                {"error": "دلیل گزارش الزامی است"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user is reporting their own comment
        if comment.user == request.user:
            return Response(
                {"error": "شما نمی‌توانید نظر خود را گزارش کنید"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user already reported this comment
        if CommentReport.objects.filter(user=request.user, comment=comment).exists():
            return Response(
                {"error": "شما قبلاً این نظر را گزارش کرده‌اید"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create report
        CommentReport.objects.create(
            user=request.user,
            comment=comment,
            reason=reason,
            description=description
        )
        
        return Response({"message": "گزارش شما ثبت شد"})
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def approve(self, request, pk=None):
        """Approve a comment (admin only)"""
        comment = self.get_object()
        comment.status = 'approved'
        comment.save()
        return Response({"message": "نظر تایید شد"})
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def reject(self, request, pk=None):
        """Reject a comment (admin only)"""
        comment = self.get_object()
        comment.status = 'rejected'
        comment.save()
        return Response({"message": "نظر رد شد"})
    
    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser])
    def pending(self, request):
        """Get pending comments (admin only)"""
        queryset = Comment.objects.filter(status='pending')
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class CommentReportViewSet(viewsets.ModelViewSet):
    """Comment report viewset for admins"""
    queryset = CommentReport.objects.all()
    serializer_class = CommentReportSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return CommentReport.objects.all()
        return CommentReport.objects.filter(user=self.request.user)
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def resolve(self, request, pk=None):
        """Resolve a report (admin only)"""
        report = self.get_object()
        action = request.data.get('action')
        admin_note = request.data.get('admin_note', '')
        
        if action not in ['dismiss', 'remove_comment']:
            return Response(
                {"error": "عملیات باید 'dismiss' یا 'remove_comment' باشد"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        report.status = 'resolved' if action == 'remove_comment' else 'dismissed'
        report.admin_note = admin_note
        report.save()
        
        if action == 'remove_comment':
            report.comment.status = 'rejected'
            report.comment.admin_note = admin_note
            report.comment.save()
        
        return Response({"message": "گزارش پردازش شد"})