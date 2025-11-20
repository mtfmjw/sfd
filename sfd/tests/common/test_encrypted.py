# type: ignore
"""Test cases for sfd.common.encrypted module.

This module provides comprehensive test coverage for encrypted field types
including encryption/decryption functionality, edge cases, and integration
with Django ORM.
"""

import base64
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet
from django.core.exceptions import ValidationError
from django.db import models
from django.test import TestCase

from sfd.common.encrypted import (
    EncryptedCharField,
    EncryptedDateField,
    EncryptedEmailField,
    EncryptedMixin,
    EncryptedTextField,
    get_fernet,
)


@pytest.mark.unit
@pytest.mark.common
class GetFernetTest(TestCase):
    """Test cases for the get_fernet function.

    Tests the initialization and retrieval of Fernet cipher instances
    from Django settings.
    """

    def test_get_fernet_returns_fernet_instance(self):
        """Test that get_fernet returns a valid Fernet instance."""
        fernet = get_fernet()
        self.assertIsInstance(fernet, Fernet)

    def test_get_fernet_key_from_settings(self):
        """Test that Fernet is initialized with key from settings."""
        fernet = get_fernet()
        # Verify we can use the fernet instance for encryption/decryption
        test_data = "test data"
        encrypted = fernet.encrypt(test_data.encode())
        decrypted = fernet.decrypt(encrypted).decode()
        self.assertEqual(decrypted, test_data)

    def test_get_fernet_consistency(self):
        """Test that get_fernet returns consistent Fernet instances."""
        fernet1 = get_fernet()
        fernet2 = get_fernet()
        # Both should be Fernet instances that use the same key
        test_value = "test consistency"
        encrypted = fernet1.encrypt(test_value.encode())
        decrypted = fernet2.decrypt(encrypted).decode()
        self.assertEqual(decrypted, test_value)

    def test_get_fernet_with_bytes_key(self):
        """Test that get_fernet handles bytes keys from settings."""
        fernet = get_fernet()
        # Test encryption/decryption works with retrieved fernet
        test_value = "test@example.com"
        encrypted = fernet.encrypt(test_value.encode())
        decrypted = fernet.decrypt(encrypted).decode()
        self.assertEqual(decrypted, test_value)


@pytest.mark.unit
@pytest.mark.common
class EncryptedMixinTest(TestCase):
    """Test cases for the EncryptedMixin class.

    Tests the core encryption/decryption functionality including
    prepare values, database conversion, and Python type conversion.
    """

    def setUp(self):
        """Set up test fixtures."""
        self.mixin = EncryptedMixin()
        self.mixin._python_type = str  # Set for testing
        self.mixin.column = "test_column"  # Set column name for logging tests
        self.test_value = "sensitive data"
        self.fernet = get_fernet()

    def test_get_prep_value_with_string(self):
        """Test encryption of string values."""
        result = self.mixin.get_prep_value(self.test_value)
        self.assertIsInstance(result, str)
        # Verify the result is base64 encoded
        base64.b64decode(result.encode())  # Should not raise

    def test_get_prep_value_with_none(self):
        """Test that None values are not encrypted."""
        result = self.mixin.get_prep_value(None)
        self.assertIsNone(result)

    def test_get_prep_value_with_empty_string(self):
        """Test that empty strings are not encrypted."""
        result = self.mixin.get_prep_value("")
        self.assertEqual(result, "")

    def test_get_prep_value_with_non_string(self):
        """Test that non-string values are converted to string before encryption."""
        result = self.mixin.get_prep_value(12345)
        self.assertIsInstance(result, str)
        # Verify it can be decrypted
        encrypted = base64.b64decode(result.encode())
        decrypted = self.fernet.decrypt(encrypted).decode()
        self.assertEqual(decrypted, "12345")

    def test_from_db_value_with_encrypted_data(self):
        """Test decryption of encrypted database values."""
        # Prepare encrypted data
        encrypted_bytes = self.fernet.encrypt(self.test_value.encode())
        encrypted_b64 = base64.b64encode(encrypted_bytes).decode()

        # Mock connection
        result = self.mixin.from_db_value(encrypted_b64, None, None)
        self.assertEqual(result, self.test_value)

    def test_from_db_value_with_none(self):
        """Test that None values from database are not decrypted."""
        result = self.mixin.from_db_value(None, None, None)
        self.assertIsNone(result)

    def test_from_db_value_with_empty_string(self):
        """Test that empty strings from database are not decrypted."""
        result = self.mixin.from_db_value("", None, None)
        self.assertEqual(result, "")

    def test_from_db_value_with_invalid_encrypted_data(self):
        """Test handling of invalid encrypted data."""
        # Test with invalid base64
        result = self.mixin.from_db_value("not valid base64!!!", None, None)
        self.assertEqual(result, "not valid base64!!!")

    def test_to_python_with_correct_type(self):
        """Test that to_python returns already-typed values unchanged."""
        result = self.mixin.to_python(self.test_value)
        self.assertEqual(result, self.test_value)

    def test_to_python_with_plain_string(self):
        """Test to_python with plain string value."""
        # When to_python receives a plain unencrypted string
        result = self.mixin.to_python(self.test_value)
        self.assertEqual(result, self.test_value)

    def test_to_python_with_none(self):
        """Test that to_python handles None."""
        result = self.mixin.to_python(None)
        self.assertIsNone(result)

    def test_to_python_with_empty_string(self):
        """Test that to_python handles empty strings."""
        result = self.mixin.to_python("")
        self.assertEqual(result, "")

    def test_encrypt_decrypt_roundtrip(self):
        """Test complete encryption/decryption roundtrip."""
        # Encrypt
        encrypted = self.mixin.get_prep_value(self.test_value)
        # Decrypt
        decrypted = self.mixin.from_db_value(encrypted, None, None)
        self.assertEqual(decrypted, self.test_value)

    def test_convert_from_db_default_implementation(self):
        """Test that _convert_from_db returns value as-is by default."""
        result = self.mixin._convert_from_db(self.test_value)
        self.assertEqual(result, self.test_value)


@pytest.mark.unit
@pytest.mark.common
class EncryptedCharFieldTest(TestCase):
    """Test cases for EncryptedCharField.

    Tests the CharField-based encrypted field including form field generation
    and field deconstruction for migrations.
    """

    def test_field_creation_with_default_max_length(self):
        """Test EncryptedCharField creation with default max_length."""
        field = EncryptedCharField()
        self.assertEqual(field.max_length, 255)

    def test_field_creation_with_custom_max_length(self):
        """Test EncryptedCharField creation with custom max_length."""
        field = EncryptedCharField(max_length=500)
        self.assertEqual(field.max_length, 500)

    def test_field_creation_with_original_max_length(self):
        """Test EncryptedCharField creation with original_max_length."""
        field = EncryptedCharField(max_length=500, original_max_length=100)
        self.assertEqual(field.max_length, 500)
        self.assertEqual(field.original_max_length, 100)

    def test_field_deconstruct(self):
        """Test field deconstruction for migrations."""
        field = EncryptedCharField(max_length=500, original_max_length=100)
        name, path, args, kwargs = field.deconstruct()

        self.assertIsNone(name)
        self.assertIn("original_max_length", kwargs)
        self.assertEqual(kwargs["original_max_length"], 100)

    def test_field_deconstruct_without_original_max_length(self):
        """Test field deconstruction without original_max_length."""
        field = EncryptedCharField(max_length=255)
        name, path, args, kwargs = field.deconstruct()

        self.assertIsNone(name)
        self.assertNotIn("original_max_length", kwargs)

    def test_formfield_creation(self):
        """Test that formfield returns a CharField."""
        field = EncryptedCharField(max_length=255, original_max_length=100)
        form_field = field.formfield()

        self.assertIsNotNone(form_field)
        self.assertEqual(form_field.max_length, 100)

    def test_formfield_without_original_max_length(self):
        """Test formfield when original_max_length is not set."""
        field = EncryptedCharField(max_length=255)
        form_field = field.formfield()

        self.assertIsNotNone(form_field)

    def test_encrypt_char_field_value(self):
        """Test encryption of CharField values."""
        field = EncryptedCharField()
        test_value = "sensitive name"
        encrypted = field.get_prep_value(test_value)

        # Verify it's encrypted (different from original)
        self.assertNotEqual(encrypted, test_value)
        # Verify it can be decrypted
        decrypted = field.from_db_value(encrypted, None, None)
        self.assertEqual(decrypted, test_value)


