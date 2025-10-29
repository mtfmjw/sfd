# Forms Documentation

This document describes form handling, validation, and best practices in the SFD application.

## Form Types

### ModelForm

Forms automatically generated from models.

```python
from django import forms
from sfd.models import Person

class PersonForm(forms.ModelForm):
    """Form for Person model"""
    
    class Meta:
        model = Person
        fields = [
            'family_name', 'name',
            'family_name_kana', 'name_kana',
            'birthday', 'gender',
            'email', 'phone_number',
            'postcode', 'municipality',
            'address_detail'
        ]
        widgets = {
            'birthday': forms.DateInput(attrs={'type': 'date'}),
            'address_detail': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'family_name': _('Family Name'),
            'name': _('Given Name'),
        }
```

### Custom Forms

Forms not directly tied to a model.

```python
class PostcodeSearchForm(forms.Form):
    """Form for searching by postcode"""
    
    postcode = forms.CharField(
        max_length=8,
        label=_('Postcode'),
        widget=forms.TextInput(attrs={
            'placeholder': '123-4567',
            'class': 'form-control'
        })
    )
    
    def clean_postcode(self):
        """Validate postcode format"""
        postcode = self.cleaned_data['postcode']
        import re
        if not re.match(r'^\d{3}-\d{4}$', postcode):
            raise forms.ValidationError(
                _('Enter postcode in format: 123-4567')
            )
        return postcode
```

## Form Structure

### Person Form

Located in `sfd/forms/person.py`.

```python
from django import forms
from django.utils.translation import gettext_lazy as _
from sfd.models import Person, Postcode, Municipality

class PersonForm(forms.ModelForm):
    """Form for creating/editing Person records"""
    
    class Meta:
        model = Person
        fields = '__all__'
        exclude = ['created_by', 'created_at', 'updated_by', 'updated_at', 'deleted_flg']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make certain fields required
        self.fields['family_name'].required = True
        self.fields['name'].required = True
        
        # Add CSS classes
        for field in self.fields:
            self.fields[field].widget.attrs['class'] = 'form-control'
        
        # Dynamic filtering of municipality based on postcode
        if self.instance.pk and self.instance.postcode:
            self.fields['municipality'].queryset = Municipality.objects.filter(
                prefecture=self.instance.postcode.prefecture
            )
    
    def clean(self):
        """Form-level validation"""
        cleaned_data = super().clean()
        
        # Validate that municipality matches postcode's prefecture
        postcode = cleaned_data.get('postcode')
        municipality = cleaned_data.get('municipality')
        
        if postcode and municipality:
            if municipality.prefecture != postcode.prefecture:
                raise forms.ValidationError(
                    _('Municipality must be in the same prefecture as postcode')
                )
        
        return cleaned_data
```

### Postcode Form

Located in `sfd/forms/postcode.py`.

```python
from django import forms
from sfd.models import Postcode

class PostcodeForm(forms.ModelForm):
    """Form for Postcode model"""
    
    class Meta:
        model = Postcode
        fields = ['code', 'prefecture', 'city', 'town']
    
    def clean_code(self):
        """Validate postcode format"""
        code = self.cleaned_data['code']
        import re
        if not re.match(r'^\d{3}-\d{4}$', code):
            raise forms.ValidationError(
                _('Postcode must be in format: 123-4567')
            )
        return code
```

### Search Form

Located in `sfd/forms/search.py`.

```python
from django import forms
from django.utils.translation import gettext_lazy as _

class PersonSearchForm(forms.Form):
    """Form for searching persons"""
    
    search_text = forms.CharField(
        max_length=100,
        required=False,
        label=_('Search'),
        widget=forms.TextInput(attrs={
            'placeholder': _('Name, email, or phone'),
            'class': 'form-control'
        })
    )
    
    gender = forms.ChoiceField(
        choices=[('', '---')] + list(GenderType.choices),
        required=False,
        label=_('Gender')
    )
    
    date_from = forms.DateField(
        required=False,
        label=_('From Date'),
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    
    date_to = forms.DateField(
        required=False,
        label=_('To Date'),
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    
    def clean(self):
        """Validate date range"""
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        
        if date_from and date_to and date_to < date_from:
            raise forms.ValidationError(
                _('End date must be after start date')
            )
        
        return cleaned_data
```

## Form Validation

### Field-Level Validation

```python
class PersonForm(forms.ModelForm):
    def clean_email(self):
        """Validate email uniqueness"""
        email = self.cleaned_data['email']
        
        # Check if email already exists (excluding current instance)
        qs = Person.objects.filter(email=email, deleted_flg=False)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        
        if qs.exists():
            raise forms.ValidationError(
                _('This email is already in use.')
            )
        
        return email
    
    def clean_phone_number(self):
        """Validate phone number format"""
        phone = self.cleaned_data['phone_number']
        if phone:
            import re
            if not re.match(r'^\d{2,4}-\d{1,4}-\d{4}$', phone):
                raise forms.ValidationError(
                    _('Enter phone number in format: 03-1234-5678')
                )
        return phone
```

