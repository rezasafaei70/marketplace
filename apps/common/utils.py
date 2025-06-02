import random
import string
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import requests
import json
import re


def generate_random_string(length=10):
    """Generate random string"""
    letters = string.ascii_lowercase + string.digits
    return ''.join(random.choice(letters) for i in range(length))


def generate_otp():
    """Generate 6 digit OTP"""
    return str(random.randint(100000, 999999))


def send_sms(phone, message, template=None):
    """Send SMS using Kavenegar API"""
    try:
        from kavenegar import KavenegarAPI
        api = KavenegarAPI(settings.SMS_API_KEY)
        
        if template:
            # Send template SMS
            params = {
                'receptor': phone,
                'template': template,
                'token': message,
            }
            response = api.verify_lookup(params)
        else:
            # Send simple SMS
            response = api.sms_send({
                'sender': settings.SMS_SENDER,
                'receptor': phone,
                'message': message
            })
        
        return response
    except Exception as e:
        print(f"SMS Error: {e}")
        return None


def send_otp_sms(phone, otp):
    """Send OTP SMS"""
    message = f"کد تایید شما: {otp}"
    return send_sms(phone, otp, template=settings.SMS_OTP_TEMPLATE)


def send_email_notification(subject, message, recipient_list, html_message=None):
    """Send email notification"""
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Email Error: {e}")
        return False


def render_email_template(template_name, context):
    """Render email template"""
    html_message = render_to_string(f'emails/{template_name}.html', context)
    plain_message = strip_tags(html_message)
    return html_message, plain_message


