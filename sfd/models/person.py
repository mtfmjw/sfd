# type: ignore
from django.db import models
from django.utils.translation import gettext_lazy as _

from sfd.common.encrypted import (
    EncryptedCharField,
    EncryptedDateField,
    EncryptedEmailField,
    generate_search_hash,
)
from sfd.models import Municipality
from sfd.models.base import MasterModel
from sfd.models.postcode import Postcode


class GenderType(models.TextChoices):
    """Gender types"""

    MALE = "Male", _("Male")
    FEMALE = "Female", _("Female")
    OTHER = "Other", _("Other")


class PersonManager(models.Manager):
    """Custom manager for Person model with encrypted field search capabilities."""

    def search_by_name(self, name):
        """Search persons by name (family_name + name combination)."""
        if not name:
            return self.none()
        name_hash = generate_search_hash(name)
        return self.filter(models.Q(family_name_hash=name_hash) | models.Q(name_hash=name_hash))

    def search_by_email(self, email):
        """Search persons by email."""
        if not email:
            return self.none()
        email_hash = generate_search_hash(email)
        return self.filter(email_hash=email_hash)

    def search_by_phone(self, phone):
        """Search persons by phone number."""
        if not phone:
            return self.none()
        phone_hash = generate_search_hash(phone)
        return self.filter(models.Q(phone_number_hash=phone_hash) | models.Q(mobile_number_hash=phone_hash))

    def search_exact(self, **kwargs):
        """Search by exact matches on encrypted fields."""
        query = models.Q()
        for field_name, value in kwargs.items():
            if value is None:
                continue
            hash_field = f"{field_name}_hash"
            hash_value = generate_search_hash(value)
            query &= models.Q(**{hash_field: hash_value})
        return self.filter(query)


class Person(MasterModel):
    # Encrypted fields for sensitive personal information
    family_name = EncryptedCharField(
        _("Family Name"), max_length=184, original_max_length=64, null=False, blank=False, searchable=True, db_index=True
    )
    family_name_kana = EncryptedCharField(
        _("Family Name Kana"), max_length=184, original_max_length=64, null=False, blank=False, searchable=True, db_index=True
    )
    family_name_romaji = EncryptedCharField(
        _("Family Name Romaji"), max_length=184, original_max_length=64, null=True, blank=True, searchable=True, db_index=True
    )
    name = EncryptedCharField(_("Name"), max_length=184, original_max_length=64, null=False, blank=False, searchable=True, db_index=True)
    name_kana = EncryptedCharField(_("Name Kana"), max_length=184, original_max_length=64, null=False, blank=False, searchable=True, db_index=True)
    name_romaji = EncryptedCharField(_("Name Romaji"), max_length=184, original_max_length=64, null=True, blank=True, searchable=True, db_index=True)
    birthday = EncryptedDateField(_("Birthday"), max_length=180, original_max_length=10, null=True, blank=True)
    gender = models.CharField(_("Gender"), max_length=10, null=True, blank=True, choices=GenderType.choices)
    email = EncryptedEmailField(_("Email"), max_length=272, original_max_length=128, null=True, blank=True, searchable=True, db_index=True)
    phone_number = EncryptedCharField(
        _("Phone Number"), max_length=144, original_max_length=20, null=True, blank=True, searchable=True, db_index=True
    )
    mobile_number = EncryptedCharField(
        _("Mobile Number"), max_length=144, original_max_length=20, null=True, blank=True, searchable=True, db_index=True
    )
    postcode = models.ForeignKey(Postcode, verbose_name=_("Postcode"), on_delete=models.DO_NOTHING, blank=True, null=True)
    municipality = models.ForeignKey(Municipality, verbose_name=_("Municipality"), on_delete=models.DO_NOTHING, blank=True, null=True)
    address_detail = EncryptedCharField(_("Address Detail"), max_length=448, original_max_length=256, null=True, blank=True)

    # Hash fields for searching encrypted data
    family_name_hash = models.CharField(_("Family Name Hash"), max_length=64, null=True, blank=True, db_index=True)
    family_name_kana_hash = models.CharField(_("Family Name Kana Hash"), max_length=64, null=True, blank=True, db_index=True)
    family_name_romaji_hash = models.CharField(_("Family Name Romaji Hash"), max_length=64, null=True, blank=True, db_index=True)
    name_hash = models.CharField(_("Name Hash"), max_length=64, null=True, blank=True, db_index=True)
    name_kana_hash = models.CharField(_("Name Kana Hash"), max_length=64, null=True, blank=True, db_index=True)
    name_romaji_hash = models.CharField(_("Name Romaji Hash"), max_length=64, null=True, blank=True, db_index=True)
    email_hash = models.CharField(_("Email Hash"), max_length=64, null=True, blank=True, db_index=True)
    phone_number_hash = models.CharField(_("Phone Number Hash"), max_length=64, null=True, blank=True, db_index=True)
    mobile_number_hash = models.CharField(_("Mobile Number Hash"), max_length=64, null=True, blank=True, db_index=True)

    objects = PersonManager()

    class Meta:  # type: ignore
        verbose_name = _("Person")
        verbose_name_plural = _("People")
        ordering = ["family_name", "name", "valid_from"]
        permissions = [
            ("view_personal_info", "Can view personal information"),
            ("change_personal_info", "Can edit personal information"),
        ]

    def __str__(self):
        return f"{self.family_name} {self.name}"

    def save(self, *args, **kwargs):
        # Generate hashes for searchable fields
        self.family_name_hash = generate_search_hash(self.family_name)
        self.family_name_kana_hash = generate_search_hash(self.family_name_kana)
        self.family_name_romaji_hash = generate_search_hash(self.family_name_romaji)
        self.name_hash = generate_search_hash(self.name)
        self.name_kana_hash = generate_search_hash(self.name_kana)
        self.name_romaji_hash = generate_search_hash(self.name_romaji)
        self.email_hash = generate_search_hash(self.email)
        self.phone_number_hash = generate_search_hash(self.phone_number)
        self.mobile_number_hash = generate_search_hash(self.mobile_number)

        super().save(*args, **kwargs)