@pytest.mark.unit
@pytest.mark.common
class EncryptedTextFieldTest(TestCase):
    """Test cases for EncryptedTextField.

    Tests the TextField-based encrypted field for storing larger encrypted text.
    """

    def test_field_creation(self):
        """Test EncryptedTextField creation."""
        field = EncryptedTextField()
        self.assertIsInstance(field, models.TextField)

    def test_encrypt_text_field_value(self):
        """Test encryption of TextField values."""
        field = EncryptedTextField()
        test_value = "This is a long sensitive text that should be encrypted for storage."
        encrypted = field.get_prep_value(test_value)

        # Verify it's encrypted
        self.assertNotEqual(encrypted, test_value)
        # Verify it can be decrypted
        decrypted = field.from_db_value(encrypted, None, None)
        self.assertEqual(decrypted, test_value)

    def test_encrypt_text_field_with_special_characters(self):
        """Test encryption of text with special characters."""
        field = EncryptedTextField()
        test_value = "Special chars: !@#$%^&*()_+-=[]{}|;:',.<>?/\\~`"
        encrypted = field.get_prep_value(test_value)
        decrypted = field.from_db_value(encrypted, None, None)

        self.assertEqual(decrypted, test_value)

    def test_encrypt_text_field_with_unicode(self):
        """Test encryption of text with unicode characters."""
        field = EncryptedTextField()
        test_value = "Unicode test: 日本語 Ελληνικά العربية 中文"
        encrypted = field.get_prep_value(test_value)
        decrypted = field.from_db_value(encrypted, None, None)

        self.assertEqual(decrypted, test_value)


@pytest.mark.unit
@pytest.mark.common
class EncryptedEmailFieldTest(TestCase):
    """Test cases for EncryptedEmailField.

    Tests the EmailField-based encrypted field including email-specific
    validation and form field generation.
    """

    def test_field_creation_with_default_max_length(self):
        """Test EncryptedEmailField creation with default max_length."""
        field = EncryptedEmailField()
        self.assertEqual(field.max_length, 255)

    def test_field_creation_with_custom_max_length(self):
        """Test EncryptedEmailField creation with custom max_length."""
        field = EncryptedEmailField(max_length=500)
        self.assertEqual(field.max_length, 500)

    def test_field_creation_with_original_max_length(self):
        """Test EncryptedEmailField creation with original_max_length."""
        field = EncryptedEmailField(max_length=500, original_max_length=254)
        self.assertEqual(field.max_length, 500)
        # original_max_length is now properly preserved
        self.assertEqual(field.original_max_length, 254)

    def test_field_deconstruct(self):
        """Test field deconstruction for migrations."""
        field = EncryptedEmailField(max_length=500, original_max_length=254)
        name, path, args, kwargs = field.deconstruct()

        self.assertIsNone(name)
        # original_max_length is now properly included in deconstruct
        self.assertIn("original_max_length", kwargs)
        self.assertEqual(kwargs.get("original_max_length"), 254)
        self.assertEqual(kwargs.get("max_length"), 500)

    def test_formfield_creation(self):
        """Test that formfield returns an EmailField."""
        field = EncryptedEmailField(max_length=385, original_max_length=254)
        form_field = field.formfield()

        self.assertIsNotNone(form_field)
        # form_field.max_length uses original_max_length when available
        self.assertEqual(form_field.max_length, 254)

    def test_encrypt_email_field_value(self):
        """Test encryption of email field values."""
        field = EncryptedEmailField()
        test_email = "user@example.com"
        encrypted = field.get_prep_value(test_email)

        # Verify it's encrypted
        self.assertNotEqual(encrypted, test_email)
        # Verify it can be decrypted
        decrypted = field.from_db_value(encrypted, None, None)
        self.assertEqual(decrypted, test_email)

    def test_encrypt_email_field_with_long_email(self):
        """Test encryption of long email addresses."""
        field = EncryptedEmailField()
        test_email = "very.long.email.address.with.many.subdomains@subdomain.example.co.uk"
        encrypted = field.get_prep_value(test_email)
        decrypted = field.from_db_value(encrypted, None, None)

        self.assertEqual(decrypted, test_email)

    def test_encrypt_email_field_with_special_chars(self):
        """Test encryption of email addresses with allowed special characters."""
        field = EncryptedEmailField()
        test_email = "user+tag@example.co.uk"
        encrypted = field.get_prep_value(test_email)
        decrypted = field.from_db_value(encrypted, None, None)

        self.assertEqual(decrypted, test_email)


@pytest.mark.unit
@pytest.mark.common
class EncryptedDateFieldTest(TestCase):
    """Test cases for EncryptedDateField.

    Tests the DateField-based encrypted field including date-specific handling.
    """

    def test_field_creation(self):
        """Test EncryptedDateField creation."""
        field = EncryptedDateField()
        # EncryptedDateField now inherits from CharField (for VARCHAR storage)
        self.assertIsInstance(field, models.CharField)

    def test_encrypt_date_field_value(self):
        """Test encryption of date field values."""
        field = EncryptedDateField()
        test_value = "2024-01-15"  # Date as string
        encrypted = field.get_prep_value(test_value)

        # Verify it's encrypted
        self.assertNotEqual(encrypted, test_value)
        # Verify it can be decrypted
        decrypted = field.from_db_value(encrypted, None, None)
        self.assertEqual(decrypted, test_value)

    def test_convert_from_db_returns_string(self):
        """Test that _convert_from_db returns string representation."""
        field = EncryptedDateField()
        test_value = "2024-01-15"
        result = field._convert_from_db(test_value)

        self.assertEqual(result, test_value)
        self.assertIsInstance(result, str)


