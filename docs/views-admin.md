# Views and Admin Documentation

This document describes the view layer and Django admin interface customizations in the SFD application.

## Admin Architecture

### Custom Admin Site

The SFD project uses a custom admin site (`SfdAdminSite`) that extends Django's default admin. Located in `sfd/admin.py`.

```python
class SfdAdminSite(AdminSite):
    site_header = _("sfd")
    site_title = _("sfd Admin")
    index_title = _("sfd Administration")
    
    def has_permission(self, request):
        """Allow any authenticated user to access admin"""
        return request.user.is_authenticated
```

**Key Features:**

- **Open Access**: Any authenticated user can access admin (not just staff)
- **Custom Ordering**: Applications and models appear in custom order
- **Localization**: Fully internationalized interface
- **Custom Login**: Uses custom login template

**Security Note:** This is less restrictive than Django's default admin. Use only in trusted environments where all authenticated users should have admin access.

### Admin Base Classes

The project provides several base admin classes with different capabilities:

```
ModelAdmin (Django)
    ↓
SfdModelAdmin
    ├── UploadMixin
    ├── DownloadMixin
    └── ModelAdminMixin
        ↓
        BaseModelAdmin
            ├── BaseModelUploadMixin
            ├── BaseModelDownloadMixin
            └── BaseModelAdminMixin
                ↓
                MasterModelAdmin
                    ├── MasterModelUploadMixin
                    ├── MasterModelDownloadMixin
                    └── MasterModelAdminMixin
```

### SfdModelAdmin

Basic admin class with upload/download functionality. Located in `sfd/views/base.py`.

```python
class SfdModelAdmin(UploadMixin, DownloadMixin, ModelAdminMixin, ModelAdmin):
    """Admin class for SFD models"""
    pass
```

**Features:**

- CSV upload capability
- CSV download capability
- Common admin enhancements

### BaseModelAdmin

Admin class for models inheriting from `BaseModel`. Located in `sfd/views/base.py`.

```python
class BaseModelAdmin(BaseModelUploadMixin, BaseModelDownloadMixin, 
                     BaseModelAdminMixin, SfdModelAdmin):
    """Base admin for BaseModel descendants"""
    
    change_list_template = "admin/change_list_custom.html"
    change_form_template = "admin/change_form_custom.html"
    is_readonly = False
```

**Features:**

- Automatic audit field handling (created_by, updated_by)
- Soft deletion support
- Configurable read-only mode
- Custom templates
- CSV upload/download with BaseModel fields

**Read-Only Mode:**

```python
class MyModelAdmin(BaseModelAdmin):
    is_readonly = True  # Disables add, change, delete permissions
```

### MasterModelAdmin

Admin class for models inheriting from `MasterModel`. Located in `sfd/views/base.py` (conceptual).

**Features:**

- All BaseModelAdmin features
- Temporal validity management
- Copy functionality for updating past records
- Validation of validity periods
- Automatic period adjustment

**Business Rules Enforced:**

1. Past records (valid_from < today) cannot be edited
2. Must use "Copy" action to update past records
3. No overlapping validity periods
4. Automatic adjustment of adjacent periods

## Admin Mixins

### ModelAdminMixin

Base mixin providing common functionality. Located in `sfd/views/common/mixins.py`.

```python
class ModelAdminMixin:
    """Common functionality for all admin classes"""
    
    def get_readonly_fields(self, request, obj=None):
        """Make audit fields read-only"""
        
    def save_model(self, request, obj, form, change):
        """Set created_by/updated_by automatically"""
```

**Features:**

- Automatic user tracking
- Custom field visibility
- Permission handling

### UploadMixin

Provides CSV upload functionality. Located in `sfd/views/common/upload.py`.

```python
class UploadMixin:
    """Add CSV upload capability to admin"""
    
    upload_template = "admin/upload.html"
    
    def upload_csv(self, request):
        """Handle CSV upload"""
```

**Usage:**

1. User uploads CSV file via admin interface
2. System validates CSV structure
3. Data is parsed and validated
4. Records are created/updated in database
5. Results are displayed to user

**CSV Format:**

```csv
field1,field2,field3
value1,value2,value3
```

- First row must contain field names
- Field names must match model field names
- Date fields: YYYY-MM-DD format
- Boolean fields: true/false or 1/0

### DownloadMixin

Provides CSV download functionality. Located in `sfd/views/common/download.py`.

```python
class DownloadMixin:
    """Add CSV download capability to admin"""
    
    def download_csv(self, modeladmin, request, queryset):
        """Download selected records as CSV"""
```

**Features:**

- Download all or selected records
- Configurable field selection
- Proper CSV encoding (UTF-8 with BOM for Excel)
- Localized field names

**Usage:**

1. Select records in admin list view
2. Choose "Download as CSV" action
3. CSV file is generated and downloaded

### BaseModelAdminMixin

Specific functionality for BaseModel. Located in `sfd/views/common/mixins.py`.

