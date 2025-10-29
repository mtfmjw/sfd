import io
import logging
import os
from typing import Any

from django.contrib import admin
from django.db.models import QuerySet
from django.utils.translation import gettext_lazy as _
from reportlab.lib.pagesizes import mm  # type: ignore
from reportlab.platypus import PageBreak, PageTemplate, Paragraph, Spacer
from reportlab.platypus.doctemplate import BaseDocTemplate
from reportlab.platypus.frames import Frame

from sfd.views.base import BaseModelAdmin
from sfd.views.common.pdf import BasePdfMixin
from sfd.views.common.upload import Encoding

logger = logging.getLogger(__name__)


class FilterYear(admin.SimpleListFilter):
    """Filter for date field"""

    title = _("year")
    parameter_name = "year"

    def lookups(self, request, model_admin) -> list[tuple[Any, str]]:
        years = model_admin.model.objects.dates("date", "year").values_list("date__year", flat=True).distinct().order_by("-date__year")
        return [(year, str(year)) for year in years[:10]]

    def queryset(self, request, queryset) -> QuerySet[Any] | None:
        if self.value():
            return queryset.filter(date__year=self.value())
        return queryset


class HolidayAdmin(BasePdfMixin, BaseModelAdmin):
    search_fields = ("date__year", "name")
    list_filter = (FilterYear,)
    fieldsets = [(None, {"fields": ("date", ("name", "holiday_type"), ("comment",))})]

    upload_column_names = ["date", "name"]
    encoding = Encoding.SJIS  # Default encoding for CSV uploads

    def get_search_field_names(self) -> str:
        return _("year, name")

    def create_pdf_files(self, request, queryset) -> list[str]:
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
        story.append(Paragraph("<b><u>祝日・休日一覧</u></b>", styles["UnderlineHeading1"]))
        story.append(Spacer(1, 5 * mm))

        # 明細一覧(年毎に改ページ)
        detail_headers = [("日付", "CellLabel"), ("名称", "CellLabel"), ("備考", "CellLabel")]
        colWidths = [60 * mm, 60 * mm, 40 * mm]
        table_style = self.get_table_style(extra_styles=[("BACKGROUND", (0, 0), (-1, 0), self.cell_label_bg_color)])

        current_year = None
        detail_data = []
        for holiday in queryset:
            if current_year != holiday.date.year:
                current_year = holiday.date.year
                if detail_data:
                    story.append(self.create_table(detail_data, colWidths=colWidths, table_style=table_style))  # type: ignore
                    story.append(PageBreak())

                # 年毎のヘッダー
                detail_data = []
                detail_data.append(detail_headers)

            detail_data.append(
                [
                    Paragraph(holiday.date.strftime("%Y年%m月%d日"), styles["CellCenter"]),
                    Paragraph(holiday.name, styles["Cell"]),
                    Paragraph(holiday.comment or "", styles["Cell"]),
                ]
            )

        if detail_data:
            story.append(self.create_table(detail_data, colWidths=colWidths, table_style=table_style))  # type: ignore
            story.append(PageBreak())

        doc.build(story)
        buffer.seek(0)
        pdf_file_name = "祝日・休日一覧.pdf"
        file_path = os.path.join(self.get_pdf_temporary_path(), pdf_file_name)
        with open(file_path, "wb") as f:
            f.write(buffer.getvalue())
        buffer.close()

        logger.debug("祝日・休日一覧ファイルを作成しました。")
        return [pdf_file_name]