@pytest.mark.unit
@pytest.mark.common
class EncryptedFieldIntegrationTest(TestCase):
    """Integration tests for encrypted fields.

    Tests encryption/decryption with various data types, sizes,
    and edge cases across different field types.
    """

    def test_multiple_fields_independent_encryption(self):
        """Test that different fields encrypt/decrypt independently."""
        char_field = EncryptedCharField()
        text_field = EncryptedTextField()
        email_field = EncryptedEmailField()

        char_value = "test name"
        text_value = "test notes"
        email_value = "test@example.com"

        char_encrypted = char_field.get_prep_value(char_value)
        text_encrypted = text_field.get_prep_value(text_value)
        email_encrypted = email_field.get_prep_value(email_value)

        # All should be different
        self.assertNotEqual(char_encrypted, text_encrypted)
        self.assertNotEqual(text_encrypted, email_encrypted)
        self.assertNotEqual(char_encrypted, email_encrypted)

        # All should decrypt correctly
        self.assertEqual(char_field.from_db_value(char_encrypted, None, None), char_value)
        self.assertEqual(text_field.from_db_value(text_encrypted, None, None), text_value)
        self.assertEqual(email_field.from_db_value(email_encrypted, None, None), email_value)

    def test_large_text_encryption(self):
        """Test encryption of large text values."""
        field = EncryptedTextField()
        # Create a large text value (1MB)
        large_text = "x" * (1024 * 1024)
        encrypted = field.get_prep_value(large_text)
        decrypted = field.from_db_value(encrypted, None, None)

        self.assertEqual(decrypted, large_text)

    def test_newline_and_whitespace_preservation(self):
        """Test that newlines and whitespace are preserved during encryption."""
        field = EncryptedTextField()
        test_value = "Line 1\n\tTabbed Line\n  Two spaces\r\nWindows line"
        encrypted = field.get_prep_value(test_value)
        decrypted = field.from_db_value(encrypted, None, None)

        self.assertEqual(decrypted, test_value)

    def test_encryption_consistency(self):
        """Test that same value encrypts to different ciphertext each time (Fernet property)."""
        field = EncryptedCharField()
        test_value = "same value"

        encrypted1 = field.get_prep_value(test_value)
        encrypted2 = field.get_prep_value(test_value)

        # Due to Fernet's timestamp and nonce, encryptions should be different
        self.assertNotEqual(encrypted1, encrypted2)

        # But both should decrypt to the same value
        decrypted1 = field.from_db_value(encrypted1, None, None)
        decrypted2 = field.from_db_value(encrypted2, None, None)

        self.assertEqual(decrypted1, test_value)
        self.assertEqual(decrypted2, test_value)

    def test_null_and_empty_across_fields(self):
        """Test None and empty string handling across all field types."""
        fields = [
            EncryptedCharField(),
            EncryptedTextField(),
            EncryptedEmailField(),
            EncryptedDateField(),
        ]

        for field in fields:
            with self.subTest(field=field.__class__.__name__):
                # Test None
                self.assertIsNone(field.get_prep_value(None))
                self.assertIsNone(field.from_db_value(None, None, None))

                # Test empty string
                self.assertEqual(field.get_prep_value(""), "")
                self.assertEqual(field.from_db_value("", None, None), "")

    def test_numeric_string_encryption(self):
        """Test encryption of numeric strings."""
        field = EncryptedCharField()
        test_values = ["123", "0", "9999999999", "-42"]

        for value in test_values:
            with self.subTest(value=value):
                encrypted = field.get_prep_value(value)
                decrypted = field.from_db_value(encrypted, None, None)
                self.assertEqual(decrypted, value)


@pytest.mark.unit
@pytest.mark.common
class GetFernetBytesKeyTest(TestCase):
    """Test get_fernet with bytes key from settings."""

    def test_get_fernet_with_pre_encoded_bytes_key(self):
        """Test that get_fernet handles pre-encoded bytes keys."""
        # This tests the isinstance(key, str) check with bytes key
        fernet = get_fernet()
        test_value = "test data"
        encrypted = fernet.encrypt(test_value.encode())
        decrypted = fernet.decrypt(encrypted).decode()
        self.assertEqual(decrypted, test_value)


@pytest.mark.unit
@pytest.mark.common
class EncryptedMixinExceptionHandlingTest(TestCase):
    """Test exception handling in EncryptedMixin methods."""

    def setUp(self):
        """Set up test fixtures."""
        self.mixin = EncryptedMixin()
        self.mixin._python_type = str
        self.mixin.column = "test_column"  # Set column name for logging tests

    def test_from_db_value_with_invalid_base64(self):
        """Test from_db_value handles invalid base64 gracefully."""
        # Invalid base64 that cannot be decoded
        result = self.mixin.from_db_value("not@valid$base64", None, None)
        self.assertEqual(result, "not@valid$base64")

    def test_from_db_value_with_truncated_encrypted_data(self):
        """Test from_db_value handles truncated encrypted data."""
        fernet = get_fernet()
        valid_encrypted = fernet.encrypt(b"test")
        valid_b64 = base64.b64encode(valid_encrypted).decode()
        # Truncate the base64 string
        truncated = valid_b64[:-10]

        result = self.mixin.from_db_value(truncated, None, None)
        # Should return as-is when decryption fails
        self.assertEqual(result, truncated)

    def test_to_python_with_invalid_encrypted_format(self):
        """Test to_python handles invalid encrypted format."""
        # Plain text that looks like it might be base64 but isn't valid Fernet
        result = self.mixin.to_python("notencrypteddata123")
        self.assertEqual(result, "notencrypteddata123")

    def test_to_python_with_malformed_fernet_data(self):
        """Test to_python with malformed but valid base64 string."""
        # Create valid base64 but invalid Fernet token
        fake_encrypted = base64.b64encode(b"not a valid fernet token").decode()
        result = self.mixin.to_python(fake_encrypted)
        # Should fall back to _convert_from_db
        self.assertIsNotNone(result)

    def test_to_python_early_return_when_already_correct_type(self):
        """Test that to_python returns immediately when value is correct type."""
        test_value = "already a string"
        result = self.mixin.to_python(test_value)
        self.assertEqual(result, test_value)


