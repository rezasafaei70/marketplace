from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('settings', views.SettingViewSet)
router.register('contacts', views.ContactMessageViewSet)
router.register('faqs', views.FAQViewSet)
router.register('provinces', views.ProvinceViewSet)
router.register('cities', views.CityViewSet)
router.register('banners', views.BannerViewSet)
router.register('newsletters', views.NewsletterViewSet)
router.register('activities', views.ActivityLogViewSet)

# حتماً urlpatterns را به عنوان یک لیست تعریف کنید
urlpatterns = [
    path('', include(router.urls)),
    # سایر مسیرها را اینجا اضافه کنید
]