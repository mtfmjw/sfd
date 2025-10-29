# type: ignore
"""Tests for CsvLogAdmin to achieve 100% coverage."""

import pytest
from django.contrib.admin import AdminSite
from django.test import TestCase
from django.urls import reverse
from django.utils.html import format_html

from sfd.models.csv_log import CsvLog, CsvProcessResult, CsvProcessType
from sfd.tests.unittest import BaseTestMixin
from sfd.views.common.csv_log import CsvLogAdmin


@pytest.mark.unit
@pytest.mark.views
class CsvLogAdminTest(BaseTestMixin, TestCase):
    """Test CsvLogAdmin functionality with comprehensive coverage."""

    databases = {"default", "postgres"}

    def setUp(self):
        """Set up test data for CsvLogAdmin tests."""
        super().setUp()
        self.admin_site = AdminSite()
        self.admin = CsvLogAdmin(CsvLog, self.admin_site)
        self.request = self.factory.get("/admin/")
        self.request.user = self.superuser

        # Create a test CsvLog instance
        self.csv_log = CsvLog.objects.create(
            app_name="test_app",
            file_name="test_file.csv",
            total_line=100,
            process_type=CsvProcessType.UPLOAD,
            process_result=CsvProcessResult.SUCCESS,
            processed_by="testuser",
            ip_address="127.0.0.1",
            comment="Test comment",
        )

    def test_list_display_configuration(self):
        """Test that list_display is properly configured."""
        expected_fields = (
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
        self.assertEqual(self.admin.list_display, expected_fields)

    def test_list_filter_configuration(self):
        """Test that list_filter is properly configured."""
        expected_filters = ("app_name", "processed_at", "process_type", "process_result")
        self.assertEqual(self.admin.list_filter, expected_filters)

    def test_search_fields_configuration(self):
        """Test that search_fields is properly configured."""
        expected_search = ("app_name", "file_name", "processed_by", "ip_address", "comment")
        self.assertEqual(self.admin.search_fields, expected_search)

    def test_date_hierarchy_configuration(self):
        """Test that date_hierarchy is properly configured."""
        self.assertEqual(self.admin.date_hierarchy, "processed_at")

    def test_readonly_fields_configuration(self):
        """Test that readonly_fields is properly configured."""
        self.assertEqual(self.admin.readonly_fields, ("processed_at",))

    def test_exclude_configuration(self):
        """Test that exclude is properly configured to exclude process_id."""
        self.assertEqual(self.admin.exclude, ("process_id",))

    def test_list_display_links_configuration(self):
        """Test that list_display_links is properly configured."""
        self.assertEqual(self.admin.list_display_links, ("file_name_link",))

    def test_file_name_link_with_valid_object(self):
        """Test file_name_link method with a valid object that has pk."""
        result = self.admin.file_name_link(self.csv_log)

        # Verify the link is properly formatted
        expected_url = reverse(f"{self.admin_site.name}:sfd_csvlog_change", args=[self.csv_log.pk])
        expected_html = format_html('<a href="{}">{}</a>', expected_url, self.csv_log.file_name)

        self.assertEqual(result, expected_html)
        self.assertIn("test_file.csv", result)
        self.assertIn("href", result)

    def test_file_name_link_with_object_without_pk(self):
        """Test file_name_link method with an object without pk."""
        # Create an unsaved object (no pk)
        unsaved_log = CsvLog(
            app_name="test_app",
            file_name="unsaved_file.csv",
            total_line=50,
            process_type=CsvProcessType.DOWNLOAD,
            process_result=CsvProcessResult.FAILURE,
            processed_by="testuser",
        )

        result = self.admin.file_name_link(unsaved_log)

        # Should return plain file_name without link
        self.assertEqual(result, "unsaved_file.csv")
        self.assertNotIn("href", result)

    def test_file_name_link_with_none_object(self):
        """Test file_name_link method with None object."""

        # Create a mock object with pk=None
        class MockObj:
            pk = None
            file_name = "none_file.csv"

        mock_obj = MockObj()
        result = self.admin.file_name_link(mock_obj)

        # Should return plain file_name without link
        self.assertEqual(result, "none_file.csv")
        self.assertNotIn("href", result)

    def test_file_name_link_short_description(self):
        """Test that file_name_link has proper short_description."""
        self.assertTrue(hasattr(self.admin.file_name_link, "short_description"))
        # The short_description should be translated, so we check it exists
        self.assertIsNotNone(self.admin.file_name_link.short_description)

    def test_has_add_permission_returns_false(self):
        """Test that has_add_permission always returns False."""
        result = self.admin.has_add_permission(self.request)
        self.assertFalse(result)

    def test_has_change_permission_returns_false(self):
        """Test that has_change_permission always returns False."""
        result = self.admin.has_change_permission(self.request)
        self.assertFalse(result)

    def test_has_change_permission_with_obj_returns_false(self):
        """Test that has_change_permission with obj always returns False."""
        result = self.admin.has_change_permission(self.request, obj=self.csv_log)
        self.assertFalse(result)

    def test_has_delete_permission_returns_false(self):
        """Test that has_delete_permission always returns False."""
        result = self.admin.has_delete_permission(self.request)
        self.assertFalse(result)

    def test_has_delete_permission_with_obj_returns_false(self):
        """Test that has_delete_permission with obj always returns False."""
        result = self.admin.has_delete_permission(self.request, obj=self.csv_log)
        self.assertFalse(result)

    def test_csv_log_admin_inherits_from_model_admin_mixin(self):
        """Test that CsvLogAdmin inherits from ModelAdminMixin."""
        from sfd.views.common.mixins import ModelAdminMixin

        self.assertIsInstance(self.admin, ModelAdminMixin)

    def test_file_name_link_with_different_file_names(self):
        """Test file_name_link with various file name formats."""
        test_cases = [
            "simple.csv",
            "file with spaces.csv",
            "file-with-dashes.csv",
            "file_with_underscores.csv",
            "ファイル.csv",  # Japanese characters
            "file123.csv",
        ]

        for file_name in test_cases:
            log = CsvLog.objects.create(
                app_name="test_app",
                file_name=file_name,
                total_line=10,
                process_type=CsvProcessType.UPLOAD,
                process_result=CsvProcessResult.SUCCESS,
                processed_by="testuser",
            )

            result = self.admin.file_name_link(log)
            self.assertIn(file_name, result)
            self.assertIn("href", result)

            # Clean up
            log.delete()

    def test_csv_log_model_fields_excluded_from_form(self):
        """Test that process_id is properly handled (not in form fields)."""
        # Get the form class
        form_class = self.admin.get_form(self.request, obj=self.csv_log)

        # Create a form instance
        form = form_class(instance=self.csv_log)

        # Verify process_id is not in form fields
        self.assertNotIn("process_id", form.fields)

        # Verify other fields are present
        expected_fields = [
            "app_name",
            "file_name",
            "process_type",
            "process_result",
            "processed_by",
            "total_line",
            "ip_address",
            "comment",
        ]
        for field in expected_fields:
            self.assertIn(field, form.fields)

    def test_readonly_field_processed_at_in_form(self):
        """Test that processed_at is marked as readonly."""
        # Get the readonly fields
        readonly = self.admin.get_readonly_fields(self.request, obj=self.csv_log)

        # Verify processed_at is in readonly fields
        self.assertIn("processed_at", readonly)
