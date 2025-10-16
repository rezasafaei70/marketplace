
from apps.core import views
from django.urls import path

app_name = 'web_urls'
urlpatterns = [
    path('', views.index, name='index'),
]
