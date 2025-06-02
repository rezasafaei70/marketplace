from rest_framework import serializers
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum
import random
import string

from .models import (
    Discount, DiscountUsage, LoyaltyPoint, LoyaltyReward, LoyaltyRewardClaim,
    DiscountType
)


class DiscountSerializer(serializers.ModelSerializer):
    discount_type_display = serializers.CharField(source='get_discount_type_display', read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    is_valid = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Discount
        fields = ('id', 'code', 'discount_type', 'discount_type_display', 'value',
                 'max_discount', 'min_purchase', 'start_date', 'end_date',
                 'usage_limit', 'usage_count', 'is_active', 'description',
                 'is_first_purchase_only', 'is_one_time_per_user',
                 'is_for_specific_users', 'is_for_specific_products',
                 'is_expired', 'is_valid', 'created_at', 'updated_at')
        read_only_fields = ('id', 'usage_count', 'created_at', 'updated_at')


class DiscountUsageSerializer(serializers.ModelSerializer):
    discount_code = serializers.CharField(source='discount.code', read_only=True)
    user_full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    
    class Meta:
        model = DiscountUsage
        fields = ('id', 'discount', 'discount_code', 'user', 'user_full_name',
                 'order', 'order_number', 'used_at', 'amount')
        read_only_fields = fields


class LoyaltyPointSerializer(serializers.ModelSerializer):
    user_full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = LoyaltyPoint
        fields = ('id', 'user', 'user_full_name', 'points', 'reason',
                 'reference_id', 'created_at')
        read_only_fields = fields


class LoyaltyRewardSerializer(serializers.ModelSerializer):
    reward_type_display = serializers.CharField(source='get_reward_type_display', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    
    class Meta:
        model = LoyaltyReward
        fields = ('id', 'name', 'description', 'points_required', 'reward_type',
                 'reward_type_display', 'discount_value', 'discount_type',
                 'product', 'product_name', 'is_active', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')


class LoyaltyRewardClaimSerializer(serializers.ModelSerializer):
    reward_name = serializers.CharField(source='reward.name', read_only=True)
    reward_points = serializers.IntegerField(source='reward.points_required', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    user_full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = LoyaltyRewardClaim
        fields = ('id', 'user', 'user_full_name', 'reward', 'reward_name',
                 'reward_points', 'claimed_at', 'status', 'status_display',
                 'discount_code', 'order', 'notes')
        read_only_fields = ('id', 'claimed_at', 'status', 'discount_code', 'order')


class ApplyDiscountSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=50)
    cart_id = serializers.UUIDField()
    
    def validate(self, data):
        code = data.get('code')
        cart_id = data.get('cart_id')
        
        # بررسی کد تخفیف
        try:
            discount = Discount.objects.get(code=code, is_active=True)
        except Discount.DoesNotExist:
            raise serializers.ValidationError('کد تخفیف نامعتبر است')
        
        # بررسی اعتبار کد تخفیف
        if not discount.is_valid:
            if discount.is_expired:
                raise serializers.ValidationError('کد تخفیف منقضی شده است')
            elif discount.is_exhausted:
                raise serializers.ValidationError('کد تخفیف به حداکثر استفاده رسیده است')
            else:
                raise serializers.ValidationError('کد تخفیف نامعتبر است')
        
        # بررسی زمان شروع
        if not discount.is_started:
            raise serializers.ValidationError('کد تخفیف هنوز فعال نشده است')
        
        # بررسی سبد خرید
        from apps.orders.models import Cart, CartStatus
        try:
            cart = Cart.objects.get(id=cart_id, status=CartStatus.OPEN)
        except Cart.DoesNotExist:
            raise serializers.ValidationError('سبد خرید نامعتبر است')
        
        # بررسی کاربر
        user = self.context['request'].user
        
        # بررسی محدودیت کاربران خاص
        if discount.is_for_specific_users and not discount.specific_users.filter(id=user.id).exists():
            raise serializers.ValidationError('این کد تخفیف برای شما قابل استفاده نیست')
        
        # بررسی محدودیت اولین خرید
        if discount.is_first_purchase_only:
            from apps.orders.models import Order
            if Order.objects.filter(user=user).exists():
                raise serializers.ValidationError('این کد تخفیف فقط برای اولین خرید قابل استفاده است')
        
        # بررسی محدودیت یک بار استفاده برای هر کاربر
        if discount.is_one_time_per_user:
            if DiscountUsage.objects.filter(discount=discount, user=user).exists():
                raise serializers.ValidationError('شما قبلاً از این کد تخفیف استفاده کرده‌اید')
        
        # بررسی حداقل خرید
        cart_total = sum(item.total_price for item in cart.items.all())
        if cart_total < discount.min_purchase:
            raise serializers.ValidationError(f'حداقل مبلغ خرید برای استفاده از این کد تخفیف {discount.min_purchase} تومان است')
        
        # بررسی محدودیت محصولات خاص
        if discount.is_for_specific_products:
            # محصولات و دسته‌بندی‌های مجاز
            allowed_products = list(discount.specific_products.values_list('id', flat=True))
            allowed_categories = list(discount.specific_categories.values_list('id', flat=True))
            
            # بررسی محصولات سبد خرید
            valid_items = False
            for item in cart.items.all():
                if item.product.id in allowed_products or item.product.category.id in allowed_categories:
                    valid_items = True
                    break
            
            if not valid_items:
                raise serializers.ValidationError('این کد تخفیف فقط برای محصولات خاص قابل استفاده است')
        
        # محاسبه مبلغ تخفیف
        if discount.discount_type == DiscountType.FIXED:
            discount_amount = discount.value
        else:  # درصدی
            discount_amount = cart_total * (discount.value / 100)
            
            # اعمال حداکثر تخفیف
            if discount.max_discount and discount_amount > discount.max_discount:
                discount_amount = discount.max_discount
        
        data['discount'] = discount
        data['cart'] = cart
        data['discount_amount'] = discount_amount
        
        return data


class ClaimLoyaltyRewardSerializer(serializers.Serializer):
    reward_id = serializers.UUIDField()
    
    def validate(self, data):
        reward_id = data.get('reward_id')
        
        # بررسی جایزه
        try:
            reward = LoyaltyReward.objects.get(id=reward_id, is_active=True)
        except LoyaltyReward.DoesNotExist:
            raise serializers.ValidationError('جایزه مورد نظر یافت نشد یا غیرفعال است')
        
        # بررسی امتیاز کاربر
        user = self.context['request'].user
        user_profile = user.profile
        
        if user_profile.loyalty_points < reward.points_required:
            raise serializers.ValidationError('امتیاز شما برای دریافت این جایزه کافی نیست')
        
        data['reward'] = reward
        return data
    
    @transaction.atomic
    def create(self, validated_data):
        reward = validated_data['reward']
        user = self.context['request'].user
        
        # کسر امتیاز از کاربر
        user_profile = user.profile
        user_profile.loyalty_points -= reward.points_required
        user_profile.save()
        
        # ثبت کسر امتیاز
        LoyaltyPoint.objects.create(
            user=user,
            points=-reward.points_required,
            reason=f"استفاده برای جایزه: {reward.name}",
            reference_id=str(reward.id)
        )
        
        # ایجاد درخواست جایزه
        claim = LoyaltyRewardClaim.objects.create(
            user=user,
            reward=reward,
            status='pending'
        )
        
        # اگر جایزه کد تخفیف است، به صورت خودکار ایجاد و تایید می‌شود
        if reward.reward_type == 'discount':
            # ایجاد کد تخفیف یکتا
            discount_code = f"LOYAL-{user.id}-{''.join(random.choices(string.ascii_uppercase + string.digits, k=6))}"
            
            # ایجاد کد تخفیف
            discount = Discount.objects.create(
                code=discount_code,
                discount_type=reward.discount_type,
                value=reward.discount_value,
                is_one_time_per_user=True,
                is_for_specific_users=True,
                start_date=timezone.now(),
                end_date=timezone.now() + timezone.timedelta(days=30),
                description=f"کد تخفیف جایزه وفاداری: {reward.name}"
            )
            
            # اضافه کردن کاربر به لیست کاربران مجاز
            discount.specific_users.add(user)
            
            # به‌روزرسانی درخواست جایزه
            claim.status = 'approved'
            claim.discount_code = discount_code
            claim.notes = "کد تخفیف به صورت خودکار ایجاد شد"
            claim.save()
        
        return claim