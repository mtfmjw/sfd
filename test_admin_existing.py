"""Test admin display with existing data."""

import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sfd_prj.settings")
django.setup()

from django.contrib.admin.sites import AdminSite

from sfd.models import Person
from sfd.views.person import PersonAdmin

# Use existing data
person = Person.objects.first()

if not person:
    print("No Person records found in database")
else:
    print("\n" + "=" * 70)
    print("ADMIN DISPLAY DECRYPTION TEST")
    print("=" * 70)

    admin = PersonAdmin(Person, AdminSite())

    print(f"\n✓ Using existing Person: {person}")
    print(f"  Phone Number: {person.phone_number}")
    print(f"  Mobile Number: {person.mobile_number}")

    print("\n✓ Testing admin display methods:")
    phone_display = admin.phone_number(person)
    mobile_display = admin.mobile_number(person)
    print(f"  admin.phone_number(): {phone_display}")
    print(f"  admin.mobile_number(): {mobile_display}")

    # Verify they match
    assert phone_display == (person.phone_number or ""), "Phone numbers don't match!"
    assert mobile_display == (person.mobile_number or ""), "Mobile numbers don't match!"

    print("\n✅ SUCCESS: Phone and mobile numbers are decrypted correctly in admin!")
    print("   Values match between model and admin display methods.")
