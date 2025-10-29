import csv
import logging
import os
import shutil
import uuid
import zipfile
from collections.abc import Sequence
from datetime import date, datetime, time, timedelta
from typing import Any

from django import forms
from django.conf import settings
from django.db import models
from django.db.models import TextChoices
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import path, reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from sfd.models.base import BaseModel, MasterModel, default_valid_from_date, default_valid_to_date
from sfd.models.csv_log import CsvLog, CsvProcessResult, CsvProcessType

logger = logging.getLogger(__name__)


class UploadType(TextChoices):
    CSV = "csv", _("CSV")
    EXCEL = "excel", _("Excel")
    ZIP = "zip", _("ZIP")


class Encoding(TextChoices):
    UTF8 = "utf-8", "UTF-8"
    SJIS = "shift-jis", "Shift-JIS"


class UploadForm(forms.Form):
    upload_file = forms.FileField(label=_("Select File"), required=True)
    upload_type = forms.ChoiceField(choices=UploadType.choices, label=_("Upload Type"))
    encoding = forms.ChoiceField(choices=Encoding.choices, label=_("Encoding"))


class UploadMixin:
    """
    Mixin to handle file uploads in views.
    """

    upload_type = UploadType.CSV  # Default upload type
    encoding = Encoding.UTF8  # Default encoding
    delimiter = ","  # Default CSV delimiter
    csv_skip_lines = 1  # Number of lines to skip at the start of the CSV file
    is_skip_existing = True  # Whether to skip existing records during upload
    upload_column_names = ()  # Columns to be read from the CSV file
    upload_model = None  # Model to be used for uploading
    chunk_size = 10000  # Process 1000 records at a time

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        opts = self.model._meta  # type: ignore[attr-defined]
        self.upload_url_name = f"{opts.app_label}_{opts.model_name}_upload_file"  # type: ignore[attr-defined]

    def get_upload_column_names(self, request) -> list[str]:
        """
        Returns the list of column names to be used for uploading.
        This should be overridden in subclasses to specify the columns.
        """
        upload_column_names = []
        if self.upload_model is not None:
            upload_column_names = [f.name for f in self.upload_model._meta.get_fields() if f.concrete and not f.auto_created]  # type: ignore
        elif self.upload_column_names:
            upload_column_names = list(self.upload_column_names)
        elif hasattr(self, "download_column_names") and self.download_column_names:  # type: ignore
            upload_column_names = list(self.download_column_names)  # type: ignore
        elif hasattr(self, "get_download_columns"):
            download_column_names = self.get_download_columns(request)  # type: ignore
            if download_column_names:
                upload_column_names = list(download_column_names.keys())
        else:
            upload_column_names = self.get_list_display(request)  # type: ignore

        logger.debug(f"Upload Column Names: {upload_column_names}")
        return upload_column_names

    def get_upload_db_fields(self, request) -> dict[str, models.Field]:
        """
        Returns the fields of the target database table to be used for uploading.
        This should be overridden in subclasses to specify the fields.
        """
        upload_column_names = self.get_upload_column_names(request)
        upload_model = self.upload_model if self.upload_model is not None else self.model  # type: ignore[attr-defined]

        model_field_names = [f.name for f in upload_model._meta.get_fields() if f.concrete and not f.auto_created]  # type: ignore
        db_fields = {name: upload_model._meta.get_field(name) for name in upload_column_names if name in model_field_names}  # type: ignore

        logger.debug(f"Upload DB Fields: {list(db_fields.keys())}")
        return db_fields

    def get_urls(self):
        """
        Override the default ModelAdmin URLs to include a custom CSV upload endpoint.

        Adds a custom URL pattern for CSV upload functionality while preserving
        all existing admin URLs. The upload URL is accessible to admin users
        and respects the same permissions as the changelist view.

        Returns:
            list: Combined list of custom upload URLs and default admin URLs,
                 with custom URLs taking precedence.

        URL Pattern:
            - Path: "upload_csv/"
            - Name: "{app_label}_{model_name}_upload_csv"
            - View: Protected by admin_site.admin_view wrapper

        Note:
            Custom URLs are placed before default URLs to ensure they take
            precedence in URL resolution.
        """
        urls = super().get_urls()  # type: ignore
        upload_url = [
            path(
                "upload_file/",
                self.admin_site.admin_view(self.upload_file),  # type: ignore
                name=self.upload_url_name,
            ),
        ]
        return upload_url + urls

    def get_context_data(self, form=None) -> dict[str, Any]:
        if form is None:
            form = UploadForm(
                initial={
                    "upload_type": self.upload_type,
                    "encoding": self.encoding,
                }
            )

            if self.upload_type == UploadType.EXCEL:
                form.fields["encoding"].widget = forms.HiddenInput()

        return {
            "form": form,
            "upload_url": reverse(f"{self.admin_site.name}:{self.upload_url_name}"),  # type: ignore
            "upload_title": _("Upload"),
            "upload_button_name": _("Upload"),
        }

    def get_model_unique_field_names(self) -> Sequence[str]:
        """Get unique field names for the upload model."""
        if self.upload_model is not None:
            return []
        elif not hasattr(self.model, "get_unique_field_names"):  # type: ignore
            return []
        else:
            return self.model.get_unique_field_names()  # type: ignore

    def upload_file(self, request) -> HttpResponse:
        if request.method == "POST":
            form = UploadForm(request.POST, request.FILES)
            if form.is_valid():
                cleaned_data = form.cleaned_data
                file = cleaned_data["upload_file"]
                upload_type = cleaned_data["upload_type"]
                encoding = cleaned_data["encoding"]

                self._bulk_create_list = []
                self._bulk_update_list = []
                self._uploaded_unique_values = set()  # 今回アップロードしたCSVのユニーク値
                self._total_inserted = 0  # Track total inserted across chunks
                self._total_updated = 0  # Track total updated across chunks
                self._upload_datetime = timezone.now()
                self._process_id = uuid.uuid4()  # Generate unique process ID for this upload
                self._total_lines = 0  # Track total lines processed

                model_name = self.upload_model._meta.verbose_name if self.upload_model is not None else self.model._meta.verbose_name  # type: ignore[attr-defined]

                try:
                    self.pre_upload(request)

                    if upload_type == UploadType.EXCEL:
                        self.excel_upload(request, file)
                    elif upload_type == UploadType.ZIP:
                        csv_files = self.zip_upload(request, file)
                        for csv_file in csv_files:
                            logger.info(f"Processing CSV file: {csv_file}")
                            self.upload_data(request, self.get_csv_reader, csv_file, encoding, request)
                    else:
                        self.upload_data(request, self.get_csv_reader, file, encoding, request)

                    self.post_upload(request)

                    upload_message = _("Upload completed. Inserted: %(inserted)s rows, Updated: %(updated)s rows.") % {
                        "inserted": self._total_inserted,
                        "updated": self._total_updated,
                    }
                    # Create CSV log record for successful upload
                    CsvLog.objects.create(
                        process_id=self._process_id,
                        process_type=CsvProcessType.UPLOAD,
                        process_result=CsvProcessResult.SUCCESS if self._total_lines > 0 else CsvProcessResult.NO_DATA,
                        app_name=self.get_app_name(),  # type: ignore
                        processed_by=request.user.username,
                        ip_address=self.get_client_ip(request),  # type: ignore
                        file_name=file.name,
                        total_line=self._total_lines,
                        comment=f"{model_name}: {upload_message}",
                    )

                    logger.info(upload_message)

                    # Add success message for both HTMX and regular requests
                    self.message_user(request, upload_message, level="success")  # type: ignore

                    # For successful uploads, close modal and refresh page
                    if "HX-Request" in request.headers:
                        # For HTMX requests, return a lightweight response
                        from django.http import HttpResponse

                        response = HttpResponse("")
                        response["HX-Trigger"] = "uploadSuccess"  # Simple trigger for page refresh

                        return response
                    else:
                        # For regular requests, render the full template
                        response = render(request, "sfd/upload.html", self.get_context_data(form=form))
                        return response

                except Exception as e:
                    error_key = str(uuid.uuid4())
                    exception_message = str(e)
                    logger.error(f"Error key: {error_key} \n Message: {exception_message}")
                    logger.exception(e)

                    upload_message = _(
                        "An unexpected error has occurred. Please contact your system administrator and provide this error key [%(error_key)s]."
                    ) % {
                        "error_key": error_key,
                    }

                    # Create CSV log record for failed upload
                    CsvLog.objects.create(
                        process_id=self._process_id,
                        process_type=CsvProcessType.UPLOAD,
                        process_result=CsvProcessResult.FAILURE,
                        app_name=self.get_app_name(),  # type: ignore
                        processed_by=request.user.username,
                        ip_address=self.get_client_ip(request),  # type: ignore
                        file_name=file.name,
                        total_line=self._total_lines,
                        comment=f"{model_name}: {upload_message}",
                    )

                    self.message_user(request, upload_message, level="error")  # type: ignore

                    # For error responses, keep modal open with error message
                    if "HX-Request" in request.headers:
                        response = render(request, "sfd/upload.html", self.get_context_data(form=form))
                        response["HX-Trigger"] = "uploadError"  # Trigger custom event
                        return response

            response = render(request, "sfd/upload.html", self.get_context_data(form=form))
            return response
        else:
            response = render(request, "sfd/upload.html", self.get_context_data())
            return response

    def pre_upload(self, request) -> None:
        """Handle pre-upload processing."""
        if self.upload_model is not None:
            self.upload_model.objects.all().delete()

    def post_upload(self, request) -> None:
        """Handle post-upload processing."""
        pass

    def excel_upload(self, request, excel_file) -> None:
        """Get Excel reader object."""
        raise NotImplementedError

    def zip_upload(self, request, zip_file) -> list:
        """Extract ZIP file and return paths to CSV files.

        Args:
            request: HTTP request object
            zip_file: Uploaded ZIP file object

        Returns:
            list: List of file paths to extracted CSV files

        Raises:
            ValueError: If no CSV files are found in the ZIP archive
        """
        temp_zip_dir = os.path.join(settings.TEMP_DIR, "zip_upload")
        os.makedirs(temp_zip_dir, exist_ok=True)

        subdirectory = os.path.join(temp_zip_dir, zip_file.name)
        shutil.rmtree(subdirectory, ignore_errors=True)
        os.makedirs(subdirectory, exist_ok=True)
        csv_files = []
        with zipfile.ZipFile(zip_file, "r") as zf:
            zf.extractall(subdirectory)

            # Find only CSV files
            for root, _list, files in os.walk(subdirectory):
                for f in files:
                    if f.lower().endswith(".csv"):
                        csv_files.append(os.path.join(root, f))

        if not csv_files:
            raise ValueError(_("No CSV files found in the ZIP archive."))

        return csv_files

    def get_csv_reader(self, csv_file, encoding, request):
        """Get CSV reader object.

        Args:
            csv_file: Either a file object (from uploaded file) or a file path string (from extracted ZIP)
            encoding: Character encoding to use when reading the file
            request: HTTP request object (optional)

        Yields:
            dict: Each row of the CSV file as a dictionary
        """
        # Handle both file objects and file paths
        if isinstance(csv_file, str):
            # csv_file is a file path (from ZIP extraction)
            with open(csv_file, encoding=encoding) as f:
                csv_content = f.read().splitlines()
        else:
            # csv_file is a file object (from direct upload)
            csv_content = csv_file.read().decode(encoding).splitlines()

        # Convert dict_keys to list for csv.DictReader compatibility
        upload_field_names = self.get_upload_column_names(request)
        reader = csv.DictReader(csv_content, fieldnames=upload_field_names, delimiter=self.delimiter)  # type: ignore
        # Skip the header row
        for _x in range(self.csv_skip_lines):
            next(reader, None)

        yield from reader

    def upload_data(self, request, upload_func, *args, **kwargs) -> None:
        """Simple implementation of CSV upload. Only inserts new rows."""

        # Initialize _total_lines if not already set (for direct calls to upload_data)
        if not hasattr(self, "_total_lines"):
            self._total_lines = 0

        upload_fields = self.get_upload_db_fields(request)
        unique_fields = self.get_model_unique_field_names()
        if issubclass(self.model, BaseModel):  # type: ignore
            creator_info = {"created_by": request.user.username, "created_at": self._upload_datetime}
            updater_info = {"updated_by": request.user.username, "updated_at": self._upload_datetime}
        else:
            creator_info = {}
            updater_info = {}

        reader = upload_func(*args, **kwargs)

        # Process data in chunks to avoid memory issues with large files
        processed_count = 0

        for row in reader:
            if not row:
                continue
            logger.debug(f"Processing row: {row}")
            self._total_lines += 1  # Track total lines processed
            row_dict = self.convert2upload_fields(request, row, upload_fields)
            if not row_dict:
                raise ValueError(_("No valid data found in the row."))
            if self.upload_model is not None:
                instance = self.upload_model(**row_dict)
                self._bulk_create_list.append(instance)
            elif not unique_fields:
                instance = self.model(**(creator_info | row_dict | updater_info))  # type: ignore
                self._bulk_create_list.append(instance)
            else:
                unique_values = {field: row_dict[field] for field in unique_fields if field in row_dict}
                # Check if any unique_fields keys are not in unique_values
                missing_unique_fields = [k for k in unique_fields if k not in unique_values.keys()]
                if missing_unique_fields:
                    raise ValueError(f"Row {row} is missing required unique fields: {missing_unique_fields}")

                instance = self.model.objects.filter(**unique_values).first()  # type: ignore
                if instance:  # DBに既存のレコードがあるか確認
                    if not self.is_skip_existing:
                        changed_values = {k: v for k, v in row_dict.items() if v != getattr(instance, k)}
                        if changed_values:  # 変更がある場合のみ更新
                            changed_values.update(updater_info)
                            for k, v in changed_values.items():
                                setattr(instance, k, v)
                            self._bulk_update_list.append(instance)
                else:
                    if tuple(v for v in unique_values.values()) not in self._uploaded_unique_values:
                        # 既にアップロード済みのレコードと重複してない場合
                        instance = self.model(**(creator_info | row_dict | updater_info))  # type: ignore
                        self._bulk_create_list.append(instance)

                self._uploaded_unique_values.add(tuple(v for v in unique_values.values()))

            processed_count += 1

            # Process in chunks to avoid memory issues
            if processed_count % self.chunk_size == 0:
                self._process_bulk_operations(request, upload_fields)
                logger.debug(f"Processed {processed_count} records so far...")

        # Process any remaining records
        if self._bulk_create_list or self._bulk_update_list:
            self._process_bulk_operations(request, upload_fields)

    def _process_bulk_operations(self, request, upload_fields) -> None:
        """Process bulk create and update operations in chunks."""
        from django.db import transaction

        # Use atomic transaction for each chunk to ensure proper commit
        with transaction.atomic():
            if self._bulk_create_list:
                create_count = len(self._bulk_create_list)
                if self.upload_model is not None:
                    self.upload_model.objects.bulk_create(self._bulk_create_list)
                else:
                    self.model.objects.bulk_create(self._bulk_create_list)  # type: ignore
                self._total_inserted += create_count
                self._bulk_create_list.clear()  # Clear the list to free memory

            if self._bulk_update_list:
                update_count = len(self._bulk_update_list)
                upload_field_names = list(upload_fields.keys())
                if self.upload_model is not None:
                    self.upload_model.objects.bulk_update(self._bulk_update_list, upload_field_names)
                else:
                    self.model.objects.bulk_update(self._bulk_update_list, upload_field_names)  # type: ignore
                self._total_updated += update_count
                self._bulk_update_list.clear()  # Clear the list to free memory

    def convert2upload_fields(self, request, row_dict, upload_fields) -> dict[str, Any]:
        """Convert CSV row_dict data to model field type
        外部キーIDはDBシーケンスになるので、Table再作成によって異なる可能性があるため、ダウン・アップロードに使用しない。
        ダウン・アップロードでは、外部キーのUnique Keyを使用し、本メソッドをOverrideして対応する。
        """
        converted = {}
        for key, value in row_dict.items():
            if key not in upload_fields.keys():
                continue

            if upload_fields[key].get_internal_type() == "DateField":
                if not value:
                    converted[key] = None
                elif isinstance(value, str):
                    value = value.replace("/", "-")
                    for fmt in ("%Y-%m-%d", "%Y-%m"):
                        try:
                            converted[key] = datetime.strptime(value, fmt).date()
                            break
                        except ValueError:
                            continue
                    else:
                        raise ValueError(f"Invalid value for {key}: {value}, it should be a datetime.")
                elif isinstance(value, date):
                    converted[key] = value
                else:
                    raise ValueError(f"Invalid value for {key}: {value}, it should be a date.")
            elif upload_fields[key].get_internal_type() == "DateTimeField":
                if not value:
                    converted[key] = None
                elif isinstance(value, str):
                    value = value.replace("/", "-")
                    for fmt in (
                        "%Y-%m-%d %H:%M:%S",
                        "%Y-%m-%d %H:%M",
                        "%Y-%m-%d %H:%M:%S.%f",
                        "%Y-%m-%d %H:%M:%S%z",
                        "%Y-%m-%d %H:%M:%S.%f%z",
                        "%Y-%m-%d",
                    ):
                        try:
                            converted[key] = datetime.strptime(value, fmt)
                            break
                        except ValueError:
                            continue
                    else:
                        raise ValueError(f"Invalid value for {key}: {value}, it should be a datetime.")
                elif isinstance(value, datetime):
                    converted[key] = value
                else:
                    raise ValueError(f"Invalid value for {key}: {value}, it should be a datetime.")
            elif upload_fields[key].get_internal_type() == "TimeField":
                if not value:
                    converted[key] = None
                elif isinstance(value, str):
                    for fmt in ("%H:%M:%S", "%H:%M"):
                        try:
                            converted[key] = datetime.strptime(value.replace("/", "-"), fmt).time()
                            break
                        except ValueError:
                            continue
                    else:
                        raise ValueError(f"Invalid value for {key}: {value}, it should be a time.")
                elif isinstance(value, time):
                    converted[key] = value
                else:
                    raise ValueError(f"Invalid value for {key}: {value}, it should be a time.")
            elif upload_fields[key].get_internal_type() == "DurationField":
                if not value:
                    converted[key] = None
                elif isinstance(value, str):
                    hour, minute, second = map(int, value.split(":"))
                    converted[key] = timedelta(hours=hour, minutes=minute, seconds=second)
                elif isinstance(value, timedelta):
                    converted[key] = value
                else:
                    raise ValueError(f"Invalid value for {key}: {value}, it should be a duration.")
            elif upload_fields[key].get_internal_type() == "BooleanField":
                if value is None:
                    converted[key] = None
                elif isinstance(value, str):
                    converted[key] = value.lower() not in ("false", "0", "no", "")
                elif isinstance(value, int):
                    converted[key] = value != 0
                else:
                    converted[key] = bool(value)
            else:
                converted[key] = value
        return converted

    def changelist_view(self, request, extra_context=None):
        if extra_context is None:
            extra_context = {}

        extra_context["upload_url"] = reverse(f"{self.admin_site.name}:{self.upload_url_name}")  # type: ignore
        extra_context["upload_button_name"] = _("Upload")
        return super().changelist_view(request, extra_context=extra_context)  # type: ignore


