import io
import logging
import os
from collections.abc import Generator
from typing import Any

import pandas as pd
from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_GET
from reportlab.lib.pagesizes import mm  # type: ignore
from reportlab.platypus import PageTemplate, Paragraph, Spacer
from reportlab.platypus.doctemplate import BaseDocTemplate
from reportlab.platypus.frames import Frame

from sfd.models import Municipality
from sfd.views.base import MasterModelAdmin
from sfd.views.common.pdf import BasePdfMixin
from sfd.views.common.upload import UploadType

logger = logging.getLogger(__name__)


class FilterPrefecture(admin.SimpleListFilter):
    """Filter for prefecture field"""

    title = _("Prefecture Name")
    parameter_name = "prefecture_name"

    def lookups(self, request, model_admin) -> list[tuple[str, str]]:
        prefectures = model_admin.model.objects.filter(municipality_name="").values_list("prefecture_name", flat=True).order_by("municipality_code")
        return [(prefecture, prefecture) for prefecture in prefectures]

    def queryset(self, request, queryset) -> QuerySet[Any] | None:
        if self.value():
            return queryset.filter(prefecture_name=self.value())
        return queryset


class MunicipalityAdmin(BasePdfMixin, MasterModelAdmin):
    is_readonly = True
    list_filter = (FilterPrefecture,)
    search_fields = ("municipality_code", "municipality_name", "prefecture_name")
    upload_type = UploadType.EXCEL
    fieldsets = [
        (
            None,
            {
                "fields": (
                    "municipality_code",
                    ("municipality_name", "municipality_name_kana"),
                    ("prefecture_name", "prefecture_name_kana"),
                )
            },
        ),
    ]

    upload_db_field_names = (
        "municipality_code",
        "prefecture_name",
        "municipality_name",
        "prefecture_name_kana",
        "municipality_name_kana",
    )

    def sheet_reader(self, file, sheet_name, request, cleaned_data=None) -> Generator[dict[str, Any]]:
        df = pd.read_excel(file, sheet_name=sheet_name, keep_default_na=False)
        for _a, row in df.iterrows():
            municipality_code = str(row.iloc[0]).zfill(6)[:5]
            data = {
                "municipality_code": municipality_code,
                "prefecture_name": row.iloc[1] if pd.notna(row.iloc[1]) else None,
                "municipality_name": row.iloc[2] if pd.notna(row.iloc[2]) else None,
                "prefecture_name_kana": row.iloc[3] if pd.notna(row.iloc[3]) else None,
                "municipality_name_kana": row.iloc[4] if pd.notna(row.iloc[4]) else None,
            }
            yield data

    def excel_upload(self, excel_file, request, cleaned_data=None) -> None:
        self.upload_data(self.sheet_reader, excel_file, 0, request, cleaned_data)
        self.upload_data(self.sheet_reader, excel_file, 1, request, cleaned_data)

    def create_pdf_files(self, request, queryset) -> list[str]:
        pdf_files = []

        queryset = queryset.filter(municipality_name__in=[None, ""]).values("prefecture_name").order_by("municipality_code")  # type: ignore
        for rec in queryset:
            pdf_data = self.model.objects.filter(prefecture_name=rec["prefecture_name"]).order_by("municipality_code")

            # PDFファイルを作成
            pdf_file = self.create_pdf_file(rec["prefecture_name"], pdf_data)
            if pdf_file:
                pdf_files.append(pdf_file)

        return pdf_files

    def create_pdf_file(self, prefecture_name, pdf_data) -> str | None:
        buffer = io.BytesIO()
        doc = BaseDocTemplate(
            buffer,
            pagesize=self.page_size,
            leftMargin=self.page_margin_left,
            rightMargin=self.page_margin_right,
            topMargin=self.page_margin_top,
            bottomMargin=self.page_margin_bottom,
        )
        styles = self.get_default_styles()

        frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="frame")
        page_template = PageTemplate(id="first_page", frames=[frame], onPage=self.write_page_header)
        doc.addPageTemplates([page_template])

        story = []

        # タイトル
        story.append(Paragraph(f"<b><u>{prefecture_name}・市区町村一覧</u></b>", styles["UnderlineHeading1"]))
        story.append(Spacer(1, 5 * mm))

        # 明細一覧
        detail_headers = [
            ("団体コード", "CellLabel"),
            ("都道府県名<br/>（漢字）", "CellLabel"),
            ("市区町村名<br/>（漢字）", "CellLabel"),
            ("都道府県名<br/>（カナ）", "CellLabel"),
            ("市区町村名<br/>（カナ）", "CellLabel"),
        ]
        colWidths = [25 * mm, 25 * mm, 40 * mm, 40 * mm, 40 * mm]
        table_style = self.get_table_style(extra_styles=[("BACKGROUND", (0, 0), (-1, 0), self.cell_label_bg_color)])

        detail_data = []
        detail_data.append(detail_headers)
        for row in pdf_data:
            detail_data.append(
                [
                    Paragraph(row.municipality_code, styles["CellCenter"]),
                    Paragraph(row.prefecture_name, styles["Cell"]),
                    Paragraph(row.municipality_name, styles["Cell"]),
                    Paragraph(row.prefecture_name_kana, styles["Cell"]),
                    Paragraph(row.municipality_name_kana, styles["Cell"]),
                ]
            )
        story.append(self.create_table(detail_data, colWidths=colWidths, table_style=table_style))  # type: ignore

        doc.build(story)
        buffer.seek(0)
        pdf_file_name = f"{prefecture_name}・市区町村一覧.pdf"
        file_path = os.path.join(self.get_pdf_temporary_path(), pdf_file_name)
        with open(file_path, "wb") as f:
            f.write(buffer.getvalue())
        buffer.close()

        logger.debug(f"{prefecture_name}の市区町村一覧ファイルを作成しました。")
        return pdf_file_name


