# Encrypted Personal Information Guide

## Overview

This project uses field-level encryption to protect sensitive personal information (names, phone numbers, email, addresses, etc.) in the PostgreSQL database. Data is automatically encrypted before being stored and decrypted when retrieved.

## How It Works

### 1. Encrypted Fields

The following sensitive fields in the `Person` model are encrypted:
- `family_name`, `family_name_kana`, `family_name_romaji`
- `name`, `name_kana`, `name_romaji`
- `birthday`
- `email`
- `phone_number`, `mobile_number`
- `address_detail`

### 2. Encryption Technology

- **Library**: `django-cryptography` with `cryptography` (Fernet symmetric encryption)
- **Algorithm**: AES-128 in CBC mode with HMAC authentication
- **Key Storage**: Encryption key stored in environment variable (`.env` file)

### 3. Database Storage

Encrypted data is stored as **binary data** in PostgreSQL. You'll see base64-encoded encrypted strings in the database, not plaintext.

Example:
```
Plaintext:  "山田太郎"
Encrypted:  "gAAAAABhN5X7k9..."
```

## Setup Instructions

### 1. Add Encryption Key to .env File

Add the following to your `.env` file (NEVER commit this to git):

```env
FIELD_ENCRYPTION_KEY=ojK3onpcmNxA5xry5PbmlR70qD7OdvdRQ3Sr8sGoq-Y=
```

**IMPORTANT**: 
- Keep this key secret and secure
- Losing this key means you **cannot decrypt** existing data
- Use different keys for development and production
- Back up the production key in a secure location

### 2. Run Migrations

Create and apply migrations for the model changes:

```bash
cd d:\silos\sfd
.venv\Scripts\activate.bat
python manage.py makemigrations
python manage.py migrate
```

### 3. Verify Installation

Check that django-cryptography is properly installed:

```bash
python -c "from django_cryptography.fields import encrypt; print('✓ Encryption ready')"
```

## Usage Examples

### Basic Model Usage

```python
from sfd.models import Person

# Create a new person (data is automatically encrypted)
person = Person.objects.create(
    family_name="山田",
    name="太郎",
    phone_number="080-1234-5678",
    email="taro.yamada@example.com"
)

# Retrieve and display (data is automatically decrypted)
person = Person.objects.get(id=1)
print(person.name)  # Output: "太郎" (automatically decrypted)
print(person.phone_number)  # Output: "080-1234-5678" (automatically decrypted)
```

### Permission-Based Display

```python
from sfd.utils.permissions import can_view_personal_info, get_masked_person_name, get_masked_phone

# In a view or template
def person_detail_view(request, person_id):
    person = Person.objects.get(id=person_id)
    user = request.user
    
    # Check permission
    if can_view_personal_info(user):
        # User has permission - show full data
        name = f"{person.family_name} {person.name}"
        phone = person.phone_number
    else:
        # User lacks permission - show masked data
        name = get_masked_person_name(person, user)  # "山*** 太***"
        phone = get_masked_phone(person.phone_number, user)  # "080********"
    
    return render(request, 'person_detail.html', {
        'name': name,
        'phone': phone,
    })
```

### Django Admin Customization

```python
from django.contrib import admin
from sfd.models import Person
from sfd.utils.permissions import can_view_personal_info, mask_sensitive_data

@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ['get_masked_name', 'get_masked_phone', 'email']
    
    def get_masked_name(self, obj):
        user = self.request.user  # Requires custom admin setup
        if can_view_personal_info(user):
            return f"{obj.family_name} {obj.name}"
        return mask_sensitive_data(f"{obj.family_name} {obj.name}", 2)
    get_masked_name.short_description = "Name"
    
    def get_masked_phone(self, obj):
        user = self.request.user
        if can_view_personal_info(user):
            return obj.phone_number
        return mask_sensitive_data(obj.phone_number, 3)
    get_masked_phone.short_description = "Phone"
```

## Setting Up Permissions

