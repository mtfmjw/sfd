from django.contrib.admin import ModelAdmin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from sfd.views.common.mixins import ModelAdminMixin


class CsvLogAdmin(ModelAdminMixin, ModelAdmin):
    list_display = (
        "app_name",
        "file_name_link",
        "total_line",
        "process_type",
        "process_result",
        "processed_by",
        "processed_at",
        "ip_address",
        "comment",
    )
    list_filter = ("app_name", "processed_at", "process_type", "process_result")
    search_fields = ("app_name", "file_name", "processed_by", "ip_address", "comment")
    date_hierarchy = "processed_at"
    exclude = ("process_id",)  # Exclude non-editable UUID field
    readonly_fields = ("processed_at",)  # Auto-generated timestamp field
    list_display_links = ("file_name_link",)

    def file_name_link(self, obj):
        """Return a clickable link to the change view."""
        if obj and obj.pk:
            url = reverse(f"{self.admin_site.name}:sfd_csvlog_change", args=[obj.pk])
            return format_html('<a href="{}">{}</a>', url, obj.file_name)
        return obj.file_name

    file_name_link.short_description = _("File Name")  # type: ignore[attr-defined]

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False
