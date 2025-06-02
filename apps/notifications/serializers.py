from rest_framework import serializers
from .models import Notification, NotificationSetting, DeviceToken


class NotificationSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'type', 'type_display', 'title', 'message', 'is_read',
            'read_at', 'priority', 'priority_display', 'action_url', 'data',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class NotificationSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationSetting
        exclude = ['user', 'created_at', 'updated_at']
    
    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        return instance


class DeviceTokenSerializer(serializers.ModelSerializer):
    platform_display = serializers.CharField(source='get_platform_display', read_only=True)
    
    class Meta:
        model = DeviceToken
        fields = [
            'id', 'token', 'platform', 'platform_display', 'device_name',
            'is_active', 'created_at', 'last_used_at'
        ]
        read_only_fields = ['id', 'created_at', 'last_used_at']
    
    def validate(self, data):
        # Check if token already exists for this user
        user = self.context['request'].user
        token = data.get('token')
        
        if self.instance is None:  # Creating new token
            if DeviceToken.objects.filter(user=user, token=token).exists():
                raise serializers.ValidationError("این توکن قبلاً برای این کاربر ثبت شده است")
        
        return data
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class NotificationCountSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    unread = serializers.IntegerField()


class BulkNotificationActionSerializer(serializers.Serializer):
    notification_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=True
    )
    action = serializers.ChoiceField(
        choices=['mark_read', 'mark_unread', 'delete'],
        required=True
    )