### Form-Level Validation

```python
class PersonForm(forms.ModelForm):
    def clean(self):
        """Cross-field validation"""
        cleaned_data = super().clean()
        
        birthday = cleaned_data.get('birthday')
        valid_from = cleaned_data.get('valid_from')
        
        # Validate that person is at least 18 years old at valid_from
        if birthday and valid_from:
            age = valid_from.year - birthday.year
            if age < 18:
                raise forms.ValidationError(
                    _('Person must be at least 18 years old')
                )
        
        return cleaned_data
```

## Custom Widgets

### Date Picker Widget

```python
class DatePickerWidget(forms.DateInput):
    """Custom date picker widget"""
    
    def __init__(self, attrs=None):
        default_attrs = {
            'type': 'date',
            'class': 'form-control datepicker'
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)

# Usage
class PersonForm(forms.ModelForm):
    class Meta:
        widgets = {
            'birthday': DatePickerWidget(),
        }
```

### Custom Select Widget

```python
class SearchableSelectWidget(forms.Select):
    """Select widget with search functionality"""
    
    def __init__(self, attrs=None):
        default_attrs = {
            'class': 'form-control select2'
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)

# Usage
class PersonForm(forms.ModelForm):
    class Meta:
        widgets = {
            'municipality': SearchableSelectWidget(),
        }
```

## Dynamic Forms

### Dependent Fields

```python
class PersonForm(forms.ModelForm):
    """Form with dependent fields"""
    
    prefecture = forms.ChoiceField(
        choices=PREFECTURE_CHOICES,
        required=False
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filter municipalities based on selected prefecture
        if 'prefecture' in self.data:
            try:
                prefecture = self.data.get('prefecture')
                self.fields['municipality'].queryset = \
                    Municipality.objects.filter(prefecture=prefecture)
            except (ValueError, TypeError):
                pass
        elif self.instance.pk:
            self.fields['municipality'].queryset = \
                self.instance.postcode.prefecture.municipality_set.all()

# JavaScript to handle dynamic loading
```

### Formsets

```python
from django.forms import formset_factory, modelformset_factory

# Simple formset
PersonFormSet = formset_factory(PersonForm, extra=3)

# Model formset
PersonModelFormSet = modelformset_factory(
    Person,
    fields=['family_name', 'name', 'email'],
    extra=1,
    can_delete=True
)

# Inline formset
from django.forms import inlineformset_factory

AddressFormSet = inlineformset_factory(
    Person,
    Address,
    fields=['postcode', 'municipality', 'address_detail'],
    extra=1,
    can_delete=True
)
```

### Using Formsets in Views

```python
def manage_persons(request):
    """View to manage multiple persons"""
    PersonFormSet = modelformset_factory(Person, form=PersonForm, extra=2)
    
    if request.method == 'POST':
        formset = PersonFormSet(request.POST)
        if formset.is_valid():
            instances = formset.save(commit=False)
            for instance in instances:
                instance.created_by = request.user.username
                instance.save()
            return redirect('success')
    else:
        formset = PersonFormSet(queryset=Person.objects.filter(deleted_flg=False))
    
    return render(request, 'form.html', {'formset': formset})
```

## Form Templates

### Basic Form Template

```django
<!-- templates/sfd/person_form.html -->
{% extends 'sfd/base.html' %}
{% load static %}

{% block content %}
<div class="container">
    <h2>{% if form.instance.pk %}Edit{% else %}Add{% endif %} Person</h2>
    
    <form method="post" novalidate>
        {% csrf_token %}
        
        {% if form.non_field_errors %}
        <div class="alert alert-danger">
            {{ form.non_field_errors }}
        </div>
        {% endif %}
        
        {% for field in form %}
        <div class="form-group">
            {{ field.label_tag }}
            {{ field }}
            {% if field.errors %}
            <div class="invalid-feedback d-block">
                {{ field.errors }}
            </div>
            {% endif %}
            {% if field.help_text %}
            <small class="form-text text-muted">{{ field.help_text }}</small>
            {% endif %}
        </div>
        {% endfor %}
        
        <button type="submit" class="btn btn-primary">Save</button>
        <a href="{% url 'person_list' %}" class="btn btn-secondary">Cancel</a>
    </form>
</div>
{% endblock %}
```

### Formset Template

```django
<!-- templates/sfd/person_formset.html -->
{% extends 'sfd/base.html' %}

{% block content %}
<form method="post">
    {% csrf_token %}
    {{ formset.management_form }}
    
    <table class="table">
        <thead>
            <tr>
                <th>Family Name</th>
                <th>Name</th>
                <th>Email</th>
                <th>Delete</th>
            </tr>
        </thead>
        <tbody>
            {% for form in formset %}
            <tr>
                <td>{{ form.family_name }}</td>
                <td>{{ form.name }}</td>
                <td>{{ form.email }}</td>
                <td>{{ form.DELETE }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    
    <button type="submit" class="btn btn-primary">Save All</button>
</form>
{% endblock %}
```

