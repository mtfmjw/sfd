from django.db import models
from django.utils.translation import gettext_lazy as _

from sfd.models import BaseModel, Municipality


class Postcode(BaseModel):
    """郵便番号マスタ"""

    postcode = models.CharField(_("Postcode"), max_length=7, null=False, blank=False)  # 郵便番号
    municipality = models.ForeignKey(Municipality, verbose_name=_("Municipality"), on_delete=models.DO_NOTHING)  # 市区町村
    town_name = models.CharField(_("Town Name"), max_length=100, null=True, blank=True, default="")  # 町域名
    town_name_kana = models.CharField(_("Town Name Kana"), max_length=100, null=True, blank=True, default="")  # 町域名カナ

    class Meta:  # type: ignore
        verbose_name = _("Postcode")
        verbose_name_plural = _("Postcodes")
        ordering = ["postcode"]
        constraints = [
            models.UniqueConstraint(
                fields=["postcode", "municipality", "town_name", "town_name_kana"],
                name="unique_postcode_postcode_town_name",
            )
        ]

    def __str__(self):
        return f"{self.postcode}"


class PostcodeUpload(models.Model):
    municipality_code = models.CharField(max_length=10, null=True, blank=True)
    old_postcode = models.CharField(max_length=5, null=True, blank=True)
    postcode = models.CharField(max_length=7, null=True, blank=True)
    prefecture_name_kana = models.CharField(max_length=1000, null=True, blank=True)  # 都道府県名
    municipality_name_kana = models.CharField(max_length=1000, blank=True, null=True)  # 市区町村名
    town_name_kana = models.CharField(max_length=1000, null=True, blank=True)
    prefecture_name = models.CharField(max_length=1000, null=True, blank=True)  # 都道府県名
    municipality_name = models.CharField(max_length=1000, blank=True, null=True)  # 市区町村名
    town_name = models.CharField(max_length=1000, null=True, blank=True)
    flag1 = models.IntegerField(blank=True, null=True)
    flag2 = models.IntegerField(blank=True, null=True)
    flag3 = models.IntegerField(blank=True, null=True)
    flag4 = models.IntegerField(blank=True, null=True)
    flag5 = models.IntegerField(blank=True, null=True)
    flag6 = models.IntegerField(blank=True, null=True)
