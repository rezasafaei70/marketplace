from rest_framework import serializers
from django.utils.text import slugify
from django.db.models import Avg
from .models import (
    Seller, SellerCategory, SellerReview, TieredCommission, SellerWithdrawal
)
from apps.categories.serializers import CategoryListSerializer


class SellerListSerializer(serializers.ModelSerializer):
    user_full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Seller
        fields = ('id', 'shop_name', 'slug', 'logo', 'rating', 'review_count', 
                 'sales_count', 'is_featured', 'user_full_name', 'status')
    
    def get_user_full_name(self, obj):
        return obj.user.get_full_name()


class TieredCommissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TieredCommission
        fields = ('id', 'min_sales', 'max_sales', 'commission_percentage')


class SellerCategorySerializer(serializers.ModelSerializer):
    category = CategoryListSerializer(read_only=True)
    category_id = serializers.UUIDField(write_only=True)
    
    class Meta:
        model = SellerCategory
        fields = ('id', 'category', 'category_id', 'is_approved')


class SellerReviewSerializer(serializers.ModelSerializer):
    user_full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = SellerReview
        fields = ('id', 'rating', 'comment', 'user_full_name', 
                 'is_approved', 'created_at')
        read_only_fields = ('user_full_name', 'is_approved', 'created_at')
    
    def get_user_full_name(self, obj):
        return obj.user.get_full_name()


class SellerDetailSerializer(serializers.ModelSerializer):
    categories = SellerCategorySerializer(many=True, read_only=True)
    tiered_commissions = TieredCommissionSerializer(many=True, read_only=True)
    reviews = serializers.SerializerMethodField()
    
    class Meta:
        model = Seller
        fields = ('id', 'user', 'shop_name', 'slug', 'description', 'logo', 'banner',
                 'status', 'identification_type', 'identification_number',
                 'identification_image', 'business_license', 'bank_account_number',
                 'bank_sheba', 'bank_card_number', 'bank_name', 'address',
                 'postal_code', 'phone_number', 'email', 'website', 'instagram',
                 'telegram', 'rating', 'review_count', 'sales_count', 'total_revenue',
                 'commission_type', 'commission_value', 'balance', 'is_featured',
                 'created_at', 'updated_at', 'categories', 'tiered_commissions', 'reviews')
        read_only_fields = ('id', 'user', 'rating', 'review_count', 'sales_count', 
                          'total_revenue', 'balance', 'created_at', 'updated_at')
    
    def get_reviews(self, obj):
        # فقط نظرات تایید شده را برمی‌گرداند
        reviews = obj.reviews.filter(is_approved=True).order_by('-created_at')
        return SellerReviewSerializer(reviews, many=True).data


class SellerRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Seller
        fields = ('shop_name', 'description', 'logo', 'identification_type',
                 'identification_number', 'identification_image', 'business_license',
                 'bank_account_number', 'bank_sheba', 'bank_card_number',
                 'bank_name', 'address', 'postal_code', 'phone_number', 'email')
    
    def create(self, validated_data):
        user = self.context['request'].user
        
        # بررسی اینکه کاربر قبلاً فروشنده نباشد
        if hasattr(user, 'seller'):
            raise serializers.ValidationError('شما قبلاً به عنوان فروشنده ثبت‌نام کرده‌اید')
        
        # ایجاد اسلاگ یکتا
        shop_name = validated_data['shop_name']
        slug = slugify(shop_name)
        
        # بررسی یکتا بودن اسلاگ
        if Seller.objects.filter(slug=slug).exists():
            slug = f"{slug}-{user.id}"
        
        # ایجاد فروشنده
        seller = Seller.objects.create(
            user=user,
            slug=slug,
            **validated_data
        )
        
        return seller


class SellerWithdrawalSerializer(serializers.ModelSerializer):
    class Meta:
        model = SellerWithdrawal
        fields = ('id', 'amount', 'status', 'transaction_id', 'description', 
                 'admin_note', 'created_at', 'updated_at')
        read_only_fields = ('id', 'status', 'transaction_id', 'admin_note', 
                          'created_at', 'updated_at')
    
    def validate_amount(self, value):
        seller = self.context['request'].user.seller
        if value > seller.balance:
            raise serializers.ValidationError('مبلغ درخواستی بیشتر از موجودی حساب شما است')
        if value < 100000:  # حداقل مبلغ برداشت 100,000 تومان
            raise serializers.ValidationError('حداقل مبلغ برداشت 100,000 تومان است')
        return value
    
    def create(self, validated_data):
        seller = self.context['request'].user.seller
        return SellerWithdrawal.objects.create(seller=seller, **validated_data)


class AdminSellerUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Seller
        fields = ('status', 'commission_type', 'commission_value', 'is_featured')


class AdminSellerWithdrawalUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SellerWithdrawal
        fields = ('status', 'transaction_id', 'admin_note')