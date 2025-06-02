from rest_framework import serializers
from .models import (
    ActivityLog, Setting, ContactMessage, FAQ, 
    Province, City, Banner, Newsletter
)


class ActivityLogSerializer(serializers.ModelSerializer):
    user_phone = serializers.CharField(source='user.phone', read_only=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)

    class Meta:
        model = ActivityLog
        fields = [
            'id', 'user', 'user_phone', 'action', 'action_display',
            'description', 'ip_address', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class SettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Setting
        fields = [
            'id', 'key', 'value', 'value_type', 'description',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = [
            'id', 'name', 'email', 'phone', 'subject', 'message',
            'is_read', 'replied', 'reply_message', 'replied_at', 'created_at'
        ]
        read_only_fields = ['id', 'is_read', 'replied', 'replied_at', 'created_at']


class ContactMessageReplySerializer(serializers.Serializer):
    reply_message = serializers.CharField(max_length=2000)

    def update(self, instance, validated_data):
        from django.utils import timezone
        instance.reply_message = validated_data['reply_message']
        instance.replied = True
        instance.replied_at = timezone.now()
        instance.save()
        return instance


class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = [
            'id', 'question', 'answer', 'category', 'order',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProvinceSerializer(serializers.ModelSerializer):
    cities_count = serializers.IntegerField(source='cities.count', read_only=True)

    class Meta:
        model = Province
        fields = ['id', 'name', 'code', 'is_active', 'cities_count']


class CitySerializer(serializers.ModelSerializer):
    province_name = serializers.CharField(source='province.name', read_only=True)

    class Meta:
        model = City
        fields = ['id', 'name', 'code', 'province', 'province_name', 'is_active']


class BannerSerializer(serializers.ModelSerializer):
    position_display = serializers.CharField(source='get_position_display', read_only=True)
    is_valid = serializers.BooleanField(read_only=True)

    class Meta:
        model = Banner
        fields = [
            'id', 'title', 'image', 'link', 'position', 'position_display',
            'order', 'is_active', 'is_valid', 'start_date', 'end_date',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class NewsletterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Newsletter
        fields = ['id', 'email', 'is_active', 'confirmed', 'created_at']
        read_only_fields = ['id', 'confirmed', 'created_at']


class NewsletterSubscribeSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def create(self, validated_data):
        newsletter, created = Newsletter.objects.get_or_create(
            email=validated_data['email'],
            defaults={'is_active': True}
        )
        return newsletter