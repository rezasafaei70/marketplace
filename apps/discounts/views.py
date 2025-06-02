from rest_framework import viewsets, permissions, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
import uuid

from .models import (
    Discount, DiscountUsage, LoyaltyPoint, LoyaltyReward, LoyaltyRewardClaim,
    DiscountType
)
from .serializers import (
    DiscountSerializer, DiscountUsageSerializer, LoyaltyPointSerializer,
    LoyaltyRewardSerializer, LoyaltyRewardClaimSerializer,
    ApplyDiscountSerializer, ClaimLoyaltyRewardSerializer
)
from apps.sellers.permissions import IsAdminUser


class DiscountViewSet(viewsets.ModelViewSet):
    queryset = Discount.objects.all()
    serializer_class = DiscountSerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # فیلتر بر اساس وضعیت
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active == 'true')
        
        # فیلتر بر اساس نوع تخفیف
        discount_type = self.request.query_params.get('discount_type')
        if discount_type:
            queryset = queryset.filter(discount_type=discount_type)
        
        # فیلتر بر اساس تاریخ
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(start_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(end_date__lte=end_date)
        
        return queryset


class DiscountUsageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DiscountUsage.objects.all()
    serializer_class = DiscountUsageSerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # فیلتر بر اساس کد تخفیف
        discount_id = self.request.query_params.get('discount_id')
        if discount_id:
            queryset = queryset.filter(discount_id=discount_id)
        
        # فیلتر بر اساس کاربر
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        # فیلتر بر اساس تاریخ
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(used_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(used_at__lte=end_date)
        
        return queryset


class ApplyDiscountView(generics.GenericAPIView):
    serializer_class = ApplyDiscountSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        discount = serializer.validated_data['discount']
        cart = serializer.validated_data['cart']
        discount_amount = serializer.validated_data['discount_amount']
        
        # ذخیره کد تخفیف در سبد خرید
        cart.discount_code = discount.code
        cart.discount_amount = discount_amount
        cart.save()
        
        return Response({
            'status': 'کد تخفیف با موفقیت اعمال شد',
            'discount_code': discount.code,
            'discount_amount': discount_amount,
            'cart_total_before_discount': sum(item.total_price for item in cart.items.all()),
            'cart_total_after_discount': sum(item.total_price for item in cart.items.all()) - discount_amount
        })


class LoyaltyRewardViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LoyaltyReward.objects.filter(is_active=True)
    serializer_class = LoyaltyRewardSerializer
    permission_classes = [permissions.IsAuthenticated]


class LoyaltyPointViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LoyaltyPointSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return LoyaltyPoint.objects.filter(user=self.request.user).order_by('-created_at')
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        user = request.user
        
        # محاسبه مجموع امتیازات
        points = LoyaltyPoint.objects.filter(user=user).aggregate(total=Sum('points'))['total'] or 0
        
        # امتیازات کسب شده
        earned_points = LoyaltyPoint.objects.filter(user=user, points__gt=0).aggregate(total=Sum('points'))['total'] or 0
        
        # امتیازات استفاده شده
        used_points = abs(LoyaltyPoint.objects.filter(user=user, points__lt=0).aggregate(total=Sum('points'))['total'] or 0)
        
        # تاریخچه امتیازات
        recent_points = LoyaltyPoint.objects.filter(user=user).order_by('-created_at')[:5]
        
        return Response({
            'total_points': user.profile.loyalty_points,
            'earned_points': earned_points,
            'used_points': used_points,
            'recent_activity': LoyaltyPointSerializer(recent_points, many=True).data
        })


class LoyaltyRewardClaimViewSet(viewsets.ModelViewSet):
    serializer_class = LoyaltyRewardClaimSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return LoyaltyRewardClaim.objects.filter(user=self.request.user).order_by('-claimed_at')
    
    def create(self, request, *args, **kwargs):
        serializer = ClaimLoyaltyRewardSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        claim = serializer.save()
        
        return Response(
            LoyaltyRewardClaimSerializer(claim).data,
            status=status.HTTP_201_CREATED
        )


class AdminLoyaltyRewardViewSet(viewsets.ModelViewSet):
    queryset = LoyaltyReward.objects.all()
    serializer_class = LoyaltyRewardSerializer
    permission_classes = [IsAdminUser]


class AdminLoyaltyPointViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LoyaltyPoint.objects.all()
    serializer_class = LoyaltyPointSerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # فیلتر بر اساس کاربر
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        return queryset


class AdminLoyaltyRewardClaimViewSet(viewsets.ModelViewSet):
    queryset = LoyaltyRewardClaim.objects.all().order_by('-claimed_at')
    serializer_class = LoyaltyRewardClaimSerializer
    permission_classes = [IsAdminUser]
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        claim = self.get_object()
        new_status = request.data.get('status')
        notes = request.data.get('notes', '')
        
        if new_status not in ['approved', 'rejected', 'delivered']:
            return Response({'error': 'وضعیت نامعتبر است'}, status=status.HTTP_400_BAD_REQUEST)
        
        with transaction.atomic():
            # به‌روزرسانی وضعیت درخواست
            claim.status = new_status
            claim.notes = notes
            claim.save()
            
            # اگر درخواست رد شده، امتیازات را برگردان
            if new_status == 'rejected':
                user_profile = claim.user.profile
                user_profile.loyalty_points += claim.reward.points_required
                user_profile.save()
                
                # ثبت برگشت امتیاز
                LoyaltyPoint.objects.create(
                    user=claim.user,
                    points=claim.reward.points_required,
                    reason=f"برگشت امتیاز به دلیل رد درخواست جایزه: {claim.reward.name}",
                    reference_id=str(claim.id)
                )
        
        return Response({'status': 'وضعیت درخواست با موفقیت به‌روزرسانی شد'})


class AdminManualPointsView(generics.GenericAPIView):
    permission_classes = [IsAdminUser]
    
    def post(self, request, *args, **kwargs):
        user_id = request.data.get('user_id')
        points = request.data.get('points')
        reason = request.data.get('reason', 'تنظیم دستی توسط مدیر')
        
        if not user_id or not points:
            return Response({'error': 'شناسه کاربر و امتیاز الزامی هستند'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'کاربر یافت نشد'}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            points = int(points)
        except ValueError:
            return Response({'error': 'امتیاز باید عددی باشد'}, status=status.HTTP_400_BAD_REQUEST)
        
        with transaction.atomic():
            # به‌روزرسانی امتیاز کاربر
            user_profile = user.profile
            user_profile.loyalty_points += points
            user_profile.save()
            
            # ثبت تغییر امتیاز
            loyalty_point = LoyaltyPoint.objects.create(
                user=user,
                points=points,
                reason=reason,
                reference_id=f"ADMIN-{uuid.uuid4().hex[:8]}"
            )
        
        return Response({
            'status': 'امتیاز با موفقیت اضافه شد',
            'user': user.get_full_name(),
            'points_added': points,
            'new_total_points': user_profile.loyalty_points,
            'loyalty_point': LoyaltyPointSerializer(loyalty_point).data
        })