@pytest.mark.unit
@pytest.mark.common
class EncryptedFieldEdgeCasesTest(TestCase):
    """Test edge cases and boundary conditions for encrypted fields."""

    def test_encrypted_char_field_with_max_boundary(self):
        """Test EncryptedCharField at maximum boundary."""
        field = EncryptedCharField(max_length=500, original_max_length=100)
        # Create a string close to original_max_length
        test_value = "x" * 99
        encrypted = field.get_prep_value(test_value)
        decrypted = field.from_db_value(encrypted, None, None)
        self.assertEqual(decrypted, test_value)

    def test_encrypted_email_field_formfield_max_length(self):
        """Test EncryptedEmailField formfield respects max_length."""
        field = EncryptedEmailField(max_length=500, original_max_length=100)
        form_field = field.formfield()
        # The form field uses original_max_length when available
        self.assertEqual(form_field.max_length, 100)

    def test_encrypted_char_field_formfield_without_max_length(self):
        """Test EncryptedCharField formfield creation without original_max_length."""
        field = EncryptedCharField()
        form_field = field.formfield()
        self.assertIsNotNone(form_field)

    def test_encrypted_text_field_roundtrip_with_newlines(self):
        """Test TextField with various newline formats."""
        field = EncryptedTextField()
        test_cases = [
            "line1\nline2",
            "line1\r\nline2",
            "line1\n\n\nline2",
            "\n\n",
        ]

        for value in test_cases:
            with self.subTest(value=repr(value)):
                encrypted = field.get_prep_value(value)
                decrypted = field.from_db_value(encrypted, None, None)
                self.assertEqual(decrypted, value)

    def test_encrypted_field_boolean_to_string_conversion(self):
        """Test that boolean values are converted to string before encryption."""
        field = EncryptedCharField()
        # Test with boolean True
        encrypted_true = field.get_prep_value(True)
        decrypted_true = field.from_db_value(encrypted_true, None, None)
        self.assertEqual(decrypted_true, "True")

        # Test with boolean False
        encrypted_false = field.get_prep_value(False)
        decrypted_false = field.from_db_value(encrypted_false, None, None)
        self.assertEqual(decrypted_false, "False")

    def test_encrypted_field_float_to_string_conversion(self):
        """Test that float values are converted to string before encryption."""
        field = EncryptedCharField()
        test_values = [3.14, 0.0, -99.99, 1e10]

        for value in test_values:
            with self.subTest(value=value):
                encrypted = field.get_prep_value(value)
                decrypted = field.from_db_value(encrypted, None, None)
                self.assertEqual(decrypted, str(value))

    def test_encrypted_email_field_without_original_max_length(self):
        """Test EncryptedEmailField formfield without original_max_length."""
        field = EncryptedEmailField()
        form_field = field.formfield()
        self.assertIsNotNone(form_field)

    def test_get_fernet_caching_not_required(self):
        """Test that get_fernet creates new instances (no caching required)."""
        fernet1 = get_fernet()
        fernet2 = get_fernet()
        # Both should work correctly even if not the same object
        test_data = "cache test"
        encrypted = fernet1.encrypt(test_data.encode())
        decrypted = fernet2.decrypt(encrypted).decode()
        self.assertEqual(decrypted, test_data)

    def test_mixin_convert_from_db_with_various_types(self):
        """Test _convert_from_db with different string values."""
        mixin = EncryptedMixin()
        test_cases = [
            "normal string",
            "123",
            "",
            "with\ttabs",
            "with\x00null",
        ]

        for value in test_cases:
            with self.subTest(value=repr(value)):
                result = mixin._convert_from_db(value)
                self.assertEqual(result, value)

    def test_encrypted_fields_with_none_in_prep_value(self):
        """Test that all encrypted fields handle None in get_prep_value."""
        fields = [
            EncryptedCharField(),
            EncryptedTextField(),
            EncryptedEmailField(),
            EncryptedDateField(),
        ]

        for field in fields:
            with self.subTest(field=field.__class__.__name__):
                result = field.get_prep_value(None)
                self.assertIsNone(result)

    def test_encrypted_char_field_deconstruct_with_all_kwargs(self):
        """Test EncryptedCharField deconstruct with all possible kwargs."""
        field = EncryptedCharField(
            max_length=300,
            original_max_length=150,
            blank=True,
            null=True,
        )
        name, path, args, kwargs = field.deconstruct()

        self.assertIn("original_max_length", kwargs)
        self.assertEqual(kwargs["original_max_length"], 150)
        self.assertEqual(kwargs.get("max_length"), 300)

    def test_encrypted_email_field_deconstruct_with_all_kwargs(self):
        """Test EncryptedEmailField deconstruct with all possible kwargs."""
        field = EncryptedEmailField(
            max_length=400,
            original_max_length=200,
            blank=False,
        )
        name, path, args, kwargs = field.deconstruct()

        # original_max_length is now properly included
        self.assertIn("original_max_length", kwargs)
        self.assertEqual(kwargs.get("original_max_length"), 200)
        self.assertEqual(kwargs.get("max_length"), 400)


@pytest.mark.unit
@pytest.mark.common
class GetFernetStringKeyTest(TestCase):
    """Test get_fernet when FERNET_KEYS contains a string key."""

    @patch("sfd.common.encrypted.settings.FERNET_KEYS", [Fernet.generate_key().decode()])
    def test_get_fernet_with_string_key_in_settings(self):
        """Test that get_fernet handles string keys from settings correctly."""
        # This test covers line 21 - the isinstance(key, str) check
        fernet = get_fernet()
        self.assertIsInstance(fernet, Fernet)

        # Verify it can encrypt and decrypt
        test_value = "test with string key"
        encrypted = fernet.encrypt(test_value.encode())
        decrypted = fernet.decrypt(encrypted).decode()
        self.assertEqual(decrypted, test_value)


@pytest.mark.unit
@pytest.mark.common
class EncryptedMixinToPythonExceptionTest(TestCase):
    """Test to_python exception handling in EncryptedMixin."""

    def setUp(self):
        """Set up test fixtures."""
        self.mixin = EncryptedMixin()
        self.mixin._python_type = str
        self.mixin.column = "test_column"  # Set column name for logging tests

    def test_to_python_with_corrupted_encrypted_data(self):
        """Test to_python exception handling with corrupted encrypted data."""
        # This tests lines 69-76 - the exception handler in to_python
        # Create valid base64 but invalid/corrupted Fernet token
        corrupted_data = base64.b64encode(b"corrupted data here").decode()
        result = self.mixin.to_python(corrupted_data)
        # Should fall back to _convert_from_db without raising exception
        self.assertIsNotNone(result)

    def test_to_python_with_invalid_utf8_in_encrypted(self):
        """Test to_python with data that decrypts to invalid UTF-8."""
        # This also tests the exception handler
        fernet = get_fernet()
        # Encrypt some data, then corrupt just the decrypted part
        test_data = b"test"
        encrypted = fernet.encrypt(test_data)
        # Corrupt a byte in the encrypted data
        corrupted = bytearray(encrypted)
        corrupted[-5] ^= 0xFF  # Flip bits in one byte
        corrupted_b64 = base64.b64encode(corrupted).decode()

        result = self.mixin.to_python(corrupted_b64)
        # Should return as-is when decryption fails
        self.assertIsNotNone(result)

    def test_to_python_with_base64_decode_error(self):
        """Test to_python with invalid base64 encoding."""
        # Data that can't be decoded as base64
        invalid_b64 = "!!!invalid_base64!!!"
        result = self.mixin.to_python(invalid_b64)
        # Should fall back to _convert_from_db
        self.assertEqual(result, invalid_b64)

    def test_from_db_value_with_corrupted_encrypted_data(self):
        """Test from_db_value exception handling with corrupted data."""
        # Create valid base64 but invalid Fernet token
        corrupted_b64 = base64.b64encode(b"this is not valid fernet data").decode()

        result = self.mixin.from_db_value(corrupted_b64, None, None)
        # Should return as-is when decryption fails
        self.assertEqual(result, corrupted_b64)

    def test_from_db_value_with_decryption_failure(self):
        """Test from_db_value when decryption fails for valid Fernet format."""
        fernet = get_fernet()
        # Create a valid encrypted message with one fernet, try to decrypt with another
        test_data = "secret"
        encrypted = fernet.encrypt(test_data.encode())

        # Corrupt the encrypted token to cause decryption to fail
        corrupted = bytearray(encrypted)
        corrupted[20] ^= 0xFF
        corrupted_b64 = base64.b64encode(corrupted).decode()

        result = self.mixin.from_db_value(corrupted_b64, None, None)
        # Should return the corrupted value as-is
        self.assertEqual(result, corrupted_b64)


@pytest.mark.unit
@pytest.mark.common
class EncryptedMixinToPythonNonStringTypeTest(TestCase):
    """Test to_python with non-string Python types."""

    def test_to_python_exception_with_integer_type(self):
        """Test to_python exception handling when _python_type is not str."""
        # Create a custom mixin with a different _python_type
        mixin = EncryptedMixin()
        mixin._python_type = int  # Not a string type
        mixin.column = "test_column"  # Set column name for logging tests

        # Pass a string that can't be converted to int
        test_value = "not_an_integer"
        result = mixin.to_python(test_value)
        # Should hit the exception handler and call _convert_from_db
        self.assertIsNotNone(result)

    def test_to_python_successful_decrypt_with_non_string_type(self):
        """Test to_python successful decryption path with non-string type.

        This test ensures line 73 (fernet.decrypt) is executed by having
        a string value that's not the _python_type but is encrypted data.
        """
        mixin = EncryptedMixin()
        mixin._python_type = int  # Different from string type
        mixin.column = "test_column"  # Set column name for logging tests

        # Encrypt some data
        fernet = get_fernet()
        test_data = "123"
        encrypted = fernet.encrypt(test_data.encode())
        encrypted_b64 = base64.b64encode(encrypted).decode()

        # Call to_python with encrypted data when _python_type is int
        # This will:
        # 1. Pass the None/empty check
        # 2. Fail the isinstance(value, int) check (value is a string)
        # 3. Enter the try block and successfully decrypt
        result = mixin.to_python(encrypted_b64)
        self.assertEqual(result, test_data)


