# type: ignore
"""
Comprehensive tests for upload.py module.

This module provides extensive test coverage for CSV upload functionality,
including form validation, file processing, data conversion, and error handling.
"""

import os
import tempfile
from datetime import date, timedelta
from unittest import TestCase
from unittest.mock import Mock, patch

import pytest
from django import forms
from django.contrib import admin
from django.contrib.admin.sites import AdminSite
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import models
from django.http import HttpResponse
from django.utils import timezone, translation

from sfd.tests.unittest import BaseTestMixin, TestBaseModel, TestMasterModel, TestModel
from sfd.views.common.upload import BaseModelUploadMixin, Encoding, MasterModelUploadMixin, UploadForm, UploadMixin, UploadType


class TestModelAdmin(UploadMixin, admin.ModelAdmin):
    pass


class TestBaseModelAdmin(BaseModelUploadMixin, admin.ModelAdmin):
    pass


class TestMasterModelAdmin(MasterModelUploadMixin, admin.ModelAdmin):
    pass


@pytest.mark.unit
@pytest.mark.upload
class UploadTypeTest(TestCase):
    """Test UploadType TextChoices class functionality."""

    def test_upload_type_choices(self):
        """Test UploadType choices are properly defined."""
        self.assertEqual(UploadType.CSV, "csv")
        self.assertEqual(UploadType.EXCEL, "excel")

    def test_upload_type_labels(self):
        """Test UploadType labels are properly internationalized."""
        choices = UploadType.choices
        self.assertEqual(len(choices), 3)
        self.assertIn(("csv", "CSV"), choices)
        self.assertIn(("excel", "Excel"), choices)
        self.assertIn(("zip", "ZIP"), choices)

    def test_upload_type_values(self):
        """Test UploadType value retrieval."""
        self.assertEqual(str(UploadType.CSV), "csv")
        self.assertEqual(str(UploadType.EXCEL), "excel")
        self.assertEqual(str(UploadType.ZIP), "zip")


@pytest.mark.unit
@pytest.mark.upload
class EncodingTest(TestCase):
    """Test Encoding TextChoices class functionality."""

    def test_encoding_choices(self):
        """Test Encoding choices are properly defined."""
        self.assertEqual(Encoding.UTF8, "utf-8")
        self.assertEqual(Encoding.SJIS, "shift-jis")

    def test_encoding_labels(self):
        """Test Encoding labels are properly defined."""
        choices = Encoding.choices
        self.assertEqual(len(choices), 2)
        self.assertIn(("utf-8", "UTF-8"), choices)
        self.assertIn(("shift-jis", "Shift-JIS"), choices)

    def test_encoding_values(self):
        """Test Encoding value retrieval."""
        self.assertEqual(str(Encoding.UTF8), "utf-8")
        self.assertEqual(str(Encoding.SJIS), "shift-jis")


@pytest.mark.unit
@pytest.mark.upload
class UploadFormTest(TestCase):
    """Test UploadForm functionality and validation."""

    def test_upload_form_fields(self):
        """Test UploadForm has required fields."""
        form = UploadForm()
        self.assertIn("upload_file", form.fields)
        self.assertIn("upload_type", form.fields)
        self.assertIn("encoding", form.fields)

    def test_upload_form_field_types(self):
        """Test UploadForm field types are correct."""
        form = UploadForm()
        self.assertIsInstance(form.fields["upload_file"], forms.FileField)
        self.assertIsInstance(form.fields["upload_type"], forms.ChoiceField)
        self.assertIsInstance(form.fields["encoding"], forms.ChoiceField)

    def test_upload_form_choices(self):
        """Test UploadForm choice fields have correct options."""
        form = UploadForm()
        self.assertEqual(form.fields["upload_type"].choices, UploadType.choices)
        self.assertEqual(form.fields["encoding"].choices, Encoding.choices)

    def test_upload_form_valid_data(self):
        """Test UploadForm validation with valid data."""
        test_file = SimpleUploadedFile("test.csv", b"name,email\ntest,test@example.com", content_type="text/csv")
        form_data = {"upload_type": UploadType.CSV, "encoding": Encoding.UTF8}
        form = UploadForm(data=form_data, files={"upload_file": test_file})
        self.assertTrue(form.is_valid())

    def test_upload_form_missing_file(self):
        """Test UploadForm validation fails without file."""
        form_data = {"upload_type": UploadType.CSV, "encoding": Encoding.UTF8}
        form = UploadForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("upload_file", form.errors)

    def test_upload_form_invalid_upload_type(self):
        """Test UploadForm validation fails with invalid upload type."""
        test_file = SimpleUploadedFile("test.csv", b"test data", content_type="text/csv")
        form_data = {"upload_type": "invalid", "encoding": Encoding.UTF8}
        form = UploadForm(data=form_data, files={"upload_file": test_file})
        self.assertFalse(form.is_valid())
        self.assertIn("upload_type", form.errors)

    def test_upload_form_invalid_encoding(self):
        """Test UploadForm validation fails with invalid encoding."""
        test_file = SimpleUploadedFile("test.csv", b"test data", content_type="text/csv")
        form_data = {"upload_type": UploadType.CSV, "encoding": "invalid"}
        form = UploadForm(data=form_data, files={"upload_file": test_file})
        self.assertFalse(form.is_valid())
        self.assertIn("encoding", form.errors)


def create_test_csv_file(content, filename="test.csv"):
    """Create a test CSV file for upload testing."""
    return SimpleUploadedFile(filename, content.encode("utf-8"), content_type="text/csv")


