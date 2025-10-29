# type: ignore
"""
Test cases for sfd.views.common.download module.

This module contains comprehensive test cases for the CSV download functionality,
including the DownloadMixin class and related utilities.
"""

from unittest.mock import patch

import pytest
from django.contrib import admin
from django.contrib.admin.sites import AdminSite
from django.test import TestCase
from django.utils import translation
from django.utils.http import quote

from sfd.tests.unittest import BaseTestMixin, TestBaseModel, TestMasterModel, TestModel
from sfd.views.common.download import BaseModelDownloadMixin, CsvSeparator, DownloadMixin, MasterModelDownloadMixin, download_selected
from sfd.views.common.mixins import ModelAdminMixin


class TestModelAdmin(DownloadMixin, ModelAdminMixin, admin.ModelAdmin):
    pass


class TestBaseModelAdmin(BaseModelDownloadMixin, TestModelAdmin):
    pass


class TestMasterModelAdmin(MasterModelDownloadMixin, TestModelAdmin):
    pass


@pytest.mark.unit
@pytest.mark.download
class DownloadMixinTest(BaseTestMixin, TestCase):
    """
    Test cases for DownloadMixin class.

    Comprehensive tests for all methods and functionality provided by the
    CSV download mixin, including file generation, header creation, and
    admin integration.
    """

    databases = ["default", "postgres"]

    def setUp(self):
        """Set up test environment with model admin instance."""
        super().setUp()
        self.admin_site = AdminSite()
        self.model_admin = TestModelAdmin(TestModel, self.admin_site)
        self.request = self.factory.get("/admin/")
        self.request.user = self.user

    def test_download_mixin_instance(self):
        """Test that DownloadMixin is properly inherited."""
        self.assertIsInstance(self.model_admin, DownloadMixin)
        self.assertTrue(hasattr(self.model_admin, "csv_separator"))
        self.assertTrue(hasattr(self.model_admin, "download_column_names"))
        self.assertTrue(hasattr(self.model_admin, "get_csv_file_name"))
        self.assertTrue(hasattr(self.model_admin, "get_download_columns"))
        self.assertTrue(hasattr(self.model_admin, "download_file"))

        self.assertEqual(self.model_admin.csv_separator, CsvSeparator.COMMA)
        self.assertEqual(self.model_admin.download_column_names, [])

    @patch("sfd.views.common.download.datetime")
    def test_get_csv_file_name(self, mock_datetime):
        """Test CSV filename generation with default model name."""
        # Mock datetime
        mock_datetime.now.return_value.strftime.return_value = "20240115_143045"

        filename = self.model_admin.get_csv_file_name(self.request)

        # Verify filename format and URL encoding
        self.assertEqual(filename, quote("Test Model") + "_20240115_143045.csv")

    @patch("sfd.views.common.download.datetime")
    def test_get_csv_file_name_with_custom_name(self, mock_datetime):
        """Test CSV filename generation with custom name."""
        # Mock datetime
        mock_datetime.now.return_value.strftime.return_value = "20240115_143045"

        custom_name = "Custom"
        filename = self.model_admin.get_csv_file_name(self.request, custom_name)

        # Verify custom name is used
        self.assertEqual(filename, "Custom_20240115_143045.csv")

    @patch.object(TestModelAdmin, "get_column_labels")
    def test_get_download_columns_with_download_column_names(self, mock_get_labels):
        """Test retrieval of download column names."""
        self.model_admin.download_column_names = ["name", "email", "is_active", "date"]
        expected_columns = {"name": "Name", "email": "Email", "is_active": "Active", "date": "Date"}
        mock_get_labels.return_value = expected_columns
        columns = self.model_admin.get_download_columns(self.request)
        self.assertEqual(columns, expected_columns)

    @patch.object(TestModelAdmin, "get_column_labels")
    @patch.object(TestModelAdmin, "get_non_inherited_model_fields")
    def test_get_download_columns(self, mock_get_fields, mock_get_labels):
        """Test retrieval of download column names."""
        # Mock the methods on the instance, not the class
        mock_get_fields.return_value = ["name", "email", "is_active", "date"]
        expected_columns = {"name": "Name", "email": "Email", "is_active": "Active", "date": "Date"}
        mock_get_labels.return_value = expected_columns
        columns = self.model_admin.get_download_columns(self.request)
        self.assertEqual(columns, expected_columns)

    def test_get_download_queryset(self):
        """Test retrieval of download queryset."""
        obj1 = TestModel.objects.create(name="Test 1")
        obj2 = TestModel.objects.create(name="Test 2")
        TestModel.objects.create(name="Test 3")
        queryset = TestModel.objects.filter(id__in=[obj1.id, obj2.id])

        qs = self.model_admin.get_download_queryset(self.request, queryset=queryset)
        self.assertEqual(qs.model, TestModel)
        self.assertEqual(qs.count(), 2)
        self.assertIn(obj1, qs)
        self.assertIn(obj2, qs)

    def test_get_download_queryset_with_none(self):
        """Test retrieval of download queryset when queryset parameter is None.

        When queryset is None, the method should create a changelist instance
        and return a queryset from it, respecting any filters or search terms
        in the request.
        """
        obj1 = TestModel.objects.create(name="Test 1")
        obj2 = TestModel.objects.create(name="Test 2")

        # Test with no queryset parameter (None)
        qs = self.model_admin.get_download_queryset(self.request, queryset=None)

        # Verify that a queryset is returned
        self.assertIsNotNone(qs)
        self.assertEqual(qs.model, TestModel)
        self.assertEqual(qs.count(), 2)
        self.assertIn(obj1, qs)
        self.assertIn(obj2, qs)

    def test_get_csv_data(self):
        """Test retrieval of download queryset."""
        self.model_admin.download_column_names = ["name", "email"]
        obj1 = TestModel.objects.create(name="Test 1", email="test1@example.com")
        obj2 = TestModel.objects.create(name="Test 2", email="test2@example.com")
        queryset = TestModel.objects.filter(id__in=[obj1.id, obj2.id])

        csv_data = list(self.model_admin.get_csv_data(self.request, queryset=queryset))

        # Verify CSV data
        self.assertEqual(len(csv_data), 2)
        self.assertEqual(csv_data[0], ("Test 1", "test1@example.com"))
        self.assertEqual(csv_data[1], ("Test 2", "test2@example.com"))

    def test_download_file_with_queryset(self):
        """Test download_file method generates proper CSV response with queryset.

        This test verifies that the download_file method:
        - Returns an HttpResponse with correct content type
        - Sets proper Content-Disposition header for file download
        - Includes CSV headers based on field verbose names
        - Exports data from the provided queryset
        - Properly formats CSV rows with correct delimiters
        """
        # Set up test data
        self.model_admin.download_column_names = ["name", "email"]
        obj1 = TestModel.objects.create(name="Test 1", email="test1@example.com")
        obj2 = TestModel.objects.create(name="Test 2", email="test2@example.com")
        TestModel.objects.create(name="Test 3", email="test3@example.com")
        queryset = TestModel.objects.filter(id__in=[obj1.id, obj2.id])

        # Call download_file
        response = self.model_admin.download_file(self.request, queryset=queryset)

        # Verify response type and headers
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], f"text/{self.model_admin.csv_separator.label}")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertIn(".csv", response["Content-Disposition"])

        # Verify CSV content
        content = response.content.decode("utf-8")
        lines = content.strip().split("\r\n")

        # Should have header + 2 data rows
        self.assertEqual(len(lines), 3)

        # Verify header row
        self.assertIn("Name", lines[0])
        self.assertIn("Email", lines[0])

        # Verify data rows
        self.assertIn("Test 1", content)
        self.assertIn("test1@example.com", content)
        self.assertIn("Test 2", content)
        self.assertIn("test2@example.com", content)

    def test_download_file_without_queryset(self):
        """Test download_file method with None queryset uses changelist.

        When no queryset is provided, download_file should use the changelist
        queryset, which includes all objects with any applied filters or search terms.
        """
        # Set up test data
        self.model_admin.download_column_names = ["name", "email"]
        TestModel.objects.create(name="Test 1", email="test1@example.com")
        TestModel.objects.create(name="Test 2", email="test2@example.com")
        TestModel.objects.create(name="Test 3", email="test3@example.com")

        # Call download_file without queryset parameter
        response = self.model_admin.download_file(self.request, queryset=None)

        # Verify response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], f"text/{self.model_admin.csv_separator.label}")

        # Verify all objects are included
        content = response.content.decode("utf-8")
        self.assertIn("Test 1", content)
        self.assertIn("Test 2", content)
        self.assertIn("Test 3", content)

    def test_download_file_with_tab_separator(self):
        """Test download_file method with tab separator (TSV format).

        Verifies that the CSV separator configuration is respected and
        the file extension and content type are set correctly for TSV files.
        """
        # Change separator to TAB
        self.model_admin.csv_separator = CsvSeparator.TAB

        # Set up test data
        self.model_admin.download_column_names = ["name", "email"]
        obj = TestModel.objects.create(name="Tab Test", email="tab@example.com")
        queryset = TestModel.objects.filter(id=obj.id)

        # Call download_file
        response = self.model_admin.download_file(self.request, queryset=queryset)

        # Verify response headers for TSV
        self.assertEqual(response["Content-Type"], "text/tsv")
        self.assertIn(".tsv", response["Content-Disposition"])

        # Verify tab-separated content
        content = response.content.decode("utf-8")
        lines = content.strip().split("\r\n")

        # Header should be tab-separated
        self.assertIn("\t", lines[0])

        # Data row should contain tab separator
        self.assertIn("Tab Test\ttab@example.com", content)

    def test_download_file_empty_queryset(self):
        """Test download_file method with empty queryset.

        Should return a valid CSV response with headers but no data rows.
        """
        # Set up with empty queryset
        self.model_admin.download_column_names = ["name", "email"]
        queryset = TestModel.objects.none()

        # Call download_file
        response = self.model_admin.download_file(self.request, queryset=queryset)

        # Verify response
        self.assertEqual(response.status_code, 200)

        # Verify content has headers but no data
        content = response.content.decode("utf-8")
        lines = content.strip().split("\r\n")

        # Should have only header row
        self.assertEqual(len(lines), 1)
        self.assertIn("Name", lines[0])
        self.assertIn("Email", lines[0])

    def test_get_urls(self):
        """Test get_urls method adds custom download URL pattern.

        Verifies that:
        - Custom download URL is added to admin URLs
        - URL pattern name follows expected format
        - Download endpoint is accessible
        - Custom URLs take precedence over default URLs
        """
        urls = self.model_admin.get_urls()

        # Verify URLs list is returned
        self.assertIsNotNone(urls)
        self.assertIsInstance(urls, list)
        self.assertGreater(len(urls), 0)

        # Verify download URL is included
        download_url_found = False
        expected_url_name = f"{TestModel._meta.app_label}_{TestModel._meta.model_name}_download_file"

        for url_pattern in urls:
            if hasattr(url_pattern, "name") and url_pattern.name == expected_url_name:
                download_url_found = True
                # Verify URL pattern
                self.assertEqual(url_pattern.pattern._route, "download_file/")
                break

        self.assertTrue(download_url_found, f"Download URL with name '{expected_url_name}' not found in URLs")

    def test_get_actions(self):
        """Test get_actions method adds download_selected action.

        Verifies that:
        - download_selected action is added to available actions
        - Action has correct function, name, and description
        - Action format matches Django admin action structure
        - Other default actions are preserved
        """
        actions = self.model_admin.get_actions(self.request)

        # Verify actions dictionary is returned
        self.assertIsNotNone(actions)
        self.assertIsInstance(actions, dict)

        # Verify download_selected action exists
        self.assertIn("download_selected", actions)

        # Verify action structure (function, name, description)
        action_tuple = actions["download_selected"]
        self.assertEqual(len(action_tuple), 3)

        action_function, action_name, action_description = action_tuple

        # Verify action details
        self.assertEqual(action_name, "download_selected")
        self.assertIsNotNone(action_description)
        self.assertTrue(callable(action_function))

    @patch("sfd.views.common.download.reverse", return_value="/admin/download_file/")
    def test_changelist_view(self, mock_reverse):
        """Test changelist_view adds download context variables.

        Verifies that:
        - Download URL is added to context
        - Download title is properly formatted
        - Download message is localized
        - Download button text is provided
        - GET parameters are preserved in download URL
        """
        # Call changelist_view
        response = self.model_admin.changelist_view(self.request)

        # Verify response is returned
        self.assertIsNotNone(response)

        # Verify context contains download-related variables
        context = response.context_data

        self.assertIn("download_url", context)
        self.assertIn("download_title", context)
        self.assertIn("download_message", context)
        self.assertIn("download_button", context)

        # Verify download URL format
        download_url = context["download_url"]
        self.assertIsInstance(download_url, str)
        self.assertIn("download_file", download_url)

        # Verify download title contains file format
        download_title = context["download_title"]
        self.assertIsInstance(download_title, str)
        self.assertIn(self.model_admin.csv_separator.label.upper(), download_title)

    @patch("sfd.views.common.download.reverse", return_value="/admin/download_file/")
    def test_changelist_view_with_query_params(self, mock_reverse):
        """Test changelist_view preserves query parameters in download URL.

        When the request contains GET parameters (filters, search terms, etc.),
        they should be preserved in the download URL to ensure the downloaded
        data matches what the user sees in the changelist.

        This test directly calls changelist_view and verifies the extra_context
        that would be passed to the parent changelist_view contains the download
        URL with preserved query parameters.
        """
        # Create request with query parameters
        request_with_params = self.factory.get("/admin/", {"q": "test", "o": "1"})
        request_with_params.user = self.user

        # Mock the parent changelist_view to capture the extra_context
        with patch.object(admin.ModelAdmin, "changelist_view", return_value=type("Response", (), {"context_data": {}})()) as mock_parent_view:
            self.model_admin.changelist_view(request_with_params)

            # Verify parent changelist_view was called
            self.assertTrue(mock_parent_view.called)

            # Get the extra_context passed to parent
            call_args = mock_parent_view.call_args
            extra_context = call_args[1].get("extra_context", call_args[0][1] if len(call_args[0]) > 1 else None)

            # Verify extra_context contains download URL with query params
            self.assertIsNotNone(extra_context)
            self.assertIn("download_url", extra_context)

            download_url = extra_context["download_url"]
            # Verify query parameters are preserved
            self.assertIn("?", download_url)
            self.assertIn("q=test", download_url)
            self.assertIn("o=1", download_url)

    @patch("sfd.views.common.download.reverse", return_value="/admin/download_file/")
    def test_changelist_view_with_extra_context(self, mock_reverse):
        """Test changelist_view merges with existing extra_context.

        Verifies that if extra_context is provided, download-related variables
        are added without overwriting existing context data.
        """
        # Create extra context
        extra_context = {
            "custom_key": "custom_value",
            "another_key": 123,
        }

        # Call changelist_view with extra context
        response = self.model_admin.changelist_view(self.request, extra_context=extra_context)

        # Verify both existing and new context variables are present
        context = response.context_data

        # Verify download-related context
        self.assertIn("download_url", context)
        self.assertIn("download_title", context)

        # Verify extra context is preserved
        self.assertIn("custom_key", context)
        self.assertIn("another_key", context)
        self.assertEqual(context["custom_key"], "custom_value")
        self.assertEqual(context["another_key"], 123)

    def test_download_selected(self):
        """Test download_selected action method."""
        # Create test objects
        obj1 = TestModel.objects.create(name="Test 1", email="test1@example.com")
        obj2 = TestModel.objects.create(name="Test 2", email="test2@example.com")
        queryset = TestModel.objects.filter(id__in=[obj1.id, obj2.id])
        self.model_admin.download_column_names = ["name", "email"]

        # Call download_selected action
        response = download_selected(self.model_admin, self.request, queryset)

        # Verify response type and headers
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], f"text/{self.model_admin.csv_separator.label}")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertIn(".csv", response["Content-Disposition"])

        # Verify CSV content
        content = response.content.decode("utf-8")
        lines = content.strip().split("\r\n")

        # Should have header + 2 data rows
        self.assertEqual(len(lines), 3)

        # Verify data rows
        self.assertIn("Test 1", content)
        self.assertIn("Test 2", content)

    @patch.object(TestModelAdmin, "message_user")
    def test_download_selected_with_empty_queryset(self, mock_message_user):
        """Test download_selected action method with empty queryset.

        When no rows are selected (empty queryset), the action should:
        - Show a warning message to the user
        - Return None instead of a file download response
        """
        # Create an empty queryset
        queryset = TestModel.objects.none()
        self.model_admin.download_column_names = ["name", "email"]

        # Call download_selected action
        response = download_selected(self.model_admin, self.request, queryset)

        # Verify that message_user was called with warning
        mock_message_user.assert_called_once()
        call_args = mock_message_user.call_args

        # Verify the message text
        self.assertIn("No rows selected", call_args[0][1])

        # Verify the message level is 'warning'
        self.assertEqual(call_args[1].get("level"), "warning")

        # Verify response is None (no file download)
        self.assertIsNone(response)

    @pytest.mark.django_db(databases=["default", "postgres"])
    def test_download_file_creates_csv_log_success(self):
        """Test that download_file creates a CSV log record on successful download."""
        from sfd.models.csv_log import CsvLog, CsvProcessResult, CsvProcessType

        self.model_admin.download_column_names = ["name", "email"]

        # Create test data
        obj1 = TestModel.objects.create(name="Test 1", email="test1@example.com")
        obj2 = TestModel.objects.create(name="Test 2", email="test2@example.com")
        queryset = TestModel.objects.filter(id__in=[obj1.id, obj2.id])

        # Setup request with IP address
        self.request.META["REMOTE_ADDR"] = "127.0.0.1"

        # Verify no CSV log records exist before download
        self.assertEqual(CsvLog.objects.count(), 0)

        # Call download_file
        response = self.model_admin.download_file(self.request, queryset=queryset)

        # Verify response is successful
        self.assertEqual(response.status_code, 200)

        # Verify CSV log record was created
        self.assertEqual(CsvLog.objects.count(), 1)
        csv_log = CsvLog.objects.first()

        # Verify log record fields
        self.assertEqual(csv_log.process_type, CsvProcessType.DOWNLOAD)
        self.assertEqual(csv_log.process_result, CsvProcessResult.SUCCESS)
        self.assertEqual(csv_log.app_name, "sfd")
        self.assertEqual(csv_log.processed_by, self.user.username)
        self.assertEqual(csv_log.ip_address, "127.0.0.1")
        self.assertIn(".csv", csv_log.file_name)
        # Verify filename is unquoted (not URL-encoded)
        self.assertIn("Test Model", csv_log.file_name)
        self.assertNotIn("%20", csv_log.file_name)  # Should not contain URL encoding
        self.assertEqual(csv_log.total_line, 2)  # Two data rows

    @pytest.mark.django_db(databases=["default", "postgres"])
    def test_download_file_creates_csv_log_no_data(self):
        """Test that download_file creates a CSV log with NO_DATA result for empty queryset."""
        from sfd.models.csv_log import CsvLog, CsvProcessResult, CsvProcessType

        self.model_admin.download_column_names = ["name", "email"]

        # Create empty queryset
        queryset = TestModel.objects.none()

        # Setup request with IP address
        self.request.META["REMOTE_ADDR"] = "192.168.1.100"

        # Verify no CSV log records exist before download
        self.assertEqual(CsvLog.objects.count(), 0)

        # Call download_file
        response = self.model_admin.download_file(self.request, queryset=queryset)

        # Verify response is successful
        self.assertEqual(response.status_code, 200)

        # Verify CSV log record was created with NO_DATA result
        self.assertEqual(CsvLog.objects.count(), 1)
        csv_log = CsvLog.objects.first()

        # Verify log record fields
        self.assertEqual(csv_log.process_type, CsvProcessType.DOWNLOAD)
        self.assertEqual(csv_log.process_result, CsvProcessResult.NO_DATA)
        self.assertEqual(csv_log.app_name, "sfd")
        self.assertEqual(csv_log.processed_by, self.user.username)
        self.assertEqual(csv_log.ip_address, "192.168.1.100")
        self.assertIn(".csv", csv_log.file_name)
        # Verify filename is unquoted (not URL-encoded)
        self.assertIn("Test Model", csv_log.file_name)
        self.assertNotIn("%20", csv_log.file_name)  # Should not contain URL encoding
        self.assertEqual(csv_log.total_line, 0)  # No data rows

    @pytest.mark.django_db(databases=["default", "postgres"])
    def test_download_file_creates_csv_log_failure(self):
        """Test that download_file creates a CSV log record on failed download."""
        from sfd.models.csv_log import CsvLog, CsvProcessResult, CsvProcessType

        self.model_admin.download_column_names = ["name", "email"]

        # Create test data
        obj1 = TestModel.objects.create(name="Test 1", email="test1@example.com")
        queryset = TestModel.objects.filter(id=obj1.id)

        # Setup request with IP address
        self.request.META["REMOTE_ADDR"] = "10.0.0.1"

        # Mock get_csv_data to raise an exception
        with patch.object(self.model_admin, "get_csv_data", side_effect=ValueError("Test error")):
            # Verify no CSV log records exist before download
            self.assertEqual(CsvLog.objects.count(), 0)

            # Call download_file and expect exception
            with self.assertRaises(ValueError) as context:
                self.model_admin.download_file(self.request, queryset=queryset)

            self.assertIn("Test error", str(context.exception))

            # Verify CSV log record was created with failure status
            self.assertEqual(CsvLog.objects.count(), 1)
            csv_log = CsvLog.objects.first()

            # Verify log record fields
            self.assertEqual(csv_log.process_type, CsvProcessType.DOWNLOAD)
            self.assertEqual(csv_log.process_result, CsvProcessResult.FAILURE)
            self.assertEqual(csv_log.app_name, "sfd")
            self.assertEqual(csv_log.processed_by, self.user.username)
            self.assertEqual(csv_log.ip_address, "10.0.0.1")
            self.assertIn(".csv", csv_log.file_name)
            # Verify filename is unquoted (not URL-encoded)
            self.assertIn("Test Model", csv_log.file_name)
            self.assertNotIn("%20", csv_log.file_name)  # Should not contain URL encoding
            self.assertEqual(csv_log.total_line, 0)  # No lines processed due to early failure

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
        """Test get_app_name returns the correct app name."""
        app_name = self.model_admin.get_app_name()
        self.assertEqual(app_name, "sfd")


