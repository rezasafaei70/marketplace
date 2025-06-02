from rest_framework import permissions


class IsSellerOwner(permissions.BasePermission):
    """
    فقط به صاحب فروشگاه اجازه می‌دهد
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and hasattr(request.user, 'seller')
    
    def has_object_permission(self, request, view, obj):
        # اگر آبجکت مستقیماً فروشنده باشد
        if hasattr(obj, 'user'):
            return obj.user == request.user
        # اگر آبجکت مرتبط با فروشنده باشد
        if hasattr(obj, 'seller'):
            return obj.seller.user == request.user
        return False


class IsAdminUser(permissions.BasePermission):
    """
    فقط به مدیران سیستم اجازه می‌دهد
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_staff