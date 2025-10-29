# Common Utilities Documentation

This document describes the common utilities, middleware, and helper functions available in the SFD application.

## Middleware

### RequestMiddleware

Captures user information from requests and stores it in thread-local storage for logging. Located in `sfd/common/middleware.py`.

```python
class RequestMiddleware:
    """Extract user info and store in thread-local for logging"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        set_user_info_per_thread(request)
        response = self.get_response(request)
        return response
```

**Configuration:**

Add to `settings.py`:

```python
MIDDLEWARE = [
    # ... other middleware ...
    'sfd.common.middleware.RequestMiddleware',
    # ... other middleware ...
]
```

**Features:**

- Extracts username from authenticated user
- Captures client IP address (respects X-Forwarded-For)
- Stores in thread-local storage
- Automatically available in logs

## Logging

### Custom Logging Setup

Enhanced logging with user context. Located in `sfd/common/logging.py`.

#### Thread-Local User Information

```python
def set_user_info_per_thread(request):
    """Store user information in thread-local storage"""
    _thread_local.username = request.user.username if request.user.is_authenticated else None
    
    if request.META.get("HTTP_X_FORWARDED_FOR"):
        ip_address = request.META.get("HTTP_X_FORWARDED_FOR").split(",")[0].strip()
    else:
        ip_address = request.META.get("REMOTE_ADDR")
    
    _thread_local.ip_address = ip_address
```

#### Custom Log Filter

```python
class UserInfoFilter(Filter):
    """Add user information to log records"""
    
    def filter(self, record):
        record.username = getattr(_thread_local, 'username', 'anonymous')
        record.ip_address = getattr(_thread_local, 'ip_address', 'unknown')
        return True
```

### Using the Logger

```python
import logging

logger = logging.getLogger(__name__)

# Log with automatic user context
logger.info("User performed action")
# Output: [INFO] [username: john] [IP: 192.168.1.100] User performed action

logger.error("Operation failed", exc_info=True)
# Includes exception traceback
```

### Log Levels

```python
logger.debug("Detailed debugging information")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error occurred")
logger.critical("Critical failure")
```

### Log Configuration

Located in `sfd_prj/settings_log.py`:

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'user_info': {
            'class': 'sfd.common.logging.UserInfoFilter',
        }
    },
    'formatters': {
        'verbose': {
            'format': '[{levelname}] [{asctime}] [{username}] [{ip_address}] '
                     '[{name}:{lineno}] {message}',
            'style': '{',
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'filters': ['user_info'],
            'formatter': 'verbose'
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/sfd.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'filters': ['user_info'],
            'formatter': 'verbose'
        }
    },
    'loggers': {
        'sfd': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        }
    }
}
```

## Font Utilities

### Japanese Font Registration

Support for Japanese fonts in PDF generation. Located in `sfd/common/font.py`.

```python
def register_japanese_fonts():
    """Register Japanese fonts for ReportLab PDF generation"""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    
    # Register fonts
    font_path = os.path.join(settings.BASE_DIR, 'fonts')
    pdfmetrics.registerFont(TTFont('Japanese', f'{font_path}/ipaexg.ttf'))
    pdfmetrics.registerFont(TTFont('Japanese-Bold', f'{font_path}/ipaexg.ttf'))
```

**Usage:**

Automatically called in `apps.py`:

```python
class SfdConfig(AppConfig):
    def ready(self):
        from sfd.common.font import register_japanese_fonts
        register_japanese_fonts()
```

**In PDF Generation:**

```python
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

def generate_pdf():
    c = canvas.Canvas("output.pdf", pagesize=A4)
    c.setFont('Japanese', 12)
    c.drawString(100, 750, "日本語テキスト")
    c.save()
```

## Form Utilities

### Common Form Helpers

Located in `sfd/common/forms.py`.

#### Dynamic Field Configuration

```python
def configure_form_field(field, required=None, readonly=None, widget=None):
    """Configure form field attributes"""
    if required is not None:
        field.required = required
    
    if readonly:
        field.widget.attrs['readonly'] = True
        field.widget.attrs['disabled'] = True
    
    if widget:
        field.widget = widget
    
    return field
```

#### Form Validation Helpers

```python
def validate_date_range(start_date, end_date, field_name='date'):
    """Validate that end_date >= start_date"""
    from django.forms import ValidationError
    from django.utils.translation import gettext as _
    
    if start_date and end_date and end_date < start_date:
        raise ValidationError({
            field_name: _('End date must be after start date')
        })
```

#### Ajax Form Mixin

```python
class AjaxFormMixin:
    """Mixin to handle AJAX form submissions"""
    
    def form_valid(self, form):
        """Return JSON response for valid form"""
        if self.request.is_ajax():
            form.save()
            return JsonResponse({
                'success': True,
                'message': _('Saved successfully')
            })
        return super().form_valid(form)
    
    def form_invalid(self, form):
        """Return JSON response for invalid form"""
        if self.request.is_ajax():
            return JsonResponse({
                'success': False,
                'errors': form.errors
            }, status=400)
        return super().form_invalid(form)
