import csv
import uuid
from collections import OrderedDict
from collections.abc import Generator
from datetime import datetime
from pathlib import Path
from typing import Any, no_type_check
from urllib.parse import quote, unquote
from venv import logger

from django.contrib import admin
from django.db import models
from django.http import HttpResponse
from django.urls import path, reverse
from django.utils.translation import gettext_lazy as _

from sfd.models.csv_log import CsvLog, CsvProcessResult, CsvProcessType


@admin.action(description=_("Download Selected Rows"))
def download_selected(modladmin, request, queryset) -> HttpResponse | None:
    """
    Admin action to download selected rows as CSV file.

    This function serves as a Django admin action that allows users to select
    multiple rows from the admin changelist and download them as a CSV file.

    Args:
        modladmin: The ModelAdmin instance that provides access to the model
                  and CSV download functionality
        request: The HttpRequest object containing request information
        queryset: QuerySet containing the selected model instances to download

    Returns:
        HttpResponse: CSV file download response if queryset has items,
                     None if no items selected (shows warning message)

    Note:
        This function relies on the ModelAdmin having a download_file method
        available, typically provided by the DownloadMixin.
    """
    if not queryset:
        modladmin.message_user(request, "No rows selected.", level="warning")
        return
    return modladmin.download_file(request, queryset)


class CsvSeparator(models.TextChoices):
    COMMA = ",", "csv"
    TAB = "\t", "tsv"