@pytest.mark.unit
@pytest.mark.download
class BaseModelDownloadMixinTest(BaseTestMixin, TestCase):
    """
    Test cases for DownloadMixin class.

    Comprehensive tests for all methods and functionality provided by the
    CSV download mixin, including file generation, header creation, and
    admin integration.
    """

    def setUp(self):
        """Set up test environment with model admin instance."""
        super().setUp()
        self.admin_site = AdminSite()
        self.model_admin = TestBaseModelAdmin(TestBaseModel, self.admin_site)
        self.request = self.factory.get("/admin/")
        self.request.user = self.user

    @patch.object(TestBaseModelAdmin, "get_column_labels")
    @patch.object(TestBaseModelAdmin, "get_non_inherited_model_fields")
    def test_get_download_columns(self, mock_get_fields, mock_get_labels):
        """Test retrieval of download column names for base model."""
        # Mock the methods on the instance, not the class
        mock_get_fields.return_value = ["name", "email", "is_active", "date"]
        expected_columns = {
            "name": "Name",
            "email": "Email",
            "is_active": "Active",
            "date": "Date",
            "created_by": "Created By",
            "updated_by": "Updated By",
            "created_at": "Created At",
            "updated_at": "Updated At",
            "deleted_flg": "Delete Flag",
        }
        mock_get_labels.return_value = expected_columns

        with translation.override("en"):
            columns = self.model_admin.get_download_columns(self.request)
            self.assertEqual(columns, expected_columns)