```

## Date/Time Utilities

### Common Date Operations

Located in `sfd/common/datetime.py`.

```python
from django.utils import timezone
from datetime import datetime, timedelta

def get_fiscal_year(date=None):
    """Get Japanese fiscal year (April 1 - March 31)"""
    if date is None:
        date = timezone.now().date()
    
    if date.month >= 4:
        return date.year
    return date.year - 1

def get_fiscal_year_range(fiscal_year):
    """Get start and end dates of fiscal year"""
    start = datetime(fiscal_year, 4, 1).date()
    end = datetime(fiscal_year + 1, 3, 31).date()
    return start, end

def is_business_day(date, holidays=None):
    """Check if date is a business day (not weekend or holiday)"""
    if date.weekday() >= 5:  # Saturday or Sunday
        return False
    
    if holidays and date in holidays:
        return False
    
    return True

def next_business_day(date, holidays=None):
    """Get next business day"""
    next_day = date + timedelta(days=1)
    while not is_business_day(next_day, holidays):
        next_day += timedelta(days=1)
    return next_day

def format_japanese_date(date):
    """Format date in Japanese style: 2025年10月29日"""
    if date:
        return date.strftime('%Y年%m月%d日')
    return ''

def parse_japanese_date(date_str):
    """Parse Japanese date format to date object"""
    import re
    match = re.match(r'(\d{4})年(\d{1,2})月(\d{1,2})日', date_str)
    if match:
        year, month, day = match.groups()
        return datetime(int(year), int(month), int(day)).date()
    return None
```

### Usage Examples

```python
from sfd.common.datetime import *

# Get current fiscal year
fy = get_fiscal_year()  # e.g., 2025

# Get fiscal year date range
start, end = get_fiscal_year_range(2025)
# Returns: (2025-04-01, 2026-03-31)

# Check business day
from sfd.models import Holiday
holidays = set(Holiday.objects.values_list('date', flat=True))
is_business = is_business_day(date.today(), holidays)

# Format date
formatted = format_japanese_date(date(2025, 10, 29))
# Returns: "2025年10月29日"
```

## Search Utilities

### Search Helper Functions

Located in `sfd/common/search.py` (if exists) or in views.

```python
def build_search_query(model, search_fields, search_term):
    """Build Q object for searching across multiple fields"""
    from django.db.models import Q
    
    query = Q()
    for field in search_fields:
        query |= Q(**{f'{field}__icontains': search_term})
    
    return query

def paginate_queryset(queryset, page_number, per_page=20):
    """Paginate queryset"""
    from django.core.paginator import Paginator, EmptyPage
    
    paginator = Paginator(queryset, per_page)
    try:
        page = paginator.page(page_number)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)
    
    return page
```

### Usage Example

```python
from sfd.models import Person

# Search across multiple fields
search_term = "yamada"
query = build_search_query(
    Person,
    ['family_name', 'name', 'email'],
    search_term
)
results = Person.objects.filter(query, deleted_flg=False)

# Paginate results
page = paginate_queryset(results, request.GET.get('page', 1))
```

## CSV Utilities

### CSV Export Helper

```python
import csv
from django.http import HttpResponse

def export_to_csv(queryset, fields, filename='export.csv'):
    """Export queryset to CSV"""
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    writer = csv.writer(response)
    
    # Write header
    header = [field.verbose_name for field in fields]
    writer.writerow(header)
    
    # Write data
    for obj in queryset:
        row = [getattr(obj, field.name) for field in fields]
        writer.writerow(row)
    
    return response
```

### CSV Import Helper

```python
import csv
from io import StringIO

def import_from_csv(csv_file, model_class, field_mapping):
    """Import data from CSV file"""
    content = csv_file.read().decode('utf-8-sig')
    reader = csv.DictReader(StringIO(content))
    
    created = 0
    updated = 0
    errors = []
    
    for row_num, row in enumerate(reader, start=2):
        try:
            # Map CSV fields to model fields
            data = {}
            for csv_field, model_field in field_mapping.items():
                if csv_field in row:
                    data[model_field] = row[csv_field]
            
            # Create or update
            obj, created_flag = model_class.objects.update_or_create(
                **data
            )
            
            if created_flag:
                created += 1
            else:
                updated += 1
                
        except Exception as e:
            errors.append(f"Row {row_num}: {str(e)}")
    
    return {
        'created': created,
        'updated': updated,
        'errors': errors
    }
```

## Cache Utilities

### Simple Caching

```python
from django.core.cache import cache

def get_cached_or_fetch(key, fetch_func, timeout=3600):
    """Get from cache or fetch and cache"""
    data = cache.get(key)
    if data is None:
        data = fetch_func()
        cache.set(key, data, timeout)
    return data

def invalidate_cache(pattern):
    """Invalidate cache keys matching pattern"""
    from django.core.cache import cache
    keys = cache.keys(pattern)
    if keys:
        cache.delete_many(keys)
