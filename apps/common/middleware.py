from django.utils.deprecation import MiddlewareMixin
from .models import ActivityLog
from .utils import parse_user_agent, get_client_ip
from django.contrib.contenttypes.models import ContentType


class ActivityLogMiddleware(MiddlewareMixin):
    """Middleware to log user activities"""
    
    def process_request(self, request):
        # Store request info for later use
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        request._activity_log_data = {
            'ip_address': get_client_ip(request),
            'user_agent': user_agent,
            'user_agent_parsed': parse_user_agent(user_agent)
        }
        return None

    def process_response(self, request, response):
        # Log activity if user is authenticated and it's a successful request
        if (hasattr(request, 'user') and 
            request.user.is_authenticated and 
            200 <= response.status_code < 400):
            self.log_activity(request, response)
        return response

    def log_activity(self, request, response):
        try:
            action = self.determine_action(request)
            if action:
                ActivityLog.objects.create(
                    user=request.user,
                    action=action,
                    description=self.get_description(request, action),
                    ip_address=request._activity_log_data.get('ip_address'),
                    user_agent=request._activity_log_data.get('user_agent')
                )
        except Exception:
            # Don't break the request if logging fails
            pass

    def determine_action(self, request):
        method = request.method.lower()
        path = request.path.lower()
        
        if 'login' in path:
            return 'login'
        elif 'logout' in path:
            return 'logout'
        elif 'payment' in path:
            return 'payment'
        elif 'order' in path and method == 'post':
            return 'purchase'
        elif 'review' in path and method == 'post':
            return 'review'
        elif method == 'post':
            return 'create'
        elif method in ['put', 'patch']:
            return 'update'
        elif method == 'delete':
            return 'delete'
        elif method == 'get' and 'search' in request.GET:
            return 'search'
        elif method == 'get':
            return 'view'
        
        return None

    def get_description(self, request, action):
        path = request.path
        method = request.method
        return f"{method} {path}"


class SecurityMiddleware(MiddlewareMixin):
    """Security middleware for additional protection"""
    
    def process_request(self, request):
        # Add security headers
        return None
    
    def process_response(self, request, response):
        # Add security headers
        if not response.get('X-Content-Type-Options'):
            response['X-Content-Type-Options'] = 'nosniff'
        
        if not response.get('X-Frame-Options'):
            response['X-Frame-Options'] = 'DENY'
        
        if not response.get('X-XSS-Protection'):
            response['X-XSS-Protection'] = '1; mode=block'
        
        return response