@pytest.mark.unit
@pytest.mark.upload
class UploadMixinTest(BaseTestMixin, TestCase):
    """Test UploadMixin functionality with comprehensive coverage."""

    databases = ["default", "postgres"]

    def setUp(self):
        """Set up test environment with model admin instance."""
        super().setUp()
        self.admin_site = AdminSite()
        self.model_admin = TestModelAdmin(TestModel, self.admin_site)

        self.request = self.factory.get("/admin/")
        self.request.user = self.user

        self.model_admin._bulk_create_list = []
        self.model_admin._bulk_update_list = []
        self.model_admin._uploaded_unique_values = set()  # 今回アップロードしたCSVのユニーク値
        self.model_admin._total_inserted = 0  # Track total inserted across chunks
        self.model_admin._total_updated = 0  # Track total updated across chunks
        self.model_admin._upload_datetime = timezone.now()

        # Mock get_app_name method for all tests
        self.model_admin.get_app_name = lambda: "sfd"

        # Mock get_client_ip method for all tests
        def mock_get_client_ip(request):
            """Mock implementation of get_client_ip."""
            x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
            if x_forwarded_for:
                return x_forwarded_for.split(",")[0]
            return request.META.get("REMOTE_ADDR")

        self.model_admin.get_client_ip = mock_get_client_ip

    def test_mixin_initialization(self):
        """Test UploadMixin initialization sets correct attributes."""
        self.assertEqual(self.model_admin.upload_type, UploadType.CSV)
        self.assertEqual(self.model_admin.encoding, Encoding.UTF8)
        self.assertEqual(self.model_admin.csv_skip_lines, 1)
        self.assertTrue(self.model_admin.is_skip_existing)
        self.assertEqual(self.model_admin.upload_column_names, ())
        self.assertEqual(self.model_admin.upload_model, None)
        self.assertEqual(self.model_admin.chunk_size, 10000)

    def test_upload_url_name_generation(self):
        """Test upload URL name is generated correctly."""
        expected_name = "sfd_testmodel_upload_file"
        self.assertEqual(self.model_admin.upload_url_name, expected_name)

    def test_get_upload_column_names_with_upload_model(self):
        """Test get_upload_column_names returns correct column names."""

        # Setup mocks
        class TestUploadModel(models.Model):
            name = models.CharField(max_length=100)
            upload_field = models.IntegerField()

            class Meta:
                app_label = "sfd"
                db_table = "test_upload_model"

        self.model_admin.upload_model = TestUploadModel
        result = self.model_admin.get_upload_column_names(self.request)

        self.assertEqual(result, ["name", "upload_field"])

    def test_get_upload_column_names_with_upload_column_names(self):
        """Test get_upload_column_names returns correct column names."""
        # Setup mocks
        self.model_admin.upload_column_names = ("name", "column1", "column2")

        result = self.model_admin.get_upload_column_names(self.request)

        self.assertEqual(result, ["name", "column1", "column2"])

    def test_get_upload_column_names_with_download_column_names(self):
        """Test get_upload_column_names returns correct column names."""
        # Setup mocks
        self.model_admin.download_column_names = ("name", "columnA", "columnB")

        result = self.model_admin.get_upload_column_names(self.request)

        self.assertEqual(result, ["name", "columnA", "columnB"])

    def test_get_upload_column_names_with_get_download_columns(self):
        """Test get_upload_column_names returns correct column names from get_download_columns."""
        # Directly assign a Mock method to the instance (simulates having get_download_columns)
        self.model_admin.get_download_columns = Mock(return_value={"name": "Name", "get_column": "Get Column"})

        result = self.model_admin.get_upload_column_names(self.request)

        self.assertEqual(result, ["name", "get_column"])
        self.model_admin.get_download_columns.assert_called_once_with(self.request)

    def test_get_upload_column_names_with_list_display(self):
        """Test get_upload_column_names returns correct column names."""
        self.model_admin.get_list_display = Mock(return_value=["name", "column_list1", "column_list2"])

        result = self.model_admin.get_upload_column_names(self.request)

        self.assertEqual(result, ["name", "column_list1", "column_list2"])

    def test_get_upload_db_fields(self):
        """Test get_upload_db_fields returns correct field mapping for BaseModel."""
        # Use TestBaseModel which inherits from BaseModel but not MasterModel
        from sfd.tests.unittest import TestBaseModel

        self.model_admin.upload_model = TestBaseModel

        result = self.model_admin.get_upload_db_fields(self.request)

        # Convert dict_keys to list for comparison
        result_keys = list(result.keys())
        # Should include local fields plus BaseModel fields
        self.assertIn("name", result_keys)
        self.assertIn("email", result_keys)
        self.assertIn("created_at", result_keys)  # BaseModel field
        self.assertIn("updated_at", result_keys)  # BaseModel field

    def test_get_upload_db_fields_with_upload_column_names(self):
        """Test get_upload_db_fields returns correct field mapping."""
        # Setup mocks
        self.model_admin.upload_column_names = ("name", "email")

        result = self.model_admin.get_upload_db_fields(self.request)

        self.assertEqual(tuple(result.keys()), self.model_admin.upload_column_names)

    def test_get_upload_db_fields_with_non_base_model(self):
        """Test get_upload_db_fields with upload_model that is not BaseModel or MasterModel."""
        # Use a model that definitely doesn't inherit from BaseModel
        from django.contrib.contenttypes.models import ContentType

        self.model_admin.upload_model = ContentType

        result = self.model_admin.get_upload_db_fields(self.request)

        # Should include concrete, non-auto-created fields from ContentType model
        result_keys = list(result.keys())
        self.assertIn("app_label", result_keys)
        self.assertIn("model", result_keys)
        # id should be excluded as it's auto-created
        self.assertNotIn("id", result_keys)

    def test_get_upload_db_fields_with_download_column_names(self):
        """Test get_upload_db_fields uses download_column_names when upload_column_names is not set."""
        # Set download_column_names attribute
        self.model_admin.download_column_names = ["name", "email"]

        result = self.model_admin.get_upload_db_fields(self.request)

        # Should use download_column_names
        result_keys = list(result.keys())
        self.assertEqual(result_keys, ["name", "email"])

    def test_get_upload_db_fields_with_get_list_display(self):
        """Test get_upload_db_fields uses get_list_display when no column names are set."""
        # Mock get_list_display to return specific fields
        self.model_admin.get_list_display = Mock(return_value=["name", "email", "is_active"])

        result = self.model_admin.get_upload_db_fields(self.request)

        # Should use get_list_display
        result_keys = list(result.keys())
        self.assertEqual(result_keys, ["name", "email", "is_active"])
        self.model_admin.get_list_display.assert_called_once_with(self.request)

    def test_get_urls(self):
        """Test get_urls includes custom upload URL."""

        # Need to create a fresh instance to test get_urls properly
        urls = self.model_admin.get_urls()

        # First URL should be our custom upload URL
        upload_url = urls[0]
        self.assertEqual(str(upload_url.pattern), "upload_file/")

    def test_get_client_ip_with_x_forwarded_for(self):
        """Test get_client_ip extracts IP from X-Forwarded-For header."""
        request = self.factory.get("/test/")
        request.META["HTTP_X_FORWARDED_FOR"] = "203.0.113.195, 70.41.3.18, 150.172.238.178"
        request.META["REMOTE_ADDR"] = "192.168.1.1"

        ip = self.model_admin.get_client_ip(request)
        self.assertEqual(ip, "203.0.113.195")

    def test_get_client_ip_without_x_forwarded_for(self):
        """Test get_client_ip uses REMOTE_ADDR when X-Forwarded-For is not present."""
        request = self.factory.get("/test/")
        request.META["REMOTE_ADDR"] = "192.168.1.100"

        ip = self.model_admin.get_client_ip(request)
        self.assertEqual(ip, "192.168.1.100")

    def test_get_client_ip_no_ip(self):
        """Test get_client_ip returns None when no IP is available."""
        request = self.factory.get("/test/")
        # RequestFactory sets REMOTE_ADDR to 127.0.0.1 by default, so we need to remove it
        if "REMOTE_ADDR" in request.META:
            del request.META["REMOTE_ADDR"]

        ip = self.model_admin.get_client_ip(request)
        self.assertIsNone(ip)

    def test_get_app_name(self):
        """Test get_app_name returns the correct app label."""
        app_name = self.model_admin.get_app_name()
        self.assertEqual(app_name, "sfd")

    @patch("sfd.views.common.upload.reverse", return_value="/test/testbasemodel/upload/")
    def test_get_context_data(self, mock_reverse):
        """Test get_context_data hides encoding field for Excel upload type."""

        context = self.model_admin.get_context_data()

        # Verify context structure
        self.assertIn("form", context)
        self.assertIn("upload_url", context)
        self.assertIn("upload_title", context)
        self.assertIn("upload_button_name", context)

    @patch("sfd.views.common.upload.reverse", return_value="/test/testbasemodel/upload/")
    def test_get_context_data_with_excel_upload_type(self, mock_reverse):
        """Test get_context_data hides encoding field for Excel upload type."""
        # Set upload type to Excel
        self.model_admin.upload_type = UploadType.EXCEL

        context = self.model_admin.get_context_data()

        # Verify context structure
        self.assertIn("form", context)
        self.assertIn("upload_url", context)
        self.assertIn("upload_title", context)
        self.assertIn("upload_button_name", context)

        # Verify encoding field is hidden for Excel
        form = context["form"]
        self.assertIsInstance(form.fields["encoding"].widget, forms.HiddenInput)

    @patch("sfd.views.common.upload.reverse", return_value="/test/testbasemodel/upload/")
    def test_get_context_data_with_custom_form(self, mock_reverse):
        """Test get_context_data uses provided form instead of creating new one."""
        # Create custom form
        custom_form = UploadForm(initial={"upload_type": UploadType.ZIP, "encoding": Encoding.SJIS})

        context = self.model_admin.get_context_data(form=custom_form)

        # Verify custom form is used
        self.assertEqual(context["form"], custom_form)
        self.assertEqual(context["form"].initial["upload_type"], UploadType.ZIP)
        self.assertEqual(context["form"].initial["encoding"], Encoding.SJIS)

    def test_get_model_unique_field_names_with_upload_model(self):
        """Test get_model_unique_field_names returns correct unique fields."""
        self.model_admin.upload_model = TestModel

        result = self.model_admin.get_model_unique_field_names()

        expected = []  # TestModel has no unique fields
        self.assertEqual(result, expected)

    def test_get_model_unique_field_names(self):
        """Test get_model_unique_field_names returns correct unique fields."""
        result = self.model_admin.get_model_unique_field_names()

        expected = []  # TestModel has no unique fields
        self.assertEqual(result, expected)

    def test_get_model_unique_field_names_with_unique_fields(self):
        """Test get_model_unique_field_names returns correct unique fields."""
        self.model_admin.model = TestBaseModel  # Has unique fields
        result = self.model_admin.get_model_unique_field_names()

        expected = ["name"]
        self.assertEqual(result, expected)

    @patch("sfd.views.common.upload.reverse", return_value="/test/testbasemodel/upload/")
    def test_upload_file_get_request(self, mock_reverse):
        """Test upload_file view with GET request returns form."""
        # Mock the render function to capture context
        with patch("sfd.views.common.upload.render") as mock_render:
            mock_render.return_value = HttpResponse("test response")

            self.model_admin.upload_file(self.request)

            # Verify render was called
            mock_render.assert_called_once()

            # Get the context that was passed to render
            args, kwargs = mock_render.call_args
            context = args[2]  # The context is the third argument to render

            self.assertIn("form", context)
            self.assertIn("upload_url", context)
            self.assertIsInstance(context["form"], UploadForm)

    @pytest.mark.django_db(databases=["default", "postgres"])
    @patch("sfd.views.common.upload.reverse", return_value="/admin/testmodel/upload/")
    @patch.object(TestModelAdmin, "_process_bulk_operations")
    def test_upload_file_post_csv(self, mock_process, mock_reverse):
        """Test upload_file view with successful POST request."""
        # Setup mocks
        self.model_admin.upload_column_names = ["name", "email"]

        # Create test CSV
        csv_content = "name,email\nJohn Doe,john@example.com"
        csv_file = create_test_csv_file(csv_content)

        # Create POST request
        request = self.factory.post("/admin/upload/", {"upload_type": UploadType.CSV, "encoding": Encoding.UTF8}, format="multipart")
        request.FILES["upload_file"] = csv_file
        request.user = self.user

        # Setup message storage for the request
        request.session = {}  # type: ignore[attr-defined]
        storage = FallbackStorage(request)
        request._messages = storage  # type: ignore[attr-defined]

        with translation.override("en"):
            # Test upload
            response = self.model_admin.upload_file(request)

            # Verify redirect
            self.assertEqual(response.status_code, 200)
            self.assertTrue(isinstance(response, HttpResponse))

            # Verify bulk_create was called
            mock_process.assert_called_once()
            self.assertEqual(len(self.model_admin._bulk_create_list), 1)

            # Verify success message was added
            messages = list(storage)
            self.assertEqual(len(messages), 1)
            self.assertIn("Uploaded test.csv successfully.", str(messages[0]))

    @pytest.mark.django_db(databases=["default", "postgres"])
    @patch("sfd.views.common.upload.reverse", return_value="/admin/testmodel/upload/")
    @patch.object(TestModelAdmin, "_process_bulk_operations")
    def test_upload_file_post_htmx(self, mock_process, mock_reverse):
        """Test upload_file view with successful POST request."""
        # Setup mocks
        self.model_admin.upload_column_names = ["name", "email"]

        # Create test CSV
        csv_content = "name,email\nJohn Doe,john@example.com"
        csv_file = create_test_csv_file(csv_content)

        # Create POST request
        request = self.factory.post("/admin/upload/", {"upload_type": UploadType.CSV, "encoding": Encoding.UTF8}, format="multipart")
        request.FILES["upload_file"] = csv_file
        request.user = self.user
        request.headers = {"HX-Request": "true"}  # Mark as HTMX request

        # Setup message storage for the request
        request.session = {}  # type: ignore[attr-defined]
        storage = FallbackStorage(request)
        request._messages = storage  # type: ignore[attr-defined]

        with translation.override("en"):
            # Test upload
            response = self.model_admin.upload_file(request)

            # Verify redirect
            self.assertEqual(response.status_code, 200)
            self.assertTrue(isinstance(response, HttpResponse))
            self.assertEqual(response["HX-Trigger"], "uploadSuccess")

            # Verify bulk_create was called
            mock_process.assert_called_once()
            self.assertEqual(len(self.model_admin._bulk_create_list), 1)

            # Verify success message was added
            messages = list(storage)
            self.assertEqual(len(messages), 1)
            self.assertIn("Uploaded test.csv successfully.", str(messages[0]))

    def test_upload_file_excel_upload_not_implemented(self):
        """Test excel_upload raises NotImplementedError."""
        with self.assertRaises(NotImplementedError):
            self.model_admin.excel_upload(self.request, Mock())

    @pytest.mark.django_db(databases=["default", "postgres"])
    @patch("sfd.views.common.upload.reverse", return_value="/admin/testmodel/upload/")
    @patch.object(TestModelAdmin, "excel_upload")
    def test_upload_file_excel(self, mock_excel_upload, mock_reverse):
        """Test Excel upload functionality."""
        # Create test CSV
        csv_content = "name,email\nJohn Doe,john@example.com"
        csv_file = create_test_csv_file(csv_content)

        # Create POST request
        request = self.factory.post("/admin/upload/", {"upload_type": UploadType.EXCEL, "encoding": Encoding.UTF8}, format="multipart")
        request.FILES["upload_file"] = csv_file
        request.user = self.user

        # Setup message storage for the request
        request.session = {}  # type: ignore[attr-defined]
        storage = FallbackStorage(request)
        request._messages = storage  # type: ignore[attr-defined]

        # Test upload
        self.model_admin.upload_file(request)

        # Verify excel upload is called
        mock_excel_upload.assert_called_once_with(request, csv_file)

    @pytest.mark.django_db(databases=["default", "postgres"])
    @patch("sfd.views.common.upload.reverse", return_value="/admin/testmodel/upload/")
    @patch.object(TestModelAdmin, "zip_upload")
    @patch.object(TestModelAdmin, "_process_bulk_operations")
    def test_zip_upload(self, mock_process, mock_zip_upload, mock_reverse):
        """Test Zip upload functionality."""

        self.model_admin.upload_column_names = ["name", "email"]

        # Create test CSV files in memory
        csv_content1 = "name,email\nTest1,test1@example.com"
        csv_content2 = "name,email\nTest2,test2@example.com"

        # Create temporary CSV files
        temp_dir = tempfile.mkdtemp()
        csv_file1 = os.path.join(temp_dir, "test1.csv")
        csv_file2 = os.path.join(temp_dir, "test2.csv")

        with open(csv_file1, "w", encoding="utf-8") as f:
            f.write(csv_content1)
        with open(csv_file2, "w", encoding="utf-8") as f:
            f.write(csv_content2)

        # Mock zip_upload to return the CSV file paths
        mock_zip_upload.return_value = [csv_file1, csv_file2]

        # Create a zip file for the request (content doesn't matter since we're mocking)
        zip_file = SimpleUploadedFile("test.zip", b"dummy content", content_type="application/zip")

        # Create POST request
        request = self.factory.post(
            "/admin/upload/",
            {
                "upload_type": UploadType.ZIP,
                "encoding": Encoding.UTF8,
            },
            format="multipart",
        )
        request.FILES["upload_file"] = zip_file
        request.user = self.user

        # Setup message storage for the request
        request.session = {}  # type: ignore[attr-defined]
        storage = FallbackStorage(request)
        request._messages = storage  # type: ignore[attr-defined]

        # Setup mock side effect to simulate inserting records
        def side_effect(request, upload_fields):
            self.model_admin._total_inserted += 1

        mock_process.side_effect = side_effect

        with translation.override("en"):
            # Test upload
            self.model_admin.upload_file(request)

            # Verify zip_upload was called
            mock_zip_upload.assert_called_once()

            # Verify _process_bulk_operations was called for each CSV file in the ZIP
            self.assertEqual(mock_process.call_count, 2)

            # Verify success message was added (one message for the entire ZIP file)
            messages = list(storage)
            self.assertEqual(len(messages), 1)
            self.assertIn("Uploaded test.zip successfully.", str(messages[0]))
            self.assertIn("Inserted: 2 rows", str(messages[0]))

    @pytest.mark.django_db(databases=["default", "postgres"])
    @patch("sfd.views.common.upload.reverse", return_value="/admin/testmodel/upload/")
    @patch.object(TestModelAdmin, "upload_data")
    def test_upload_file_exception_handling(self, mock_upload_data, mock_reverse):
        """Test upload_file handles exceptions properly."""
        self.model_admin.upload_column_names = ["name", "email"]

        # Mock upload_data to raise an exception
        mock_upload_data.side_effect = ValueError("Test error message")

        # Create test CSV
        csv_content = "name,email\nJohn Doe,john@example.com"
        csv_file = create_test_csv_file(csv_content)

        # Create POST request
        request = self.factory.post("/admin/upload/", {"upload_type": UploadType.CSV, "encoding": Encoding.UTF8}, format="multipart")
        request.FILES["upload_file"] = csv_file
        request.user = self.user

        # Setup message storage for the request
        request.session = {}  # type: ignore[attr-defined]
        storage = FallbackStorage(request)
        request._messages = storage  # type: ignore[attr-defined]

        with translation.override("en"):
            # Test upload
            response = self.model_admin.upload_file(request)

            # Verify response is still successful (error is handled gracefully)
            self.assertEqual(response.status_code, 200)

            # Verify error message was added
            messages = list(storage)
            self.assertGreaterEqual(len(messages), 1)

            # Check that an error message with error key was added
            error_messages = [str(m) for m in messages]
            self.assertTrue(
                any("An unexpected error has occurred" in msg and "error key" in msg for msg in error_messages),
                f"Expected error message not found. Messages: {error_messages}",
            )

    @pytest.mark.django_db(databases=["default", "postgres"])
    @patch("sfd.views.common.upload.reverse", return_value="/admin/testmodel/upload/")
    @patch.object(TestModelAdmin, "zip_upload")
    def test_upload_file_zip_no_csv_exception(self, mock_zip_upload, mock_reverse):
        """Test upload_file handles ZIP with no CSV files exception."""
        self.model_admin.upload_column_names = ["name", "email"]

        # Mock zip_upload to raise ValueError (no CSV files found)
        mock_zip_upload.side_effect = ValueError("No CSV files found in the ZIP archive.")

        # Create a dummy zip file
        zip_file = SimpleUploadedFile("test.zip", b"dummy content", content_type="application/zip")

        # Create POST request
        request = self.factory.post(
            "/admin/upload/",
            {
                "upload_type": UploadType.ZIP,
                "encoding": Encoding.UTF8,
            },
            format="multipart",
        )
        request.FILES["upload_file"] = zip_file
        request.user = self.user

        # Setup message storage for the request
        request.session = {}  # type: ignore[attr-defined]
        storage = FallbackStorage(request)
        request._messages = storage  # type: ignore[attr-defined]

        with translation.override("en"):
            # Test upload
            response = self.model_admin.upload_file(request)

            # Verify response is still successful (error is handled gracefully)
            self.assertEqual(response.status_code, 200)

            # Verify error message was added
            messages = list(storage)
            self.assertGreaterEqual(len(messages), 1)

            # Check that an error message with error key was added
            error_messages = [str(m) for m in messages]
            self.assertTrue(
                any("An unexpected error has occurred" in msg and "error key" in msg for msg in error_messages),
                f"Expected error message not found. Messages: {error_messages}",
            )

    @pytest.mark.django_db(databases=["default", "postgres"])
    @patch("sfd.views.common.upload.reverse", return_value="/admin/testmodel/upload/")
    @patch.object(TestModelAdmin, "_process_bulk_operations")
    def test_upload_file_creates_csv_log_success(self, mock_process, mock_reverse):
        """Test that upload_file creates a CSV log record on successful upload."""
        from sfd.models.csv_log import CsvLog, CsvProcessResult, CsvProcessType

        self.model_admin.upload_column_names = ["name", "email"]

        # Create test CSV
        csv_content = "name,email\nJohn Doe,john@example.com\nJane Smith,jane@example.com"
        csv_file = create_test_csv_file(csv_content)

        # Create POST request
        request = self.factory.post("/admin/upload/", {"upload_type": UploadType.CSV, "encoding": Encoding.UTF8}, format="multipart")
        request.FILES["upload_file"] = csv_file
        request.user = self.user
        request.META["REMOTE_ADDR"] = "127.0.0.1"

        # Setup message storage for the request
        request.session = {}  # type: ignore[attr-defined]
        storage = FallbackStorage(request)
        request._messages = storage  # type: ignore[attr-defined]

        with translation.override("en"):
            # Verify no CSV log records exist before upload
            self.assertEqual(CsvLog.objects.count(), 0)

            # Test upload
            response = self.model_admin.upload_file(request)

            # Verify response is successful
            self.assertEqual(response.status_code, 200)

            # Verify CSV log record was created
            self.assertEqual(CsvLog.objects.count(), 1)
            csv_log = CsvLog.objects.first()

            # Verify log record fields
            self.assertEqual(csv_log.process_type, CsvProcessType.UPLOAD)
            self.assertEqual(csv_log.process_result, CsvProcessResult.SUCCESS)
            self.assertEqual(csv_log.app_name, "sfd")
            self.assertEqual(csv_log.processed_by, self.user.username)
            self.assertEqual(csv_log.ip_address, "127.0.0.1")
            self.assertEqual(csv_log.file_name, "test.csv")
            self.assertEqual(csv_log.total_line, 2)  # Two data rows (excluding header)

    @pytest.mark.django_db(databases=["default", "postgres"])
    @patch("sfd.views.common.upload.reverse", return_value="/admin/testmodel/upload/")
    @patch.object(TestModelAdmin, "upload_data")
    def test_upload_file_creates_csv_log_failure(self, mock_upload_data, mock_reverse):
        """Test that upload_file creates a CSV log record on failed upload."""
        from sfd.models.csv_log import CsvLog, CsvProcessResult, CsvProcessType

        self.model_admin.upload_column_names = ["name", "email"]

        # Mock upload_data to raise an exception
        mock_upload_data.side_effect = ValueError("Test error")

        # Create test CSV
        csv_content = "name,email\nJohn Doe,john@example.com"
        csv_file = create_test_csv_file(csv_content)

        # Create POST request
        request = self.factory.post("/admin/upload/", {"upload_type": UploadType.CSV, "encoding": Encoding.UTF8}, format="multipart")
        request.FILES["upload_file"] = csv_file
        request.user = self.user
        request.META["REMOTE_ADDR"] = "192.168.1.100"

        # Setup message storage for the request
        request.session = {}  # type: ignore[attr-defined]
        storage = FallbackStorage(request)
        request._messages = storage  # type: ignore[attr-defined]

        with translation.override("en"):
            # Verify no CSV log records exist before upload
            self.assertEqual(CsvLog.objects.count(), 0)

            # Test upload
            response = self.model_admin.upload_file(request)

            # Verify response
            self.assertEqual(response.status_code, 200)

            # Verify CSV log record was created with failure status
            self.assertEqual(CsvLog.objects.count(), 1)
            csv_log = CsvLog.objects.first()

            # Verify log record fields
            self.assertEqual(csv_log.process_type, CsvProcessType.UPLOAD)
            self.assertEqual(csv_log.process_result, CsvProcessResult.FAILURE)
            self.assertEqual(csv_log.app_name, "sfd")
            self.assertEqual(csv_log.processed_by, self.user.username)
            self.assertEqual(csv_log.ip_address, "192.168.1.100")
            self.assertEqual(csv_log.file_name, "test.csv")
            self.assertEqual(csv_log.total_line, 0)  # No lines processed due to early failure

    @pytest.mark.django_db(databases=["default", "postgres"])
    def test_pre_upload(self):
        """Test pre_upload method does nothing by default."""
        TestModel.objects.create(name="Test 1", email="test1@example.com")
        self.model_admin.upload_model = TestModel

        self.model_admin.pre_upload(self.request)

        self.assertEqual(TestModel.objects.count(), 0)

    @patch("sfd.views.common.upload.settings.TEMP_DIR", tempfile.gettempdir())
    def test_zip_upload_extraction(self):
        """Test zip_upload method extracts CSV files correctly."""
        import io
        import zipfile

        # Create test CSV content
        csv_content1 = "name,email\nTest1,test1@example.com"
        csv_content2 = "name,email\nTest2,test2@example.com"

        # Create a zip file containing the CSV files
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("test1.csv", csv_content1)
            zf.writestr("test2.csv", csv_content2)
            zf.writestr("readme.txt", "This should be ignored")  # Non-CSV file
        zip_buffer.seek(0)

        # Create SimpleUploadedFile from buffer
        zip_file = SimpleUploadedFile("test.zip", zip_buffer.read(), content_type="application/zip")

        # Call zip_upload
        csv_files = self.model_admin.zip_upload(self.request, zip_file)

        # Verify results
        self.assertEqual(len(csv_files), 2, "Should extract exactly 2 CSV files")
        self.assertTrue(all(f.endswith(".csv") for f in csv_files), "All extracted files should be CSV files")

        # Verify files exist and have correct content
        for csv_file in csv_files:
            self.assertTrue(os.path.exists(csv_file), f"CSV file should exist: {csv_file}")
            with open(csv_file, encoding="utf-8") as f:
                content = f.read()
                self.assertIn("name,email", content)
                self.assertTrue("Test1" in content or "Test2" in content)

    def test_zip_upload_no_csv_files(self):
        """Test zip_upload raises ValueError when no CSV files are found."""
        import io
        import zipfile

        # Create a zip file with no CSV files
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("readme.txt", "No CSV files here")
            zf.writestr("data.json", '{"test": "data"}')
        zip_buffer.seek(0)

        # Create SimpleUploadedFile from buffer
        zip_file = SimpleUploadedFile("test.zip", zip_buffer.read(), content_type="application/zip")

        with translation.override("en"):
            # Call zip_upload and expect ValueError
            with self.assertRaises(ValueError) as context:
                self.model_admin.zip_upload(self.request, zip_file)

            self.assertIn("No CSV files found", str(context.exception))

    @patch("sfd.views.common.upload.settings.TEMP_DIR", tempfile.gettempdir())
    def test_zip_upload_nested_directories(self):
        """Test zip_upload handles CSV files in nested directories."""
        import io
        import zipfile

        # Create test CSV content
        csv_content = "name,email\nTest,test@example.com"

        # Create a zip file with nested directory structure
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("folder1/test1.csv", csv_content)
            zf.writestr("folder1/subfolder/test2.csv", csv_content)
            zf.writestr("folder2/test3.csv", csv_content)
        zip_buffer.seek(0)

        # Create SimpleUploadedFile from buffer
        zip_file = SimpleUploadedFile("test.zip", zip_buffer.read(), content_type="application/zip")

        # Call zip_upload
        csv_files = self.model_admin.zip_upload(self.request, zip_file)

        # Verify results
        self.assertEqual(len(csv_files), 3, "Should extract all CSV files from nested directories")
        self.assertTrue(all(f.endswith(".csv") for f in csv_files), "All extracted files should be CSV files")

    def test_get_csv_reader(self):
        """Test get_csv_reader returns a CSV reader with correct encoding."""
        self.model_admin.upload_column_names = ["name", "email"]

        # Create test CSV content
        csv_content = "name,email\nTest,test@example.com"
        csv_file = create_test_csv_file(csv_content)

        # Call get_csv_reader with correct parameter order: csv_file, encoding, request
        reader = self.model_admin.get_csv_reader(csv_file, Encoding.UTF8, self.request)
        # Verify reader content
        rows = list(reader)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0], {"name": "Test", "email": "test@example.com"})

    def test_get_csv_reader_with_file_path(self):
        """Test get_csv_reader with file path string instead of file object."""
        self.model_admin.upload_column_names = ["name", "email"]

        # Create a temporary CSV file on disk
        csv_content = "name,email\nJohn Doe,john@example.com\nJane Smith,jane@example.com"
        temp_dir = tempfile.mkdtemp()
        csv_file_path = os.path.join(temp_dir, "test.csv")

        with open(csv_file_path, "w", encoding="utf-8") as f:
            f.write(csv_content)

        try:
            # Call get_csv_reader with file path string
            reader = self.model_admin.get_csv_reader(csv_file_path, Encoding.UTF8, self.request)

            # Verify reader content
            rows = list(reader)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0], {"name": "John Doe", "email": "john@example.com"})
            self.assertEqual(rows[1], {"name": "Jane Smith", "email": "jane@example.com"})
        finally:
            # Clean up temporary file
            if os.path.exists(csv_file_path):
                os.remove(csv_file_path)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)

    @pytest.mark.django_db(databases=["default", "postgres"])
    @patch.object(TestModelAdmin, "_process_bulk_operations")
    def test_upload_data_creates_new_records(self, mock_process):
        """Test upload_data creates new records when no unique fields exist."""
        self.model_admin.upload_column_names = ["name", "email"]

        # Create CSV content
        csv_content = "name,email\nAlice,alice@example.com\nBob,bob@example.com"
        csv_file = create_test_csv_file(csv_content)

        # Call upload_data
        self.model_admin.upload_data(self.request, self.model_admin.get_csv_reader, csv_file, Encoding.UTF8, self.request)

        # Verify records were added to bulk_create_list
        self.assertEqual(len(self.model_admin._bulk_create_list), 2)
        self.assertEqual(self.model_admin._bulk_create_list[0].name, "Alice")
        self.assertEqual(self.model_admin._bulk_create_list[0].email, "alice@example.com")
        self.assertEqual(self.model_admin._bulk_create_list[1].name, "Bob")
        self.assertEqual(self.model_admin._bulk_create_list[1].email, "bob@example.com")

        # Verify _process_bulk_operations was called
        mock_process.assert_called_once()

    @pytest.mark.django_db(databases=["default", "postgres"])
    @patch.object(TestModelAdmin, "_process_bulk_operations")
    def test_upload_data_with_unique_fields_insert(self, mock_process):
        """Test upload_data inserts records with unique fields when they don't exist in DB."""
        self.model_admin.model = TestBaseModel
        self.model_admin.upload_column_names = ["name", "email"]

        # Create CSV content with unique name field
        csv_content = "name,email\nUniquePerson,unique@example.com"
        csv_file = create_test_csv_file(csv_content)

        # Call upload_data
        self.model_admin.upload_data(self.request, self.model_admin.get_csv_reader, csv_file, Encoding.UTF8, self.request)

        # Verify record was added to bulk_create_list
        self.assertEqual(len(self.model_admin._bulk_create_list), 1)
        self.assertEqual(self.model_admin._bulk_create_list[0].name, "UniquePerson")
        mock_process.assert_called_once()

    @pytest.mark.django_db(databases=["default", "postgres"])
    @patch.object(TestModelAdmin, "_process_bulk_operations")
    def test_upload_data_with_unique_fields_update(self, mock_process):
        """Test upload_data updates existing records when unique fields match."""
        self.model_admin.model = TestBaseModel
        self.model_admin.upload_column_names = ["name", "email"]
        self.model_admin.is_skip_existing = False

        # Create existing record
        TestBaseModel.objects.create(name="ExistingPerson", email="old@example.com")

        # Create CSV content with same unique name but different email
        csv_content = "name,email\nExistingPerson,new@example.com"
        csv_file = create_test_csv_file(csv_content)

        # Call upload_data
        self.model_admin.upload_data(self.request, self.model_admin.get_csv_reader, csv_file, Encoding.UTF8, self.request)

        # Verify record was added to bulk_update_list
        self.assertEqual(len(self.model_admin._bulk_update_list), 1)
        self.assertEqual(self.model_admin._bulk_update_list[0].name, "ExistingPerson")
        self.assertEqual(self.model_admin._bulk_update_list[0].email, "new@example.com")
        mock_process.assert_called_once()

    @pytest.mark.django_db(databases=["default", "postgres"])
    @patch.object(TestModelAdmin, "_process_bulk_operations")
    def test_upload_data_skip_existing_records(self, mock_process):
        """Test upload_data skips existing records when is_skip_existing is True."""
        self.model_admin.model = TestBaseModel
        self.model_admin.upload_column_names = ["name", "email"]
        self.model_admin.is_skip_existing = True

        # Create existing record
        TestBaseModel.objects.create(name="SkipPerson", email="skip@example.com")

        # Create CSV content with same unique name
        csv_content = "name,email\nSkipPerson,newemail@example.com"
        csv_file = create_test_csv_file(csv_content)

        # Call upload_data
        self.model_admin.upload_data(self.request, self.model_admin.get_csv_reader, csv_file, Encoding.UTF8, self.request)

        # Verify no records were added to either list
        self.assertEqual(len(self.model_admin._bulk_create_list), 0)
        self.assertEqual(len(self.model_admin._bulk_update_list), 0)

    @pytest.mark.django_db(databases=["default", "postgres"])
    @patch.object(TestModelAdmin, "_process_bulk_operations")
    def test_upload_data_with_upload_model(self, mock_process):
        """Test upload_data uses upload_model when specified."""
        self.model_admin.upload_model = TestModel
        self.model_admin.upload_column_names = ["name", "email"]

        # Create CSV content
        csv_content = "name,email\nModelTest,model@example.com"
        csv_file = create_test_csv_file(csv_content)

        # Call upload_data
        self.model_admin.upload_data(self.request, self.model_admin.get_csv_reader, csv_file, Encoding.UTF8, self.request)

        # Verify record was created with upload_model
        self.assertEqual(len(self.model_admin._bulk_create_list), 1)
        self.assertIsInstance(self.model_admin._bulk_create_list[0], TestModel)
        self.assertEqual(self.model_admin._bulk_create_list[0].name, "ModelTest")
        mock_process.assert_called_once()

    @pytest.mark.django_db(databases=["default", "postgres"])
    @patch.object(TestModelAdmin, "_process_bulk_operations")
    def test_upload_data_chunk_processing(self, mock_process):
        """Test upload_data processes records in chunks."""
        self.model_admin.upload_column_names = ["name", "email"]
        self.model_admin.chunk_size = 2  # Set small chunk size for testing

        # Create CSV with 5 records (will trigger chunking)
        csv_content = "name,email\n"
        csv_content += "\n".join([f"Person{i},person{i}@example.com" for i in range(5)])
        csv_file = create_test_csv_file(csv_content)

        # Call upload_data
        self.model_admin.upload_data(self.request, self.model_admin.get_csv_reader, csv_file, Encoding.UTF8, self.request)

        # Verify _process_bulk_operations was called multiple times (for chunks + final)
        # With 5 records and chunk_size=2: called at 2, 4, and final
        self.assertEqual(mock_process.call_count, 3)

    @pytest.mark.django_db(databases=["default", "postgres"])
    @patch.object(TestModelAdmin, "_process_bulk_operations")
    def test_upload_data_empty_row_handling(self, mock_process):
        """Test upload_data processes rows even with empty values."""
        self.model_admin.upload_column_names = ["name", "email"]

        # Create CSV with row that has empty values
        csv_content = "name,email\nAlice,alice@example.com\n,\nBob,bob@example.com"
        csv_file = create_test_csv_file(csv_content)

        # Call upload_data
        self.model_admin.upload_data(self.request, self.model_admin.get_csv_reader, csv_file, Encoding.UTF8, self.request)

        # Verify all rows were processed (even those with empty values)
        # CSV DictReader treats empty lines as rows with empty string values
        self.assertEqual(len(self.model_admin._bulk_create_list), 3)
        self.assertEqual(self.model_admin._bulk_create_list[0].name, "Alice")
        self.assertEqual(self.model_admin._bulk_create_list[1].name, "")  # Empty name
        self.assertEqual(self.model_admin._bulk_create_list[2].name, "Bob")

    @pytest.mark.django_db(databases=["default", "postgres"])
    def test_upload_data_missing_unique_fields_error(self):
        """Test upload_data raises error when unique fields are missing from row."""
        self.model_admin.model = TestBaseModel
        self.model_admin.upload_column_names = ["email"]  # Missing 'name' which is unique

        # Create CSV without unique field
        csv_content = "email\nmissing@example.com"
        csv_file = create_test_csv_file(csv_content)

        # Call upload_data and expect ValueError
        with self.assertRaises(ValueError) as context:
            self.model_admin.upload_data(self.request, self.model_admin.get_csv_reader, csv_file, Encoding.UTF8, self.request)

        self.assertIn("missing required unique fields", str(context.exception))

    @pytest.mark.django_db(databases=["default", "postgres"])
    def test_upload_data_no_valid_data_error(self):
        """Test upload_data raises error when row has no valid data."""
        self.model_admin.upload_column_names = ["name", "email"]

        # Mock convert2upload_fields to return empty dict
        with patch.object(self.model_admin, "convert2upload_fields", return_value={}):
            csv_content = "name,email\nTest,test@example.com"
            csv_file = create_test_csv_file(csv_content)

            # Call upload_data and expect ValueError
            with self.assertRaises(ValueError) as context, translation.override("en"):
                self.model_admin.upload_data(self.request, self.model_admin.get_csv_reader, csv_file, Encoding.UTF8, self.request)

                self.assertIn("No valid data found in the row", str(context.exception))

    @pytest.mark.django_db(databases=["default", "postgres"])
    @patch.object(TestModelAdmin, "_process_bulk_operations")
    def test_upload_data_duplicate_in_csv(self, mock_process):
        """Test upload_data handles duplicate unique values within the same CSV."""
        self.model_admin.model = TestBaseModel
        self.model_admin.upload_column_names = ["name", "email"]

        # Create CSV with duplicate unique name
        csv_content = "name,email\nDuplicate,first@example.com\nDuplicate,second@example.com"
        csv_file = create_test_csv_file(csv_content)

        # Call upload_data
        self.model_admin.upload_data(self.request, self.model_admin.get_csv_reader, csv_file, Encoding.UTF8, self.request)

        # Verify only first occurrence was added (second is skipped due to _uploaded_unique_values)
        self.assertEqual(len(self.model_admin._bulk_create_list), 1)
        self.assertEqual(self.model_admin._bulk_create_list[0].name, "Duplicate")
        self.assertEqual(self.model_admin._bulk_create_list[0].email, "first@example.com")

    @pytest.mark.django_db(databases=["default", "postgres"])
    def test_process_bulk_operations_create_only(self):
        """Test _process_bulk_operations with only create operations."""
        self.model_admin.upload_column_names = ["name", "email"]
        upload_fields = self.model_admin.get_upload_db_fields(self.request)

        # Add records to bulk_create_list
        self.model_admin._bulk_create_list = [
            TestModel(name="Person1", email="person1@example.com"),
            TestModel(name="Person2", email="person2@example.com"),
        ]

        # Call _process_bulk_operations
        self.model_admin._process_bulk_operations(self.request, upload_fields)

        # Verify records were inserted
        self.assertEqual(self.model_admin._total_inserted, 2)
        self.assertEqual(self.model_admin._total_updated, 0)
        self.assertEqual(len(self.model_admin._bulk_create_list), 0)  # List cleared
        self.assertEqual(TestModel.objects.count(), 2)

    @pytest.mark.django_db(databases=["default", "postgres"])
    def test_process_bulk_operations_update_only(self):
        """Test _process_bulk_operations with only update operations."""
        self.model_admin.model = TestBaseModel
        self.model_admin.upload_column_names = ["name", "email"]
        upload_fields = self.model_admin.get_upload_db_fields(self.request)

        # Create existing records
        record1 = TestBaseModel.objects.create(name="Person1", email="old1@example.com")
        record2 = TestBaseModel.objects.create(name="Person2", email="old2@example.com")

        # Update records
        record1.email = "new1@example.com"
        record2.email = "new2@example.com"

        # Add to bulk_update_list
        self.model_admin._bulk_update_list = [record1, record2]

        # Call _process_bulk_operations
        self.model_admin._process_bulk_operations(self.request, upload_fields)

        # Verify records were updated
        self.assertEqual(self.model_admin._total_inserted, 0)
        self.assertEqual(self.model_admin._total_updated, 2)
        self.assertEqual(len(self.model_admin._bulk_update_list), 0)  # List cleared

        # Verify database changes
        record1.refresh_from_db()
        record2.refresh_from_db()
        self.assertEqual(record1.email, "new1@example.com")
        self.assertEqual(record2.email, "new2@example.com")

    @pytest.mark.django_db(databases=["default", "postgres"])
    def test_process_bulk_operations_mixed(self):
        """Test _process_bulk_operations with both create and update operations."""
        self.model_admin.model = TestBaseModel
        self.model_admin.upload_column_names = ["name", "email"]
        upload_fields = self.model_admin.get_upload_db_fields(self.request)

        # Create existing record
        existing = TestBaseModel.objects.create(name="Existing", email="old@example.com")
        existing.email = "updated@example.com"

        # Setup lists
        self.model_admin._bulk_create_list = [TestBaseModel(name="New1", email="new1@example.com")]
        self.model_admin._bulk_update_list = [existing]

        # Call _process_bulk_operations
        self.model_admin._process_bulk_operations(self.request, upload_fields)

        # Verify counts
        self.assertEqual(self.model_admin._total_inserted, 1)
        self.assertEqual(self.model_admin._total_updated, 1)
        self.assertEqual(TestBaseModel.objects.count(), 2)

    @pytest.mark.django_db(databases=["default", "postgres"])
    def test_process_bulk_operations_with_upload_model(self):
        """Test _process_bulk_operations uses upload_model when specified."""
        self.model_admin.upload_model = TestModel
        self.model_admin.upload_column_names = ["name", "email"]
        upload_fields = self.model_admin.get_upload_db_fields(self.request)

        # Add records to bulk_create_list
        self.model_admin._bulk_create_list = [TestModel(name="Test1", email="test1@example.com")]

        # Call _process_bulk_operations
        self.model_admin._process_bulk_operations(self.request, upload_fields)

        # Verify record was created using upload_model
        self.assertEqual(self.model_admin._total_inserted, 1)
        self.assertEqual(TestModel.objects.count(), 1)

    def test_convert2upload_fields_basic(self):
        """Test convert2upload_fields with basic string fields."""
        self.model_admin.upload_column_names = ["name", "email"]
        upload_fields = self.model_admin.get_upload_db_fields(self.request)

        row_dict = {"name": "John Doe", "email": "john@example.com", "extra_field": "ignored"}

        result = self.model_admin.convert2upload_fields(self.request, row_dict, upload_fields)

        self.assertEqual(result, {"name": "John Doe", "email": "john@example.com"})
        self.assertNotIn("extra_field", result)

    def test_convert2upload_fields_date_field(self):
        """Test convert2upload_fields with DateField conversion."""
        self.model_admin.model = TestBaseModel
        self.model_admin.upload_column_names = ["name", "date"]
        upload_fields = self.model_admin.get_upload_db_fields(self.request)

        # Test with string date
        row_dict = {"name": "Test", "date": "2024-12-25"}
        result = self.model_admin.convert2upload_fields(self.request, row_dict, upload_fields)
        self.assertEqual(result["date"], date(2024, 12, 25))

        # Test with slash format
        row_dict = {"name": "Test", "date": "2024/12/25"}
        result = self.model_admin.convert2upload_fields(self.request, row_dict, upload_fields)
        self.assertEqual(result["date"], date(2024, 12, 25))

        # Test with empty value
        row_dict = {"name": "Test", "date": ""}
        result = self.model_admin.convert2upload_fields(self.request, row_dict, upload_fields)
        self.assertIsNone(result["date"])

    def test_convert2upload_fields_date_field_error(self):
        """Test convert2upload_fields raises error for invalid date."""
        self.model_admin.model = TestBaseModel
        self.model_admin.upload_column_names = ["name", "date"]
        upload_fields = self.model_admin.get_upload_db_fields(self.request)

        row_dict = {"name": "Test", "date": "invalid-date"}

        with self.assertRaises(ValueError) as context:
            self.model_admin.convert2upload_fields(self.request, row_dict, upload_fields)

        self.assertIn("Invalid value", str(context.exception))
        self.assertIn("should be a datetime", str(context.exception))

    def test_convert2upload_fields_boolean_field(self):
        """Test convert2upload_fields with BooleanField conversion."""
        self.model_admin.model = TestModel
        self.model_admin.upload_column_names = ["name", "is_active"]
        upload_fields = self.model_admin.get_upload_db_fields(self.request)

        # Test with string "true"
        row_dict = {"name": "Test", "is_active": "true"}
        result = self.model_admin.convert2upload_fields(self.request, row_dict, upload_fields)
        self.assertTrue(result["is_active"])

        # Test with string "false"
        row_dict = {"name": "Test", "is_active": "false"}
        result = self.model_admin.convert2upload_fields(self.request, row_dict, upload_fields)
        self.assertFalse(result["is_active"])

        # Test with string "0"
        row_dict = {"name": "Test", "is_active": "0"}
        result = self.model_admin.convert2upload_fields(self.request, row_dict, upload_fields)
        self.assertFalse(result["is_active"])

        # Test with empty string
        row_dict = {"name": "Test", "is_active": ""}
        result = self.model_admin.convert2upload_fields(self.request, row_dict, upload_fields)
        self.assertFalse(result["is_active"])

        # Test with integer 1
        row_dict = {"name": "Test", "is_active": 1}
        result = self.model_admin.convert2upload_fields(self.request, row_dict, upload_fields)
        self.assertTrue(result["is_active"])

        # Test with integer 0
        row_dict = {"name": "Test", "is_active": 0}
        result = self.model_admin.convert2upload_fields(self.request, row_dict, upload_fields)
        self.assertFalse(result["is_active"])

    def test_convert2upload_fields_ignores_unknown_fields(self):
        """Test convert2upload_fields ignores fields not in upload_fields."""
        self.model_admin.upload_column_names = ["name"]
        upload_fields = self.model_admin.get_upload_db_fields(self.request)

        row_dict = {"name": "Test", "email": "test@example.com", "unknown": "value"}

        result = self.model_admin.convert2upload_fields(self.request, row_dict, upload_fields)

        self.assertEqual(result, {"name": "Test"})
        self.assertNotIn("email", result)
        self.assertNotIn("unknown", result)

    @pytest.mark.django_db(databases=["default", "postgres"])
    @patch("sfd.views.common.upload.reverse", return_value="/admin/testmodel/upload/")
    def test_changelist_view(self, mock_reverse):
        """Test changelist_view adds upload URL to context."""
        # Call changelist_view
        response = self.model_admin.changelist_view(self.request)

        # Verify response is returned
        self.assertIsNotNone(response)

        # Verify context contains download-related variables
        context = response.context_data

        # Verify extra_context was passed
        self.assertIn("upload_url", context)
        self.assertIn("upload_button_name", context)
        self.assertEqual(context["upload_url"], "/admin/testmodel/upload/")

    @patch("sfd.views.common.upload.reverse", return_value="/admin/testmodel/upload/")
    def test_upload_file_post_invalid_form(self, mock_reverse):
        """Test upload_file with invalid POST request (no file)."""
        # Create POST request without file
        request = self.factory.post("/admin/upload/", {"upload_type": UploadType.CSV, "encoding": Encoding.UTF8})
        request.user = self.user

        # Setup message storage
        request.session = {}  # type: ignore[attr-defined]
        storage = FallbackStorage(request)
        request._messages = storage  # type: ignore[attr-defined]

        # Test upload with invalid form (missing file)
        response = self.model_admin.upload_file(request)

        # Verify response is returned
        self.assertEqual(response.status_code, 200)

    @pytest.mark.django_db(databases=["default", "postgres"])
    @patch("sfd.views.common.upload.reverse", return_value="/admin/testmodel/upload/")
    def test_upload_file_exception(self, mock_reverse):
        self.model_admin.upload_column_names = ["name", "email"]

        # Mock upload_data to raise an exception
        with patch.object(self.model_admin, "upload_data", side_effect=ValueError("Test debug error")):
            csv_content = "name,email\nJohn,john@example.com"
            csv_file = create_test_csv_file(csv_content)

            # Create POST request
            request = self.factory.post("/admin/upload/", {"upload_type": UploadType.CSV, "encoding": Encoding.UTF8}, format="multipart")
            request.FILES["upload_file"] = csv_file
            request.user = self.user

            # Setup message storage
            request.session = {}  # type: ignore[attr-defined]
            storage = FallbackStorage(request)
            request._messages = storage  # type: ignore[attr-defined]

            with translation.override("en"):
                # Test upload
                response = self.model_admin.upload_file(request)

                # Verify response
                self.assertEqual(response.status_code, 200)

                # Verify error messages
                messages = list(storage)
                self.assertGreaterEqual(len(messages), 1)
                self.assertIn("An unexpected error has occurred", str(messages[0]))

    @pytest.mark.django_db(databases=["default", "postgres"])
    @patch("sfd.views.common.upload.reverse", return_value="/admin/testmodel/upload/")
    def test_upload_file_exception_with_htmx_error(self, mock_reverse):
        """Test upload_file exception handling with HTMX request."""
        self.model_admin.upload_column_names = ["name", "email"]

        # Mock upload_data to raise an exception
        with patch.object(self.model_admin, "upload_data", side_effect=ValueError("Test HTMX error")):
            csv_content = "name,email\nJohn,john@example.com"
            csv_file = create_test_csv_file(csv_content)

            # Create HTMX POST request
            request = self.factory.post("/admin/upload/", {"upload_type": UploadType.CSV, "encoding": Encoding.UTF8}, format="multipart")
            request.FILES["upload_file"] = csv_file
            request.user = self.user
            request.headers = {"HX-Request": "true"}  # Mark as HTMX request

            # Setup message storage
            request.session = {}  # type: ignore[attr-defined]
            storage = FallbackStorage(request)
            request._messages = storage  # type: ignore[attr-defined]

            with translation.override("en"):
                # Test upload
                response = self.model_admin.upload_file(request)

                # Verify response
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response["HX-Trigger"], "uploadError")

    def test_convert2upload_fields_datetime_field(self):
        """Test convert2upload_fields with DateTimeField conversion."""
        from datetime import datetime

        # Mock a DateTimeField
        mock_field = Mock()
        mock_field.get_internal_type.return_value = "DateTimeField"

        upload_fields = {"datetime_field": mock_field}

        # Test with string datetime
        row_dict = {"datetime_field": "2024-12-25 10:30:00"}
        result = self.model_admin.convert2upload_fields(self.request, row_dict, upload_fields)
        self.assertEqual(result["datetime_field"], datetime(2024, 12, 25, 10, 30, 0))

        # Test with empty value
        row_dict = {"datetime_field": ""}
        result = self.model_admin.convert2upload_fields(self.request, row_dict, upload_fields)
        self.assertIsNone(result["datetime_field"])

        # Test with datetime object
        dt = datetime(2024, 12, 25, 10, 30, 0)
        row_dict = {"datetime_field": dt}
        result = self.model_admin.convert2upload_fields(self.request, row_dict, upload_fields)
        self.assertEqual(result["datetime_field"], dt)

        # Test with various datetime formats
        test_formats = [
            ("2024-12-25 10:30", datetime(2024, 12, 25, 10, 30)),
            ("2024-12-25 10:30:00.123456", datetime(2024, 12, 25, 10, 30, 0, 123456)),
            ("2024-12-25", datetime(2024, 12, 25, 0, 0, 0)),
        ]
        for date_str, expected in test_formats:
            row_dict = {"datetime_field": date_str}
            result = self.model_admin.convert2upload_fields(self.request, row_dict, upload_fields)
            self.assertEqual(result["datetime_field"], expected)

    def test_convert2upload_fields_datetime_field_error(self):
        """Test convert2upload_fields raises error for invalid datetime."""
        # Mock a DateTimeField
        mock_field = Mock()
        mock_field.get_internal_type.return_value = "DateTimeField"

        upload_fields = {"datetime_field": mock_field}

        # Test with invalid datetime string
        row_dict = {"datetime_field": "invalid-datetime"}
        with self.assertRaises(ValueError) as context:
            self.model_admin.convert2upload_fields(self.request, row_dict, upload_fields)
        self.assertIn("Invalid value", str(context.exception))

        # Test with invalid type
        row_dict = {"datetime_field": 12345}
        with self.assertRaises(ValueError) as context:
            self.model_admin.convert2upload_fields(self.request, row_dict, upload_fields)
        self.assertIn("Invalid value", str(context.exception))

    def test_convert2upload_fields_time_field(self):
        """Test convert2upload_fields with TimeField conversion."""
        from datetime import time

        # Mock a TimeField
        mock_field = Mock()
        mock_field.get_internal_type.return_value = "TimeField"

        upload_fields = {"time_field": mock_field}

        # Test with string time
        row_dict = {"time_field": "10:30:45"}
        result = self.model_admin.convert2upload_fields(self.request, row_dict, upload_fields)
        self.assertEqual(result["time_field"], time(10, 30, 45))

        # Test with empty value
        row_dict = {"time_field": ""}
        result = self.model_admin.convert2upload_fields(self.request, row_dict, upload_fields)
        self.assertIsNone(result["time_field"])

        # Test with time object
        t = time(10, 30, 45)
        row_dict = {"time_field": t}
        result = self.model_admin.convert2upload_fields(self.request, row_dict, upload_fields)
        self.assertEqual(result["time_field"], t)

        # Test with short format
        row_dict = {"time_field": "10:30"}
        result = self.model_admin.convert2upload_fields(self.request, row_dict, upload_fields)
        self.assertEqual(result["time_field"], time(10, 30, 0))

    def test_convert2upload_fields_time_field_error(self):
        """Test convert2upload_fields raises error for invalid time."""
        # Mock a TimeField
        mock_field = Mock()
        mock_field.get_internal_type.return_value = "TimeField"

        upload_fields = {"time_field": mock_field}

        # Test with invalid time string
        row_dict = {"time_field": "invalid-time"}
        with self.assertRaises(ValueError) as context:
            self.model_admin.convert2upload_fields(self.request, row_dict, upload_fields)
        self.assertIn("Invalid value", str(context.exception))

        # Test with invalid type
        row_dict = {"time_field": 12345}
        with self.assertRaises(ValueError) as context:
            self.model_admin.convert2upload_fields(self.request, row_dict, upload_fields)
        self.assertIn("Invalid value", str(context.exception))

    def test_convert2upload_fields_duration_field(self):
        """Test convert2upload_fields with DurationField conversion."""
        from datetime import timedelta

        # Mock a DurationField
        mock_field = Mock()
        mock_field.get_internal_type.return_value = "DurationField"

        upload_fields = {"duration_field": mock_field}

        # Test with string duration
        row_dict = {"duration_field": "10:30:45"}
        result = self.model_admin.convert2upload_fields(self.request, row_dict, upload_fields)
        self.assertEqual(result["duration_field"], timedelta(hours=10, minutes=30, seconds=45))

        # Test with empty value
        row_dict = {"duration_field": ""}
        result = self.model_admin.convert2upload_fields(self.request, row_dict, upload_fields)
        self.assertIsNone(result["duration_field"])

        # Test with timedelta object
        td = timedelta(hours=10, minutes=30, seconds=45)
        row_dict = {"duration_field": td}
        result = self.model_admin.convert2upload_fields(self.request, row_dict, upload_fields)
        self.assertEqual(result["duration_field"], td)

    def test_convert2upload_fields_duration_field_error(self):
        """Test convert2upload_fields raises error for invalid duration."""
        # Mock a DurationField
        mock_field = Mock()
        mock_field.get_internal_type.return_value = "DurationField"

        upload_fields = {"duration_field": mock_field}

        # Test with invalid type
        row_dict = {"duration_field": 12345}
        with self.assertRaises(ValueError) as context:
            self.model_admin.convert2upload_fields(self.request, row_dict, upload_fields)
        self.assertIn("Invalid value", str(context.exception))

    def test_convert2upload_fields_boolean_field_none(self):
        """Test convert2upload_fields with BooleanField None value."""
        self.model_admin.model = TestModel
        self.model_admin.upload_column_names = ["name", "is_active"]
        upload_fields = self.model_admin.get_upload_db_fields(self.request)

        # Test with None value
        row_dict = {"name": "Test", "is_active": None}
        result = self.model_admin.convert2upload_fields(self.request, row_dict, upload_fields)
        self.assertIsNone(result["is_active"])

    def test_convert2upload_fields_date_instance_and_errors(self):
        """Test convert2upload_fields with date instance and error cases."""
        self.model_admin.model = TestBaseModel
        self.model_admin.upload_column_names = ["name", "date"]
        upload_fields = self.model_admin.get_upload_db_fields(self.request)

        # Test with date instance
        test_date = date(2024, 12, 25)
        row_dict = {"name": "Test", "date": test_date}
        result = self.model_admin.convert2upload_fields(self.request, row_dict, upload_fields)
        self.assertEqual(result["date"], test_date)

        # Test with invalid type
        row_dict = {"name": "Test", "date": 12345}
        with self.assertRaises(ValueError) as context:
            self.model_admin.convert2upload_fields(self.request, row_dict, upload_fields)
        self.assertIn("Invalid value", str(context.exception))

    @pytest.mark.django_db(databases=["default", "postgres"])
    @patch.object(TestModelAdmin, "_process_bulk_operations")
    def test_upload_data_with_continue_on_empty_row(self, mock_process):
        """Test upload_data continues when row is empty."""
        self.model_admin.upload_column_names = ["name", "email"]

        # Mock a CSV reader that returns None/empty rows
        def mock_csv_reader(*args, **kwargs):
            """Generator that yields empty and non-empty rows."""
            yield None  # Empty row (should be skipped)
            yield {"name": "Alice", "email": "alice@example.com"}
            yield {}  # Empty dict (should be skipped)
            yield {"name": "Bob", "email": "bob@example.com"}
            yield False  # Falsy value (should be skipped)
            yield {"name": "Charlie", "email": "charlie@example.com"}

        # Call upload_data with mock reader
        self.model_admin.upload_data(self.request, mock_csv_reader, None, Encoding.UTF8, self.request)

        # Only non-empty rows should be processed (3 records)
        self.assertEqual(len(self.model_admin._bulk_create_list), 3)
        self.assertEqual(self.model_admin._bulk_create_list[0].name, "Alice")
        self.assertEqual(self.model_admin._bulk_create_list[1].name, "Bob")
        self.assertEqual(self.model_admin._bulk_create_list[2].name, "Charlie")

    @pytest.mark.django_db(databases=["default", "postgres"])
    def test_process_bulk_operations_with_upload_model_update(self):
        """Test _process_bulk_operations with upload_model for update operations."""
        self.model_admin.model = TestModel
        self.model_admin.upload_model = TestModel
        self.model_admin.upload_column_names = ["name", "email"]
        upload_fields = self.model_admin.get_upload_db_fields(self.request)

        # Create existing record
        record1 = TestModel.objects.create(name="Person1", email="old1@example.com")
        record1.email = "new1@example.com"

        # Add to bulk_update_list
        self.model_admin._bulk_update_list = [record1]

        # Call _process_bulk_operations
        self.model_admin._process_bulk_operations(self.request, upload_fields)

        # Verify record was updated
        self.assertEqual(self.model_admin._total_updated, 1)
        self.assertEqual(len(self.model_admin._bulk_update_list), 0)

        # Verify database changes
        record1.refresh_from_db()
        self.assertEqual(record1.email, "new1@example.com")


