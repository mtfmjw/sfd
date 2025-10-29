# API Reference

Quick reference for commonly used classes, methods, and utilities in the SFD application.

## Models

### BaseModel

**Location**: `sfd/models/base.py`

**Fields**:
- `created_by` (CharField): Username who created the record
- `created_at` (DateTimeField): Timestamp of creation
- `updated_by` (CharField): Username who last updated the record
- `updated_at` (DateTimeField): Timestamp of last update
- `deleted_flg` (BooleanField): Soft deletion flag

**Methods**:
```python
@classmethod
def get_unique_field_names(cls) -> list[str]
    """Returns list of field names that form unique constraint"""

@classmethod
def get_local_concrete_fields(cls) -> list[models.Field]
    """Returns list of concrete fields excluding auto-created fields"""
```

### MasterModel

**Location**: `sfd/models/base.py`

**Inherits**: BaseModel

**Additional Fields**:
- `valid_from` (DateField): Start of validity period
- `valid_to` (DateField): End of validity period

**Methods**:
```python
@classmethod
def get_master_model_fields(cls) -> list[models.Field]
    """Returns valid_from and valid_to fields"""

@classmethod
def get_unique_fields_without_valid_from(cls)
    """Returns unique fields excluding valid_from"""

def get_previous_instance(self)
    """Get the previous record based on valid_from"""

def get_next_instance(self)
    """Get the next record based on valid_from"""

def clean(self)
    """Validates that valid_to >= valid_from"""

def save(self, *args, **kwargs)
    """Automatically adjusts adjacent records' validity periods"""
```

### Person

**Location**: `sfd/models/person.py`

**Inherits**: MasterModel

**Key Fields**:
- Name fields: `family_name`, `name`, `family_name_kana`, `name_kana`
- Contact: `email`, `phone_number`, `mobile_number`
- Address: `postcode` (FK), `municipality` (FK), `address_detail`
- Demographics: `birthday`, `gender`

**String Representation**:
```python
def __str__(self):
    return f"{self.family_name} {self.name}"
```

## Admin Classes

### SfdModelAdmin

**Location**: `sfd/views/base.py`

**Inherits**: UploadMixin, DownloadMixin, ModelAdminMixin, ModelAdmin

**Usage**:
```python
from sfd.views.base import SfdModelAdmin

class MyModelAdmin(SfdModelAdmin):
    list_display = ['field1', 'field2']
```

### BaseModelAdmin

**Location**: `sfd/views/base.py`

**Inherits**: SfdModelAdmin

**Attributes**:
- `change_list_template`: "admin/change_list_custom.html"
- `change_form_template`: "admin/change_form_custom.html"
- `is_readonly` (bool): Enables read-only mode

**Methods**:
```python
def get_readonly_fields(self, request, obj=None)
    """Returns audit fields as read-only"""

def save_model(self, request, obj, form, change)
    """Automatically sets created_by/updated_by"""

def has_add_permission(self, request)
    """Controls add permission based on is_readonly"""

def has_change_permission(self, request, obj=None)
    """Controls change permission based on is_readonly"""

def has_delete_permission(self, request, obj=None)
    """Controls delete permission based on is_readonly"""
```

## Mixins

### UploadMixin

**Location**: `sfd/views/common/upload.py`

**Methods**:
```python
def upload_csv(self, request)
    """Handle CSV file upload and import"""

def process_upload(self, request, file)
    """Process uploaded CSV file"""
```

### DownloadMixin

**Location**: `sfd/views/common/download.py`

**Methods**:
```python
@admin.action(description="Download as CSV")
def download_csv(self, modeladmin, request, queryset)
    """Export queryset to CSV file"""
```

### ModelAdminMixin

**Location**: `sfd/views/common/mixins.py`

**Methods**:
```python
def get_readonly_fields(self, request, obj=None)
    """Returns read-only fields"""

def save_model(self, request, obj, form, change)
    """Save model with automatic user tracking"""
```

## Utility Functions

### Logging

**Location**: `sfd/common/logging.py`

```python
def set_user_info_per_thread(request)
    """Store user info in thread-local storage for logging"""

class UserInfoFilter(Filter)
    """Log filter that adds username and IP address to log records"""
```

**Usage**:
```python
import logging
logger = logging.getLogger(__name__)

logger.info("Message")  # Automatically includes user context
```

### Date/Time Utilities

**Location**: `sfd/common/datetime.py`

```python
def get_fiscal_year(date=None) -> int
    """Get Japanese fiscal year (April 1 - March 31)"""

def get_fiscal_year_range(fiscal_year) -> tuple[date, date]
    """Get start and end dates of fiscal year"""

def is_business_day(date, holidays=None) -> bool
    """Check if date is a business day"""

def next_business_day(date, holidays=None) -> date
    """Get next business day"""

def format_japanese_date(date) -> str
    """Format date in Japanese style: 2025年10月29日"""

def parse_japanese_date(date_str) -> date
    """Parse Japanese date format to date object"""
```

