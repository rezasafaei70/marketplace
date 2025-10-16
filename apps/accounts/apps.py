from django.apps import AppConfig
from django.contrib import admin

class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.accounts'
    
    def ready(self):
        # تنظیمات پنل ادمین
        admin.site.site_header = "🚀 پنل مدیریت سیستم"
        admin.site.site_title = "مدیریت"
        admin.site.index_title = "خوش آمدید به پنل مدیریت 👋"