@pytest.mark.unit
@pytest.mark.upload
class BaseModelUploadMixinTest(BaseTestMixin, TestCase):
    """Test BaseModelUploadMixin functionality with comprehensive coverage."""

    databases = ["default", "postgres"]

    def setUp(self):
        """Set up test environment with model admin instance."""
        super().setUp()
        self.admin_site = AdminSite()
        self.model_admin = TestBaseModelAdmin(TestBaseModel, self.admin_site)

        self.request = self.factory.get("/admin/")
        self.request.user = self.user

        self.model_admin._bulk_create_list = []
        self.model_admin._bulk_update_list = []
        self.model_admin._uploaded_unique_values = set()  # 今回アップロードしたCSVのユニーク値
        self.model_admin._total_inserted = 0  # Track total inserted across chunks
        self.model_admin._total_updated = 0  # Track total updated across chunks
        self.model_admin._upload_datetime = timezone.now()

    def test_get_upload_column_names_includes_base_model_fields(self):
        """Test get_upload_column_names includes BaseModel fields at the end."""
        self.model_admin.upload_column_names = ["name", "email"]

        result = self.model_admin.get_upload_column_names(self.request)

        # Should include user-defined fields first, then BaseModel fields
        self.assertIn("name", result)
        self.assertIn("email", result)
        self.assertIn("created_at", result)
        self.assertIn("updated_at", result)
        self.assertIn("created_by", result)
        self.assertIn("updated_by", result)

        # BaseModel fields should be at the end
        base_model_fields = ["created_at", "updated_at", "created_by", "updated_by", "delete_flg"]
        user_fields = ["name", "email"]
        for user_field in user_fields:
            user_field_index = result.index(user_field)
            for base_field in base_model_fields:
                if base_field in result:
                    base_field_index = result.index(base_field)
                    self.assertLess(user_field_index, base_field_index, f"{user_field} should come before {base_field}")

    def test_get_upload_column_names_removes_duplicate_base_model_fields(self):
        """Test get_upload_column_names removes duplicate BaseModel fields."""
        # Set upload_column_names with BaseModel fields already included
        self.model_admin.upload_column_names = ["name", "email", "created_at", "created_by"]

        result = self.model_admin.get_upload_column_names(self.request)

        # Should have each field only once
        self.assertEqual(result.count("created_at"), 1, "created_at should appear only once")
        self.assertEqual(result.count("created_by"), 1, "created_by should appear only once")
        self.assertIn("name", result)
        self.assertIn("email", result)

    def test_get_upload_column_names_with_upload_model(self):
        """Test get_upload_column_names with upload_model specified."""
        self.model_admin.upload_model = TestBaseModel

        result = self.model_admin.get_upload_column_names(self.request)

        # Should include all fields from TestBaseModel
        self.assertIn("name", result)
        self.assertIn("email", result)
        # BaseModel fields should be moved to the end
        self.assertIn("created_at", result)
        self.assertIn("updated_at", result)

    def test_convert2upload_fields_adds_created_by(self):
        """Test convert2upload_fields adds created_by from request user."""
        # Set initial column names, then get the full list with BaseModel fields
        self.model_admin.upload_column_names = ["name", "email"]
        column_names = self.model_admin.get_upload_column_names(self.request)
        self.assertIn("created_by", column_names, "created_by should be in column names")
        self.assertIn("name", column_names, "name should be in column names")
        self.assertIn("email", column_names, "email should be in column names")

        self.model_admin.upload_column_names = column_names
        upload_fields = self.model_admin.get_upload_db_fields(self.request)
        self.assertIn("created_by", upload_fields, "created_by should be in upload_fields")

        row_dict = {"name": "Test User", "email": "test@example.com"}
        result = self.model_admin.convert2upload_fields(self.request, row_dict, upload_fields)

        self.assertEqual(result["name"], "Test User")
        self.assertEqual(result["email"], "test@example.com")
        self.assertEqual(result["created_by"], self.user.username)

    def test_convert2upload_fields_adds_updated_by(self):
        """Test convert2upload_fields adds updated_by from request user."""
        self.model_admin.upload_column_names = ["name", "email"]
        column_names = self.model_admin.get_upload_column_names(self.request)
        self.model_admin.upload_column_names = column_names
        upload_fields = self.model_admin.get_upload_db_fields(self.request)

        row_dict = {"name": "Test User", "email": "test@example.com"}
        result = self.model_admin.convert2upload_fields(self.request, row_dict, upload_fields)

        self.assertEqual(result["updated_by"], self.user.username)

    def test_convert2upload_fields_preserves_existing_created_by(self):
        """Test convert2upload_fields preserves existing created_by if present."""
        self.model_admin.upload_column_names = ["name", "email", "created_by"]
        upload_fields = self.model_admin.get_upload_db_fields(self.request)

        row_dict = {"name": "Test User", "email": "test@example.com", "created_by": "original_user"}
        result = self.model_admin.convert2upload_fields(self.request, row_dict, upload_fields)

        # Should preserve the original created_by value
        self.assertEqual(result["created_by"], "original_user")

    def test_convert2upload_fields_overwrites_updated_by(self):
        """Test convert2upload_fields always overwrites updated_by with current user."""
        self.model_admin.upload_column_names = ["name", "email", "updated_by"]
        upload_fields = self.model_admin.get_upload_db_fields(self.request)

        row_dict = {"name": "Test User", "email": "test@example.com", "updated_by": "original_updater"}
        result = self.model_admin.convert2upload_fields(self.request, row_dict, upload_fields)

        # Should overwrite with the current user (not preserve original value)
        self.assertEqual(result["updated_by"], self.user.username)

    def test_convert2upload_fields_handles_date_fields(self):
        """Test convert2upload_fields handles DateField conversion for BaseModel."""
        self.model_admin.upload_column_names = ["name", "date"]
        column_names = self.model_admin.get_upload_column_names(self.request)
        self.model_admin.upload_column_names = column_names
        upload_fields = self.model_admin.get_upload_db_fields(self.request)

        row_dict = {"name": "Test User", "date": "2024-12-25"}
        result = self.model_admin.convert2upload_fields(self.request, row_dict, upload_fields)

        self.assertEqual(result["date"], date(2024, 12, 25))
        self.assertEqual(result["created_by"], self.user.username)
        self.assertEqual(result["updated_by"], self.user.username)

    def test_convert2upload_fields_handles_boolean_fields(self):
        """Test convert2upload_fields handles BooleanField conversion for BaseModel."""
        self.model_admin.upload_column_names = ["name", "is_active"]
        column_names = self.model_admin.get_upload_column_names(self.request)
        self.model_admin.upload_column_names = column_names
        upload_fields = self.model_admin.get_upload_db_fields(self.request)

        row_dict = {"name": "Test User", "is_active": "true"}
        result = self.model_admin.convert2upload_fields(self.request, row_dict, upload_fields)

        self.assertTrue(result["is_active"])
        self.assertEqual(result["created_by"], self.user.username)

    @pytest.mark.django_db(databases=["default", "postgres"])
    @patch.object(TestBaseModelAdmin, "_process_bulk_operations")
    def test_upload_data_with_base_model(self, mock_process):
        """Test upload_data correctly processes BaseModel records."""
        self.model_admin.upload_column_names = ["name", "email"]

        # Create test CSV
        csv_content = "name,email\nJohn Doe,john@example.com"
        csv_file = create_test_csv_file(csv_content)

        # Call upload_data
        self.model_admin.upload_data(self.request, self.model_admin.get_csv_reader, csv_file, Encoding.UTF8, self.request)

        # Verify record was created with user information
        self.assertEqual(len(self.model_admin._bulk_create_list), 1)
        record = self.model_admin._bulk_create_list[0]
        self.assertEqual(record.name, "John Doe")
        self.assertEqual(record.email, "john@example.com")
        # The created_by and updated_by should be set by upload_data's creator_info/updater_info merge,
        # not by convert2upload_fields, because those fields are handled at the upload_data level
        self.assertEqual(record.created_by, self.user.username)
        self.assertEqual(record.updated_by, self.user.username)

    def test_get_upload_db_fields_excludes_base_fields_then_adds_back(self):
        """Test get_upload_db_fields properly handles BaseModel fields."""
        self.model_admin.upload_column_names = ["name", "email", "created_at"]

        result = self.model_admin.get_upload_db_fields(self.request)

        # Should include all specified fields
        result_keys = list(result.keys())
        self.assertIn("name", result_keys)
        self.assertIn("email", result_keys)
        self.assertIn("created_at", result_keys)

    def test_get_upload_column_names_with_non_base_model_upload_model(self):
        """Test get_upload_column_names when upload_model is not a BaseModel."""
        from sfd.tests.unittest import TestModel

        # TestModel is not a BaseModel
        self.model_admin.upload_model = TestModel
        self.model_admin.upload_column_names = ["name", "email"]

        result = self.model_admin.get_upload_column_names(self.request)

        # Should NOT add base model fields since upload_model is not a BaseModel
        self.assertNotIn("created_by", result)
        self.assertNotIn("updated_by", result)
        self.assertNotIn("created_at", result)
        self.assertNotIn("updated_at", result)
        self.assertIn("name", result)
        self.assertIn("email", result)


