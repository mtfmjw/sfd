"""
Encrypted field types for storing sensitive data.

These fields automatically encrypt data before saving to the database
and decrypt when retrieving, providing transparent field-level encryption.

Compatible with Django 5.x and PostgreSQL.
"""

import base64
import hashlib
import logging

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from django.conf import settings
from django.db import models

logger = logging.getLogger(__name__)


def get_fernet():
    """Get Fernet cipher instance using the key from settings."""
    key = settings.FERNET_KEYS[0]
    if isinstance(key, str):
        key = key.encode()
    return Fernet(key)


def get_deterministic_key():
    """Get deterministic encryption key from settings."""
    # Use a separate key for deterministic encryption
    key = getattr(settings, "DETERMINISTIC_ENCRYPTION_KEY", settings.FERNET_KEYS[0])
    if isinstance(key, str):
        key = key.encode()
    # Ensure key is 32 bytes for AES-256
    if len(key) < 32:
        key = key.ljust(32, b"\0")[:32]
    elif len(key) > 32:
        key = key[:32]
    return key


def deterministic_encrypt(value):
    """Deterministic encryption for searchable fields using AES."""
    if value is None or value == "":
        return value

    if not isinstance(value, str):
        value = str(value)

    key = get_deterministic_key()
    # Use a fixed IV for deterministic encryption
    iv = b"\0" * 16  # Fixed IV for deterministic behavior

    # Pad the value
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(value.encode()) + padder.finalize()

    # Encrypt
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    encrypted = encryptor.update(padded_data) + encryptor.finalize()

    # Base64 encode for storage
    encrypted_str = base64.b64encode(encrypted).decode()
    return encrypted_str


def deterministic_decrypt(encrypted_value):
    """Decrypt deterministically encrypted value."""
    if encrypted_value is None or encrypted_value == "":
        return encrypted_value

    try:
        key = get_deterministic_key()
        iv = b"\0" * 16  # Same fixed IV

        # Base64 decode
        encrypted = base64.b64decode(encrypted_value.encode())

        # Decrypt
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
        decryptor = cipher.decryptor()
        padded_data = decryptor.update(encrypted) + decryptor.finalize()

        # Unpad
        unpadder = padding.PKCS7(128).unpadder()
        data = unpadder.update(padded_data) + unpadder.finalize()

        return data.decode()
    except Exception:
        return encrypted_value


def generate_search_hash(value):
    """Generate a SHA-256 hash for searching."""
    if value is None or value == "":
        return None

    if not isinstance(value, str):
        value = str(value)

    # Use a consistent salt/key for hashing
    key = get_deterministic_key()
    hash_obj = hashlib.sha256(key + value.encode())
    return hash_obj.hexdigest()


class EncryptedMixin:
    """Mixin to add encryption/decryption to Django fields."""

    original_max_length = None  # Store original unencrypted max_length
    searchable = False  # Whether this field supports searching/indexing

    def __init__(self, *args, **kwargs):
        self.searchable = kwargs.pop("searchable", False)
        super().__init__(*args, **kwargs)

    def get_prep_value(self, value):
        """Encrypt the value before saving to database."""
        if value is None or value == "":
            return value

        # Convert to string if not already
        if not isinstance(value, str):
            value = str(value)

        # Choose encryption method based on searchable flag
        if self.searchable:
            encrypted_str = deterministic_encrypt(value)
        else:
            # Encrypt the value
            fernet = get_fernet()
            encrypted = fernet.encrypt(value.encode())
            encrypted_str = base64.b64encode(encrypted).decode()

        # Check if encrypted value exceeds max_length
        max_length = getattr(self, "max_length", None)  # type: ignore
        if max_length is not None:
            if len(encrypted_str) > max_length:
                from django.core.exceptions import ValidationError

                field_name = getattr(self, "name", "unknown field")  # type: ignore
                error_message = (
                    f"Encrypted value for '{field_name}' is {len(encrypted_str)} characters, "
                    f"but max_length is {max_length}. The original value is too long for encryption. "
                    f"Please increase max_length to at least {len(encrypted_str)} characters."
                )
                logger.error(error_message)
                raise ValidationError(error_message)

        return encrypted_str

    def from_db_value(self, value, expression, connection):
        """Decrypt the value when loading from database."""
        if value is None or value == "":
            return value

        try:
            if self.searchable:
                decrypted = deterministic_decrypt(value)
            else:
                # Decode and decrypt
                fernet = get_fernet()
                encrypted = base64.b64decode(value.encode())
                decrypted = fernet.decrypt(encrypted).decode()
            return self._convert_from_db(decrypted)
        except Exception:
            # If decryption fails, return as-is (might be unencrypted data)
            column_name = getattr(self, "column", "unknown")  # type: ignore
            logger.warning(f"An error occurred while decrypting a value from the {column_name} column in the database.")
            return value

    def to_python(self, value):
        """Convert to Python type."""
        if value is None or value == "":
            return value

        # If it's already the correct type, return it
        if isinstance(value, self._python_type):  # type: ignore
            return value

        # Try to decrypt if it looks encrypted (base64)
        try:
            if self.searchable:
                decrypted = deterministic_decrypt(value)
            else:
                fernet = get_fernet()
                encrypted = base64.b64decode(value.encode())
                decrypted = fernet.decrypt(encrypted).decode()
            return self._convert_from_db(decrypted)
        except Exception:
            # If decryption fails, try to convert directly
            column_name = getattr(self, "column", "unknown")  # type: ignore
            logger.warning(f"Failed to decrypt {column_name} during conversion to a Python value.")
            return self._convert_from_db(value)

    def _convert_from_db(self, value):
        """Override in subclasses to convert from string."""
        return value