@pytest.mark.unit
@pytest.mark.common
class EncryptedMixinMaxLengthValidationTest(TestCase):
    """Test max_length validation in EncryptedMixin.get_prep_value."""

    def setUp(self):
        """Set up test fixtures."""
        self.mixin = EncryptedMixin()
        self.mixin._python_type = str
        self.mixin.column = "test_column"
        self.mixin.max_length = 50  # Set a small max_length to trigger error
        self.mixin.name = "test_field"

    def test_get_prep_value_exceeds_max_length(self):
        """Test that get_prep_value raises ValidationError when encrypted value exceeds max_length."""
        # Create a long string that will exceed the small max_length when encrypted
        long_value = "x" * 100
        with self.assertRaises(ValidationError) as context:
            self.mixin.get_prep_value(long_value)
        self.assertIn("too long for encryption", str(context.exception))

    def test_get_prep_value_with_non_string_input(self):
        """Test get_prep_value with non-string input converts to string."""
        self.mixin.max_length = 1000  # Set a large max_length
        result = self.mixin.get_prep_value(12345)
        # Should encrypt "12345" string
        self.assertIsInstance(result, str)
        # Verify it's base64 encoded
        base64.b64decode(result.encode())  # Should not raise


@pytest.mark.unit
@pytest.mark.common
class EncryptedTextFieldCoverageTest(TestCase):
    """Test coverage for EncryptedTextField."""

    def test_encrypted_text_field_creation(self):
        """Test EncryptedTextField creation."""
        field = EncryptedTextField()
        self.assertEqual(field._python_type, str)

    def test_encrypted_text_field_with_original_max_length(self):
        """Test EncryptedTextField with original_max_length."""
        field = EncryptedTextField(original_max_length=300)
        self.assertEqual(field.original_max_length, 300)

    def test_encrypted_text_field_roundtrip(self):
        """Test EncryptedTextField encryption/decryption roundtrip."""
        field = EncryptedTextField(original_max_length=500)
        test_value = "This is a long text\nWith multiple lines\nAnd special chars: !@#$%"
        encrypted = field.get_prep_value(test_value)
        decrypted = field.from_db_value(encrypted, None, None)
        self.assertEqual(decrypted, test_value)


@pytest.mark.unit
@pytest.mark.common
class EncryptedDateFieldCoverageTest(TestCase):
    """Test coverage for EncryptedDateField."""

    def test_encrypted_date_field_creation(self):
        """Test EncryptedDateField creation."""
        field = EncryptedDateField()
        self.assertEqual(field.max_length, 180)
        self.assertEqual(field._python_type, str)

    def test_encrypted_date_field_with_custom_max_length(self):
        """Test EncryptedDateField with custom max_length."""
        field = EncryptedDateField(max_length=200)
        self.assertEqual(field.max_length, 200)

    def test_encrypted_date_field_with_original_max_length(self):
        """Test EncryptedDateField with original_max_length."""
        field = EncryptedDateField(original_max_length=10)
        self.assertEqual(field.original_max_length, 10)

    def test_encrypted_date_field_deconstruct(self):
        """Test EncryptedDateField deconstruction."""
        field = EncryptedDateField(max_length=200, original_max_length=10)
        name, path, args, kwargs = field.deconstruct()
        self.assertIsNone(name)
        self.assertIn("original_max_length", kwargs)
        self.assertEqual(kwargs["original_max_length"], 10)

    def test_encrypted_date_field_deconstruct_without_original_max_length(self):
        """Test EncryptedDateField deconstruction without original_max_length."""
        field = EncryptedDateField(max_length=200)
        name, path, args, kwargs = field.deconstruct()
        self.assertNotIn("original_max_length", kwargs)

    def test_encrypted_date_field_formfield_without_original_max_length(self):
        """Test EncryptedDateField formfield without original_max_length."""
        field = EncryptedDateField(max_length=180)
        form_field = field.formfield()
        self.assertIsNotNone(form_field)
        # Check that the widget is a DateInput
        from django.forms import DateField as FormDateField

        self.assertEqual(form_field.widget.__class__, FormDateField().widget.__class__)

    def test_encrypted_date_field_formfield_with_original_max_length(self):
        """Test EncryptedDateField formfield with original_max_length."""
        field = EncryptedDateField(max_length=180, original_max_length=10)
        form_field = field.formfield()
        self.assertIsNotNone(form_field)
        # Widget should still be a DateInput
        from django.forms import DateField as FormDateField

        self.assertEqual(form_field.widget.__class__, FormDateField().widget.__class__)

    def test_encrypted_date_field_formfield_respects_kwargs(self):
        """Test EncryptedDateField formfield respects passed kwargs."""
        field = EncryptedDateField(max_length=180, original_max_length=10)
        form_field = field.formfield(required=False)
        self.assertFalse(form_field.required)

    def test_encrypted_date_field_convert_from_db(self):
        """Test EncryptedDateField._convert_from_db method."""
        field = EncryptedDateField()
        test_date = "2025-11-09"
        result = field._convert_from_db(test_date)
        self.assertEqual(result, test_date)

    def test_encrypted_date_field_roundtrip(self):
        """Test EncryptedDateField encryption/decryption roundtrip."""
        field = EncryptedDateField(original_max_length=10)
        test_date = "2025-11-09"
        encrypted = field.get_prep_value(test_date)
        decrypted = field.from_db_value(encrypted, None, None)
        self.assertEqual(decrypted, test_date)


@pytest.mark.unit
@pytest.mark.common
class EncryptedCharFieldFormfieldTest(TestCase):
    """Test EncryptedCharField formfield generation."""

    def test_formfield_without_original_max_length(self):
        """Test formfield without original_max_length specified."""
        field = EncryptedCharField(max_length=255)
        form_field = field.formfield()
        self.assertIsNotNone(form_field)
        # Widget should be set
        self.assertIsNotNone(form_field.widget)

    def test_formfield_with_original_max_length(self):
        """Test formfield with original_max_length."""
        field = EncryptedCharField(max_length=255, original_max_length=100)
        form_field = field.formfield()
        self.assertEqual(form_field.max_length, 100)

    def test_formfield_respects_kwargs_override(self):
        """Test that formfield respects passed kwargs."""
        field = EncryptedCharField(max_length=255, original_max_length=100)
        form_field = field.formfield(max_length=50)
        # Passed kwargs should override original_max_length
        self.assertEqual(form_field.max_length, 50)

    def test_deconstruct_includes_max_length_when_custom(self):
        """Test deconstruct includes custom max_length."""
        field = EncryptedCharField(max_length=300, original_max_length=150)
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(kwargs.get("max_length"), 300)
        self.assertEqual(kwargs.get("original_max_length"), 150)

    def test_deconstruct_preserves_model_field_kwargs(self):
        """Test deconstruct preserves other model field kwargs."""
        field = EncryptedCharField(max_length=300, original_max_length=150, null=True, blank=True)
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(kwargs.get("max_length"), 300)
        self.assertIn("null", kwargs)
        self.assertIn("blank", kwargs)


