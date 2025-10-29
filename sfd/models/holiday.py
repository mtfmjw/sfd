from django.db import models
from django.utils.translation import gettext_lazy as _

from sfd.models.base import BaseModel


class HolidayType(models.TextChoices):
    """holiday type"""

    NATIONAL_HOLIDAY = "National Holiday", _("National Holiday")
    SUBSTITUTE_HOLIDAY = "Substitute Holiday", _("Substitute Holiday")  # 振替休日
    OTHER_HOLIDAY = "Other Holiday", _("Other Holiday")  # 企業指定休日など


class Holiday(BaseModel):
    """Holds holidays and designated holidays"""

    date = models.DateField(_("date"))
    name = models.CharField(_("name"), max_length=100, null=True, blank=True)
    holiday_type = models.CharField(_("holiday type"), max_length=20, choices=HolidayType.choices, default=HolidayType.NATIONAL_HOLIDAY)
    comment = models.CharField(_("comment"), max_length=255, null=True, blank=True, help_text=_("Additional information about the holiday"))

    class Meta:  # type: ignore
        # db_table = "holiday"
        verbose_name = _("holiday")
        verbose_name_plural = _("holidays")
        ordering = ["-date__year", "date"]
        constraints = [models.UniqueConstraint(fields=["date"], name="unique_holiday_date")]

    def __str__(self):
        return f"{self.name}"
