from rest_framework import serializers
from .models import Review, ReviewImage, ReviewHelpful, ReviewReply, ReviewReport, ReviewSummary


class ReviewImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewImage
        fields = ['id', 'image', 'caption']


class ReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.first_name', read_only=True)
    user_phone_masked = serializers.SerializerMethodField()
    product_name = serializers.CharField(source='product.name', read_only=True)
    images = ReviewImageSerializer(many=True, read_only=True)
    rating_display = serializers.CharField(source='get_rating_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    helpful_percentage = serializers.ReadOnlyField()
    average_aspect_rating = serializers.ReadOnlyField()

    class Meta:
        model = Review
        fields = [
            'id', 'user', 'user_name', 'user_phone_masked', 'product', 'product_name',
            'rating', 'rating_display', 'title', 'comment', 'quality_rating',
            'value_rating', 'delivery_rating', 'average_aspect_rating',
            'status', 'status_display', 'is_verified_purchase',
            'helpful_count', 'not_helpful_count', 'helpful_percentage',
            'images', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'status', 'helpful_count', 'not_helpful_count',
            'is_verified_purchase', 'created_at', 'updated_at'
        ]

    def get_user_phone_masked(self, obj):
        """Mask user phone for privacy"""
        phone = obj.user.phone
        if len(phone) > 6:
            return phone[:3] + '*' * (len(phone) - 6) + phone[-3:]
        return phone

    def validate(self, data):
        user = self.context['request'].user
        product = data.get('product')
        
        # Check if user already reviewed this product
        if Review.objects.filter(user=user, product=product).exists():
            raise serializers.ValidationError('شما قبلاً برای این محصول نظر ثبت کرده‌اید')
        
        # Check if user purchased this product
        from apps.orders.models import OrderItem
        has_purchased = OrderItem.objects.filter(
            order__user=user,
            product=product,
            order__status='delivered'
        ).exists()
        
        if not has_purchased:
            raise serializers.ValidationError('شما این محصول را خریداری نکرده‌اید')
        
        return data

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        
        # Find the order item for this purchase
        from apps.orders.models import OrderItem
        try:
            order_item = OrderItem.objects.filter(
                order__user=validated_data['user'],
                product=validated_data['product'],
                order__status='delivered'
            ).first()
            validated_data['order_item'] = order_item
        except:
            pass
        
        return super().create(validated_data)


class ReviewCreateSerializer(serializers.ModelSerializer):
    images = serializers.ListField(
        child=serializers.ImageField(),
        required=False,
        allow_empty=True
    )

    class Meta:
        model = Review
        fields = [
            'product', 'rating', 'title', 'comment',
            'quality_rating', 'value_rating', 'delivery_rating', 'images'
        ]

    def create(self, validated_data):
        images_data = validated_data.pop('images', [])
        validated_data['user'] = self.context['request'].user
        
        review = super().create(validated_data)
        
        # Create review images
        for image_data in images_data:
            ReviewImage.objects.create(review=review, image=image_data)
        
        return review


class ReviewHelpfulSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewHelpful
        fields = ['id', 'review', 'is_helpful', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate(self, data):
        user = self.context['request'].user
        review = data.get('review')
        
        # Check if user already voted for this review
        if ReviewHelpful.objects.filter(user=user, review=review).exists():
            raise serializers.ValidationError('شما قبلاً برای این نظر رای داده‌اید')
        
        # Users cannot vote for their own reviews
        if review.user == user:
            raise serializers.ValidationError('نمی‌توانید برای نظر خود رای دهید')
        
        return data

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class ReviewReplySerializer(serializers.ModelSerializer):
    seller_name = serializers.CharField(source='seller.business_name', read_only=True)

    class Meta:
        model = ReviewReply
        fields = ['id', 'review', 'seller', 'seller_name', 'message', 'created_at']
        read_only_fields = ['id', 'seller', 'created_at']

    def validate(self, data):
        review = data.get('review')
        seller = self.context['request'].user.seller_profile
        
        # Check if seller owns the product
        if review.product.seller != seller:
            raise serializers.ValidationError('شما فقط می‌توانید به نظرات محصولات خود پاسخ دهید')
        
        # Check if reply already exists
        if hasattr(review, 'reply'):
            raise serializers.ValidationError('قبلاً به این نظر پاسخ داده‌اید')
        
        return data

    def create(self, validated_data):
        validated_data['seller'] = self.context['request'].user.seller_profile
        return super().create(validated_data)


class ReviewReportSerializer(serializers.ModelSerializer):
    reason_display = serializers.CharField(source='get_reason_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = ReviewReport
        fields = [
            'id', 'review', 'reason', 'reason_display', 'description',
            'status', 'status_display', 'created_at'
        ]
        read_only_fields = ['id', 'status', 'created_at']

    def validate(self, data):
        user = self.context['request'].user
        review = data.get('review')
        
        # Check if user already reported this review
        if ReviewReport.objects.filter(user=user, review=review).exists():
            raise serializers.ValidationError('شما قبلاً این نظر را گزارش کرده‌اید')
        
        # Users cannot report their own reviews
        if review.user == user:
            raise serializers.ValidationError('نمی‌توانید نظر خود را گزارش کنید')
        
        return data

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class ReviewSummarySerializer(serializers.ModelSerializer):
    rating_distribution = serializers.SerializerMethodField()

    class Meta:
        model = ReviewSummary
        fields = [
            'total_reviews', 'average_rating', 'rating_distribution',
            'average_quality_rating', 'average_value_rating', 'average_delivery_rating',
            'verified_purchases_percentage', 'last_updated'
        ]

    def get_rating_distribution(self, obj):
        return {
            '1': obj.rating_1_count,
            '2': obj.rating_2_count,
            '3': obj.rating_3_count,
            '4': obj.rating_4_count,
            '5': obj.rating_5_count,
        }


class ReviewAdminSerializer(serializers.ModelSerializer):
    """Serializer for admin review management"""
    user_phone = serializers.CharField(source='user.phone', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    seller_name = serializers.CharField(source='product.seller.business_name', read_only=True)

    class Meta:
        model = Review
        fields = [
            'id', 'user', 'user_phone', 'product', 'product_name', 'seller_name',
            'rating', 'title', 'comment', 'status', 'admin_notes',
            'is_verified_purchase', 'helpful_count', 'not_helpful_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'product', 'helpful_count', 'not_helpful_count', 'created_at']

    def update(self, instance, validated_data):
        # Update review summary when status changes
        old_status = instance.status
        instance = super().update(instance, validated_data)
        
        if old_status != instance.status:
            ReviewSummary.update_for_product(instance.product)
        
        return instance