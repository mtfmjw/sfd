import logging
from typing import Any

from django.contrib import admin
from django.db import connection, transaction
from django.db.models import Q
from django.db.models.query import QuerySet
from django.utils.translation import gettext_lazy as _

from sfd.forms.postcode import PostcodeAdminForm, PostcodeSearchForm
from sfd.models.municipality import Municipality
from sfd.models.postcode import Postcode, PostcodeUpload
from sfd.views.base import BaseModelAdmin
from sfd.views.common.search import BaseSearchView
from sfd.views.common.upload import UploadType

logger = logging.getLogger(__name__)


class FilterPrefecture(admin.SimpleListFilter):
    """Filter for prefecture field"""

    title = _("Prefecture Name")
    parameter_name = "prefecture_name"

    def lookups(self, request, model_admin) -> list[tuple[str, str]]:
        prefectures = Municipality.objects.filter(municipality_name="").values_list("prefecture_name", flat=True).order_by("municipality_code")
        return [(prefecture, prefecture) for prefecture in prefectures]

    def queryset(self, request, queryset) -> QuerySet[Any] | None:
        if self.value():
            return queryset.filter(municipality__prefecture_name=self.value())
        return queryset


class PostcodeAdmin(BaseModelAdmin):
    """Django admin configuration for Postcode model with cascading dropdowns.

    This admin class provides a user-friendly interface for managing postcode
    records with cascading prefecture/municipality dropdown functionality.
    Instead of showing all municipalities in a single large dropdown, users
    first select a prefecture, which then populates the municipality dropdown
    with only relevant options.

    Features:
        - Cascading prefecture/municipality dropdowns
        - Custom form with dynamic field population
        - JavaScript-powered AJAX interactions
        - Maintains all existing functionality (upload, filtering, etc.)

    Attributes:
        form: Custom form class with cascading dropdown functionality
        fields: Form field ordering and organization
        list_display: Columns shown in the admin list view
        list_filter: Available filters in the admin sidebar
        search_fields: Fields searchable from the admin search box
        readonly_fields: Fields that cannot be edited
        upload_type: Type of file upload supported (ZIP)
        upload_model: Model used for bulk upload operations
        upload_column_names: CSV column names for bulk upload

    Note:
        Requires accompanying JavaScript and AJAX view for full functionality.
    """

    form = PostcodeAdminForm
    list_filter = (FilterPrefecture,)
    search_fields = ("postcode", "town_name", "municipality__municipality_name")
    list_display = ("postcode_display", "municipality_name", "town_name", "town_name_kana")
    list_display_links = ("postcode_display", "municipality_name")

    upload_type = UploadType.ZIP
    upload_model = PostcodeUpload
    upload_column_names = [
        "municipality_code",
        "old_postcode",
        "postcode",
        "prefecture_name_kana",
        "municipality_name_kana",
        "town_name_kana",
        "prefecture_name",
        "municipality_name",
        "town_name",
        "flag1",
        "flag2",
        "flag3",
        "flag4",
        "flag5",
        "flag6",
    ]
    download_column_names = [
        "postcode",
        "municipality__prefecture_name",
        "municipality__municipality_name",
        "town_name",
        "town_name_kana",
        "created_by",
        "created_at",
        "updated_by",
        "updated_at",
    ]

    def postcode_display(self, obj) -> str:
        if not obj.postcode:
            return ""
        return obj.postcode[:3] + "-" + obj.postcode[3:]

    def municipality_name(self, obj) -> str:
        """Display municipality name with link to municipality admin change form.

        This method creates a clickable link from the municipality name
        to the corresponding municipality's admin change form. This provides
        easy navigation from postcode records to their associated municipality
        details for editing or viewing.

        Args:
            obj (Postcode): The postcode instance containing municipality relation

        Returns:
            str: HTML formatted link to municipality admin change form,
                 or empty string if no municipality is associated

        Note:
            Uses format_html for XSS protection and proper HTML formatting.
            The link opens the municipality change form in the admin interface.
        """
        if not obj.municipality:
            return ""

        municipality_name = obj.municipality.prefecture_name + obj.municipality.municipality_name
        if not municipality_name:
            return ""

        # Return HTML link with XSS protection
        return self.get_popup_model_hyperlink(obj.municipality)

    municipality_name.short_description = _("Municipality Name")  # type: ignore[attr-defined]
    municipality_name.allow_tags = True  # For older Django versions  # type: ignore[attr-defined]
    municipality_name.admin_order_field = "municipality__municipality_name"  # type: ignore[attr-defined]

    def get_fieldsets(self, request, obj=None) -> list[tuple[str | None, dict[str, list[str] | str]]]:  # noqa: D401 - merged extended behavior
        fieldsets = super().get_fieldsets(request, obj=obj)
        # Base layout (edit/add mode)
        base_fields = (("postcode",), ("prefecture", "municipality"), ("town_name", "town_name_kana"))

        # If the user only has view permission (no change/add), replace FK field with plain text display
        # to suppress the default Django admin hyperlink to the related Municipality change page.
        if not self.has_change_permission(request, obj) and not self.has_add_permission(request):
            base_fields = (("postcode",), ("prefecture", "municipality_display"), ("town_name", "town_name_kana"))

        fieldsets[0][1]["fields"] = base_fields
        return fieldsets

    def get_readonly_fields(self, request, obj=None) -> list[str]:  # noqa: D401 - merged extended behavior
        """Customize readonly fields for view-only mode.

        Responsibilities:
            - Ensure custom form field "prefecture" isn't treated as readonly unnecessarily.
            - When user lacks change/add permission, include municipality_display so Django
              renders plain text instead of a hyperlink for the municipality FK.
        """
        readonly = list(super().get_readonly_fields(request, obj))
        # Remove prefecture if Django added it automatically
        if "prefecture" in readonly:
            readonly.remove("prefecture")
        # View-only: add plain municipality display method
        if not self.has_change_permission(request, obj) and not self.has_add_permission(request):
            readonly.append("municipality_display")
        return list(readonly)

    def prefecture(self, obj) -> str:  # noqa: D401 - short simple display method
        """Return prefecture name for readonly display.

        This method allows the custom non-model form field "prefecture" to have
        a proper value shown (instead of "-") when the user only has view
        permission and all fields are rendered as readonly. By adding the field
        name to readonly fields in that scenario, Django will call this method
        to obtain the display value.

        Args:
            obj (Postcode): Postcode instance whose municipality holds prefecture name.

        Returns:
            str: Prefecture name or empty string if unavailable.
        """
        if not obj or not getattr(obj, "municipality", None):
            return ""
        return obj.municipality.prefecture_name

    prefecture.short_description = _("Prefecture")  # type: ignore[attr-defined]

    # ------------------------------------------------------------------
    # Plain municipality display (used in view-only change form)
    # ------------------------------------------------------------------
    def municipality_display(self, obj) -> str:  # noqa: D401 - simple display method
        """Return plain municipality full name without hyperlink.

        Used only when user lacks change permission for Postcode; replaces the
        normal FK readonly rendering (which would include a link to Municipality
        change page) with plain text.

        Args:
            obj (Postcode): Instance being displayed.

        Returns:
            str: Concatenated prefecture + municipality name or empty string.
        """
        if not obj or not getattr(obj, "municipality", None):
            return ""
        m = obj.municipality
        return f"{m.prefecture_name}{m.municipality_name or ''}"

    municipality_display.short_description = _("Municipality Name")  # type: ignore[attr-defined]

    def get_search_field_names(self) -> str:
        return _("Postcode, Municipality Name, Town Name.")

    def convert2upload_fields(self, row_dict, upload_fields, request, cleaned_data=None) -> dict[str, Any]:
        """Convert CSV row data to model field type"""
        converted = super().convert2upload_fields(row_dict, upload_fields, request, cleaned_data)
        if converted["town_name"] == "以下に掲載がない場合":
            converted["town_name"] = ""
            converted["town_name_kana"] = ""
        elif "（" in converted["town_name"]:
            converted["town_name"] = converted["town_name"].split("（")[0]
            converted["town_name_kana"] = converted["town_name_kana"].split("（")[0]

        return converted

    def post_upload(self, request, cleaned_data=None) -> None:  # pragma: no cover
        """unique key単位で重複したものは除外してpostcodeテーブルに登録する"""

        with_clause_sql = """
        with uploaded_data as (
            SELECT postcode
                ,m.id municipality_id
                ,case
                    when town_name = '以下に掲載がない場合' then ''
                    when position('（' in town_name) > 1 then substring(town_name,1, position('（' in town_name) - 1)
                    else town_name
                 end town_name
                ,case
                    when town_name_kana = '以下に掲載がない場合' then ''
                    when position('（' in town_name_kana) > 1 then substring(town_name_kana,1, position('（' in town_name_kana) - 1)
                    else town_name_kana
                 end town_name_kana
            FROM sfd_postcodeupload AS p
            JOIN sfd_municipality AS m
            ON p.municipality_code = m.municipality_code
        ), numbered_uploaded_data AS (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY postcode, municipality_id, town_name, town_name_kana ORDER BY postcode) AS rn
            FROM uploaded_data
        ), insert_data as (
            select uploaded.postcode
                ,uploaded.municipality_id
                ,uploaded.town_name
                ,uploaded.town_name_kana
            from numbered_uploaded_data uploaded
            left join sfd_postcode main
            on uploaded.postcode = main.postcode
                and uploaded.municipality_id = main.municipality_id
                and uploaded.town_name = main.town_name
                and uploaded.town_name_kana = main.town_name_kana
            where uploaded.rn = 1
                and main.id is null
        )
        """

        insert_sql = (
            with_clause_sql
            + """
        INSERT INTO sfd_postcode (
            postcode
            ,municipality_id
            ,town_name
            ,town_name_kana
            ,created_at
            ,created_by
            ,updated_at
            ,updated_by
            ,deleted_flg
        )
        SELECT postcode
            ,municipality_id
            ,town_name
            ,town_name_kana
            ,NOW() created_at
            ,'upload' created_by
            ,NOW() updated_at
            ,'upload' updated_by
            ,false deleted_flg
        FROM insert_data
        """
        )

        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(insert_sql)
                self._total_inserted = cursor.rowcount


