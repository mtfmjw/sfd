import logging

from django.db import models
from django.utils.translation import gettext_lazy as _

from sfd.models import MasterModel

logger = logging.getLogger(__name__)


class Municipality(MasterModel):
    """市区町村マスタ"""

    municipality_code = models.CharField(_("Municipality Code"), max_length=10)  # 市区町村コード
    municipality_name = models.CharField(_("Municipality Name"), max_length=100, blank=True, null=True)  # 市区町村名
    municipality_name_kana = models.CharField(_("Municipality Name Kana"), max_length=100, blank=True, null=True)  # 市区町村名
    prefecture_name = models.CharField(_("Prefecture Name"), max_length=100)  # 都道府県名
    prefecture_name_kana = models.CharField(_("Prefecture Name Kana"), max_length=100)  # 都道府県名

    class Meta:  # type: ignore
        # db_table = "Municipality"
        verbose_name = _("Municipality")
        verbose_name_plural = _("Municipalities")
        ordering = ["municipality_code", "-valid_from"]
        constraints = [models.UniqueConstraint(fields=["municipality_code", "valid_from"], name="unique_municipality_code_valid_from")]

    def __str__(self):
        return f"{self.prefecture_name}{self.municipality_name}"
