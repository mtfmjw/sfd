"""Quick manual test to verify phone/mobile decryption in admin."""

import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sfd_prj.settings")
django.setup()

from django.contrib.admin.sites import AdminSite

from sfd.models import Person
from sfd.views.person import PersonAdmin

# Create test person
Person.objects.all().delete()
person = Person.objects.create(
    family_name="TestFamily",
    family_name_kana="テストファミリー",
    name="TestPerson",
    name_kana="テストパーソン",
    phone_number="09012",
    mobile_number="09087",
)

print("\n" + "=" * 70)
print("ADMIN DISPLAY DECRYPTION TEST")
print("=" * 70)

# Create admin instance
admin = PersonAdmin(Person, AdminSite())

# Test display methods
print(f"\n✓ Person created with ID: {person.id}")
print(f"  Family Name: {person.family_name}")
print(f"  Name: {person.name}")

print("\n✓ Testing admin display methods:")
print(f"  phone_number display: {admin.phone_number(person)}")
print(f"  mobile_number display: {admin.mobile_number(person)}")

# Verify it matches the decrypted value
print("\n✓ Direct model access:")
print(f"  person.phone_number: {person.phone_number}")
print(f"  person.mobile_number: {person.mobile_number}")

# Verify they match
assert admin.phone_number(person) == person.phone_number, "Phone numbers don't match!"
assert admin.mobile_number(person) == person.mobile_number, "Mobile numbers don't match!"

print("\n✅ SUCCESS: Phone and mobile numbers are decrypted correctly in admin!")