class PostcodeSearchView(BaseSearchView):
    """Search view for Postcode model."""

    model = Postcode
    form_class = PostcodeSearchForm
    template_name = "sfd/search_postcode.html"
    list_display = ("postcode", "municipality", "town_name", "town_name_kana")
    fieldsets = [
        (
            None,
            {"fields": ("postcode", ("municipality_name", "municipality_name_kana"), ("town_name", "town_name_kana"))},
        ),
    ]

    def get_query(self, form) -> Q:  # pragma: no cover
        """This method should be implemented to return a Q object based on cleaned_data"""
        postcode = form.cleaned_data.get("postcode", "")
        municipality_name = form.cleaned_data.get("municipality_name", "")
        municipality_name_kana = form.cleaned_data.get("municipality_name_kana", "")
        town_name = form.cleaned_data.get("town_name", "")
        town_name_kana = form.cleaned_data.get("town_name_kana", "")

        query = Q()
        if postcode:
            query &= Q(postcode=postcode)
        if municipality_name:
            query &= Q(municipality__municipality_name__icontains=municipality_name)
        if municipality_name_kana:
            query &= Q(municipality__municipality_name_kana__icontains=municipality_name_kana)
        if town_name:
            query &= Q(town_name__icontains=town_name)
        if town_name_kana:
            query &= Q(town_name_kana__icontains=town_name_kana)

        return query