### Font Utilities

**Location**: `sfd/common/font.py`

```python
def register_japanese_fonts()
    """Register Japanese fonts for PDF generation"""
```

## Views

### IndexView

**Location**: `sfd/views/index.py`

**Type**: TemplateView

**URL**: `/sfd/` (name: `sfd:index`)

```python
class IndexView(TemplateView):
    template_name = "sfd/index.html"
```

### PostcodeSearchView

**Location**: `sfd/views/postcode.py`

**Type**: View (AJAX endpoint)

**URL**: `/sfd/search_postcode/` (name: `sfd:search_postcode`)

**Parameters**:
- `postcode` (GET): Postcode to search

**Returns**: JSON with address information

### get_municipalities_by_prefecture

**Location**: `sfd/views/municipality.py`

**Type**: Function view (AJAX endpoint)

**URL**: `/sfd/change_prefecture/` (name: `sfd:change_prefecture`)

**Parameters**:
- `prefecture_id` (GET): Prefecture ID

**Returns**: JSON with municipalities

## Forms

### PersonForm

**Location**: `sfd/forms/person.py`

```python
class PersonForm(forms.ModelForm):
    class Meta:
        model = Person
        fields = '__all__'
        exclude = ['created_by', 'created_at', 'updated_by', 
                   'updated_at', 'deleted_flg']
    
    def clean(self):
        """Validates municipality matches postcode's prefecture"""
```

### PostcodeSearchForm

**Location**: `sfd/forms/search.py`

```python
class PostcodeSearchForm(forms.Form):
    postcode = forms.CharField(max_length=8)
    
    def clean_postcode(self):
        """Validates postcode format: 123-4567"""
```

## Middleware

### RequestMiddleware

**Location**: `sfd/common/middleware.py`

**Configuration**: Add to `settings.MIDDLEWARE`

**Purpose**: Captures user information for logging

```python
class RequestMiddleware:
    def __call__(self, request):
        set_user_info_per_thread(request)
        response = self.get_response(request)
        return response
```

## Settings

### Key Settings

**Location**: `sfd_prj/settings.py`

```python
# Application definition
INSTALLED_APPS = [
    'sfd',  # Main application
    'django.contrib.admin',
    ...
]

# Middleware
MIDDLEWARE = [
    ...
    'sfd.common.middleware.RequestMiddleware',  # User tracking
    ...
]

# Internationalization
LANGUAGE_CODE = 'ja'  # or 'en'
USE_I18N = True
USE_TZ = True
```

### Logging Settings

**Location**: `sfd_prj/settings_log.py`

```python
LOGGING = {
    'version': 1,
    'filters': {
        'user_info': {
            'class': 'sfd.common.logging.UserInfoFilter',
        }
    },
    ...
}
```

## URL Patterns

### App URLs

**Location**: `sfd/urls.py`

```python
app_name = "sfd"

urlpatterns = [
    path("", IndexView.as_view(), name="index"),
    path("change_prefecture/", get_municipalities_by_prefecture, 
         name="change_prefecture"),
    path("search_postcode/", PostcodeSearchView.as_view(), 
         name="search_postcode"),
]
```

**Usage**:
```python
from django.urls import reverse
url = reverse('sfd:index')
url = reverse('sfd:search_postcode')
```

## Template Tags

### Common Filters

**Location**: `sfd/templatetags/common_filters.py`

```python
@register.filter
def format_date(value):
    """Format date in Japanese style"""
    if value:
        return value.strftime('%Y年%m月%d日')
    return ''
```

**Usage in templates**:
```django
{% load common_filters %}
{{ person.birthday|format_date }}
```

## Database Operations

### Common Queries

```python
# Get active records
Person.objects.filter(deleted_flg=False)

# Get currently valid records
from django.utils import timezone
today = timezone.now().date()
Person.objects.filter(
    valid_from__lte=today,
    valid_to__gte=today,
    deleted_flg=False
)

# Get person history
Person.objects.filter(
    family_name='Yamada',
    name='Taro',
    deleted_flg=False
).order_by('valid_from')

# Soft delete
person.deleted_flg = True
person.updated_by = username
person.save()

# Create with related objects
Person.objects.create(
    family_name='Yamada',
    name='Taro',
    postcode=postcode_obj,
    municipality=municipality_obj,
    created_by=username
)
```

## Constants

### Gender Types

**Location**: `sfd/models/person.py`

