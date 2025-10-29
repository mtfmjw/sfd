import uuid

from django.db import models
from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _


class CsvProcessType(TextChoices):
    """CSV process type choices."""

    UPLOAD = "Upload", _("Upload")
    DOWNLOAD = "Download", _("Download")


class CsvProcessResult(TextChoices):
    """CSV process result choices."""

    SUCCESS = "Success", _("Success")
    FAILURE = "Failure", _("Failure")
    NO_DATA = "No Data", _("No Data")


class CsvLog(models.Model):
    """Model to log CSV import activities."""

    process_id = models.UUIDField(default=uuid.uuid4, editable=False, verbose_name=_("Process ID"), db_index=True)
    process_type = models.CharField(choices=CsvProcessType.choices, max_length=20, verbose_name=_("Process Type"))
    process_result = models.CharField(
        choices=CsvProcessResult.choices,
        max_length=20,
        default=CsvProcessResult.SUCCESS,
        verbose_name=_("Process Result"),
    )
    app_name = models.CharField(max_length=100, verbose_name=_("App Name"))
    processed_by = models.CharField(max_length=150, verbose_name=_("Processed By"))
    processed_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Processed At"))
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name=_("IP Address"))
    file_name = models.CharField(max_length=255, verbose_name=_("File Name"))
    total_line = models.IntegerField(default=0, verbose_name=_("Total Lines"))
    comment = models.TextField(blank=True, null=True, verbose_name=_("Comment"))

    class Meta:  # type: ignore
        verbose_name = _("CSV Log")
        verbose_name_plural = _("CSV Logs")
        indexes = [
            models.Index(fields=["process_id", "file_name"]),
            models.Index(fields=["processed_at"]),
            models.Index(fields=["app_name"]),
            models.Index(fields=["process_result"]),
        ]
