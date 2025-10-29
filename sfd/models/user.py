from django.db import models


class UserUpload(models.Model):
    username = models.CharField(max_length=150)
    first_name = models.CharField(max_length=150, null=True, blank=True)
    last_name = models.CharField(max_length=150, null=True, blank=True)
    last_login = models.DateTimeField(null=True, blank=True)
    email = models.EmailField(max_length=254, null=True, blank=True)
    is_superuser = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    group_name = models.CharField(max_length=500, null=True, blank=True)
    codename = models.CharField(max_length=100, null=True, blank=True)
    app_label = models.CharField(max_length=100, null=True, blank=True)
    model = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        verbose_name = "User Upload"
        verbose_name_plural = "User Uploads"
        constraints = [
            models.UniqueConstraint(fields=["username", "codename", "group_name"], name="unique_user_upload")
        ]
