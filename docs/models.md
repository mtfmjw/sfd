# Models Documentation

This document provides detailed information about the data models in the SFD application.

## Model Hierarchy

### BaseModel (Abstract)

The foundation for all models in the SFD application. Located in `sfd/models/base.py`.

```python
class BaseModel(models.Model):
    created_by = models.CharField(max_length=150, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=150, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_flg = models.BooleanField(default=False)
    
    class Meta:
        abstract = True
```

**Features:**

- **Audit Trail**: Automatically tracks who created/updated records and when
- **Soft Deletion**: Records are marked as deleted, never physically removed
- **Optimistic Locking**: Uses `updated_at` for concurrency control
- **Unique Key Support**: Helper method to get unique field names for validation

**Key Methods:**

```python
@classmethod
def get_unique_field_names(cls) -> list[str]:
    """Returns list of fields that form the unique constraint."""
    # Checks UniqueConstraint, unique_together, or unique fields
```

**Usage Example:**

```python
from sfd.models.base import BaseModel

class YourModel(BaseModel):
    name = models.CharField(max_length=100)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['name'], name='unique_name')
        ]
```

### MasterModel (Abstract)

Extends `BaseModel` to add temporal validity support. Located in `sfd/models/base.py`.

```python
class MasterModel(BaseModel):
    valid_from = models.DateField(default=default_valid_from_date)
    valid_to = models.DateField(default=default_valid_to_date)
    
    class Meta:
        abstract = True
```

**Features:**

- **Temporal Validity**: Records have validity periods (valid_from to valid_to)
- **Automatic Period Adjustment**: When creating overlapping periods, automatically adjusts adjacent records
- **Historical Data**: Maintains complete history of changes over time
- **Point-in-Time Queries**: Can query data as it was at any point in time

**Business Rules:**

1. **No Overlapping Periods**: Same entity cannot have overlapping validity periods
2. **Past Records Are Immutable**: Records with past `valid_from` cannot be edited directly
3. **Copy for Updates**: To update past records, create a new record with future `valid_from`
4. **Automatic Adjustment**: Previous record's `valid_to` is automatically adjusted
5. **No Batch Deletion**: Cannot bulk delete from list view

**Default Values:**

```python
def default_valid_from_date():
    """Returns tomorrow's date"""
    return timezone.now().date() + timezone.timedelta(days=1)

def default_valid_to_date():
    """Returns maximum date (2222-12-31)"""
    return timezone.datetime(2222, 12, 31).date()
```

**Key Methods:**

```python
def get_previous_instance(self):
    """Get the previous record based on valid_from"""
    
def get_next_instance(self):
    """Get the next record based on valid_from"""
    
def clean(self):
    """Validates that valid_to >= valid_from"""
    
def save(self, *args, **kwargs):
    """Automatically adjusts adjacent records' validity periods"""
```

**Usage Example:**

```python
# Create initial record
person = Person.objects.create(
    name="John Doe",
    valid_from=date(2025, 1, 1),
    valid_to=date(2222, 12, 31)
)

# Update by creating new record with future date
new_person = Person.objects.create(
    name="John Doe (Updated)",
    valid_from=date(2025, 6, 1),
    # Previous record's valid_to automatically set to 2025-05-31
)
```

## Domain Models

### Person

Represents individuals in the system. Located in `sfd/models/person.py`.

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `family_name` | CharField(100) | Yes | Last name |
| `family_name_kana` | CharField(100) | Yes | Last name in katakana |
| `family_name_romaji` | CharField(100) | No | Last name in romaji |
| `name` | CharField(100) | Yes | First name |
| `name_kana` | CharField(100) | Yes | First name in katakana |
| `name_romaji` | CharField(100) | No | First name in romaji |
| `birthday` | DateField | No | Date of birth |
| `gender` | CharField(10) | No | Gender (Male/Female/Other) |
| `email` | EmailField(100) | No | Email address |
| `phone_number` | CharField(20) | No | Phone number |
| `mobile_number` | CharField(20) | No | Mobile number |
| `postcode` | ForeignKey(Postcode) | No | Postal code |
| `municipality` | ForeignKey(Municipality) | No | Municipality/city |
| `address_detail` | CharField(255) | No | Detailed address |