@pytest.mark.unit
@pytest.mark.upload
class MasterModelUploadMixinTest(BaseTestMixin, TestCase):
    """Test UploadMixin functionality with comprehensive coverage."""

    databases = ["default", "postgres"]

    def setUp(self):
        """Set up test environment with model admin instance."""
        super().setUp()
        self.admin_site = AdminSite()
        self.model_admin = TestMasterModelAdmin(TestMasterModel, self.admin_site)

        self.request = self.factory.get("/admin/")
        self.request.user = self.user

        self.model_admin._bulk_create_list = []
        self.model_admin._bulk_update_list = []
        self.model_admin._uploaded_unique_values = set()  # 今回アップロードしたCSVのユニーク値
        self.model_admin._total_inserted = 0  # Track total inserted across chunks
        self.model_admin._total_updated = 0  # Track total updated across chunks
        self.model_admin._upload_datetime = timezone.now()

    def test_get_upload_db_fields(self):
        """Test get_upload_db_fields returns correct field mapping for MasterModel."""
        # Set upload_model to get all fields including valid_from and valid_to
        self.model_admin.upload_model = TestMasterModel

        result = self.model_admin.get_upload_db_fields(self.request)

        # TestMasterModel should have local fields plus valid_from and valid_to from MasterModel
        result_keys = list(result.keys())
        self.assertIn("name", result_keys)
        self.assertIn("email", result_keys)
        self.assertIn("valid_from", result_keys)
        self.assertIn("valid_to", result_keys)

    def test_convert2upload_fields(self):
        """Test convert2upload_fields maps CSV row to model fields correctly."""
        self.model_admin.upload_column_names = ["name", "email", "is_active", "date"]
        upload_fields = self.model_admin.get_upload_db_fields(self.request)

        row_dict = {
            "name": "Master Test",
            "email": "master@example.com",
            "is_active": "true",
            "date": "2024-12-31",
        }
        result = self.model_admin.convert2upload_fields(self.request, row_dict, upload_fields)
        self.assertEqual(result["name"], "Master Test")
        self.assertEqual(result["email"], "master@example.com")
        self.assertEqual(result["is_active"], True)
        self.assertEqual(result["date"], date(2024, 12, 31))
        self.assertIn("valid_from", result)
        self.assertIn("valid_to", result)

    def test_convert2upload_fields_with_valid_dates(self):
        """Test convert2upload_fields with explicit valid_from and valid_to dates."""
        self.model_admin.upload_column_names = ["name", "valid_from", "valid_to"]
        upload_fields = self.model_admin.get_upload_db_fields(self.request)

        row_dict = {
            "name": "Master Test",
            "valid_from": "2024-01-01",
            "valid_to": "2024-12-31",
        }
        result = self.model_admin.convert2upload_fields(self.request, row_dict, upload_fields)
        self.assertEqual(result["name"], "Master Test")
        self.assertEqual(result["valid_from"], date(2024, 1, 1))
        self.assertEqual(result["valid_to"], date(2024, 12, 31))

    def test_convert2upload_fields_default_valid_dates(self):
        """Test convert2upload_fields sets default valid_from and valid_to when not provided."""
        self.model_admin.upload_column_names = ["name"]
        upload_fields = self.model_admin.get_upload_db_fields(self.request)

        row_dict = {"name": "Master Test"}
        result = self.model_admin.convert2upload_fields(self.request, row_dict, upload_fields)

        # valid_from should be tomorrow
        expected_valid_from = timezone.now().date() + timedelta(days=1)
        self.assertEqual(result["valid_from"], expected_valid_from)

        # valid_to should be 2222-12-31
        expected_valid_to = date(2222, 12, 31)
        self.assertEqual(result["valid_to"], expected_valid_to)

    def test_get_upload_db_fields_with_valid_fields_already_present(self):
        """Test get_upload_db_fields when valid_from and valid_to are already in upload_db_fields."""
        self.model_admin.upload_column_names = ["name", "email", "valid_from", "valid_to"]

        result = self.model_admin.get_upload_db_fields(self.request)

        # Should include valid_from and valid_to without duplication
        self.assertIn("name", result)
        self.assertIn("email", result)
        self.assertIn("valid_from", result)
        self.assertIn("valid_to", result)

    def test_convert2upload_fields_boolean_with_other_value(self):
        """Test convert2upload_fields with BooleanField using bool() for other types."""
        # This test covers the 'else' branch for BooleanField (line 483)
        mock_field = Mock()
        mock_field.get_internal_type.return_value = "BooleanField"

        upload_fields = {"is_active": mock_field}

        # Test with list (triggers else branch -> bool())
        row_dict = {"is_active": [1, 2, 3]}  # Non-empty list is truthy
        result = self.model_admin.convert2upload_fields(self.request, row_dict, upload_fields)
        self.assertTrue(result["is_active"])

        # Test with empty list (triggers else branch -> bool())
        row_dict = {"is_active": []}  # Empty list is falsy
        result = self.model_admin.convert2upload_fields(self.request, row_dict, upload_fields)
        self.assertFalse(result["is_active"])

    def test_convert2upload_fields_other_field_type(self):
        """Test convert2upload_fields with other field types (line 485)."""
        # This test covers the 'else' branch for unknown field types
        mock_field = Mock()
        mock_field.get_internal_type.return_value = "UnknownField"

        upload_fields = {"other_field": mock_field}

        # Test with string value
        row_dict = {"other_field": "some value"}
        result = self.model_admin.convert2upload_fields(self.request, row_dict, upload_fields)
        self.assertEqual(result["other_field"], "some value")

        # Test with integer value
        row_dict = {"other_field": 42}
        result = self.model_admin.convert2upload_fields(self.request, row_dict, upload_fields)
        self.assertEqual(result["other_field"], 42)

    def test_get_upload_column_names_with_non_master_model_upload_model(self):
        """Test get_upload_column_names when upload_model is not a MasterModel."""
        from sfd.tests.unittest import TestModel

        # TestModel is not a MasterModel
        self.model_admin.upload_model = TestModel
        self.model_admin.upload_column_names = ["name", "email"]

        result = self.model_admin.get_upload_column_names(self.request)

        # Should NOT add master model fields since upload_model is not a MasterModel
        self.assertNotIn("valid_from", result)
        self.assertNotIn("valid_to", result)
        self.assertIn("name", result)
        self.assertIn("email", result)