@require_GET
def get_municipalities_by_prefecture(request) -> HttpResponse:
    """Get municipalities filtered by prefecture via basic HTMX.

    This function provides a simple HTML endpoint for retrieving municipalities
    that belong to a specific prefecture. It's designed to support
    cascading dropdown functionality in admin forms using basic HTMX
    without any additional Django packages.

    Args:
        request (HttpRequest): Django request object with GET parameters
                                Expected parameter: 'prefecture' - prefecture name

    Returns:
        HttpResponse: HTML response containing municipality dropdown options
                        Error format: HTML with error message

    Example:
        GET /sfd/change_prefecture/?prefecture=東京都
        Response: HTML select options for municipalities in Tokyo

    Note:
        Requires staff member authentication to access.
        Filters out prefecture-level entries (empty municipality_name).
        Works with basic HTMX without django-htmx package.
    """
    # Try both 'prefecture' and 'id_prefecture' parameter names
    prefecture = request.GET.get("prefecture") or request.GET.get("id_prefecture")

    if not prefecture:
        logger.warning("get_municipalities_by_prefecture called without prefecture parameter")
        title = _("Select Prefecture first")
        return HttpResponse(f'<option value="">{title}</option>')

    municipalities = (
        Municipality.objects.filter(prefecture_name=prefecture)
        .exclude(municipality_name="")  # Exclude prefecture-level entries
        .values("id", "municipality_name")
        .order_by("municipality_code")
    )

    option_title = _("Select Municipality")
    options_html = f'<option value="" selected>{option_title}</option>'
    if not municipalities:
        logger.info(f"No municipalities found for prefecture: {prefecture}")
        return HttpResponse(options_html)

    # Generate HTML options for municipalities
    for municipality in municipalities:
        options_html += f'<option value="{municipality["id"]}">{municipality["municipality_name"]}</option>'

    logger.debug(f"Found {len(municipalities)} municipalities for prefecture: {prefecture}")
    return HttpResponse(options_html)