**Gender Choices:**

```python
class GenderType(models.TextChoices):
    MALE = "Male", _("Male")
    FEMALE = "Female", _("Female")
    OTHER = "Other", _("Other")
```

**Meta Options:**

```python
class Meta:
    verbose_name = _("Person")
    verbose_name_plural = _("People")
    ordering = ["family_name", "name", "valid_from"]
```

**String Representation:**

```python
def __str__(self):
    return f"{self.family_name} {self.name}"
```

### Postcode

Represents Japanese postal codes. Located in `sfd/models/postcode.py`.

**Fields:**

- Postal code information
- Prefecture data
- City/municipality references
- Address components

**Use Cases:**

- Address lookup by postal code
- Automatic address completion in forms
- Geographic data analysis

### Municipality

Represents cities, towns, and villages in Japan. Located in `sfd/models/municipality.py`.

**Fields:**

- Municipality name
- Prefecture association
- Administrative codes
- Geographic information

**Relationships:**

- Related to Person (address)
- Related to Postcode (geographic lookup)

### Holiday

Represents holidays and special dates. Located in `sfd/models/holiday.py`.

**Fields:**

- Holiday name (multi-language support)
- Date
- Type/category
- Recurring rules

**Use Cases:**

- Calendar displays
- Business day calculations
- Scheduling systems

### User (Custom)

Custom user model extending Django's authentication. Located in `sfd/models/user.py`.

**Features:**

- Extended user profile
- Additional authentication options
- Permission management
- Group associations

### Group (Custom)

Custom group model for permission management. Located in `sfd/models/group.py`.

**Features:**

- Role-based access control
- Permission sets
- User assignment

## Model Managers

Models can define custom managers for specialized queries:

```python
class ActiveManager(models.Manager):
    """Manager that returns only non-deleted records"""
    def get_queryset(self):
        return super().get_queryset().filter(deleted_flg=False)

class PersonManager(models.Manager):
    """Manager for Person-specific queries"""
    def current(self):
        """Returns currently valid persons"""
        today = timezone.now().date()
        return self.filter(
            valid_from__lte=today,
            valid_to__gte=today,
            deleted_flg=False
        )
```

## Model Validation

### Field-Level Validation

```python
from django.core.validators import MinValueValidator, MaxValueValidator

class MyModel(BaseModel):
    age = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(120)]
    )
```

### Model-Level Validation

```python
class Person(MasterModel):
    def clean(self):
        super().clean()
        if self.birthday and self.birthday > timezone.now().date():
            raise ValidationError({
                'birthday': _('Birthday cannot be in the future')
            })
```

### Unique Constraints

```python
class Meta:
    constraints = [
        models.UniqueConstraint(
            fields=['family_name', 'name', 'valid_from'],
            name='unique_person_valid_from'
        )
    ]
```

## Querying Models

### Basic Queries

```python
# Get all active persons
persons = Person.objects.filter(deleted_flg=False)

# Get currently valid records
today = timezone.now().date()
current_persons = Person.objects.filter(
    valid_from__lte=today,
    valid_to__gte=today,
    deleted_flg=False
)

# Get specific person
person = Person.objects.get(id=1)
```

### Complex Queries

```python
# Search by name (case-insensitive)
persons = Person.objects.filter(
    family_name__icontains='yamada',
    deleted_flg=False
)

# Filter by related model
from sfd.models import Municipality
tokyo_persons = Person.objects.filter(
    municipality__name='Tokyo',
    deleted_flg=False
)

# Prefetch related data
persons = Person.objects.prefetch_related(
    'postcode',
    'municipality'
).filter(deleted_flg=False)
```

### Historical Queries

```python
# Get person as of specific date
specific_date = date(2025, 3, 15)
person_at_date = Person.objects.filter(
    id=person_id,
    valid_from__lte=specific_date,
    valid_to__gte=specific_date,
    deleted_flg=False
).first()

# Get all versions of a person
person_history = Person.objects.filter(
    family_name='Yamada',
    name='Taro',
    deleted_flg=False
).order_by('valid_from')
```