### 1. Create Custom Permissions

Add to your `Person` model:

```python
class Person(MasterModel):
    # ... existing fields ...
    
    class Meta:
        verbose_name = _("Person")
        verbose_name_plural = _("People")
        ordering = ["family_name", "name", "valid_from"]
        permissions = [
            ("view_personal_info", "Can view personal information"),
            ("change_personal_info", "Can edit personal information"),
        ]
```

### 2. Assign Permissions to Users/Groups

```python
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from sfd.models import Person

# Get the permission
content_type = ContentType.objects.get_for_model(Person)
permission = Permission.objects.get(
    codename='view_personal_info',
    content_type=content_type,
)

# Assign to a user
user = User.objects.get(username='john')
user.user_permissions.add(permission)

# Or assign to a group
hr_group = Group.objects.create(name='HR Staff')
hr_group.permissions.add(permission)
user.groups.add(hr_group)
```

### 3. Use in Views

```python
from django.contrib.auth.decorators import permission_required
from django.core.exceptions import PermissionDenied

@permission_required('sfd.view_personal_info', raise_exception=True)
def view_sensitive_data(request):
    # Only users with permission can access this view
    people = Person.objects.all()
    return render(request, 'people_list.html', {'people': people})

# Or check manually
def view_person(request, person_id):
    person = Person.objects.get(id=person_id)
    
    if not request.user.has_perm('sfd.view_personal_info'):
        raise PermissionDenied("You don't have permission to view personal information")
    
    return render(request, 'person_detail.html', {'person': person})
```

## Important Considerations

### 1. Performance

- **Encryption/Decryption Overhead**: Minimal for single records, but consider caching for large lists
- **Searching**: You CANNOT search encrypted fields directly in the database
  ```python
  # ❌ This won't work as expected
  Person.objects.filter(name__icontains="太郎")
  
  # ✅ Instead, load and filter in Python
  people = Person.objects.all()
  filtered = [p for p in people if "太郎" in p.name]
  ```

### 2. Indexing

- Cannot create database indexes on encrypted fields
- Consider using separate unencrypted search fields if needed (e.g., initials, partial data)

### 3. Migrations

When changing encrypted fields, be careful:
```bash
# Backup data before migrations
python manage.py dumpdata sfd.person > backup_person.json

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Restore if needed
python manage.py loaddata backup_person.json
```

### 4. Key Rotation

To rotate encryption keys:
1. Generate new key
2. Decrypt all data with old key
3. Re-encrypt with new key
4. Update FIELD_ENCRYPTION_KEY in .env

### 5. Backup and Recovery

- Always backup your encryption key separately from database backups
- Test recovery procedures regularly
- Document key storage locations

## Security Best Practices

1. **Never commit encryption keys to version control**
   - Add `.env` to `.gitignore`
   - Use different keys per environment

2. **Secure key storage**
   - Production: Use secure key management service (AWS KMS, Azure Key Vault)
   - Development: Use `.env` file with restricted permissions

3. **Access control**
   - Implement proper Django permissions
   - Log access to sensitive data
   - Regular permission audits

4. **HTTPS/TLS**
   - Always use HTTPS in production
   - Encryption at rest (database) + in transit (HTTPS)

5. **Audit logging**
   - Log who accesses encrypted data and when
   - Monitor for unusual access patterns

## Troubleshooting

### "Invalid token" or Decryption Errors

- Check that FIELD_ENCRYPTION_KEY matches the key used to encrypt
- Verify key hasn't been modified or corrupted

### Performance Issues

- Consider adding caching for frequently accessed encrypted data
- Use `select_related()` and `prefetch_related()` for related objects

### Migration Issues

- Always backup before migrations involving encrypted fields
- Test migrations on a copy of production data first

## References

- [django-cryptography Documentation](https://github.com/georgemarshall/django-cryptography)
- [cryptography Library](https://cryptography.io/)
- [Fernet Specification](https://github.com/fernet/spec/blob/master/Spec.md)