class EncryptedCharField(EncryptedMixin, models.CharField):
    """
    CharField that automatically encrypts its contents before saving to database.
    Uses CharField as base to ensure text input widget in forms/admin.

    Usage:
        name = EncryptedCharField(max_length=180, original_max_length=100)

    Parameters:
        max_length: Size for encrypted data in database (VARCHAR)
        original_max_length: Size for the original unencrypted data (for form validation)
    """

    _python_type = str

    def __init__(self, *args, **kwargs):
        # Extract original_max_length before passing to parent
        self.original_max_length = kwargs.pop("original_max_length", None)

        # Set a default max_length if not provided
        if "max_length" not in kwargs:
            kwargs["max_length"] = 255
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if self.original_max_length:
            kwargs["original_max_length"] = self.original_max_length
        if self.searchable:
            kwargs["searchable"] = self.searchable
        return name, path, args, kwargs

    def formfield(self, **kwargs):
        """Return a CharField for forms with original_max_length validation."""
        defaults = {"widget": models.CharField().formfield().widget}
        if self.original_max_length:
            defaults["max_length"] = self.original_max_length
        defaults.update(kwargs)
        return super().formfield(**defaults)


class EncryptedTextField(EncryptedMixin, models.TextField):
    """
    TextField that automatically encrypts its contents.
    Uses TextField as base.

    Usage:
        description = EncryptedTextField(max_length=420, original_max_length=255)

    Parameters:
        max_length: Size for encrypted data in database (used for validation)
        original_max_length: Size for the original unencrypted data (for form validation)
    """

    _python_type = str

    def __init__(self, *args, **kwargs):
        self.original_max_length = kwargs.pop("original_max_length", None)
        super().__init__(*args, **kwargs)


class EncryptedEmailField(EncryptedCharField):
    """
    EmailField that automatically encrypts its contents.
    Inherits from EncryptedCharField to provide encryption for email fields.

    Usage:
        email = EncryptedEmailField(max_length=385, original_max_length=100)

    Parameters:
        max_length: Size for encrypted data in database (VARCHAR)
        original_max_length: Size for the original unencrypted data (for form validation)
    """

    _python_type = str

    def __init__(self, *args, **kwargs):
        # Don't pop original_max_length here - parent EncryptedCharField handles it
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if self.original_max_length:
            kwargs["original_max_length"] = self.original_max_length
        return name, path, args, kwargs

    def formfield(self, **kwargs):
        """Return an EmailField for forms with original_max_length validation."""
        defaults = {}
        if self.original_max_length:
            defaults["max_length"] = self.original_max_length
        defaults.update(kwargs)
        return super().formfield(**defaults)


class EncryptedDateField(EncryptedMixin, models.CharField):
    """
    DateField that automatically encrypts its contents before saving to database.
    Uses CharField as base to store encrypted date data as VARCHAR in the database.

    Usage:
        birthday = EncryptedDateField(max_length=180, original_max_length=10)

    Parameters:
        max_length: Size for encrypted data in database (VARCHAR)
        original_max_length: Size for the original unencrypted date data (for form validation)
    """

    _python_type = str

    def __init__(self, *args, **kwargs):
        # Extract original_max_length before passing to parent
        self.original_max_length = kwargs.pop("original_max_length", None)

        # Set a default max_length if not provided
        if "max_length" not in kwargs:
            kwargs["max_length"] = 180
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if self.original_max_length:
            kwargs["original_max_length"] = self.original_max_length
        return name, path, args, kwargs

    def formfield(self, **kwargs):
        """Return a DateField for forms with original_max_length validation."""
        from django.forms import DateField as FormDateField

        defaults = {"widget": FormDateField().widget}
        if self.original_max_length:
            # For date fields, we typically want date input widget
            pass
        defaults.update(kwargs)
        return super().formfield(**defaults)

    def _convert_from_db(self, value):
        """Convert from string to date representation."""
        # Keep as string for now - you can add date parsing if needed
        return value