```

### Usage Example

```python
def get_person_list():
    """Get cached person list"""
    return get_cached_or_fetch(
        'person_list',
        lambda: list(Person.objects.filter(deleted_flg=False)),
        timeout=3600  # 1 hour
    )

# Invalidate on update
def update_person(person):
    person.save()
    invalidate_cache('person_*')
```

## Validation Utilities

### Common Validators

```python
from django.core.validators import BaseValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

class JapanesePhoneValidator(BaseValidator):
    """Validate Japanese phone number format"""
    message = _('Enter a valid Japanese phone number')
    
    def __call__(self, value):
        import re
        # Match formats: 03-1234-5678, 090-1234-5678, etc.
        pattern = r'^\d{2,4}-\d{1,4}-\d{4}$'
        if not re.match(pattern, value):
            raise ValidationError(self.message, code='invalid')

class PostcodeValidator(BaseValidator):
    """Validate Japanese postcode format"""
    message = _('Enter a valid postcode (e.g., 123-4567)')
    
    def __call__(self, value):
        import re
        pattern = r'^\d{3}-\d{4}$'
        if not re.match(pattern, value):
            raise ValidationError(self.message, code='invalid')
```

### Usage in Models

```python
from django.db import models
from sfd.common.validators import JapanesePhoneValidator

class Person(MasterModel):
    phone_number = models.CharField(
        max_length=20,
        validators=[JapanesePhoneValidator()]
    )
```

## Email Utilities

### Email Sending

```python
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

def send_notification_email(to_email, subject, template_name, context):
    """Send HTML email with text fallback"""
    html_content = render_to_string(template_name, context)
    text_content = strip_tags(html_content)
    
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        to=[to_email]
    )
    email.attach_alternative(html_content, "text/html")
    email.send()

def send_bulk_emails(recipients, subject, message):
    """Send email to multiple recipients"""
    from django.core.mail import send_mass_mail
    
    messages = [
        (subject, message, 'noreply@example.com', [recipient])
        for recipient in recipients
    ]
    send_mass_mail(messages, fail_silently=False)
```

## URL Utilities

### URL Building

```python
from django.urls import reverse
from urllib.parse import urlencode

def build_url_with_params(view_name, params=None, **kwargs):
    """Build URL with query parameters"""
    url = reverse(view_name, kwargs=kwargs)
    if params:
        url += '?' + urlencode(params)
    return url
```

### Usage Example

```python
url = build_url_with_params(
    'sfd:person_list',
    params={'search': 'yamada', 'page': 2}
)
# Returns: /sfd/person/?search=yamada&page=2
```

## Template Tag Utilities

### Custom Template Tags

Create custom tags in `sfd/templatetags/custom_tags.py`:

```python
from django import template

register = template.Library()

@register.simple_tag
def active_class(request, pattern):
    """Return 'active' if URL matches pattern"""
    if request.path.startswith(pattern):
        return 'active'
    return ''

@register.filter
def dict_get(dictionary, key):
    """Get value from dictionary by key"""
    return dictionary.get(key, '')

@register.inclusion_tag('sfd/pagination.html')
def show_pagination(page_obj):
    """Render pagination controls"""
    return {'page_obj': page_obj}
```

## Best Practices

1. **Use thread-local storage carefully**: Only for request-scoped data
2. **Log appropriately**: INFO for important events, DEBUG for details
3. **Cache expensive operations**: But invalidate when data changes
4. **Validate input early**: At form and model levels
5. **Handle exceptions gracefully**: Log and provide user feedback
6. **Use timezone-aware datetimes**: Always use `timezone.now()`
7. **Write reusable utilities**: Keep them focused and well-tested
8. **Document utility functions**: Clear docstrings with examples
9. **Use type hints**: Improves code clarity
10. **Test utilities thoroughly**: They're used everywhere

## Common Patterns

### Decorator for Logging

```python
import logging
from functools import wraps

logger = logging.getLogger(__name__)

def log_execution(func):
    """Decorator to log function execution"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger.info(f"Executing {func.__name__}")
        try:
            result = func(*args, **kwargs)
            logger.info(f"{func.__name__} completed successfully")
            return result
        except Exception as e:
            logger.error(f"{func.__name__} failed: {str(e)}", exc_info=True)
            raise
    return wrapper

@log_execution
def complex_operation():
    # Your code here
    pass
```

### Context Manager for Transactions

```python
from django.db import transaction
from contextlib import contextmanager

@contextmanager
def atomic_operation(log_message=""):
    """Context manager for atomic database operations with logging"""
    logger.info(f"Starting transaction: {log_message}")
    try:
        with transaction.atomic():
            yield
        logger.info(f"Transaction committed: {log_message}")
    except Exception as e:
        logger.error(f"Transaction failed: {log_message} - {str(e)}")
        raise

# Usage
with atomic_operation("Update person records"):
    person.save()
    address.save()
```
