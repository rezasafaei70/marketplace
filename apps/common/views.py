from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils import timezone
from .models import (
    ActivityLog, Setting, ContactMessage, FAQ,
    Province, City, Banner, Newsletter
)
from .serializers import (
    ActivityLogSerializer, SettingSerializer, ContactMessageSerializer,
    ContactMessageReplySerializer, FAQSerializer, ProvinceSerializer,
    CitySerializer, BannerSerializer, NewsletterSerializer,
    NewsletterSubscribeSerializer
)
from .pagination import StandardResultsSetPagination


class ActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Activity logs viewset"""
    queryset = ActivityLog.objects.all()
    serializer_class = ActivityLogSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['action', 'user']
    search_fields = ['description', 'user__phone']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        if self.request.user.is_staff:
            return ActivityLog.objects.all()
        return ActivityLog.objects.filter(user=self.request.user)


class SettingViewSet(viewsets.ModelViewSet):
    """System settings viewset"""
    queryset = Setting.objects.filter(is_active=True)
    serializer_class = SettingSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [SearchFilter]
    search_fields = ['key', 'description']

    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def public(self, request):
        """Get public settings"""
        public_keys = ['site_name', 'site_description', 'contact_email', 'contact_phone']
        settings = Setting.objects.filter(key__in=public_keys, is_active=True)
        serializer = self.get_serializer(settings, many=True)
        return Response(serializer.data)


class ContactMessageViewSet(viewsets.ModelViewSet):
    """Contact messages viewset"""
    queryset = ContactMessage.objects.all()
    serializer_class = ContactMessageSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_read', 'replied']
    search_fields = ['name', 'email', 'subject']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_permissions(self):
        if self.action == 'create':
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAdminUser]
        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        serializer.save()
        # Send notification to admin
        # self.send_admin_notification(serializer.instance)

    @action(detail=True, methods=['post'])
    def reply(self, request, pk=None):
        """Reply to contact message"""
        message = self.get_object()
        serializer = ContactMessageReplySerializer(message, data=request.data)
        if serializer.is_valid():
            serializer.save()
            # Send email reply
            # self.send_reply_email(message)
            return Response({'message': 'پاسخ با موفقیت ارسال شد'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Mark message as read"""
        message = self.get_object()
        message.is_read = True
        message.save()
        return Response({'message': 'پیام به عنوان خوانده شده علامت‌گذاری شد'})


class FAQViewSet(viewsets.ModelViewSet):
    """FAQ viewset"""
    queryset = FAQ.objects.filter(is_active=True)
    serializer_class = FAQSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['question', 'answer', 'category']
    ordering_fields = ['order', 'created_at']
    ordering = ['order']

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAdminUser]
        return [permission() for permission in permission_classes]

    @action(detail=False, methods=['get'])
    def categories(self, request):
        """Get FAQ categories"""
        categories = FAQ.objects.filter(is_active=True).values_list('category', flat=True).distinct()
        return Response(list(categories))


class ProvinceViewSet(viewsets.ReadOnlyModelViewSet):
    """Provinces viewset"""
    queryset = Province.objects.filter(is_active=True)
    serializer_class = ProvinceSerializer
    permission_classes = [AllowAny]
    ordering = ['name']


class CityViewSet(viewsets.ReadOnlyModelViewSet):
    """Cities viewset"""
    queryset = City.objects.filter(is_active=True)
    serializer_class = CitySerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['province']
    ordering = ['name']


class BannerViewSet(viewsets.ModelViewSet):
    """Banners viewset"""
    queryset = Banner.objects.all()
    serializer_class = BannerSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['position', 'is_active']
    ordering_fields = ['order', 'created_at']
    ordering = ['position', 'order']

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAdminUser]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        if self.action in ['list', 'retrieve'] and not self.request.user.is_staff:
            # Only show valid banners to public
            now = timezone.now()
            return Banner.objects.filter(
                is_active=True
            ).filter(
                models.Q(start_date__isnull=True) | models.Q(start_date__lte=now)
            ).filter(
                models.Q(end_date__isnull=True) | models.Q(end_date__gte=now)
            )
        return Banner.objects.all()

    @action(detail=False, methods=['get'])
    def by_position(self, request):
        """Get banners by position"""
        position = request.query_params.get('position')
        if not position:
            return Response({'error': 'موقعیت الزامی است'}, status=status.HTTP_400_BAD_REQUEST)
        
        banners = self.get_queryset().filter(position=position)
        serializer = self.get_serializer(banners, many=True)
        return Response(serializer.data)


class NewsletterViewSet(viewsets.ModelViewSet):
    """Newsletter viewset"""
    queryset = Newsletter.objects.all()
    serializer_class = NewsletterSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['is_active', 'confirmed']
    search_fields = ['email']
    ordering = ['-created_at']

    def get_permissions(self):
        if self.action == 'subscribe':
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAdminUser]
        return [permission() for permission in permission_classes]

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def subscribe(self, request):
        """Subscribe to newsletter"""
        serializer = NewsletterSubscribeSerializer(data=request.data)
        if serializer.is_valid():
            newsletter = serializer.save()
            if newsletter:
                # Send confirmation email
                # self.send_confirmation_email(newsletter)
                return Response({
                    'message': 'با موفقیت در خبرنامه عضو شدید',
                    'email': newsletter.email
                })
            return Response({'message': 'قبلاً عضو خبرنامه هستید'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def unsubscribe(self, request):
        """Unsubscribe from newsletter"""
        email = request.data.get('email')
        if not email:
            return Response({'error': 'ایمیل الزامی است'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            newsletter = Newsletter.objects.get(email=email)
            newsletter.is_active = False
            newsletter.save()
            return Response({'message': 'با موفقیت از خبرنامه لغو عضویت کردید'})
        except Newsletter.DoesNotExist:
            return Response({'error': 'ایمیل در خبرنامه یافت نشد'}, status=status.HTTP_404_NOT_FOUND)