class DownloadMixin:
    """
    Mixin class that adds CSV download functionality to Django ModelAdmin classes.

    This mixin provides comprehensive CSV export capabilities for Django admin interfaces,
    including both bulk download of all filtered results and selective download of
    specific records. It integrates seamlessly with Django's admin system by adding
    custom URLs, actions, and view enhancements.

    Features:
        - Configurable CSV separator (comma or tab)
        - Automatic filename generation with timestamps
        - Header generation based on model field verbose names
        - Support for filtered and searched querysets
        - Admin action for downloading selected rows
        - Custom download URL endpoint
        - Japanese localization support

    Attributes:
        csv_separator (CsvSeparator): The separator character to use in CSV files.
                                     Defaults to TAB format.

    Usage:
        Inherit from this mixin in your ModelAdmin classes to add CSV download
        functionality:

        ```python
        class MyModelAdmin(DownloadMixin, admin.ModelAdmin):
            list_display = ['field1', 'field2', 'field3']
        ```

    Note:
        This mixin overrides several ModelAdmin methods (get_urls, get_actions,
        changelist_view) to integrate download functionality. Ensure proper
        method resolution order when using with other mixins.
    """

    csv_separator = CsvSeparator.COMMA
    download_column_names = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        opts = self.model._meta  # type: ignore[attr-defined]
        self.download_url_name = f"{opts.app_label}_{opts.model_name}_download_file"

    def get_csv_file_name(self, request, name=None) -> str:
        """
        Generate a CSV filename based on the model name and current datetime.

        Creates a properly formatted filename for CSV downloads that includes
        the model's verbose name (or custom name) and a timestamp to ensure
        uniqueness. The filename is URL-encoded to handle Japanese characters
        properly in web browsers.

        Args:
            name (str, optional): Custom name to use instead of model verbose_name.
                                 If None, uses the model's verbose_name.

        Returns:
            str: A formatted filename in the pattern:
                 "{name}_{YYYYMMDD_HHMMSS}.{extension}"
                 where extension is determined by csv_separator.

        Example:
            If model verbose_name is "ユーザー" and current time is 2024-01-15 14:30:45:
            Returns: "%E3%83%A6%E3%83%BC%E3%82%B6%E3%83%BC_20240115_143045.tsv"
        """
        current_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")
        # ファイル名を日本語にする場合はurlencodeが必要
        quoted_name = quote(name) if name else quote(str(self.model._meta.verbose_name))  # type: ignore[attr-defined]
        return f"{quoted_name}_{current_datetime}.{self.csv_separator.label}"

    def get_download_columns(self, request) -> dict[str, str]:
        if self.download_column_names:
            column_names = self.download_column_names
        else:
            column_names = self.get_list_display(request)  # type: ignore

        return self.get_column_labels(column_names)  # type: ignore

    @no_type_check
    def get_download_queryset(self, request, queryset=None) -> models.QuerySet:
        # If queryset is not provided, use the default changelist queryset
        # This allows the admin to download all objects searched or filtered
        # in the changelist view.
        if queryset is None:  # type: ignore
            ChangeListClass = self.get_changelist(request)
            cl = ChangeListClass(
                request,
                self.model,
                self.list_display,
                self.list_display_links,
                self.list_filter,
                self.date_hierarchy,
                self.search_fields,
                self.list_select_related,
                self.list_per_page,
                self.list_max_show_all,
                self.list_editable,
                self,
                sortable_by=self.get_sortable_by(request),
                search_help_text=self.search_help_text,
            )

            queryset = cl.get_queryset(request)

        return queryset

    def get_csv_data(self, request, queryset=None) -> Generator[tuple]:
        """
        Returns the data to be included in the CSV download as a generator.

        This method retrieves the data from the queryset to be used for the CSV
        download. It uses the fields defined in the ModelAdmin's list_display
        attribute to determine which fields to include in the CSV.

        Args:
            request: The HttpRequest object containing request information
            queryset (QuerySet, optional): Specific queryset to export. If None,
                                          uses the default changelist queryset with
                                          all applied filters and search terms.

        Returns:
            generator: Generator yielding tuples representing the data to be
                      included in the CSV download. Memory efficient for large datasets.
        """
        queryset = self.get_download_queryset(request, queryset)
        columns = list(self.get_download_columns(request).keys())
        yield from queryset.values_list(*columns)

    def download_file(self, request, queryset=None) -> HttpResponse:
        """
        Generate and return a CSV file download response for the given queryset.

        This method creates a CSV file containing the data from the provided queryset
        or the default changelist queryset if none is provided. It respects any
        applied filters, search terms, and sorting from the admin changelist view.

        Args:
            request: The HttpRequest object containing request information
            queryset (QuerySet, optional): Specific queryset to export. If None,
                                          uses the default changelist queryset with
                                          all applied filters and search terms.

        Returns:
            HttpResponse: CSV file download response with appropriate headers
                         for browser download handling.

        Note:
            - Uses list_display fields to determine which data to export
            - Includes CSV headers based on field verbose names
            - Respects admin changelist filters, search, and sorting when
              queryset is None
            - File format determined by csv_separator attribute

        Example:
            Called directly: admin.download_file(request, User.objects.all())
            Called from action: Automatically uses selected objects queryset
        """
        process_id = uuid.uuid4()
        file_name = self.get_csv_file_name(request)
        log_file_name = unquote(file_name)  # Decode URL-encoded filename for logging

        total_lines = 0
        process_result = CsvProcessResult.SUCCESS

        try:
            response = HttpResponse(content_type=f"text/{self.csv_separator.label}")
            response["Content-Disposition"] = f'attachment; filename="{file_name}"'
            writer = csv.writer(response, delimiter=self.csv_separator)

            if self.get_download_columns(request).values():
                writer.writerow(self.get_download_columns(request).values())

            csv_data = self.get_csv_data(request, queryset)

            for row in csv_data:
                writer.writerow(row)
                total_lines += 1

            # Set NO_DATA result if no data rows were written
            if total_lines == 0:
                process_result = CsvProcessResult.NO_DATA
                download_message = _("No data rows were written to the CSV file.")
            else:
                download_message = _(f"Total {total_lines} data rows were written to the {log_file_name} file.")

            logger.info(download_message)

            # Create CSV log record for successful download
            CsvLog.objects.create(
                process_id=process_id,
                process_type=CsvProcessType.DOWNLOAD,
                process_result=process_result,
                app_name=self.get_app_name(),  # type: ignore
                processed_by=request.user.username,
                ip_address=self.get_client_ip(request),  # type: ignore
                file_name=log_file_name,
                total_line=total_lines,
                comment=f"{self.model._meta.verbose_name}: {download_message}",  # type: ignore
            )

            return response

        except Exception:
            # Create CSV log record for failed download
            CsvLog.objects.create(
                process_id=process_id,
                process_type=CsvProcessType.DOWNLOAD,
                process_result=CsvProcessResult.FAILURE,
                app_name=self.get_app_name(),  # type: ignore
                processed_by=request.user.username,
                ip_address=self.get_client_ip(request),  # type: ignore
                file_name=log_file_name,
                total_line=total_lines,
            )
            # Re-raise the exception to maintain original behavior
            raise

    def get_urls(self) -> list[Path]:
        """
        Override the default ModelAdmin URLs to include a custom CSV download endpoint.

        Adds a custom URL pattern for CSV download functionality while preserving
        all existing admin URLs. The download URL is accessible to admin users
        and respects the same permissions as the changelist view.

        Returns:
            list: Combined list of custom download URLs and default admin URLs,
                 with custom URLs taking precedence.

        URL Pattern:
            - Path: "download_file/"
            - Name: "{app_label}_{model_name}_download_file"
            - View: Protected by admin_site.admin_view wrapper

        Note:
            Custom URLs are placed before default URLs to ensure they take
            precedence in URL resolution.
        """
        urls = super().get_urls()  # type: ignore
        download_url = [
            path(
                "download_file/",
                self.admin_site.admin_view(self.download_file),  # type: ignore
                name=self.download_url_name,
            ),
        ]
        return download_url + urls

    def get_actions(self, request) -> OrderedDict[Any, Any]:
        """
        Add CSV download action to the list of available admin actions.

        Extends the default admin actions with a custom "download_selected" action
        that allows users to download selected rows from the changelist as a CSV file.

        Args:
            request: The HttpRequest object containing request information

        Returns:
            OrderedDict: Dictionary of available actions including the new download action.
                 Format: {action_name: (function, name, description)}

        Action Details:
            - Key: "download_selected"
            - Function: download_selected function from this module
            - Description: Localized Japanese text "選択行のダウンロード"

        Note:
            The download action will appear in the admin changelist action dropdown
            and can be applied to any selected rows.
        """
        actions = super().get_actions(request)  # type: ignore
        actions["download_selected"] = (
            download_selected,
            "download_selected",
            download_selected.short_description,  # type: ignore
        )
        return actions

    def changelist_view(self, request, extra_context=None) -> Any:
        """
        Override the changelist view to add CSV download button and functionality.

        Enhances the default admin changelist view by adding context variables
        needed to display a download button and handle CSV export functionality.
        The download URL preserves any applied filters, search terms, or sorting.

        Args:
            request: The HttpRequest object containing request information
            extra_context (dict, optional): Additional context data for the template

        Returns:
            TemplateResponse: The changelist view response with additional
                            download-related context variables.

        Context Variables Added:
            - download_url: URL for CSV download with current filters/search preserved
            - download_button_name: Localized button text based on file format

        Note:
            The download URL includes any GET parameters from the current request
            to ensure that filters, search terms, and sorting are preserved in
            the downloaded data.
        """
        if extra_context is None:
            extra_context = {}

        # url = reverse(f"admin:{self.model._meta.app_label}_{self.model._meta.model_name}_download_file")
        url = reverse(f"{self.admin_site.name}:{self.download_url_name}")  # type: ignore
        params = request.GET.urlencode()
        if params:
            url = f"{url}?{params}"
        extra_context["download_url"] = url
        extra_context["download_title"] = _("Download {label} File").format(label=self.csv_separator.label.upper())
        extra_context["download_message"] = _("Are you sure you want to download the file?")
        extra_context["download_button"] = _("Download")
        return super().changelist_view(request, extra_context=extra_context)  # type: ignore


class BaseModelDownloadMixin(DownloadMixin):
    def get_download_columns(self, request) -> dict[str, str]:
        columns = super().get_download_columns(request)

        base_model_fields = {f.name: f.verbose_name for f in self.model.get_base_model_fields()}  # type: ignore
        # Remove base model fields from current columns
        filtered_columns = {k: v for k, v in columns.items() if k not in base_model_fields and k != "deleted" and k != "update_timestamp"}

        return filtered_columns | base_model_fields


class MasterModelDownloadMixin(DownloadMixin):
    def get_download_columns(self, request) -> dict[str, str]:
        columns = super().get_download_columns(request)
        # Master modelは論理削除しないので、deleted_flgを除外
        columns.pop("deleted_flg", None)

        master_model_fields = {f.name: f.verbose_name for f in self.model.get_master_model_fields()}  # type: ignore
        # Remove master model fields from current columns
        filtered_columns = {k: v for k, v in columns.items() if k not in master_model_fields}

        return filtered_columns | master_model_fields