## Model Signals

While the project doesn't extensively use signals, they can be added for specific needs:

```python
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

@receiver(pre_save, sender=Person)
def person_pre_save(sender, instance, **kwargs):
    """Called before saving a Person"""
    # Custom logic here
    pass

@receiver(post_save, sender=Person)
def person_post_save(sender, instance, created, **kwargs):
    """Called after saving a Person"""
    if created:
        # Logic for new records
        pass
```

## Database Migrations

### Creating Migrations

```bash
# After model changes
python manage.py makemigrations

# With custom name
python manage.py makemigrations --name add_person_fields sfd
```

### Applying Migrations

```bash
# Apply all migrations
python manage.py migrate

# Apply specific migration
python manage.py migrate sfd 0001

# Show migration status
python manage.py showmigrations
```

### Data Migrations

Create a data migration for complex changes:

```bash
python manage.py makemigrations --empty sfd --name populate_default_data
```

```python
# Generated migration file
def populate_data(apps, schema_editor):
    Person = apps.get_model('sfd', 'Person')
    # Add data here
    
class Migration(migrations.Migration):
    dependencies = [
        ('sfd', '0001_initial'),
    ]
    
    operations = [
        migrations.RunPython(populate_data),
    ]
```

## Best Practices

1. **Always use BaseModel or MasterModel**: Never create models from scratch
2. **Add verbose_name for all fields**: Supports internationalization
3. **Define __str__ method**: Makes debugging easier
4. **Use constraints**: Define uniqueness at database level
5. **Add indexes**: For frequently queried fields
6. **Write clean methods**: Validate business logic
7. **Use transactions**: For operations that affect multiple records
8. **Avoid nullable booleans**: Use True/False with defaults
9. **Use choices**: For fields with limited options
10. **Document complex logic**: Add comments for non-obvious behavior

## Common Patterns

### Creating Related Records

```python
# Create with related objects
person = Person.objects.create(
    family_name='Yamada',
    name='Taro',
    postcode=postcode_instance,
    municipality=municipality_instance,
    valid_from=date.today(),
    created_by=request.user.username
)
```

### Updating Records

```python
# Update single record
person = Person.objects.get(id=1)
person.email = 'new@example.com'
person.updated_by = request.user.username
person.save()

# Bulk update (bypasses save() method)
Person.objects.filter(
    municipality__name='Tokyo'
).update(updated_by='system')
```

### Soft Delete

```python
# Soft delete
person = Person.objects.get(id=1)
person.deleted_flg = True
person.updated_by = request.user.username
person.save()

# Restore
person.deleted_flg = False
person.save()
```

### Temporal Updates

```python
# For past records, create new version
current_person = Person.objects.get(id=1)

# Create new version starting tomorrow
new_person = Person()
for field in current_person._meta.fields:
    if field.name not in ['id', 'created_at', 'created_by']:
        setattr(new_person, field.name, getattr(current_person, field.name))

new_person.pk = None  # Force new record
new_person.valid_from = date.today() + timedelta(days=1)
new_person.email = 'updated@example.com'
new_person.created_by = request.user.username
new_person.save()
# Previous record's valid_to is automatically adjusted
```

## Performance Tips

1. **Use select_related**: For foreign keys
2. **Use prefetch_related**: For reverse foreign keys and many-to-many
3. **Add database indexes**: For frequently filtered fields
4. **Avoid N+1 queries**: Use prefetch/select_related
5. **Use only()**: To fetch specific fields
6. **Use values()**: For read-only data
7. **Batch operations**: Use bulk_create/bulk_update
8. **Cache query results**: For frequently accessed data

```python
# Efficient querying
persons = Person.objects.select_related(
    'postcode',
    'municipality'
).prefetch_related(
    'group_set'
).filter(
    deleted_flg=False
).only(
    'id', 'family_name', 'name'
)
```