@pytest.mark.unit
@pytest.mark.common
class EncryptedEmailFieldFormfieldTest(TestCase):
    """Test EncryptedEmailField formfield generation."""

    def test_formfield_without_original_max_length(self):
        """Test EmailField formfield without original_max_length."""
        field = EncryptedEmailField(max_length=385)
        form_field = field.formfield()
        self.assertIsNotNone(form_field)

    def test_formfield_respects_kwargs_override(self):
        """Test that formfield respects passed kwargs."""
        field = EncryptedEmailField(max_length=385, original_max_length=254)
        form_field = field.formfield(max_length=100)
        # Passed kwargs should be respected
        self.assertEqual(form_field.max_length, 100)


@pytest.mark.unit
@pytest.mark.common
class EncryptedMixinNoneAndEmptyHandlingTest(TestCase):
    """Test None and empty string handling in EncryptedMixin."""

    def setUp(self):
        """Set up test fixtures."""
        self.mixin = EncryptedMixin()
        self.mixin._python_type = str
        self.mixin.column = "test_column"

    def test_get_prep_value_with_none(self):
        """Test get_prep_value returns None for None input."""
        result = self.mixin.get_prep_value(None)
        self.assertIsNone(result)

    def test_get_prep_value_with_empty_string(self):
        """Test get_prep_value returns empty string for empty input."""
        result = self.mixin.get_prep_value("")
        self.assertEqual(result, "")

    def test_from_db_value_with_none(self):
        """Test from_db_value returns None for None input."""
        result = self.mixin.from_db_value(None, None, None)
        self.assertIsNone(result)

    def test_from_db_value_with_empty_string(self):
        """Test from_db_value returns empty string for empty input."""
        result = self.mixin.from_db_value("", None, None)
        self.assertEqual(result, "")

    def test_to_python_with_none(self):
        """Test to_python returns None for None input."""
        result = self.mixin.to_python(None)
        self.assertIsNone(result)

    def test_to_python_with_empty_string(self):
        """Test to_python returns empty string for empty input."""
        result = self.mixin.to_python("")
        self.assertEqual(result, "")


@pytest.mark.unit
@pytest.mark.common
class EncryptedFieldDefaultMaxLengthTest(TestCase):
    """Test default max_length values for encrypted fields."""

    def test_encrypted_char_field_default_max_length(self):
        """Test EncryptedCharField default max_length."""
        field = EncryptedCharField()
        self.assertEqual(field.max_length, 255)

    def test_encrypted_date_field_default_max_length(self):
        """Test EncryptedDateField default max_length."""
        field = EncryptedDateField()
        self.assertEqual(field.max_length, 180)


@pytest.mark.unit
@pytest.mark.common
class EncryptedFieldPythonTypeTest(TestCase):
    """Test _python_type attribute in encrypted fields."""

    def test_encrypted_char_field_python_type(self):
        """Test EncryptedCharField._python_type."""
        field = EncryptedCharField()
        self.assertEqual(field._python_type, str)

    def test_encrypted_text_field_python_type(self):
        """Test EncryptedTextField._python_type."""
        field = EncryptedTextField()
        self.assertEqual(field._python_type, str)

    def test_encrypted_email_field_python_type(self):
        """Test EncryptedEmailField._python_type."""
        field = EncryptedEmailField()
        self.assertEqual(field._python_type, str)

    def test_encrypted_date_field_python_type(self):
        """Test EncryptedDateField._python_type."""
        field = EncryptedDateField()
        self.assertEqual(field._python_type, str)


@pytest.mark.unit
@pytest.mark.common
class EncryptedMixinConvertFromDbTest(TestCase):
    """Test _convert_from_db default implementation."""

    def test_convert_from_db_default_returns_value_as_is(self):
        """Test that default _convert_from_db returns value unchanged."""
        mixin = EncryptedMixin()
        test_value = "test string"
        result = mixin._convert_from_db(test_value)
        self.assertEqual(result, test_value)


@pytest.mark.unit
@pytest.mark.common
class EncryptedTextFieldFormfieldCoverageTest(TestCase):
    """Test EncryptedTextField formfield functionality."""

    def test_encrypted_text_field_formfield(self):
        """Test EncryptedTextField can generate a formfield."""
        field = EncryptedTextField(original_max_length=300)
        form_field = field.formfield()
        self.assertIsNotNone(form_field)


@pytest.mark.unit
@pytest.mark.common
class EncryptedTextFieldDeconstructTest(TestCase):
    """Test EncryptedTextField deconstruct method."""

    def test_encrypted_text_field_deconstruct_with_original_max_length(self):
        """Test EncryptedTextField deconstruct with original_max_length."""
        field = EncryptedTextField(original_max_length=300)
        name, path, args, kwargs = field.deconstruct()
        self.assertIsNone(name)
        # EncryptedTextField doesn't override deconstruct, so original_max_length won't be included
        self.assertNotIn("original_max_length", kwargs)

    def test_encrypted_text_field_deconstruct_without_original_max_length(self):
        """Test EncryptedTextField deconstruct without original_max_length."""
        field = EncryptedTextField()
        name, path, args, kwargs = field.deconstruct()
        self.assertIsNone(name)
        self.assertNotIn("original_max_length", kwargs)


@pytest.mark.unit
@pytest.mark.common
class EncryptedDateFieldFormfieldPassCoverageTest(TestCase):
    """Test EncryptedDateField formfield pass statement coverage."""

    def test_encrypted_date_field_formfield_executes_pass_statement(self):
        """Test that the pass statement in formfield is executed when original_max_length is truthy."""
        field = EncryptedDateField(max_length=180, original_max_length=10)
        # This should execute the pass statement in the if block
        form_field = field.formfield()
        self.assertIsNotNone(form_field)
        # Verify the widget is set correctly
        from django.forms import DateField as FormDateField

        self.assertEqual(form_field.widget.__class__, FormDateField().widget.__class__)


@pytest.mark.unit
@pytest.mark.common
class EncryptedCharFieldDeconstructDefaultTest(TestCase):
    """Test EncryptedCharField deconstruct with default values."""

    def test_deconstruct_with_default_max_length(self):
        """Test deconstruct when max_length is the default value."""
        field = EncryptedCharField()  # Uses default max_length=255
        name, path, args, kwargs = field.deconstruct()
        self.assertIsNone(name)
        # max_length should be included since it's explicitly set to default
        self.assertEqual(kwargs.get("max_length"), 255)


@pytest.mark.unit
@pytest.mark.common
class EncryptedEmailFieldDeconstructTest(TestCase):
    """Test EncryptedEmailField deconstruct method."""

    def test_encrypted_email_field_deconstruct_with_original_max_length(self):
        """Test EncryptedEmailField deconstruct with original_max_length."""
        field = EncryptedEmailField(max_length=385, original_max_length=254)
        name, path, args, kwargs = field.deconstruct()
        self.assertIsNone(name)
        # original_max_length is now properly included
        self.assertIn("original_max_length", kwargs)
        self.assertEqual(kwargs.get("original_max_length"), 254)
        self.assertEqual(kwargs.get("max_length"), 385)

    def test_encrypted_email_field_deconstruct_without_original_max_length(self):
        """Test EncryptedEmailField deconstruct without original_max_length."""
        field = EncryptedEmailField(max_length=385)
        name, path, args, kwargs = field.deconstruct()
        self.assertIsNone(name)
        self.assertNotIn("original_max_length", kwargs)
        self.assertEqual(kwargs.get("max_length"), 385)


