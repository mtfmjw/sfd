from django.db import models
from django.utils.translation import gettext_lazy as _

from sfd.models import Municipality
from sfd.models.base import MasterModel
from sfd.models.postcode import Postcode


class GenderType(models.TextChoices):
    """Gender types"""

    MALE = "Male", _("Male")
    FEMALE = "Female", _("Female")
    OTHER = "Other", _("Other")


class Person(MasterModel):
    family_name = models.CharField(_("Family Name"), max_length=100, null=False, blank=False)
    family_name_kana = models.CharField(_("Family Name Kana"), max_length=100, null=False, blank=False)
    family_name_romaji = models.CharField(_("Family Name Romaji"), max_length=100, null=True, blank=True)
    name = models.CharField(_("Name"), max_length=100, null=False, blank=False)
    name_kana = models.CharField(_("Name Kana"), max_length=100, null=False, blank=False)
    name_romaji = models.CharField(_("Name Romaji"), max_length=100, null=True, blank=True)
    birthday = models.DateField(_("Birthday"), null=True, blank=True)
    gender = models.CharField(_("Gender"), max_length=10, null=True, blank=True, choices=GenderType.choices)
    email = models.EmailField(_("Email"), max_length=100, null=True, blank=True)
    phone_number = models.CharField(_("Phone Number"), max_length=20, null=True, blank=True)
    mobile_number = models.CharField(_("Mobile Number"), max_length=20, null=True, blank=True)
    postcode = models.ForeignKey(Postcode, verbose_name=_("Postcode"), on_delete=models.DO_NOTHING, blank=True, null=True)
    municipality = models.ForeignKey(Municipality, verbose_name=_("Municipality"), on_delete=models.DO_NOTHING, blank=True, null=True)
    address_detail = models.CharField(_("Address Detail"), max_length=255, null=True, blank=True)

    class Meta:  # type: ignore
        verbose_name = _("Person")
        verbose_name_plural = _("People")
        ordering = ["family_name", "name", "valid_from"]

    def __str__(self):
        return f"{self.family_name} {self.name}"
