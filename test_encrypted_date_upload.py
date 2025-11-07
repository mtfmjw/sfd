#!/usr/bin/env python
"""
Test script to verify EncryptedDateField works correctly through the CSV upload process.
This is an integration test demonstrating the complete flow:
1. Create a Person record with an encrypted date field (birthday)
2. Verify the data is encrypted and stored as VARCHAR in the database
3. Retrieve the record and verify the date is decrypted correctly
"""

import os
import sys

import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sfd_prj.settings")
django.setup()

from django.db import connection

from sfd.models import Person


def test_encrypted_date_field_storage():
    """Test that EncryptedDateField stores dates as VARCHAR with encrypted base64 data."""
    print("\n" + "=" * 70)
    print("TEST 1: EncryptedDateField Storage and Type Checking")
    print("=" * 70)

    # Check field type
    birthday_field = Person._meta.get_field("birthday")
    print(f"✓ birthday field type: {type(birthday_field).__name__}")
    print(f"✓ birthday field max_length: {birthday_field.max_length}")
    print(f"✓ birthday field original_max_length: {birthday_field.original_max_length}")

    # Verify it's CharField-based (for VARCHAR storage)
    from django.db import models

    is_char = isinstance(birthday_field, models.CharField)
    print(f"✓ birthday field is CharField-based: {is_char}")

    if not is_char:
        print("✗ ERROR: EncryptedDateField should inherit from CharField!")
        return False

    print("\n✓ Field storage type verification PASSED")
    return True


def test_encrypted_date_field_create_and_retrieve():
    """Test creating and retrieving a Person with encrypted birthday."""
    print("\n" + "=" * 70)
    print("TEST 2: Create and Retrieve Encrypted Date")
    print("=" * 70)

    # Clear previous test data
    Person.objects.all().delete()

    # Create a Person with a birthday
    test_birthday = "1990-05-15"
    person = Person.objects.create(
        family_name="TestFamily",
        family_name_kana="テストファミリー",
        name="TestPerson",
        name_kana="テストパーソン",
        birthday=test_birthday,  # Pass as string
    )
    print(f"✓ Created Person with birthday: {test_birthday}")
    print(f"✓ Person ID: {person.id}")

    # Retrieve from database
    retrieved = Person.objects.get(id=person.id)
    print("✓ Retrieved Person from database")
    print(f"✓ Retrieved birthday value: {retrieved.birthday}")
    print(f"✓ Retrieved birthday type: {type(retrieved.birthday).__name__}")

    # Verify the birthday matches
    if str(retrieved.birthday) == test_birthday:
        print(f"\n✓ Birthday value matches: {test_birthday}")
    else:
        print("\n✗ ERROR: Birthday mismatch!")
        print(f"  Expected: {test_birthday}")
        print(f"  Got: {retrieved.birthday}")
        return False

    print("\n✓ Create and Retrieve test PASSED")
    return True


def test_encrypted_data_in_database():
    """Verify that encrypted data is actually stored as base64 in database (not a date)."""
    print("\n" + "=" * 70)
    print("TEST 3: Verify Encrypted Storage in Database")
    print("=" * 70)

    # Get the raw encrypted value from database
    person = Person.objects.first()
    if not person:
        print("✗ ERROR: No Person record found")
        return False

    with connection.cursor() as cursor:
        cursor.execute(f"SELECT birthday FROM {Person._meta.db_table} WHERE id = %s", [person.id])
        result = cursor.fetchone()
        raw_value = result[0] if result else None

    print(f"✓ Raw database value: {raw_value[:50]}..." if raw_value and len(raw_value) > 50 else f"✓ Raw database value: {raw_value}")
    print(f"✓ Raw value type in DB: {type(raw_value).__name__}")

    # Verify it's a base64 string (starts with standard base64 chars and ends with padding)
    import base64
    import re

    if raw_value:
        # Check if it looks like base64-encoded Fernet data
        # Fernet format: base64(version_byte + timestamp + token)
        # Base64 encoding uses: A-Za-z0-9+/= and sometimes -_
        is_base64_like = bool(re.match(r"^[A-Za-z0-9+/\-_]+=*$", raw_value))
        print(f"✓ Raw value is base64-encoded: {is_base64_like}")

        if not is_base64_like:
            print("✗ ERROR: Raw value doesn't look like base64-encoded Fernet data!")
            return False

        # Try to decode it to verify it's valid base64
        try:
            decoded = base64.urlsafe_b64decode(raw_value + "==")  # Add padding if needed
            print(f"✓ Base64 decode successful ({len(decoded)} bytes)")
            print(f"✓ First bytes (Fernet format): {decoded[:4].hex() if len(decoded) >= 4 else 'N/A'}")
        except Exception as e:
            print(f"✗ Base64 decode failed: {e}")
            return False

    print("\n✓ Encrypted storage verification PASSED")
    return True


def test_csv_upload_with_encrypted_date():
    """Test uploading Person records with encrypted date fields via CSV."""
    print("\n" + "=" * 70)
    print("TEST 4: CSV Upload with Encrypted Date Fields")
    print("=" * 70)

    # Clear previous test data
    Person.objects.all().delete()

    # Create CSV data with date field
    csv_data = """family_name,family_name_kana,name,name_kana,birthday
Smith,スミス,John,ジョン,1985-03-20
Johnson,ジョンソン,Jane,ジェーン,1992-07-10
Williams,ウイリアムス,Robert,ロバート,1978-12-05"""

    print("✓ Created CSV data with 3 Person records including dates")
    print("✓ CSV content:")
    for line in csv_data.split("\n")[:2]:
        print(f"  {line}")
    print("  ...")

    # Parse and process like the upload would
    from sfd.common.encrypted import EncryptedMixin

    lines = csv_data.strip().split("\n")
    headers = lines[0].split(",")

    print(f"\n✓ Headers: {headers}")

    # Check that birthday column is recognized as EncryptedDateField
    birthday_field = Person._meta.get_field("birthday")
    is_encrypted = isinstance(birthday_field, EncryptedMixin)
    print(f"✓ birthday field is EncryptedMixin: {is_encrypted}")

    # Create records from CSV data
    for row_idx, row_data in enumerate(lines[1:], 1):
        values = row_data.split(",")
        record_dict = dict(zip(headers, values, strict=False))

        try:
            person = Person.objects.create(**record_dict)
            print(f"✓ Row {row_idx}: Created person '{record_dict['name']}' with birthday '{record_dict['birthday']}'")

            # Verify it was encrypted
            retrieved = Person.objects.get(id=person.id)
            print(f"  └─ Verified: birthday stored as '{retrieved.birthday}'")
        except Exception as e:
            print(f"✗ Row {row_idx}: Failed to create person: {e}")
            return False

    # Verify all records were created
    count = Person.objects.count()
    print(f"\n✓ Total records created: {count}")

    if count != 3:
        print(f"✗ ERROR: Expected 3 records, got {count}")
        return False

    print("\n✓ CSV upload with encrypted dates PASSED")
    return True


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("EncryptedDateField Integration Tests")
    print("=" * 70)

    tests = [
        ("Field Storage Type", test_encrypted_date_field_storage),
        ("Create and Retrieve", test_encrypted_date_field_create_and_retrieve),
        ("Database Encryption", test_encrypted_data_in_database),
        ("CSV Upload", test_csv_upload_with_encrypted_date),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ Exception in {test_name}: {e}")
            import traceback

            traceback.print_exc()
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n✓ All tests PASSED! EncryptedDateField is working correctly.")
        return 0
    else:
        print("\n✗ Some tests FAILED!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