```python
class GenderType(models.TextChoices):
    MALE = "Male", _("Male")
    FEMALE = "Female", _("Female")
    OTHER = "Other", _("Other")
```

### Default Dates

**Location**: `sfd/models/base.py`

```python
def default_valid_from_date():
    """Returns tomorrow's date"""
    return timezone.now().date() + timezone.timedelta(days=1)

def default_valid_to_date():
    """Returns 2222-12-31"""
    return timezone.datetime(2222, 12, 31).date()
```

## Testing Utilities

### Base Test Class

**Location**: `sfd/tests/unittest.py`

```python
class SfdTestCase(TestCase):
    """Base test case with common setup"""
    
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
    
    def setUp(self):
        self.client.login(username='testuser', password='testpass123')
```

### Factory Pattern

```python
class PersonFactory:
    @staticmethod
    def create(**kwargs):
        defaults = {
            'family_name': 'Yamada',
            'name': 'Taro',
            'family_name_kana': 'ヤマダ',
            'name_kana': 'タロウ',
        }
        defaults.update(kwargs)
        return Person.objects.create(**defaults)
```

## Management Commands

### Running Batch Scripts

```bash
# Database operations
batch\create_database.bat          # Initialize database
batch\makemigrations.bat           # Create migrations
batch\migrate.bat                  # Apply migrations

# Development
batch\run_server.bat               # Start dev server
batch\create_superuser.bat         # Create admin user

# Testing
batch\pytest_module.bat test_name  # Run specific tests

# Internationalization
batch\makemessages.bat             # Extract translations
batch\compilemessages.bat          # Compile translations
```

## Quick Examples

### Create a New Model

```python
# 1. Define model
from sfd.models.base import MasterModel

class MyModel(MasterModel):
    name = models.CharField(_("Name"), max_length=100)
    
    class Meta:
        verbose_name = _("My Model")
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'valid_from'],
                name='unique_mymodel'
            )
        ]

# 2. Create admin
from sfd.views.base import BaseModelAdmin

class MyModelAdmin(BaseModelAdmin):
    list_display = ['name', 'valid_from', 'valid_to']
    search_fields = ['name']

# 3. Register
admin_site.register(MyModel, MyModelAdmin)

# 4. Create migrations
# batch\makemigrations.bat
# batch\migrate.bat
```

### Create a Form

```python
from django import forms
from sfd.models import MyModel

class MyModelForm(forms.ModelForm):
    class Meta:
        model = MyModel
        fields = ['name', 'valid_from', 'valid_to']
    
    def clean_name(self):
        name = self.cleaned_data['name']
        # Custom validation
        return name
```

### Add a View

```python
from django.views.generic import ListView
from sfd.models import MyModel

class MyModelListView(ListView):
    model = MyModel
    template_name = 'sfd/mymodel_list.html'
    context_object_name = 'objects'
    paginate_by = 20
    
    def get_queryset(self):
        return MyModel.objects.filter(deleted_flg=False)
```

### Create a Test

```python
from sfd.tests.unittest import SfdTestCase
from sfd.models import MyModel

class TestMyModel(SfdTestCase):
    def test_create(self):
        obj = MyModel.objects.create(
            name='Test',
            created_by=self.user.username
        )
        self.assertEqual(obj.name, 'Test')
```

## Common Imports

```python
# Models
from sfd.models import Person, Holiday, Municipality, Postcode
from sfd.models.base import BaseModel, MasterModel

# Admin
from sfd.views.base import SfdModelAdmin, BaseModelAdmin
from django.contrib import admin

# Forms
from django import forms
from django.forms import ModelForm

# Views
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.shortcuts import render, redirect, get_object_or_404

# URLs
from django.urls import path, reverse

# Utilities
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.db import transaction

# Testing
from django.test import TestCase, Client
import pytest
```

## Error Handling

### Common Exceptions

```python
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db import IntegrityError

try:
    person = Person.objects.get(id=person_id)
except ObjectDoesNotExist:
    # Handle not found
    pass
except MultipleObjectsReturned:
    # Handle multiple results
    pass
```

### Form Errors

```python
if form.is_valid():
    instance = form.save()
else:
    # form.errors contains validation errors
    # form.non_field_errors() for form-level errors
    pass
```

## Performance Tips

```python
# Use select_related for foreign keys
Person.objects.select_related('postcode', 'municipality')

# Use prefetch_related for reverse relations
Person.objects.prefetch_related('address_set')

# Use only() to fetch specific fields
Person.objects.only('family_name', 'name')

# Use values() for read-only data
Person.objects.values('id', 'family_name', 'name')

# Bulk operations
Person.objects.bulk_create([person1, person2, person3])
Person.objects.filter(...).update(field=value)
```