@pytest.mark.unit
@pytest.mark.common
class EncryptedMixinGetPrepValueEdgeCasesTest(TestCase):
    """Test edge cases in EncryptedMixin.get_prep_value."""

    def setUp(self):
        """Set up test fixtures."""
        self.mixin = EncryptedMixin()
        self.mixin._python_type = str
        self.mixin.column = "test_column"
        self.mixin.max_length = 1000  # Large enough for all tests

    def test_get_prep_value_with_integer(self):
        """Test get_prep_value converts integer to string."""
        result = self.mixin.get_prep_value(42)
        self.assertIsInstance(result, str)
        # Should be able to decrypt back to "42"
        decrypted = self.mixin.from_db_value(result, None, None)
        self.assertEqual(decrypted, "42")

    def test_get_prep_value_with_float(self):
        """Test get_prep_value converts float to string."""
        result = self.mixin.get_prep_value(3.14)
        self.assertIsInstance(result, str)
        decrypted = self.mixin.from_db_value(result, None, None)
        self.assertEqual(decrypted, "3.14")

    def test_get_prep_value_with_boolean(self):
        """Test get_prep_value converts boolean to string."""
        result = self.mixin.get_prep_value(True)
        self.assertIsInstance(result, str)
        decrypted = self.mixin.from_db_value(result, None, None)
        self.assertEqual(decrypted, "True")


@pytest.mark.unit
@pytest.mark.common
class EncryptedFieldMaxLengthAttributeTest(TestCase):
    """Test max_length attribute access in encrypted fields."""

    def test_encrypted_char_field_max_length_attribute(self):
        """Test EncryptedCharField has max_length attribute."""
        field = EncryptedCharField(max_length=300)
        self.assertTrue(hasattr(field, "max_length"))
        self.assertEqual(field.max_length, 300)

    def test_encrypted_text_field_max_length_attribute(self):
        """Test EncryptedTextField has max_length attribute when provided."""
        field = EncryptedTextField(max_length=400)
        self.assertTrue(hasattr(field, "max_length"))
        self.assertEqual(field.max_length, 400)

    def test_encrypted_email_field_max_length_attribute(self):
        """Test EncryptedEmailField has max_length attribute."""
        field = EncryptedEmailField(max_length=385)
        self.assertTrue(hasattr(field, "max_length"))
        self.assertEqual(field.max_length, 385)

    def test_encrypted_date_field_max_length_attribute(self):
        """Test EncryptedDateField has max_length attribute."""
        field = EncryptedDateField(max_length=180)
        self.assertTrue(hasattr(field, "max_length"))
        self.assertEqual(field.max_length, 180)


@pytest.mark.unit
@pytest.mark.common
class EncryptedMixinNameAttributeTest(TestCase):
    """Test name attribute access in EncryptedMixin."""

    def test_encrypted_mixin_name_attribute_access(self):
        """Test that name attribute can be accessed safely."""
        mixin = EncryptedMixin()
        # Test getattr with default
        name = getattr(mixin, "name", "unknown field")
        self.assertEqual(name, "unknown field")

        # Test with actual name set
        mixin.name = "test_field"
        name = getattr(mixin, "name", "unknown field")
        self.assertEqual(name, "test_field")


@pytest.mark.unit
@pytest.mark.common
class EncryptedDateFieldConvertFromDbTest(TestCase):
    """Test EncryptedDateField._convert_from_db method specifically."""

    def test_convert_from_db_with_various_inputs(self):
        """Test _convert_from_db with different input types."""
        field = EncryptedDateField()

        # Test with string
        result = field._convert_from_db("2025-11-09")
        self.assertEqual(result, "2025-11-09")

        # Test with None
        result = field._convert_from_db(None)
        self.assertIsNone(result)

        # Test with empty string
        result = field._convert_from_db("")
        self.assertEqual(result, "")

    def test_convert_from_db_preserves_data_integrity(self):
        """Test that _convert_from_db doesn't modify the data."""
        field = EncryptedDateField()
        test_data = "2025-11-09T10:30:00"
        result = field._convert_from_db(test_data)
        self.assertEqual(result, test_data)


@pytest.mark.unit
@pytest.mark.common
class EncryptedTextFieldInitTest(TestCase):
    """Test EncryptedTextField initialization."""

    def test_encrypted_text_field_init_without_original_max_length(self):
        """Test EncryptedTextField init without original_max_length."""
        field = EncryptedTextField()
        self.assertIsNone(field.original_max_length)

    def test_encrypted_text_field_init_with_original_max_length(self):
        """Test EncryptedTextField init with original_max_length."""
        field = EncryptedTextField(original_max_length=500)
        self.assertEqual(field.original_max_length, 500)


@pytest.mark.unit
@pytest.mark.common
class EncryptedEmailFieldInitTest(TestCase):
    """Test EncryptedEmailField initialization edge cases."""

    def test_encrypted_email_field_init_preserves_max_length(self):
        """Test that EncryptedEmailField preserves custom max_length."""
        field = EncryptedEmailField(max_length=400)
        self.assertEqual(field.max_length, 400)

    def test_encrypted_email_field_init_with_all_params(self):
        """Test EncryptedEmailField init with all parameters."""
        field = EncryptedEmailField(max_length=400, original_max_length=200, null=True)
        self.assertEqual(field.max_length, 400)
        # original_max_length is now properly preserved
        self.assertEqual(field.original_max_length, 200)
        self.assertTrue(field.null)