## AJAX Form Submission

### View

```python
from django.http import JsonResponse

def create_person_ajax(request):
    """Handle AJAX form submission"""
    if request.method == 'POST':
        form = PersonForm(request.POST)
        if form.is_valid():
            person = form.save(commit=False)
            person.created_by = request.user.username
            person.save()
            return JsonResponse({
                'success': True,
                'message': _('Person created successfully'),
                'person_id': person.id
            })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors
            }, status=400)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)
```

### JavaScript

```javascript
// Submit form via AJAX
$('#person-form').on('submit', function(e) {
    e.preventDefault();
    
    $.ajax({
        url: $(this).attr('action'),
        method: 'POST',
        data: $(this).serialize(),
        success: function(response) {
            if (response.success) {
                alert(response.message);
                window.location.reload();
            }
        },
        error: function(xhr) {
            const errors = xhr.responseJSON.errors;
            // Display errors
            $.each(errors, function(field, messages) {
                $(`#id_${field}`).addClass('is-invalid');
                $(`#id_${field}`).after(
                    `<div class="invalid-feedback">${messages.join(', ')}</div>`
                );
            });
        }
    });
});
```

## File Upload Forms

### Form with File Field

```python
class PersonPhotoForm(forms.ModelForm):
    """Form with photo upload"""
    
    photo = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'accept': 'image/*'
        })
    )
    
    class Meta:
        model = Person
        fields = ['family_name', 'name', 'photo']
    
    def clean_photo(self):
        """Validate photo file"""
        photo = self.cleaned_data.get('photo')
        if photo:
            # Check file size (max 5MB)
            if photo.size > 5 * 1024 * 1024:
                raise forms.ValidationError(
                    _('Photo file size cannot exceed 5MB')
                )
            
            # Check file type
            if not photo.content_type.startswith('image/'):
                raise forms.ValidationError(
                    _('File must be an image')
                )
        
        return photo
```

### Template with File Upload

```django
<form method="post" enctype="multipart/form-data">
    {% csrf_token %}
    
    {{ form.family_name }}
    {{ form.name }}
    {{ form.photo }}
    
    <button type="submit">Upload</button>
</form>
```

## Form Best Practices

1. **Always use CSRF protection**: Include `{% csrf_token %}`
2. **Validate on both client and server**: Don't rely only on JavaScript
3. **Use clean methods**: For custom validation logic
4. **Provide helpful error messages**: Be specific about what's wrong
5. **Use widgets for better UX**: Date pickers, select2, etc.
6. **Keep forms focused**: One responsibility per form
7. **Use labels and help text**: Make forms user-friendly
8. **Test form validation**: Write tests for edge cases
9. **Handle file uploads properly**: Validate size and type
10. **Use formsets for multiple records**: Better than manual loops

## Common Patterns

### Read-Only Form

```python
class PersonDetailForm(PersonForm):
    """Read-only form for displaying person details"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs['readonly'] = True
            self.fields[field].widget.attrs['disabled'] = True
```

### Multi-Step Form

```python
class PersonStep1Form(forms.Form):
    """Step 1: Basic information"""
    family_name = forms.CharField()
    name = forms.CharField()

class PersonStep2Form(forms.Form):
    """Step 2: Contact information"""
    email = forms.EmailField()
    phone = forms.CharField()

# View to handle multi-step
def person_create_wizard(request):
    if request.method == 'POST':
        step = request.POST.get('step', '1')
        
        if step == '1':
            form = PersonStep1Form(request.POST)
            if form.is_valid():
                request.session['step1_data'] = form.cleaned_data
                form = PersonStep2Form()
                return render(request, 'step2.html', {'form': form})
        
        elif step == '2':
            form = PersonStep2Form(request.POST)
            if form.is_valid():
                # Combine data from both steps
                step1_data = request.session.get('step1_data', {})
                step2_data = form.cleaned_data
                # Create person
                person = Person.objects.create(**step1_data, **step2_data)
                return redirect('success')
    else:
        form = PersonStep1Form()
    
    return render(request, 'step1.html', {'form': form})
```

### Conditional Field Display

```python
class PersonForm(forms.ModelForm):
    """Form with conditional fields"""
    
    is_employee = forms.BooleanField(required=False)
    employee_number = forms.CharField(required=False)
    
    def clean(self):
        cleaned_data = super().clean()
        is_employee = cleaned_data.get('is_employee')
        employee_number = cleaned_data.get('employee_number')
        
        if is_employee and not employee_number:
            raise forms.ValidationError(
                _('Employee number is required for employees')
            )
        
        return cleaned_data
```