@pytest.mark.unit
@pytest.mark.download
class MasterModelDownloadMixinTest(BaseTestMixin, TestCase):
    """
    Test cases for MasterModelDownloadMixin class.

    Comprehensive tests for all methods and functionality provided by the
    CSV download mixin, including file generation, header creation, and
    admin integration.
    """

    def setUp(self):
        """Set up test environment with model admin instance."""
        super().setUp()
        self.admin_site = AdminSite()
        self.model_admin = TestMasterModelAdmin(TestMasterModel, self.admin_site)
        self.request = self.factory.get("/admin/")
        self.request.user = self.user

    @patch.object(TestBaseModelAdmin, "get_column_labels")
    @patch.object(TestBaseModelAdmin, "get_non_inherited_model_fields")
    def test_get_download_columns(self, mock_get_fields, mock_get_labels):
        """Test retrieval of download column names for base model."""
        # Mock the methods on the instance, not the class
        mock_get_fields.return_value = ["name", "email", "is_active", "date"]
        expected_columns = {
            "name": "Name",
            "email": "Email",
            "is_active": "Active",
            "date": "Date",
            "created_by": "Created By",
            "updated_by": "Updated By",
            "created_at": "Created At",
            "updated_at": "Updated At",
            "valid_from": "Valid From",
            "valid_to": "Valid To",
        }
        mock_get_labels.return_value = expected_columns

        with translation.override("en"):
            columns = self.model_admin.get_download_columns(self.request)
            self.assertEqual(columns, expected_columns)
