from django.db import models


class GroupUpload(models.Model):
    name = models.CharField(max_length=150)
    codename = models.CharField(max_length=100, null=True, blank=True)
    app_label = models.CharField(max_length=100, null=True, blank=True)
    model = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        verbose_name = "Group Upload"
        verbose_name_plural = "Group Uploads"
        constraints = [models.UniqueConstraint(fields=["name", "codename"], name="unique_group_upload")]