```python
class BaseModelAdminMixin:
    """Mixin for BaseModel admin classes"""
    
    exclude = ['deleted_flg']
    list_filter = ['deleted_flg', 'created_at', 'updated_at']
    
    def get_queryset(self, request):
        """Filter out deleted records by default"""
        return super().get_queryset(request).filter(deleted_flg=False)
```

**Features:**

- Filters deleted records from list view
- Makes audit fields read-only
- Automatic user assignment
- Optimistic locking checks

### MasterModelAdminMixin

Specific functionality for MasterModel. Located in `sfd/views/common/mixins.py`.

```python
class MasterModelAdminMixin(BaseModelAdminMixin):
    """Mixin for MasterModel admin classes"""
    
    list_display = [..., 'valid_from', 'valid_to']
    list_filter = ['valid_from', 'valid_to'] + BaseModelAdminMixin.list_filter
    
    def get_readonly_fields(self, request, obj=None):
        """Make valid_from readonly for past records"""
```

**Features:**

- Validity period display in list view
- Copy action for updating past records
- Validation of validity periods
- Past record protection
- Automatic period adjustment

**Copy Action:**

```python
@admin.action(description=_('Copy selected records'))
def copy_records(self, request, queryset):
    """Create copies of selected records with future valid_from"""
```

## Admin Customization

### List Display

Customize columns shown in list view:

```python
class PersonAdmin(BaseModelAdmin):
    list_display = [
        'family_name',
        'name',
        'email',
        'phone_number',
        'created_at',
        'updated_at'
    ]
```

### Search Fields

Enable search functionality:

```python
class PersonAdmin(BaseModelAdmin):
    search_fields = [
        'family_name',
        'name',
        'email',
        'phone_number'
    ]
```

### List Filters

Add sidebar filters:

```python
class PersonAdmin(BaseModelAdmin):
    list_filter = [
        'gender',
        'municipality',
        ('birthday', admin.DateFieldListFilter),
        'created_at'
    ]
```

### Field Organization

Group fields in forms:

```python
class PersonAdmin(BaseModelAdmin):
    fieldsets = [
        (_('Basic Information'), {
            'fields': ['family_name', 'name', 'birthday', 'gender']
        }),
        (_('Contact Information'), {
            'fields': ['email', 'phone_number', 'mobile_number']
        }),
        (_('Address'), {
            'fields': ['postcode', 'municipality', 'address_detail'],
            'classes': ['collapse']  # Collapsible section
        })
    ]
```

### Inline Editing

Add related models inline:

```python
class AddressInline(admin.TabularInline):
    model = Address
    extra = 1
    
class PersonAdmin(BaseModelAdmin):
    inlines = [AddressInline]
```

### Custom Actions

Add custom bulk actions:

```python
class PersonAdmin(BaseModelAdmin):
    actions = ['mark_as_verified', 'send_notification']
    
    @admin.action(description=_('Mark as verified'))
    def mark_as_verified(self, request, queryset):
        """Mark selected persons as verified"""
        updated = queryset.update(
            verified=True,
            updated_by=request.user.username
        )
        self.message_user(
            request,
            f'{updated} records marked as verified.'
        )
```

### Custom Validation

Add admin-level validation:

```python
class PersonAdmin(BaseModelAdmin):
    def save_model(self, request, obj, form, change):
        """Custom validation before saving"""
        if not change and obj.birthday:
            if obj.birthday > timezone.now().date():
                messages.error(request, _('Birthday cannot be in future'))
                return
        super().save_model(request, obj, form, change)
```

## Regular Views

### Index View

Main landing page. Located in `sfd/views/index.py`.

```python
class IndexView(TemplateView):
    """Homepage view"""
    template_name = "sfd/index.html"
```

### Postcode Search View

AJAX view for postcode lookup. Located in `sfd/views/postcode.py`.

```python
class PostcodeSearchView(View):
    """Search postcode and return address information"""
    
    def get(self, request):
        postcode = request.GET.get('postcode')
        # Search and return JSON response
```

**Usage:**

```javascript
// Frontend JavaScript
fetch('/sfd/search_postcode/?postcode=1000001')
    .then(response => response.json())
    .then(data => {
        // Populate address fields
    });
```

### Municipality Filter View

AJAX view for filtering municipalities by prefecture. Located in `sfd/views/municipality.py`.

```python
def get_municipalities_by_prefecture(request):
    """Get municipalities for a prefecture"""
    prefecture_id = request.GET.get('prefecture_id')
    municipalities = Municipality.objects.filter(
        prefecture_id=prefecture_id
    )
    return JsonResponse({'municipalities': list(municipalities)})
```

## URL Configuration

URL patterns for the SFD app. Located in `sfd/urls.py`.

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

**URL Naming:**

- Use `app_name` for namespacing
- Name all URL patterns
- Use descriptive names

**Reverse URLs:**

```python
from django.urls import reverse

url = reverse('sfd:index')
url = reverse('sfd:search_postcode')
```

## Templates

### Template Structure