def get_client_ip(request):
    """Get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def parse_user_agent(user_agent_string):
    """Parse user agent string to extract browser and OS info"""
    if not user_agent_string:
        return {
            'browser': 'Unknown',
            'browser_version': 'Unknown',
            'os': 'Unknown',
            'device': 'Unknown',
            'is_mobile': False,
            'is_tablet': False,
            'is_desktop': True
        }
    
    user_agent_string = user_agent_string.lower()
    
    # Browser detection
    browser = 'Unknown'
    browser_version = 'Unknown'
    
    if 'chrome' in user_agent_string and 'edg' not in user_agent_string:
        browser = 'Chrome'
        match = re.search(r'chrome/([0-9.]+)', user_agent_string)
        if match:
            browser_version = match.group(1)
    elif 'firefox' in user_agent_string:
        browser = 'Firefox'
        match = re.search(r'firefox/([0-9.]+)', user_agent_string)
        if match:
            browser_version = match.group(1)
    elif 'safari' in user_agent_string and 'chrome' not in user_agent_string:
        browser = 'Safari'
        match = re.search(r'safari/([0-9.]+)', user_agent_string)
        if match:
            browser_version = match.group(1)
    elif 'edg' in user_agent_string:
        browser = 'Edge'
        match = re.search(r'edg/([0-9.]+)', user_agent_string)
        if match:
            browser_version = match.group(1)
    elif 'opera' in user_agent_string or 'opr' in user_agent_string:
        browser = 'Opera'
        match = re.search(r'(opera|opr)/([0-9.]+)', user_agent_string)
        if match:
            browser_version = match.group(2)
    
    # OS detection
    os = 'Unknown'
    if 'windows' in user_agent_string:
        os = 'Windows'
        if 'windows nt 10' in user_agent_string:
            os = 'Windows 10'
        elif 'windows nt 6.3' in user_agent_string:
            os = 'Windows 8.1'
        elif 'windows nt 6.2' in user_agent_string:
            os = 'Windows 8'
        elif 'windows nt 6.1' in user_agent_string:
            os = 'Windows 7'
    elif 'mac os x' in user_agent_string or 'macos' in user_agent_string:
        os = 'macOS'
        match = re.search(r'mac os x ([0-9_]+)', user_agent_string)
        if match:
            version = match.group(1).replace('_', '.')
            os = f'macOS {version}'
    elif 'linux' in user_agent_string:
        os = 'Linux'
        if 'ubuntu' in user_agent_string:
            os = 'Ubuntu'
        elif 'android' in user_agent_string:
            os = 'Android'
    elif 'iphone' in user_agent_string or 'ipad' in user_agent_string:
        os = 'iOS'
        match = re.search(r'os ([0-9_]+)', user_agent_string)
        if match:
            version = match.group(1).replace('_', '.')
            os = f'iOS {version}'
    
    # Device detection
    device = 'Desktop'
    is_mobile = False
    is_tablet = False
    is_desktop = True
    
    if any(mobile in user_agent_string for mobile in ['mobile', 'iphone', 'android', 'blackberry', 'windows phone']):
        device = 'Mobile'
        is_mobile = True
        is_desktop = False
    elif any(tablet in user_agent_string for tablet in ['ipad', 'tablet', 'kindle']):
        device = 'Tablet'
        is_tablet = True
        is_desktop = False
    
    return {
        'browser': browser,
        'browser_version': browser_version,
        'os': os,
        'device': device,
        'is_mobile': is_mobile,
        'is_tablet': is_tablet,
        'is_desktop': is_desktop
    }


def validate_iranian_phone(phone):
    """Validate Iranian phone number"""
    pattern = r'^(\+98|0)?9\d{9}$'
    return bool(re.match(pattern, phone))


def normalize_phone(phone):
    """Normalize phone number to standard format"""
    phone = phone.strip().replace(' ', '').replace('-', '')
    if phone.startswith('+98'):
        phone = phone[3:]
    elif phone.startswith('0098'):
        phone = phone[4:]
    elif phone.startswith('98'):
        phone = phone[2:]
    
    if not phone.startswith('0'):
        phone = '0' + phone
    
    return phone


def jalali_to_gregorian(jalali_date):
    """Convert Jalali date to Gregorian"""
    try:
        import jdatetime
        if isinstance(jalali_date, str):
            # Parse string date
            parts = jalali_date.split('-')
            if len(parts) == 3:
                year, month, day = map(int, parts)
                j_date = jdatetime.date(year, month, day)
                return j_date.togregorian()
        elif isinstance(jalali_date, jdatetime.date):
            return jalali_date.togregorian()
    except:
        pass
    return None


def gregorian_to_jalali(gregorian_date):
    """Convert Gregorian date to Jalali"""
    try:
        import jdatetime
        if hasattr(gregorian_date, 'date'):
            gregorian_date = gregorian_date.date()
        return jdatetime.date.fromgregorian(date=gregorian_date)
    except:
        pass
    return None


def format_price(price):
    """Format price with thousand separators"""
    return f"{price:,}"


def calculate_discount_amount(price, discount_percent):
    """Calculate discount amount"""
    return int(price * discount_percent / 100)


def slugify_persian(text):
    """Create slug from Persian text"""
    from django.utils.text import slugify
    
    # Replace Persian characters
    persian_map = {
        'آ': 'a', 'ا': 'a', 'ب': 'b', 'پ': 'p', 'ت': 't', 'ث': 's',
        'ج': 'j', 'چ': 'ch', 'ح': 'h', 'خ': 'kh', 'د': 'd', 'ذ': 'z',
        'ر': 'r', 'ز': 'z', 'ژ': 'zh', 'س': 's', 'ش': 'sh', 'ص': 's',
        'ض': 'z', 'ط': 't', 'ظ': 'z', 'ع': 'a', 'غ': 'gh', 'ف': 'f',
        'ق': 'gh', 'ک': 'k', 'گ': 'g', 'ل': 'l', 'م': 'm', 'ن': 'n',
        'و': 'v', 'ه': 'h', 'ی': 'y'
    }
    
    for persian, english in persian_map.items():
        text = text.replace(persian, english)
    
    return slugify(text)


def detect_device_type(user_agent_string):
    """Detect device type from user agent"""
    if not user_agent_string:
        return 'unknown'
    
    user_agent_string = user_agent_string.lower()
    
    if any(mobile in user_agent_string for mobile in ['mobile', 'iphone', 'android', 'blackberry', 'windows phone']):
        return 'mobile'
    elif any(tablet in user_agent_string for tablet in ['ipad', 'tablet', 'kindle']):
        return 'tablet'
    else:
        return 'desktop'


def get_location_from_ip(ip_address):
    """Get location information from IP address"""
    try:
        # Using a free IP geolocation service
        response = requests.get(f'http://ip-api.com/json/{ip_address}', timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data['status'] == 'success':
                return {
                    'country': data.get('country', 'Unknown'),
                    'country_code': data.get('countryCode', 'Unknown'),
                    'region': data.get('regionName', 'Unknown'),
                    'city': data.get('city', 'Unknown'),
                    'timezone': data.get('timezone', 'Unknown'),
                    'isp': data.get('isp', 'Unknown')
                }
    except:
        pass
    
    return {
        'country': 'Unknown',
        'country_code': 'Unknown',
        'region': 'Unknown',
        'city': 'Unknown',
        'timezone': 'Unknown',
        'isp': 'Unknown'
    }


def mask_sensitive_data(data, field_name):
    """Mask sensitive data like phone numbers, emails"""
    if not data:
        return data
    
    if field_name == 'phone':
        if len(data) > 6:
            return data[:3] + '*' * (len(data) - 6) + data[-3:]
    elif field_name == 'email':
        if '@' in data:
            username, domain = data.split('@', 1)
            if len(username) > 2:
                masked_username = username[:2] + '*' * (len(username) - 2)
                return f"{masked_username}@{domain}"
    elif field_name == 'card_number':
        if len(data) > 8:
            return data[:4] + '*' * (len(data) - 8) + data[-4:]
    
    return data


def generate_tracking_code():
    """Generate unique tracking code"""
    import uuid
    return str(uuid.uuid4()).replace('-', '').upper()[:10]


def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points using Haversine formula"""
    from math import radians, cos, sin, asin, sqrt
    
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371  # Radius of earth in kilometers
    
    return c * r


