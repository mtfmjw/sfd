"""
Test to verify phone_number and mobile_number are decrypted in admin list view.
"""

import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sfd_prj.settings")
django.setup()

from django.contrib.admin.sites import AdminSite
from django.test import TestCase

from sfd.models import Person
from sfd.views.person import PersonAdmin


class TestPersonAdminDisplayDecryption(TestCase):
    """Test that encrypted fields are decrypted in admin list view."""

    def setUp(self):
        """Create a test person record."""
        self.person = Person.objects.create(
            family_name="Smith",
            family_name_kana="スミス",
            name="John",
            name_kana="ジョン",
            phone_number="09012345678",
            mobile_number="09087654321",
        )
        self.admin = PersonAdmin(Person, AdminSite())

    def test_phone_number_displayed_decrypted(self):
        """Test that phone_number is displayed as decrypted value in admin."""
        displayed_value = self.admin.phone_number(self.person)
        self.assertEqual(displayed_value, "09012345678")
        print(f"✓ Phone number displayed correctly: {displayed_value}")

    def test_mobile_number_displayed_decrypted(self):
        """Test that mobile_number is displayed as decrypted value in admin."""
        displayed_value = self.admin.mobile_number(self.person)
        self.assertEqual(displayed_value, "09087654321")
        print(f"✓ Mobile number displayed correctly: {displayed_value}")

    def test_phone_number_null_handled(self):
        """Test that phone_number handles None values gracefully."""
        person = Person.objects.create(
            family_name="Doe",
            family_name_kana="ドゥー",
            name="Jane",
            name_kana="ジェーン",
            phone_number=None,
            mobile_number=None,
        )
        displayed_value = self.admin.phone_number(person)
        self.assertEqual(displayed_value, "")
        print(f"✓ Null phone number handled correctly: '{displayed_value}'")

    def test_encrypted_data_stored_correctly(self):
        """Verify that encrypted data is actually encrypted in database."""
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute("SELECT phone_number FROM sfd_person WHERE id = %s", [self.person.id])
            result = cursor.fetchone()
            raw_value = result[0] if result else None

        # Raw value should be base64-encoded (not plain text)
        self.assertNotEqual(raw_value, "09012345678")
        self.assertTrue(raw_value.startswith("Z0FB"))  # Base64 encoded Fernet format starts with Z0FB
        print(f"✓ Phone number encrypted in database: {raw_value[:30]}...")


if __name__ == "__main__":
    import unittest

    suite = unittest.TestLoader().loadTestsFromTestCase(TestPersonAdminDisplayDecryption)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    if result.wasSuccessful():
        print("✓ All tests PASSED!")
        print("✓ Phone number and mobile_number fields are now decrypted in admin list view")
    else:
        print("✗ Some tests FAILED!")
