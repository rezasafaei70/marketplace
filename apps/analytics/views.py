from rest_framework import viewsets, permissions, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Sum, Avg, F, Q
from django.db.models.functions import TruncDate, TruncMonth, TruncWeek
from django.utils import timezone
from datetime import timedelta
import pandas as pd

from .models import (
    PageView, ProductView, SearchQuery, CartEvent,
    UserActivity, SalesReport, ProductPerformance
)
from .serializers import (
    PageViewSerializer, ProductViewSerializer, SearchQuerySerializer,
    CartEventSerializer, UserActivitySerializer, SalesReportSerializer,
    ProductPerformanceSerializer, TrackPageViewSerializer,
    TrackProductViewSerializer, TrackSearchQuerySerializer,
    TrackCartEventSerializer
)
from apps.sellers.permissions import IsAdminUser


class TrackPageViewView(generics.CreateAPIView):
    serializer_class = TrackPageViewSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'status': 'بازدید صفحه ثبت شد'}, status=status.HTTP_201_CREATED)


class TrackProductViewView(generics.CreateAPIView):
    serializer_class = TrackProductViewSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'status': 'بازدید محصول ثبت شد'}, status=status.HTTP_201_CREATED)


class TrackSearchQueryView(generics.CreateAPIView):
    serializer_class = TrackSearchQuerySerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'status': 'جستجو ثبت شد'}, status=status.HTTP_201_CREATED)


class TrackCartEventView(generics.CreateAPIView):
    serializer_class = TrackCartEventSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'status': 'رویداد سبد خرید ثبت شد'}, status=status.HTTP_201_CREATED)


class AdminDashboardView(generics.GenericAPIView):
    permission_classes = [IsAdminUser]
    
    def get(self, request, *args, **kwargs):
        # تاریخ‌های مورد نیاز
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        start_of_week = today - timedelta(days=today.weekday())
        start_of_month = today.replace(day=1)
        
        # آمار فروش
        from apps.orders.models import Order, OrderStatus
        
        # فروش امروز
        today_sales = Order.objects.filter(
            status=OrderStatus.PAID,
            payment_date__date=today
        ).aggregate(
            total=Sum('final_price'),
            count=Count('id')
        )
        
        # فروش دیروز
        yesterday_sales = Order.objects.filter(
            status=OrderStatus.PAID,
            payment_date__date=yesterday
        ).aggregate(
            total=Sum('final_price'),
            count=Count('id')
        )
        
        # فروش این هفته
        week_sales = Order.objects.filter(
            status=OrderStatus.PAID,
            payment_date__date__gte=start_of_week
        ).aggregate(
            total=Sum('final_price'),
            count=Count('id')
        )
        
        # فروش این ماه
        month_sales = Order.objects.filter(
            status=OrderStatus.PAID,
            payment_date__date__gte=start_of_month
        ).aggregate(
            total=Sum('final_price'),
            count=Count('id')
        )
        
        # میانگین ارزش سفارش
        avg_order_value = Order.objects.filter(
            status=OrderStatus.PAID
        ).aggregate(
            avg=Avg('final_price')
        )
        
        # آمار کاربران
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # کاربران جدید امروز
        new_users_today = User.objects.filter(
            date_joined__date=today
        ).count()
        
        # کاربران جدید این هفته
        new_users_week = User.objects.filter(
            date_joined__date__gte=start_of_week
        ).count()
        
        # کل کاربران
        total_users = User.objects.count()
        
        # آمار محصولات
        from apps.products.models import Product
        
        # محصولات پربازدید
        popular_products = ProductView.objects.filter(
            created_at__date__gte=start_of_month
        ).values('product').annotate(
            views=Count('id')
        ).order_by('-views')[:5]
        
        popular_product_ids = [item['product'] for item in popular_products]
        popular_product_details = Product.objects.filter(id__in=popular_product_ids)
        
        # محصولات پرفروش
        from apps.orders.models import OrderItem
        
        best_selling = OrderItem.objects.filter(
            order__status=OrderStatus.PAID,
            order__payment_date__date__gte=start_of_month
        ).values('product').annotate(
            sales=Sum('quantity')
        ).order_by('-sales')[:5]
        
        best_selling_ids = [item['product'] for item in best_selling]
        best_selling_details = Product.objects.filter(id__in=best_selling_ids)
        
        # آمار جستجو
        top_searches = SearchQuery.objects.filter(
            created_at__date__gte=start_of_month
        ).values('query').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        # آمار بازدید
        visits_by_date = PageView.objects.filter(
            created_at__date__gte=start_of_month
        ).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')
        
        # تبدیل به فرمت مناسب برای نمودار
        dates = [item['date'].strftime('%Y-%m-%d') for item in visits_by_date]
        visit_counts = [item['count'] for item in visits_by_date]
        
        # نمودار فروش
        sales_by_date = Order.objects.filter(
            status=OrderStatus.PAID,
            payment_date__date__gte=start_of_month
        ).annotate(
            date=TruncDate('payment_date')
        ).values('date').annotate(
            total=Sum('final_price'),
            count=Count('id')
        ).order_by('date')
        
        # تبدیل به فرمت مناسب برای نمودار
        sale_dates = [item['date'].strftime('%Y-%m-%d') for item in sales_by_date]
        sale_totals = [float(item['total']) for item in sales_by_date]
        sale_counts = [item['count'] for item in sales_by_date]
        
        return Response({
            'sales': {
                'today': {
                    'total': today_sales['total'] or 0,
                    'count': today_sales['count'] or 0
                },
                'yesterday': {
                    'total': yesterday_sales['total'] or 0,
                    'count': yesterday_sales['count'] or 0
                },
                'week': {
                    'total': week_sales['total'] or 0,
                    'count': week_sales['count'] or 0
                },
                'month': {
                    'total': month_sales['total'] or 0,
                    'count': month_sales['count'] or 0
                },
                'avg_order_value': avg_order_value['avg'] or 0
            },
            'users': {
                'new_today': new_users_today,
                'new_week': new_users_week,
                'total': total_users
            },
            'products': {
                'popular': [
                    {
                        'id': str(product.id),
                        'name': product.name,
                        'views': next((item['views'] for item in popular_products if item['product'] == product.id), 0)
                    } for product in popular_product_details
                ],
                'best_selling': [
                    {
                        'id': str(product.id),
                        'name': product.name,
                        'sales': next((item['sales'] for item in best_selling if item['product'] == product.id), 0)
                    } for product in best_selling_details
                ]
            },
            'searches': [
                {
                    'query': item['query'],
                    'count': item['count']
                } for item in top_searches
            ],
            'charts': {
                'visits': {
                    'labels': dates,
                    'data': visit_counts
                },
                'sales': {
                    'labels': sale_dates,
                    'amounts': sale_totals,
                    'counts': sale_counts
                }
            }
        })


class AdminSalesReportViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SalesReport.objects.all().order_by('-date')
    serializer_class = SalesReportSerializer
    permission_classes = [IsAdminUser]
    
    @action(detail=False, methods=['get'])
    def generate(self, request):
        # تاریخ‌های مورد نیاز
        end_date = timezone.now().date()
        start_date = request.query_params.get('start_date')
        if not start_date:
            start_date = end_date - timedelta(days=30)
        else:
            from datetime import datetime
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        
        # تولید گزارش برای هر روز
        from apps.orders.models import Order, OrderStatus
        
        current_date = start_date
        while current_date <= end_date:
            # بررسی آیا گزارش قبلاً ایجاد شده است
            existing_report = SalesReport.objects.filter(date=current_date).first()
            if not existing_report:
                # دریافت داده‌های سفارش برای این روز
                daily_orders = Order.objects.filter(
                    payment_date__date=current_date,
                    status=OrderStatus.PAID
                )
                
                if daily_orders.exists():
                    # محاسبه آمار فروش
                    order_stats = daily_orders.aggregate(
                        total_sales=Sum('final_price'),
                        total_orders=Count('id'),
                        total_discount=Sum('total_discount'),
                        total_shipping=Sum('shipping_cost'),
                        total_tax=Sum('tax')
                    )
                    
                    # محاسبه برگشتی‌ها
                    refunded_orders = Order.objects.filter(
                        payment_date__date=current_date,
                        status=OrderStatus.REFUNDED
                    )
                    
                    total_refund = refunded_orders.aggregate(total=Sum('final_price'))['total'] or 0
                    
                    # محاسبه میانگین ارزش سفارش
                    average_order_value = 0
                    if order_stats['total_orders'] > 0:
                        average_order_value = order_stats['total_sales'] / order_stats['total_orders']
                    
                    # محاسبه فروش خالص
                    net_sales = order_stats['total_sales'] - total_refund
                    
                    # ایجاد گزارش
                    SalesReport.objects.create(
                        date=current_date,
                        total_sales=order_stats['total_sales'] or 0,
                        total_orders=order_stats['total_orders'] or 0,
                        average_order_value=average_order_value,
                        total_discount=order_stats['total_discount'] or 0,
                        total_shipping=order_stats['total_shipping'] or 0,
                        total_tax=order_stats['total_tax'] or 0,
                        total_refund=total_refund,
                        net_sales=net_sales
                    )
            
            current_date += timedelta(days=1)
        
        # بازگرداندن گزارش‌های ایجاد شده
        reports = SalesReport.objects.filter(date__range=[start_date, end_date]).order_by('date')
        serializer = self.get_serializer(reports, many=True)
        
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        # دریافت پارامترهای فیلتر
        period = request.query_params.get('period', 'month')  # day, week, month, year
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        # تنظیم تاریخ‌ها
        if start_date and end_date:
            from datetime import datetime
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        else:
            end_date = timezone.now().date()
            if period == 'day':
                start_date = end_date
            elif period == 'week':
                start_date = end_date - timedelta(days=7)
            elif period == 'month':
                start_date = end_date - timedelta(days=30)
            else:  # year
                start_date = end_date - timedelta(days=365)
        
        # دریافت گزارش‌ها
        reports = SalesReport.objects.filter(date__range=[start_date, end_date])
        
        if not reports.exists():
            return Response({
                'error': 'داده‌ای برای این بازه زمانی یافت نشد'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # محاسبه آمار کلی
        summary = reports.aggregate(
            total_sales=Sum('total_sales'),
            total_orders=Sum('total_orders'),
            total_discount=Sum('total_discount'),
            total_shipping=Sum('total_shipping'),
            total_tax=Sum('total_tax'),
            total_refund=Sum('total_refund'),
            net_sales=Sum('net_sales')
        )
        
        # محاسبه میانگین ارزش سفارش
        average_order_value = 0
        if summary['total_orders'] > 0:
            average_order_value = summary['total_sales'] / summary['total_orders']
        
        # تهیه داده‌های نمودار
        if period == 'day':
            # نمودار ساعتی
            from apps.orders.models import Order, OrderStatus
            hourly_data = Order.objects.filter(
                payment_date__date=start_date,
                status=OrderStatus.PAID
            ).annotate(
                hour=F('payment_date__hour')
            ).values('hour').annotate(
                total=Sum('final_price'),
                count=Count('id')
            ).order_by('hour')
            
            labels = [f"{h:02d}:00" for h in range(24)]
            sales_data = [0] * 24
            orders_data = [0] * 24
            
            for item in hourly_data:
                hour = item['hour']
                sales_data[hour] = float(item['total'])
                orders_data[hour] = item['count']
            
            chart_data = {
                'labels': labels,
                'sales': sales_data,
                'orders': orders_data
            }
        else:
            # نمودار روزانه/هفتگی/ماهانه
            if period == 'week':
                # گروه‌بندی روزانه
                labels = []
                sales_data = []
                orders_data = []
                
                current_date = start_date
                while current_date <= end_date:
                    labels.append(current_date.strftime('%Y-%m-%d'))
                    
                    daily_report = reports.filter(date=current_date).first()
                    if daily_report:
                        sales_data.append(float(daily_report.total_sales))
                        orders_data.append(daily_report.total_orders)
                    else:
                        sales_data.append(0)
                        orders_data.append(0)
                    
                    current_date += timedelta(days=1)
            elif period == 'month':
                # گروه‌بندی روزانه
                labels = []
                sales_data = []
                orders_data = []
                
                current_date = start_date
                while current_date <= end_date:
                    labels.append(current_date.strftime('%Y-%m-%d'))
                    
                    daily_report = reports.filter(date=current_date).first()
                    if daily_report:
                        sales_data.append(float(daily_report.total_sales))
                        orders_data.append(daily_report.total_orders)
                    else:
                        sales_data.append(0)
                        orders_data.append(0)
                    
                    current_date += timedelta(days=1)
            else:  # year
                # گروه‌بندی ماهانه
                monthly_data = pd.DataFrame(list(reports.values()))
                monthly_data['month'] = pd.to_datetime(monthly_data['date']).dt.strftime('%Y-%m')
                monthly_grouped = monthly_data.groupby('month').agg({
                    'total_sales': 'sum',
                    'total_orders': 'sum'
                }).reset_index()
                
                labels = monthly_grouped['month'].tolist()
                sales_data = monthly_grouped['total_sales'].astype(float).tolist()
                orders_data = monthly_grouped['total_orders'].tolist()
            
            chart_data = {
                'labels': labels,
                'sales': sales_data,
                'orders': orders_data
            }
        
        return Response({
            'summary': {
                'total_sales': summary['total_sales'],
                'total_orders': summary['total_orders'],
                'average_order_value': average_order_value,
                'total_discount': summary['total_discount'],
                'total_shipping': summary['total_shipping'],
                'total_tax': summary['total_tax'],
                'total_refund': summary['total_refund'],
                'net_sales': summary['net_sales'],
                'period': period,
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d')
            },
            'chart': chart_data
        })


class AdminProductPerformanceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ProductPerformance.objects.all().order_by('-date')
    serializer_class = ProductPerformanceSerializer
    permission_classes = [IsAdminUser]
    
    @action(detail=False, methods=['get'])
    def generate(self, request):
        # تاریخ‌های مورد نیاز
        end_date = timezone.now().date()
        start_date = request.query_params.get('start_date')
        if not start_date:
            start_date = end_date - timedelta(days=30)
        else:
            from datetime import datetime
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        
        # دریافت همه محصولات
        from apps.products.models import Product
        products = Product.objects.all()
        
        # تولید گزارش برای هر محصول و هر روز
        from apps.orders.models import OrderItem
        
        for product in products:
            current_date = start_date
            while current_date <= end_date:
                # بررسی آیا گزارش قبلاً ایجاد شده است
                existing_report = ProductPerformance.objects.filter(
                    product=product,
                    date=current_date
                ).first()
                
                if not existing_report:
                    # محاسبه بازدیدها
                    views = ProductView.objects.filter(
                        product=product,
                        created_at__date=current_date
                    ).count()
                    
                    # محاسبه افزودن به سبد
                    add_to_carts = CartEvent.objects.filter(
                        product=product,
                        event_type='add',
                        created_at__date=current_date
                    ).count()
                    
                    # محاسبه خریدها
                    purchases_data = OrderItem.objects.filter(
                        product=product,
                        order__payment_date__date=current_date,
                        order__status='paid'
                    ).aggregate(
                        purchases=Sum('quantity'),
                        revenue=Sum(F('quantity') * F('unit_price'))
                    )
                    
                    purchases = purchases_data['purchases'] or 0
                    revenue = purchases_data['revenue'] or 0
                    
                    # محاسبه نرخ تبدیل
                    conversion_rate = 0
                    if views > 0:
                        conversion_rate = (purchases / views) * 100
                    
                    # ایجاد گزارش
                    ProductPerformance.objects.create(
                        product=product,
                        date=current_date,
                        views=views,
                        add_to_carts=add_to_carts,
                        purchases=purchases,
                        revenue=revenue,
                        conversion_rate=conversion_rate
                    )
                
                current_date += timedelta(days=1)
        
        # بازگرداندن گزارش‌های ایجاد شده
        product_id = request.query_params.get('product_id')
        if product_id:
            reports = ProductPerformance.objects.filter(
                product_id=product_id,
                date__range=[start_date, end_date]
            ).order_by('date')
        else:
            reports = ProductPerformance.objects.filter(
                date__range=[start_date, end_date]
            ).order_by('-revenue')[:20]  # فقط 20 محصول برتر
        
        serializer = self.get_serializer(reports, many=True)
        
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def top_products(self, request):
        # دریافت پارامترهای فیلتر
        period = request.query_params.get('period', 'month')  # week, month, year
        metric = request.query_params.get('metric', 'revenue')  # revenue, purchases, views, conversion
        
        # تنظیم تاریخ‌ها
        end_date = timezone.now().date()
        if period == 'week':
            start_date = end_date - timedelta(days=7)
        elif period == 'month':
            start_date = end_date - timedelta(days=30)
        else:  # year
            start_date = end_date - timedelta(days=365)
        
        # گروه‌بندی داده‌ها بر اساس محصول
        reports = ProductPerformance.objects.filter(
            date__range=[start_date, end_date]
        ).values(
            'product', 'product__name'
        ).annotate(
            total_views=Sum('views'),
            total_add_to_carts=Sum('add_to_carts'),
            total_purchases=Sum('purchases'),
            total_revenue=Sum('revenue'),
            avg_conversion_rate=Avg('conversion_rate')
        )
        
        # مرتب‌سازی بر اساس معیار انتخاب شده
        if metric == 'revenue':
            reports = reports.order_by('-total_revenue')
        elif metric == 'purchases':
            reports = reports.order_by('-total_purchases')
        elif metric == 'views':
            reports = reports.order_by('-total_views')
        else:  # conversion
            reports = reports.order_by('-avg_conversion_rate')
        
        # محدود کردن به 10 محصول برتر
        reports = reports[:10]
        
        return Response({
            'period': period,
            'metric': metric,
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'products': [
                {
                    'id': str(item['product']),
                    'name': item['product__name'],
                    'views': item['total_views'],
                    'add_to_carts': item['total_add_to_carts'],
                    'purchases': item['total_purchases'],
                    'revenue': float(item['total_revenue']),
                    'conversion_rate': item['avg_conversion_rate']
                } for item in reports
            ]
        })


class AdminPageViewViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PageView.objects.all().order_by('-created_at')
    serializer_class = PageViewSerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # فیلتر بر اساس URL
        url = self.request.query_params.get('url')
        if url:
            queryset = queryset.filter(url__icontains=url)
        
        # فیلتر بر اساس کاربر
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        # فیلتر بر اساس نوع دستگاه
        device_type = self.request.query_params.get('device_type')
        if device_type:
            queryset = queryset.filter(device_type=device_type)
        
        # فیلتر بر اساس تاریخ
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        # دریافت پارامترهای فیلتر
        period = request.query_params.get('period', 'month')  # day, week, month, year
        
        # تنظیم تاریخ‌ها
        end_date = timezone.now().date()
        if period == 'day':
            start_date = end_date
        elif period == 'week':
            start_date = end_date - timedelta(days=7)
        elif period == 'month':
            start_date = end_date - timedelta(days=30)
        else:  # year
            start_date = end_date - timedelta(days=365)
        
        # آمار کلی
        total_views = PageView.objects.filter(
            created_at__date__range=[start_date, end_date]
        ).count()
        
        unique_visitors = PageView.objects.filter(
            created_at__date__range=[start_date, end_date]
        ).values('session_id').distinct().count()
        
        # آمار بر اساس نوع دستگاه
        device_stats = PageView.objects.filter(
            created_at__date__range=[start_date, end_date]
        ).values('device_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # صفحات پربازدید
        top_pages = PageView.objects.filter(
            created_at__date__range=[start_date, end_date]
        ).values('url', 'page_title').annotate(
            views=Count('id')
        ).order_by('-views')[:10]
        
        # آمار بر اساس مرورگر
        browser_stats = PageView.objects.filter(
            created_at__date__range=[start_date, end_date]
        ).values('browser').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # آمار بر اساس سیستم عامل
        os_stats = PageView.objects.filter(
            created_at__date__range=[start_date, end_date]
        ).values('os').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # نمودار بازدید بر اساس زمان
        if period == 'day':
            # نمودار ساعتی
            time_stats = PageView.objects.filter(
                created_at__date=end_date
            ).annotate(
                hour=F('created_at__hour')
            ).values('hour').annotate(
                count=Count('id')
            ).order_by('hour')
            
            labels = [f"{h:02d}:00" for h in range(24)]
            data = [0] * 24
            
            for item in time_stats:
                hour = item['hour']
                data[hour] = item['count']
        elif period == 'week':
            # نمودار روزانه
            time_stats = PageView.objects.filter(
                created_at__date__range=[start_date, end_date]
            ).annotate(
                date=TruncDate('created_at')
            ).values('date').annotate(
                count=Count('id')
            ).order_by('date')
            
            labels = []
            data = []
            
            current_date = start_date
            while current_date <= end_date:
                labels.append(current_date.strftime('%Y-%m-%d'))
                
                count = next((item['count'] for item in time_stats if item['date'] == current_date), 0)
                data.append(count)
                
                current_date += timedelta(days=1)
        elif period == 'month':
            # نمودار روزانه
            time_stats = PageView.objects.filter(
                created_at__date__range=[start_date, end_date]
            ).annotate(
                date=TruncDate('created_at')
            ).values('date').annotate(
                count=Count('id')
            ).order_by('date')
            
            labels = []
            data = []
            
            current_date = start_date
            while current_date <= end_date:
                labels.append(current_date.strftime('%Y-%m-%d'))
                
                count = next((item['count'] for item in time_stats if item['date'] == current_date), 0)
                data.append(count)
                
                current_date += timedelta(days=1)
        else:  # year
            # نمودار ماهانه
            time_stats = PageView.objects.filter(
                created_at__date__range=[start_date, end_date]
            ).annotate(
                month=TruncMonth('created_at')
            ).values('month').annotate(
                count=Count('id')
            ).order_by('month')
            
            labels = [item['month'].strftime('%Y-%m') for item in time_stats]
            data = [item['count'] for item in time_stats]
        
        return Response({
            'summary': {
                'total_views': total_views,
                'unique_visitors': unique_visitors,
                'period': period,
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d')
            },
            'device_stats': [
                {
                    'device_type': item['device_type'] or 'unknown',
                    'count': item['count'],
                    'percentage': (item['count'] / total_views * 100) if total_views > 0 else 0
                } for item in device_stats
            ],
            'browser_stats': [
                {
                    'browser': item['browser'] or 'unknown',
                    'count': item['count'],
                    'percentage': (item['count'] / total_views * 100) if total_views > 0 else 0
                } for item in browser_stats
            ],
            'os_stats': [
                {
                    'os': item['os'] or 'unknown',
                    'count': item['count'],
                    'percentage': (item['count'] / total_views * 100) if total_views > 0 else 0
                } for item in os_stats
            ],
            'top_pages': [
                {
                    'url': item['url'],
                    'title': item['page_title'] or item['url'],
                    'views': item['views'],
                    'percentage': (item['views'] / total_views * 100) if total_views > 0 else 0
                } for item in top_pages
            ],
            'chart': {
                'labels': labels,
                'data': data
            }
        })


class AdminSearchQueryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SearchQuery.objects.all().order_by('-created_at')
    serializer_class = SearchQuerySerializer
    permission_classes = [IsAdminUser]
    
    @action(detail=False, methods=['get'])
    def popular(self, request):
        # دریافت پارامترهای فیلتر
        period = request.query_params.get('period', 'month')  # week, month, year
        
        # تنظیم تاریخ‌ها
        end_date = timezone.now().date()
        if period == 'week':
            start_date = end_date - timedelta(days=7)
        elif period == 'month':
            start_date = end_date - timedelta(days=30)
        else:  # year
            start_date = end_date - timedelta(days=365)
        
        # عبارات جستجوی محبوب
        popular_queries = SearchQuery.objects.filter(
            created_at__date__range=[start_date, end_date]
        ).values('query').annotate(
            count=Count('id'),
            avg_results=Avg('results_count')
        ).order_by('-count')[:20]
        
        # عبارات جستجوی بدون نتیجه
        zero_result_queries = SearchQuery.objects.filter(
            created_at__date__range=[start_date, end_date],
            results_count=0
        ).values('query').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        return Response({
            'period': period,
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'popular_queries': [
                {
                    'query': item['query'],
                    'count': item['count'],
                    'avg_results': item['avg_results']
                } for item in popular_queries
            ],
            'zero_result_queries': [
                {
                    'query': item['query'],
                    'count': item['count']
                } for item in zero_result_queries
            ]
        })


class AdminUserActivityViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = UserActivity.objects.all().order_by('-created_at')
    serializer_class = UserActivitySerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # فیلتر بر اساس کاربر
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        # فیلتر بر اساس نوع فعالیت
        activity_type = self.request.query_params.get('activity_type')
        if activity_type:
            queryset = queryset.filter(activity_type=activity_type)
        
        # فیلتر بر اساس تاریخ
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        
        return queryset