def validate_national_code(national_code):
    """Validate Iranian national code"""
    if not national_code or len(national_code) != 10:
        return False
    
    if not national_code.isdigit():
        return False
    
    # Check for invalid patterns
    if national_code in ['0000000000', '1111111111', '2222222222', '3333333333',
                        '4444444444', '5555555555', '6666666666', '7777777777',
                        '8888888888', '9999999999']:
        return False
    
    # Calculate check digit
    check = 0
    for i in range(9):
        check += int(national_code[i]) * (10 - i)
    
    check = check % 11
    
    if check < 2:
        return check == int(national_code[9])
    else:
        return (11 - check) == int(national_code[9])


def clean_html(html_content):
    """Clean HTML content and remove dangerous tags"""
    import bleach
    
    allowed_tags = [
        'p', 'br', 'strong', 'b', 'em', 'i', 'u', 'ul', 'ol', 'li',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'code', 'pre'
    ]
    
    allowed_attributes = {
        '*': ['class'],
        'a': ['href', 'title'],
        'img': ['src', 'alt', 'width', 'height']
    }
    
    return bleach.clean(html_content, tags=allowed_tags, attributes=allowed_attributes)


class CacheManager:
    """Cache management utility"""
    
    @staticmethod
    def get_cache_key(prefix, *args):
        """Generate cache key"""
        key_parts = [str(arg) for arg in args]
        cache_prefix = getattr(settings, 'CACHE_KEY_PREFIX', 'shop_')
        return f"{cache_prefix}{prefix}:{'_'.join(key_parts)}"
    
    @staticmethod
    def set_cache(key, value, timeout=None):
        """Set cache value"""
        from django.core.cache import cache
        if timeout is None:
            timeout = getattr(settings, 'CACHE_TTL', 300)
        cache.set(key, value, timeout)
    
    @staticmethod
    def get_cache(key, default=None):
        """Get cache value"""
        from django.core.cache import cache
        return cache.get(key, default)
    
    @staticmethod
    def delete_cache(key):
        """Delete cache value"""
        from django.core.cache import cache
        cache.delete(key)
    
    @staticmethod
    def clear_cache_pattern(pattern):
        """Clear cache by pattern"""
        from django.core.cache import cache
        try:
            cache.delete_many(cache.keys(f"*{pattern}*"))
        except:
            # Some cache backends don't support keys() method
            pass


class RateLimiter:
    """Simple rate limiting utility"""
    
    @staticmethod
    def is_rate_limited(key, limit=60, period=60):
        """Check if action is rate limited"""
        from django.core.cache import cache
        
        current_count = cache.get(key, 0)
        if current_count >= limit:
            return True
        
        cache.set(key, current_count + 1, period)
        return False
    
    @staticmethod
    def get_rate_limit_key(user_id, action):
        """Generate rate limit key"""
        return f"rate_limit:{user_id}:{action}"