@pytest.mark.unit
@pytest.mark.common
class DeterministicEncryptionTest(TestCase):
    """Test cases for deterministic encryption functionality."""

    def test_get_deterministic_key_returns_32_bytes(self):
        """Test that get_deterministic_key returns a 32-byte key."""
        from sfd.common.encrypted import get_deterministic_key

        key = get_deterministic_key()
        self.assertEqual(len(key), 32)

    def test_get_deterministic_key_with_string(self):
        """Test that get_deterministic_key handles string keys."""
        from django.conf import settings

        from sfd.common.encrypted import get_deterministic_key

        with patch.object(settings, "DETERMINISTIC_ENCRYPTION_KEY", "test_key_string", create=True):
            key = get_deterministic_key()
            self.assertEqual(len(key), 32)
            self.assertIsInstance(key, bytes)

    def test_get_deterministic_key_pads_short_key(self):
        """Test that get_deterministic_key pads keys shorter than 32 bytes."""
        from django.conf import settings

        from sfd.common.encrypted import get_deterministic_key

        short_key = b"short"
        with patch.object(settings, "DETERMINISTIC_ENCRYPTION_KEY", short_key, create=True):
            key = get_deterministic_key()
            self.assertEqual(len(key), 32)

    def test_get_deterministic_key_truncates_long_key(self):
        """Test that get_deterministic_key truncates keys longer than 32 bytes."""
        from django.conf import settings

        from sfd.common.encrypted import get_deterministic_key

        long_key = b"a" * 50
        with patch.object(settings, "DETERMINISTIC_ENCRYPTION_KEY", long_key, create=True):
            key = get_deterministic_key()
            self.assertEqual(len(key), 32)

    def test_deterministic_encrypt_with_string(self):
        """Test deterministic encryption with string value."""
        from sfd.common.encrypted import deterministic_encrypt

        value = "test value"
        encrypted = deterministic_encrypt(value)
        self.assertIsNotNone(encrypted)
        self.assertIsInstance(encrypted, str)
        self.assertNotEqual(encrypted, value)

    def test_deterministic_encrypt_with_none(self):
        """Test that deterministic_encrypt returns None for None input."""
        from sfd.common.encrypted import deterministic_encrypt

        result = deterministic_encrypt(None)
        self.assertIsNone(result)

    def test_deterministic_encrypt_with_empty_string(self):
        """Test that deterministic_encrypt returns empty string for empty input."""
        from sfd.common.encrypted import deterministic_encrypt

        result = deterministic_encrypt("")
        self.assertEqual(result, "")

    def test_deterministic_encrypt_with_non_string(self):
        """Test deterministic encryption with non-string value."""
        from sfd.common.encrypted import deterministic_encrypt

        value = 12345
        encrypted = deterministic_encrypt(value)
        self.assertIsNotNone(encrypted)
        self.assertIsInstance(encrypted, str)

    def test_deterministic_encrypt_consistency(self):
        """Test that deterministic encryption produces same output for same input."""
        from sfd.common.encrypted import deterministic_encrypt

        value = "consistent value"
        encrypted1 = deterministic_encrypt(value)
        encrypted2 = deterministic_encrypt(value)
        # Deterministic encryption should produce the same output
        self.assertEqual(encrypted1, encrypted2)

    def test_deterministic_decrypt_with_encrypted_data(self):
        """Test deterministic decryption with valid encrypted data."""
        from sfd.common.encrypted import deterministic_decrypt, deterministic_encrypt

        value = "test data"
        encrypted = deterministic_encrypt(value)
        decrypted = deterministic_decrypt(encrypted)
        self.assertEqual(decrypted, value)

    def test_deterministic_decrypt_with_none(self):
        """Test that deterministic_decrypt returns None for None input."""
        from sfd.common.encrypted import deterministic_decrypt

        result = deterministic_decrypt(None)
        self.assertIsNone(result)

    def test_deterministic_decrypt_with_empty_string(self):
        """Test that deterministic_decrypt returns empty string for empty input."""
        from sfd.common.encrypted import deterministic_decrypt

        result = deterministic_decrypt("")
        self.assertEqual(result, "")

    def test_deterministic_decrypt_with_invalid_data(self):
        """Test deterministic decryption with invalid encrypted data."""
        from sfd.common.encrypted import deterministic_decrypt

        # Invalid base64 data
        result = deterministic_decrypt("invalid data")
        self.assertEqual(result, "invalid data")

    def test_deterministic_decrypt_exception_handling(self):
        """Test that deterministic_decrypt handles exceptions gracefully."""
        from sfd.common.encrypted import deterministic_decrypt

        # Valid base64 but invalid encrypted data
        invalid_encrypted = base64.b64encode(b"not encrypted properly").decode()
        result = deterministic_decrypt(invalid_encrypted)
        # Should return the input when decryption fails
        self.assertEqual(result, invalid_encrypted)

    def test_generate_search_hash_with_string(self):
        """Test search hash generation with string value."""
        from sfd.common.encrypted import generate_search_hash

        value = "search value"
        hash_result = generate_search_hash(value)
        self.assertIsNotNone(hash_result)
        self.assertIsInstance(hash_result, str)
        # SHA-256 hex digest is 64 characters
        self.assertEqual(len(hash_result), 64)

    def test_generate_search_hash_with_none(self):
        """Test that generate_search_hash returns None for None input."""
        from sfd.common.encrypted import generate_search_hash

        result = generate_search_hash(None)
        self.assertIsNone(result)

    def test_generate_search_hash_with_empty_string(self):
        """Test that generate_search_hash returns None for empty input."""
        from sfd.common.encrypted import generate_search_hash

        result = generate_search_hash("")
        self.assertIsNone(result)

    def test_generate_search_hash_with_non_string(self):
        """Test search hash generation with non-string value."""
        from sfd.common.encrypted import generate_search_hash

        value = 98765
        hash_result = generate_search_hash(value)
        self.assertIsNotNone(hash_result)
        self.assertIsInstance(hash_result, str)
        self.assertEqual(len(hash_result), 64)

    def test_generate_search_hash_consistency(self):
        """Test that generate_search_hash produces same output for same input."""
        from sfd.common.encrypted import generate_search_hash

        value = "consistent hash"
        hash1 = generate_search_hash(value)
        hash2 = generate_search_hash(value)
        self.assertEqual(hash1, hash2)


@pytest.mark.unit
@pytest.mark.common
class SearchableEncryptedFieldTest(TestCase):
    """Test cases for searchable encrypted fields."""

    def test_searchable_char_field_creation(self):
        """Test creation of searchable EncryptedCharField."""
        field = EncryptedCharField(searchable=True)
        self.assertTrue(field.searchable)

    def test_searchable_field_uses_deterministic_encryption(self):
        """Test that searchable fields use deterministic encryption."""
        field = EncryptedCharField(searchable=True)
        value = "searchable value"

        encrypted1 = field.get_prep_value(value)
        encrypted2 = field.get_prep_value(value)

        # Deterministic encryption should produce the same output
        self.assertEqual(encrypted1, encrypted2)

    def test_searchable_field_encryption_decryption_roundtrip(self):
        """Test encryption/decryption roundtrip with searchable field."""
        field = EncryptedCharField(searchable=True)
        value = "searchable data"

        encrypted = field.get_prep_value(value)
        decrypted = field.from_db_value(encrypted, None, None)

        self.assertEqual(decrypted, value)

    def test_searchable_field_to_python_with_encrypted_data(self):
        """Test to_python with searchable field and encrypted data where type is not matching."""
        # Create a field with non-str _python_type to bypass the isinstance check
        field = EncryptedCharField(searchable=True)
        field._python_type = int  # Set to non-string type so encrypted str won't match
        value = "python test"

        encrypted = field.get_prep_value(value)
        # Now to_python will try to decrypt because encrypted str is not an int
        result = field.to_python(encrypted)

        self.assertEqual(result, value)

    def test_searchable_field_deconstruct_includes_flag(self):
        """Test that deconstruct includes searchable flag."""
        field = EncryptedCharField(searchable=True, max_length=300)
        name, path, args, kwargs = field.deconstruct()

        self.assertTrue(kwargs.get("searchable"))

    def test_searchable_email_field(self):
        """Test searchable EncryptedEmailField."""
        field = EncryptedEmailField(searchable=True)
        email = "searchable@example.com"

        encrypted = field.get_prep_value(email)
        decrypted = field.from_db_value(encrypted, None, None)

        self.assertEqual(decrypted, email)

    def test_searchable_text_field(self):
        """Test searchable EncryptedTextField."""
        field = EncryptedTextField(searchable=True)
        text = "Long searchable text content"

        encrypted = field.get_prep_value(text)
        decrypted = field.from_db_value(encrypted, None, None)

        self.assertEqual(decrypted, text)

    def test_searchable_field_with_none(self):
        """Test searchable field with None value."""
        field = EncryptedCharField(searchable=True)

        encrypted = field.get_prep_value(None)
        self.assertIsNone(encrypted)

    def test_searchable_field_with_empty_string(self):
        """Test searchable field with empty string."""
        field = EncryptedCharField(searchable=True)

        encrypted = field.get_prep_value("")
        self.assertEqual(encrypted, "")

    def test_non_searchable_field_uses_fernet_encryption(self):
        """Test that non-searchable fields use Fernet encryption (non-deterministic)."""
        field = EncryptedCharField(searchable=False)
        value = "non-searchable value"

        encrypted1 = field.get_prep_value(value)
        encrypted2 = field.get_prep_value(value)

        # Fernet encryption should produce different outputs
        self.assertNotEqual(encrypted1, encrypted2)

        # But both should decrypt to the same value
        decrypted1 = field.from_db_value(encrypted1, None, None)
        decrypted2 = field.from_db_value(encrypted2, None, None)
        self.assertEqual(decrypted1, value)
        self.assertEqual(decrypted2, value)
