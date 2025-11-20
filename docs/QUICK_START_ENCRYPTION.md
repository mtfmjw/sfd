# Quick Start: Encrypted Personal Information

## ✅ What's Been Set Up

Your Django application now has **field-level encryption** for sensitive personal data using the `cryptography` library with Fernet encryption (AES-128).

### Encrypted Fields in Person Model

The following fields are now encrypted in the database:

- ✓ `family_name`, `family_name_kana`, `family_name_romaji`
- ✓ `name`, `name_kana`, `name_romaji`
- ✓ `birthday`
- ✓ `email`
- ✓ `phone_number`, `mobile_number`
- ✓ `address_detail`

## 📝 Next Steps

### 1. Run Migrations

```bash
cd d:\silos\sfd
.venv\Scripts\python.exe manage.py migrate
```

This will apply the database changes to use encrypted fields.

### 2. Test the Encryption

```python
# In Django shell
python manage.py shell

from sfd.models import Person

# Create a person (data is automatically encrypted)
person = Person.objects.create(
    family_name="山田",
    name="太郎",
    family_name_kana="ヤマダ",
    name_kana="タロウ",
    email="taro@example.com",
    phone_number="080-1234-5678"
)

# Retrieve (data is automatically decrypted)
person = Person.objects.get(id=person.id)
print(person.name)  # Output: "太郎" (decrypted!)
```

### 3. Check the Database

Connect to PostgreSQL and query the person table:

```sql
SELECT family_name, name, email FROM sfd_person WHERE id = 1;
```

You'll see encrypted data like:

```
family_name: Z0FBQUFBQm5ONVg3azk...
name:        Z0FBQUFBQm5ONVg3azk...
email:       Z0FBQUFBQm5ONVg3azk...
```

### 4. Set Up Permissions

Create permissions for viewing/editing personal information:

```python
# In Django shell or admin
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from sfd.models import Person

# Get the permissions (they were created by the migration)
content_type = ContentType.objects.get_for_model(Person)
view_perm = Permission.objects.get(codename='view_personal_info', content_type=content_type)
change_perm = Permission.objects.get(codename='change_personal_info', content_type=content_type)

# Create an HR group with these permissions
hr_group = Group.objects.create(name='HR Staff')
hr_group.permissions.add(view_perm, change_perm)

# Add users to the group
user = User.objects.get(username='john')
user.groups.add(hr_group)
```

### 5. Use in Views

```python
from sfd.utils.permissions import can_view_personal_info, get_masked_person_name

def person_view(request, person_id):
    person = Person.objects.get(id=person_id)
    
    if can_view_personal_info(request.user):
        # Show full data
        name = f"{person.family_name} {person.name}"
        phone = person.phone_number
    else:
        # Show masked data
        name = get_masked_person_name(person, request.user)  # "山*** 太***"
        phone = "080********"
    
    return render(request, 'person.html', {'name': name, 'phone': phone})
```

## 📚 Documentation

Full documentation is available in:

- **Setup Guide**: `docs/encryption-guide.md`
- **Code Examples**: `sfd/examples/encrypted_fields_example.py`
- **Permission Utils**: `sfd/utils/permissions.py`

## 🔐 Security Checklist

- [x] Encryption key stored in `.env` file
- [x] `.env` file is in `.gitignore` (verify this!)
- [ ] Backup encryption key to secure location
- [ ] Use different key for production
- [ ] Enable HTTPS in production
- [ ] Set up permission groups
- [ ] Implement audit logging

## ⚠️ Important Notes

### Backup Your Encryption Key

**Store `FIELD_ENCRYPTION_KEY` from `.env` in a secure location.**
If you lose this key, you **cannot decrypt** existing data!

### Existing Data Migration

If you have existing unencrypted data in the database, you need to:

1. Backup the database
2. Export existing data
3. Run migrations
4. Re-import data (it will be encrypted on save)

Example migration script:

```python
# migration_script.py
from sfd.models import Person

# This will re-save all people, encrypting their data
for person in Person.objects.all():
    person.save()
print("All data encrypted!")
```

### Searching Limitations

Because data is encrypted, you cannot search in SQL:

```python
# ❌ This won't work as expected
Person.objects.filter(name__icontains="太郎")

# ✅ Do this instead
people = Person.objects.all()
results = [p for p in people if "太郎" in p.name]
```

## 🧪 Testing

Test that encryption is working:

```bash
# Run tests
python manage.py test sfd

# Or check manually
python -c "
from django.conf import settings
from cryptography.fernet import Fernet

# Test the key
key = settings.FERNET_KEYS[0]
if isinstance(key, str):
    key = key.encode()

f = Fernet(key)
test_data = '山田太郎'.encode()
encrypted = f.encrypt(test_data)
decrypted = f.decrypt(encrypted)

assert decrypted.decode() == '山田太郎'
print('✓ Encryption working correctly!')
"
```

## 📞 Support

For questions or issues with encryption:

1. Check `docs/encryption-guide.md`
2. Review examples in `sfd/examples/encrypted_fields_example.py`
3. Verify encryption key in `.env` file
4. Check database field types (should be TEXT for encrypted fields)

## 🚀 Performance Tips

1. **Caching**: Cache frequently accessed encrypted data
2. **Bulk Operations**: Use `select_related()` and `prefetch_related()`
3. **Indexing**: Create indexes on non-encrypted fields for searching
4. **Pagination**: Limit result sets when filtering in Python

## 🔄 Key Rotation

To rotate encryption keys:

```python
# 1. Generate new key
from cryptography.fernet import Fernet
new_key = Fernet.generate_key()
print(f"New key: {new_key.decode()}")

# 2. Add new key to FERNET_KEYS (keep old key first)
FERNET_KEYS = [
    b'old_key...',  # Keep old key for reading
    new_key,        # New key for writing
]

# 3. Re-encrypt all data with new key (custom script needed)

# 4. Remove old key from FERNET_KEYS
```

---

**Ready to use encrypted fields!** 🎉

Next: Run migrations and test the encryption.
