# type: ignore
from django.db import models
from django.utils.translation import gettext_lazy as _

from sfd.common.encrypted import (
    EncryptedCharField,
    EncryptedDateField,
    EncryptedEmailField,
)
from sfd.models import Municipality
from sfd.models.base import MasterModel
from sfd.models.postcode import Postcode


class GenderType(models.TextChoices):
    """Gender types"""

    MALE = "Male", _("Male")
    FEMALE = "Female", _("Female")
    OTHER = "Other", _("Other")


class Person(MasterModel):
    # Encrypted fields for sensitive personal information
    family_name = EncryptedCharField(_("Family Name"), max_length=184, original_max_length=64, null=False, blank=False)
    family_name_kana = EncryptedCharField(_("Family Name Kana"), max_length=184, original_max_length=64, null=False, blank=False)
    family_name_romaji = EncryptedCharField(_("Family Name Romaji"), max_length=184, original_max_length=64, null=True, blank=True)
    name = EncryptedCharField(_("Name"), max_length=184, original_max_length=64, null=False, blank=False)
    name_kana = EncryptedCharField(_("Name Kana"), max_length=184, original_max_length=64, null=False, blank=False)
    name_romaji = EncryptedCharField(_("Name Romaji"), max_length=184, original_max_length=64, null=True, blank=True)
    birthday = EncryptedDateField(_("Birthday"), max_length=180, original_max_length=10, null=True, blank=True)
    gender = models.CharField(_("Gender"), max_length=10, null=True, blank=True, choices=GenderType.choices)
    email = EncryptedEmailField(_("Email"), max_length=272, original_max_length=128, null=True, blank=True)
    phone_number = EncryptedCharField(_("Phone Number"), max_length=144, original_max_length=20, null=True, blank=True)
    mobile_number = EncryptedCharField(_("Mobile Number"), max_length=144, original_max_length=20, null=True, blank=True)
    postcode = models.ForeignKey(Postcode, verbose_name=_("Postcode"), on_delete=models.DO_NOTHING, blank=True, null=True)
    municipality = models.ForeignKey(Municipality, verbose_name=_("Municipality"), on_delete=models.DO_NOTHING, blank=True, null=True)
    address_detail = EncryptedCharField(_("Address Detail"), max_length=448, original_max_length=256, null=True, blank=True)

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
