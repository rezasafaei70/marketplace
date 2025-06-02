from rest_framework import status, viewsets, generics, permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes,action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from django.db.models import Q
from django.contrib.auth import get_user_model
from datetime import timedelta
import random
import uuid
import re

from .models import OTP, UserProfile, Address, UserSession, LoginAttempt
from .serializers import (
    PhoneNumberSerializer, OTPVerificationSerializer, UserSerializer,
    UserProfileSerializer, AddressSerializer, UserSessionSerializer,
    ChangePasswordSerializer
)
from apps.common.utils import send_otp_sms, get_client_ip, parse_user_agent

User = get_user_model()


@api_view(['POST'])
@permission_classes([AllowAny])
def request_otp(request):
    serializer = PhoneNumberSerializer(data=request.data)
    if serializer.is_valid():
        phone_number = serializer.validated_data['phone_number']
        
        # محدودیت تعداد درخواست OTP
        recent_otps = OTP.objects.filter(
            phone_number=phone_number,
            created_at__gt=timezone.now() - timedelta(minutes=10)
        )
        
        if recent_otps.count() >= 5:
            return Response(
                {'error': 'تعداد درخواست‌های شما بیش از حد مجاز است. لطفا بعدا تلاش کنید.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        
        # ایجاد کد OTP
        code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        expires_at = timezone.now() + timedelta(minutes=2)
        
        # ذخیره OTP در دیتابیس
        OTP.objects.create(
            phone_number=phone_number,
            code=code,
            expires_at=expires_at
        )
        
        # ارسال پیامک
        send_otp_sms(phone_number, code)
        
        return Response({'message': 'کد تایید برای شما ارسال شد'}, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_otp(request):
    serializer = OTPVerificationSerializer(data=request.data)
    if serializer.is_valid():
        phone_number = serializer.validated_data['phone_number']
        otp = serializer.validated_data['otp']
        
        # ثبت تلاش ورود
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # کد OTP را استفاده شده علامت‌گذاری می‌کنیم
        otp.is_used = True
        otp.save()
        
        # بررسی وجود کاربر یا ایجاد کاربر جدید
        user, created = User.objects.get_or_create(phone_number=phone_number)
        
        # ایجاد پروفایل در صورت عدم وجود
        if created:
            UserProfile.objects.create(user=user)
        
        # ثبت نشست کاربر
        device_info = parse_user_agent(user_agent)
        UserSession.objects.create(
            user=user,
            session_key=str(uuid.uuid4()),
            ip_address=ip_address,
            user_agent=user_agent,
            device=device_info.get('device', 'نامشخص')
        )
        
        # ثبت ورود موفق
        LoginAttempt.objects.create(
            phone_number=phone_number,
            ip_address=ip_address,
            user_agent=user_agent,
            success=True
        )
        
        # تولید توکن JWT
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserSerializer(user).data,
            'is_new_user': created
        }, status=status.HTTP_200_OK)
    
    # ثبت تلاش ناموفق
    if 'phone_number' in request.data:
        LoginAttempt.objects.create(
            phone_number=request.data['phone_number'],
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            success=False
        )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer
    
    def get_object(self):
        return UserProfile.objects.get(user=self.request.user)
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        user_data = request.data.pop('user', {})
        
        # به‌روزرسانی اطلاعات کاربر
        user = instance.user
        if 'email' in user_data:
            user.email = user_data['email']
        if 'first_name' in user_data:
            user.first_name = user_data['first_name']
        if 'last_name' in user_data:
            user.last_name = user_data['last_name']
        user.save()
        
        # به‌روزرسانی پروفایل
        return super().update(request, *args, **kwargs)


class AddressViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = AddressSerializer
    
    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)


class UserSessionViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSessionSerializer
    
    def get_queryset(self):
        return UserSession.objects.filter(user=self.request.user, is_active=True)
    
    @action(detail=True, methods=['post'])
    def terminate(self, request, pk=None):
        try:
            session = UserSession.objects.get(pk=pk, user=request.user)
            session.is_active = False
            session.save()
            return Response({'message': 'نشست با موفقیت خاتمه یافت'}, status=status.HTTP_200_OK)
        except UserSession.DoesNotExist:
            return Response({'error': 'نشست یافت نشد'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['post'])
    def terminate_all_except_current(self, request):
        current_session_key = request.session.session_key
        UserSession.objects.filter(user=request.user).exclude(session_key=current_session_key).update(is_active=False)
        return Response({'message': 'تمام نشست‌های دیگر با موفقیت خاتمه یافتند'}, status=status.HTTP_200_OK)


class ChangePasswordView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ChangePasswordSerializer
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            
            # خاتمه دادن به تمام نشست‌های کاربر به جز نشست فعلی
            current_session_key = request.session.session_key
            UserSession.objects.filter(user=user).exclude(session_key=current_session_key).update(is_active=False)
            
            return Response({'message': 'رمز عبور با موفقیت تغییر یافت'}, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)