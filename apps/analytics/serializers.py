from rest_framework import serializers
from .models import (
    PageView, ProductView, SearchQuery, CartEvent,
    UserActivity, SalesReport, ProductPerformance
)


class PageViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = PageView
        fields = ('id', 'user', 'session_id', 'url', 'page_title', 'referrer',
                 'user_agent', 'ip_address', 'device_type', 'os', 'browser', 'created_at')
        read_only_fields = ('id', 'created_at')


class ProductViewSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    
    class Meta:
        model = ProductView
        fields = ('id', 'product', 'product_name', 'user', 'session_id',
                 'ip_address', 'referrer', 'created_at')
        read_only_fields = ('id', 'created_at')


class SearchQuerySerializer(serializers.ModelSerializer):
    class Meta:
        model = SearchQuery
        fields = ('id', 'query', 'user', 'session_id', 'results_count',
                 'category', 'created_at')
        read_only_fields = ('id', 'created_at')


class CartEventSerializer(serializers.ModelSerializer):
    event_type_display = serializers.CharField(source='get_event_type_display', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    
    class Meta:
        model = CartEvent
        fields = ('id', 'cart', 'user', 'session_id', 'event_type', 'event_type_display',
                 'product', 'product_name', 'quantity', 'created_at')
        read_only_fields = ('id', 'created_at')


class UserActivitySerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    activity_type_display = serializers.CharField(source='get_activity_type_display', read_only=True)
    
    class Meta:
        model = UserActivity
        fields = ('id', 'user', 'user_name', 'activity_type', 'activity_type_display',
                 'ip_address', 'user_agent', 'object_id', 'description', 'created_at')
        read_only_fields = ('id', 'created_at')


class SalesReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalesReport
        fields = ('id', 'date', 'total_sales', 'total_orders', 'average_order_value',
                 'total_discount', 'total_shipping', 'total_tax', 'total_refund', 'net_sales')
        read_only_fields = fields


class ProductPerformanceSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    
    class Meta:
        model = ProductPerformance
        fields = ('id', 'product', 'product_name', 'date', 'views', 'add_to_carts',
                 'purchases', 'revenue', 'conversion_rate')
        read_only_fields = fields


class TrackPageViewSerializer(serializers.Serializer):
    url = serializers.URLField()
    page_title = serializers.CharField(required=False, allow_blank=True)
    referrer = serializers.URLField(required=False, allow_null=True)
    user_agent = serializers.CharField(required=False, allow_blank=True)
    
    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user if request.user.is_authenticated else None
        session_id = request.session.session_key or 'anonymous'
        ip_address = self._get_client_ip(request)
        
        # تشخیص نوع دستگاه، سیستم عامل و مرورگر
        user_agent = validated_data.get('user_agent', '')
        device_type, os, browser = self._parse_user_agent(user_agent)
        
        page_view = PageView.objects.create(
            user=user,
            session_id=session_id,
            url=validated_data['url'],
            page_title=validated_data.get('page_title', ''),
            referrer=validated_data.get('referrer'),
            user_agent=user_agent,
            ip_address=ip_address,
            device_type=device_type,
            os=os,
            browser=browser
        )
        
        return page_view
    
    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
        return ip
    
    def _parse_user_agent(self, user_agent):
        # این تابع می‌تواند با استفاده از کتابخانه‌های تشخیص user-agent پیاده‌سازی شود
        # برای سادگی، یک پیاده‌سازی ساده ارائه می‌دهیم
        device_type = 'unknown'
        os = 'unknown'
        browser = 'unknown'
        
        user_agent = user_agent.lower()
        
        # تشخیص نوع دستگاه
        if 'mobile' in user_agent or 'android' in user_agent or 'iphone' in user_agent:
            device_type = 'mobile'
        elif 'tablet' in user_agent or 'ipad' in user_agent:
            device_type = 'tablet'
        else:
            device_type = 'desktop'
        
        # تشخیص سیستم عامل
        if 'windows' in user_agent:
            os = 'Windows'
        elif 'mac os' in user_agent or 'macos' in user_agent:
            os = 'MacOS'
        elif 'linux' in user_agent:
            os = 'Linux'
        elif 'android' in user_agent:
            os = 'Android'
        elif 'ios' in user_agent or 'iphone' in user_agent or 'ipad' in user_agent:
            os = 'iOS'
        
        # تشخیص مرورگر
        if 'chrome' in user_agent and 'edge' not in user_agent:
            browser = 'Chrome'
        elif 'firefox' in user_agent:
            browser = 'Firefox'
        elif 'safari' in user_agent and 'chrome' not in user_agent:
            browser = 'Safari'
        elif 'edge' in user_agent:
            browser = 'Edge'
        elif 'opera' in user_agent or 'opr' in user_agent:
            browser = 'Opera'
        
        return device_type, os, browser


class TrackProductViewSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    referrer = serializers.URLField(required=False, allow_null=True)
    
    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user if request.user.is_authenticated else None
        session_id = request.session.session_key or 'anonymous'
        ip_address = self._get_client_ip(request)
        
        from apps.products.models import Product
        try:
            product = Product.objects.get(id=validated_data['product_id'])
        except Product.DoesNotExist:
            raise serializers.ValidationError('محصول مورد نظر یافت نشد')
        
        product_view = ProductView.objects.create(
            product=product,
            user=user,
            session_id=session_id,
            ip_address=ip_address,
            referrer=validated_data.get('referrer')
        )
        
        return product_view
    
    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
        return ip


class TrackSearchQuerySerializer(serializers.Serializer):
    query = serializers.CharField()
    results_count = serializers.IntegerField(required=False, default=0)
    category_id = serializers.UUIDField(required=False, allow_null=True)
    
    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user if request.user.is_authenticated else None
        session_id = request.session.session_key or 'anonymous'
        
        category = None
        if validated_data.get('category_id'):
            from apps.categories.models import Category
            try:
                category = Category.objects.get(id=validated_data['category_id'])
            except Category.DoesNotExist:
                pass
        
        search_query = SearchQuery.objects.create(
            query=validated_data['query'],
            user=user,
            session_id=session_id,
            results_count=validated_data.get('results_count', 0),
            category=category
        )
        
        return search_query


class TrackCartEventSerializer(serializers.Serializer):
    cart_id = serializers.UUIDField()
    event_type = serializers.ChoiceField(choices=CartEvent.event_type_choices)
    product_id = serializers.UUIDField(required=False, allow_null=True)
    quantity = serializers.IntegerField(required=False, allow_null=True)
    
    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user if request.user.is_authenticated else None
        session_id = request.session.session_key or 'anonymous'
        
        from apps.orders.models import Cart
        try:
            cart = Cart.objects.get(id=validated_data['cart_id'])
        except Cart.DoesNotExist:
            raise serializers.ValidationError('سبد خرید مورد نظر یافت نشد')
        
        product = None
        if validated_data.get('product_id'):
            from apps.products.models import Product
            try:
                product = Product.objects.get(id=validated_data['product_id'])
            except Product.DoesNotExist:
                raise serializers.ValidationError('محصول مورد نظر یافت نشد')
        
        cart_event = CartEvent.objects.create(
            cart=cart,
            user=user,
            session_id=session_id,
            event_type=validated_data['event_type'],
            product=product,
            quantity=validated_data.get('quantity')
        )
        
        return cart_event