class BaseModelUploadMixin(UploadMixin):
    def get_upload_column_names(self, request) -> list[str]:
        column_names = super().get_upload_column_names(request)
        # Only add base model fields if uploading to a BaseModel (not to a different upload_model)
        upload_model = self.upload_model if self.upload_model is not None else self.model  # type: ignore[attr-defined]
        if issubclass(upload_model, BaseModel):
            base_model_field_names = [f.name for f in BaseModel.get_base_model_fields()]
            return [name for name in column_names if name not in base_model_field_names] + base_model_field_names
        return column_names

    def convert2upload_fields(self, request, row_dict, upload_fields):
        converted = super().convert2upload_fields(request, row_dict, upload_fields)

        # Only add base model fields if uploading to a BaseModel (not to a different upload_model)
        upload_model = self.upload_model if self.upload_model is not None else self.model  # type: ignore[attr-defined]
        if issubclass(upload_model, BaseModel):
            if "created_by" not in converted or converted.get("created_by") is None:
                converted["created_by"] = request.user.username

            converted["updated_by"] = request.user.username

            if "deleted_flg" not in converted or converted.get("deleted_flg") is None:
                converted["deleted_flg"] = False

        # logger.debug(f"Converted upload fields for BaseModel: {converted}")
        return converted


class MasterModelUploadMixin(UploadMixin):
    def get_upload_column_names(self, request) -> list[str]:
        column_names = super().get_upload_column_names(request)
        # Only add master model fields if uploading to a MasterModel (not to a different upload_model)
        upload_model = self.upload_model if self.upload_model is not None else self.model  # type: ignore[attr-defined]
        if issubclass(upload_model, MasterModel):
            master_model_field_names = [f.name for f in MasterModel.get_master_model_fields()]
            return [name for name in column_names if name not in master_model_field_names and name != "deleted_flg"] + master_model_field_names
        return column_names

    def convert2upload_fields(self, request, row_dict, upload_fields):
        """Convert row dictionary to upload fields for MasterModel.

        This method processes the row dictionary to convert it into a format
        suitable for uploading MasterModel instances. It ensures that the
        upload fields are correctly mapped and formatted.

        Args:
            row_dict (dict): The row data to be converted
            upload_fields (list): List of fields to be included in the upload

        Returns:
            dict: A dictionary containing the converted upload fields
        """
        converted = super().convert2upload_fields(request, row_dict, upload_fields)  # type: ignore

        # Only add master model fields if uploading to a MasterModel (not to a different upload_model)
        upload_model = self.upload_model if self.upload_model is not None else self.model  # type: ignore[attr-defined]
        if issubclass(upload_model, MasterModel):
            if "valid_from" not in converted or converted.get("valid_from") is None:
                converted["valid_from"] = default_valid_from_date()
            if "valid_to" not in converted or converted.get("valid_to") is None:
                converted["valid_to"] = default_valid_to_date()

        logger.debug(f"Converted upload fields for MasterModel: {converted}")
        return converted
