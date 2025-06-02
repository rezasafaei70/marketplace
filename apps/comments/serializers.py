from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType
from .models import Comment, CommentVote, CommentReport


class CommentSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    user_avatar = serializers.SerializerMethodField()
    content_type_name = serializers.CharField(write_only=True)
    object_id = serializers.UUIDField(write_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    replies_count = serializers.IntegerField(read_only=True)
    is_reply = serializers.BooleanField(read_only=True)
    user_vote = serializers.SerializerMethodField()
    
    class Meta:
        model = Comment
        fields = [
            'id', 'user', 'user_name', 'user_avatar', 'content_type_name', 
            'object_id', 'text', 'status', 'status_display', 'parent', 
            'likes_count', 'dislikes_count', 'replies_count', 'is_reply',
            'user_vote', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'status', 'likes_count', 'dislikes_count', 'created_at', 'updated_at']
    
    def get_user_name(self, obj):
        """Get user's name"""
        if obj.user.first_name or obj.user.last_name:
            return f"{obj.user.first_name} {obj.user.last_name}".strip()
        return obj.user.phone
    
    def get_user_avatar(self, obj):
        """Get user's avatar"""
        if hasattr(obj.user, 'profile') and obj.user.profile.avatar:
            return obj.user.profile.avatar.url
        return None
    
    def get_user_vote(self, obj):
        """Get current user's vote on this comment"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            vote = CommentVote.objects.filter(user=request.user, comment=obj).first()
            if vote:
                return vote.vote_type
        return None
    
    def validate(self, data):
        """Validate content type and object ID"""
        content_type_name = data.pop('content_type_name', None)
        object_id = data.get('object_id')
        
        if not content_type_name or not object_id:
            raise serializers.ValidationError("نوع محتوا و شناسه محتوا الزامی است")
        
        try:
            app_label, model = content_type_name.split('.')
            content_type = ContentType.objects.get(app_label=app_label, model=model)
            data['content_type'] = content_type
            
            # Check if object exists
            model_class = content_type.model_class()
            model_class.objects.get(id=object_id)
            
        except (ValueError, ContentType.DoesNotExist):
            raise serializers.ValidationError("نوع محتوا نامعتبر است")
        except model_class.DoesNotExist:
            raise serializers.ValidationError("محتوا با این شناسه یافت نشد")
        
        # Check if parent comment exists and belongs to the same content object
        parent = data.get('parent')
        if parent:
            if parent.content_type != data['content_type'] or parent.object_id != object_id:
                raise serializers.ValidationError("نظر والد باید متعلق به همان محتوا باشد")
            
            # Check if parent is already a reply
            if parent.parent:
                raise serializers.ValidationError("پاسخ به پاسخ مجاز نیست")
        
        return data
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class CommentVoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommentVote
        fields = ['id', 'comment', 'vote_type', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def validate(self, data):
        user = self.context['request'].user
        comment = data['comment']
        
        # Check if user is voting on their own comment
        if comment.user == user:
            raise serializers.ValidationError("شما نمی‌توانید به نظر خود رای دهید")
        
        return data
    
    def create(self, validated_data):
        user = self.context['request'].user
        comment = validated_data['comment']
        vote_type = validated_data['vote_type']
        
        # Check if vote already exists
        vote, created = CommentVote.objects.update_or_create(
            user=user,
            comment=comment,
            defaults={'vote_type': vote_type}
        )
        
        return vote


class CommentReportSerializer(serializers.ModelSerializer):
    reason_display = serializers.CharField(source='get_reason_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = CommentReport
        fields = [
            'id', 'comment', 'reason', 'reason_display', 'description',
            'status', 'status_display', 'created_at'
        ]
        read_only_fields = ['id', 'status', 'created_at']
    
    def validate(self, data):
        user = self.context['request'].user
        comment = data['comment']
        
        # Check if user is reporting their own comment
        if comment.user == user:
            raise serializers.ValidationError("شما نمی‌توانید نظر خود را گزارش کنید")
        
        # Check if user already reported this comment
        if CommentReport.objects.filter(user=user, comment=comment).exists():
            raise serializers.ValidationError("شما قبلاً این نظر را گزارش کرده‌اید")
        
        return data
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class ReplySerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    user_avatar = serializers.SerializerMethodField()
    
    class Meta:
        model = Comment
        fields = [
            'id', 'user', 'user_name', 'user_avatar', 'text',
            'likes_count', 'dislikes_count', 'created_at'
        ]
    
    def get_user_name(self, obj):
        """Get user's name"""
        if obj.user.first_name or obj.user.last_name:
            return f"{obj.user.first_name} {obj.user.last_name}".strip()
        return obj.user.phone
    
    def get_user_avatar(self, obj):
        """Get user's avatar"""
        if hasattr(obj.user, 'profile') and obj.user.profile.avatar:
            return obj.user.profile.avatar.url
        return None