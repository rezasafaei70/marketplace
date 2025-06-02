from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Q, Count
from .models import Notification, NotificationSetting, DeviceToken
from .serializers import (
    NotificationSerializer, NotificationSettingSerializer, DeviceTokenSerializer,
    NotificationCountSerializer, BulkNotificationActionSerializer
)
from apps.common.pagination import StandardResultsSetPagination


class NotificationViewSet(viewsets.ModelViewSet):
    """Notification viewset for user notifications"""
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Mark a notification as read"""
        notification = self.get_object()
        notification.mark_as_read()
        return Response({'message': 'اعلان به عنوان خوانده شده علامت‌گذاری شد'})
    
    @action(detail=True, methods=['post'])
    def mark_as_unread(self, request, pk=None):
        """Mark a notification as unread"""
        notification = self.get_object()
        notification.is_read = False
        notification.read_at = None
        notification.save()
        return Response({'message': 'اعلان به عنوان خوانده نشده علامت‌گذاری شد'})
    
    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        """Mark all notifications as read"""
        Notification.objects.filter(user=request.user, is_read=False).update(
            is_read=True,
            read_at=timezone.now()
        )
        return Response({'message': 'همه اعلان‌ها به عنوان خوانده شده علامت‌گذاری شدند'})
    
    @action(detail=False, methods=['get'])
    def unread(self, request):
        """Get unread notifications"""
        queryset = self.get_queryset().filter(is_read=False)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def count(self, request):
        """Get notification counts"""
        total = self.get_queryset().count()
        unread = self.get_queryset().filter(is_read=False).count()
        
        serializer = NotificationCountSerializer({
            'total': total,
            'unread': unread
        })
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def bulk_action(self, request):
        """Perform bulk action on notifications"""
        serializer = BulkNotificationActionSerializer(data=request.data)
        if serializer.is_valid():
            notification_ids = serializer.validated_data['notification_ids']
            action = serializer.validated_data['action']
            
            notifications = self.get_queryset().filter(id__in=notification_ids)
            
            if action == 'mark_read':
                notifications.update(is_read=True, read_at=timezone.now())
                return Response({'message': f'{notifications.count()} اعلان به عنوان خوانده شده علامت‌گذاری شد'})
            elif action == 'mark_unread':
                notifications.update(is_read=False, read_at=None)
                return Response({'message': f'{notifications.count()} اعلان به عنوان خوانده نشده علامت‌گذاری شد'})
            elif action == 'delete':
                count = notifications.count()
                notifications.delete()
                return Response({'message': f'{count} اعلان حذف شد'})
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """Get notifications grouped by type"""
        notification_type = request.query_params.get('type')
        if not notification_type:
            return Response(
                {"error": "نوع اعلان الزامی است"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = self.get_queryset().filter(type=notification_type)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class NotificationSettingViewSet(viewsets.ModelViewSet):
    """Notification settings viewset"""
    serializer_class = NotificationSettingSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return NotificationSetting.get_or_create_settings(self.request.user)
    
    def list(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)
    
    def perform_update(self, serializer):
        serializer.save()


class DeviceTokenViewSet(viewsets.ModelViewSet):
    """Device token viewset for push notifications"""
    serializer_class = DeviceTokenSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return DeviceToken.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate a device token"""
        device_token = self.get_object()
        device_token.is_active = False
        device_token.save()
        return Response({'message': 'توکن دستگاه غیرفعال شد'})