```
templates/
├── admin/                     # Admin template overrides
│   ├── base_site.html        # Custom admin base
│   ├── change_list_custom.html
│   └── change_form_custom.html
├── registration/              # Authentication templates
│   └── login.html
└── sfd/                       # App-specific templates
    ├── base.html
    └── index.html
```

### Template Inheritance

```django
<!-- sfd/base.html -->
{% load static %}
<!DOCTYPE html>
<html>
<head>
    <title>{% block title %}SFD{% endblock %}</title>
    {% block extra_css %}{% endblock %}
</head>
<body>
    {% block content %}{% endblock %}
    {% block extra_js %}{% endblock %}
</body>
</html>

<!-- sfd/index.html -->
{% extends 'sfd/base.html' %}

{% block title %}Home - {{ block.super }}{% endblock %}

{% block content %}
    <h1>{% trans "Welcome to SFD" %}</h1>
{% endblock %}
```

### Template Tags

Custom template tags in `sfd/templatetags/`.

**Common Filters:**

Located in `sfd/templatetags/common_filters.py`.

```python
from django import template

register = template.Library()

@register.filter
def format_date(value):
    """Format date in Japanese style"""
    if value:
        return value.strftime('%Y年%m月%d日')
    return ''
```

**Usage:**

```django
{% load common_filters %}
{{ person.birthday|format_date }}
```

## Permission Control

### Model-Level Permissions

```python
class PersonAdmin(BaseModelAdmin):
    def has_add_permission(self, request):
        """Control who can add records"""
        return request.user.is_superuser
    
    def has_change_permission(self, request, obj=None):
        """Control who can edit records"""
        if obj and obj.created_by != request.user.username:
            return request.user.is_superuser
        return True
    
    def has_delete_permission(self, request, obj=None):
        """Control who can delete records"""
        return request.user.is_superuser
```

### Field-Level Permissions

```python
class PersonAdmin(BaseModelAdmin):
    def get_readonly_fields(self, request, obj=None):
        """Make fields readonly based on permissions"""
        readonly = super().get_readonly_fields(request, obj)
        if not request.user.is_superuser:
            readonly = readonly + ('email',)
        return readonly
```

### View-Level Permissions

```python
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

@method_decorator(login_required, name='dispatch')
class MyView(View):
    """View requiring authentication"""
    pass
```

## Form Handling

### ModelForm in Admin

```python
from django import forms
from sfd.models import Person

class PersonAdminForm(forms.ModelForm):
    class Meta:
        model = Person
        fields = '__all__'
    
    def clean(self):
        cleaned_data = super().clean()
        # Custom validation
        return cleaned_data

class PersonAdmin(BaseModelAdmin):
    form = PersonAdminForm
```

### Custom Widgets

```python
class PersonAdminForm(forms.ModelForm):
    class Meta:
        model = Person
        fields = '__all__'
        widgets = {
            'birthday': forms.DateInput(attrs={'type': 'date'}),
            'address_detail': forms.Textarea(attrs={'rows': 3}),
        }
```

## Best Practices

1. **Always extend base admin classes**: Use BaseModelAdmin or MasterModelAdmin
2. **Use mixins for reusable functionality**: Keep code DRY
3. **Add docstrings**: Document custom methods and actions
4. **Use transactions**: Wrap multi-model operations
5. **Validate in clean methods**: Both form and model level
6. **Use messages framework**: Provide user feedback
7. **Log important operations**: Track admin actions
8. **Test admin customizations**: Write tests for custom behavior
9. **Keep views thin**: Business logic belongs in models
10. **Use named URLs**: Never hardcode URL paths

## Common Patterns

### Custom Admin Action with Form

```python
from django.shortcuts import render

class PersonAdmin(BaseModelAdmin):
    actions = ['bulk_update_email']
    
    def bulk_update_email(self, request, queryset):
        """Update email with confirmation"""
        if 'apply' in request.POST:
            new_email = request.POST.get('email')
            queryset.update(email=new_email)
            self.message_user(request, f'{queryset.count()} updated')
            return
        
        return render(
            request,
            'admin/bulk_email_update.html',
            {'persons': queryset}
        )
```

### AJAX Form Handling

```python
from django.http import JsonResponse

def ajax_search(request):
    """AJAX endpoint for search"""
    query = request.GET.get('q', '')
    results = Person.objects.filter(
        family_name__icontains=query,
        deleted_flg=False
    )[:10]
    
    data = [{
        'id': p.id,
        'name': str(p),
        'email': p.email
    } for p in results]
    
    return JsonResponse({'results': data})
```

### Dynamic Form Fields

```python
class PersonAdminForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Dynamically filter municipality choices based on postcode
        if self.instance.postcode:
            self.fields['municipality'].queryset = \
                Municipality.objects.filter(
                    prefecture=self.instance.postcode.prefecture
                )
```

### Custom Template Context

```python
class PersonAdmin(BaseModelAdmin):
    def changeform_view(self, request, object_id=None, 
                       form_url='', extra_context=None):
        """Add extra context to change form"""
        extra_context = extra_context or {}
        extra_context['show_special_info'] = True
        return super().changeform_view(
            request, object_id, form_url, extra_context
        )
```
