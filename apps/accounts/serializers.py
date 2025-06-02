from rest_framework import serializers
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta
import random
from .models import OTP, UserProfile, Address, UserSession
from apps.common.utils import send_otp_sms

User = get_user_model()


class PhoneNumberSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=11)
    
    def validate_phone_number(self, value):
        if not value.isdigit() or len(value) != 11 or not value.startswith('09'):
            raise serializers.ValidationError('شماره موبایل معتبر نیست')
        return value


class OTPVerificationSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=11)
    code = serializers.CharField(max_length=6)
    
    def validate(self, data):
        phone_number = data.get('phone_number')
        code = data.get('code')
        
        try:
            otp = OTP.objects.filter(
                phone_number=phone_number,
                code=code,
                is_used=False,
                expires_at__gt=timezone.now()
            ).latest('created_at')
        except OTP.DoesNotExist:
            raise serializers.ValidationError('کد وارد شده نامعتبر است یا منقضی شده است')
        
        data['otp'] = otp
        return data


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'phone_number', 'email', 'first_name', 'last_name', 'date_joined')
        read_only_fields = ('id', 'phone_number', 'date_joined')


class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = UserProfile
        fields = ('user', 'avatar', 'birth_date', 'loyalty_points')
        read_only_fields = ('loyalty_points',)


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ('id', 'title', 'province', 'city', 'postal_code', 'address',
                  'receiver_name', 'receiver_phone', 'is_default')
        read_only_fields = ('id',)
    
    def create(self, validated_data):
        user = self.context['request'].user
        if validated_data.get('is_default', False):
            # اگر آدرس جدید پیش‌فرض باشد، سایر آدرس‌های پیش‌فرض را غیرفعال کنیم
            Address.objects.filter(user=user, is_default=True).update(is_default=False)
        
        validated_data['user'] = user
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        if validated_data.get('is_default', False) and not instance.is_default:
            # اگر آدرس به پیش‌فرض تغییر کند، سایر آدرس‌های پیش‌فرض را غیرفعال کنیم
            Address.objects.filter(user=instance.user, is_default=True).update(is_default=False)
        
        return super().update(instance, validated_data)


class UserSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSession
        fields = ('id', 'device', 'ip_address', 'location', 'last_activity', 'created_at')
        read_only_fields = fields


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('رمز عبور فعلی اشتباه است')
        return value