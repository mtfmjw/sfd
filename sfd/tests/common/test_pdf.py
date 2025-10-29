# type: ignore
"""
Comprehensive test suite for PDF generation functionality.

This module tests the BasePdfMixin class and related PDF generation utilities,
including table creation, styling, file handling, and admin integration.
Tests cover Japanese font support, ReportLab integration, and Django admin
functionality.

Test Categories:
    - PDF generation admin actions and views
    - Table creation and styling functionality
    - File handling and ZIP generation
    - Japanese text support and font registration
    - Error handling and edge cases
    - Integration with Django admin interface
"""

from unittest.mock import Mock, patch
from urllib.parse import quote

import pytest
from django.contrib import admin
from django.contrib.admin.sites import AdminSite
from django.http import HttpResponse
from django.test import TestCase
from django.utils.translation import gettext_lazy as _
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle

from sfd.models import Municipality
from sfd.tests.unittest import BaseTestMixin
from sfd.views.common.pdf import BasePdfMixin, generate_pdf_selected


class TestModelAdmin(BasePdfMixin, admin.ModelAdmin):
    """Mock implementation of BasePdfMixin for testing purposes."""

    model = Municipality

    def __init__(self):
        """Initialize mock mixin with required attributes."""
        super().__init__(Municipality, AdminSite())
        self.model = Municipality
        self.admin_site = AdminSite()

    def create_pdf_files(self, request, queryset=None):
        """Mock implementation that returns test PDF filenames."""
        if queryset is None:
            return ["test_file.pdf"]
        return [f"test_{obj.id}.pdf" for obj in queryset]


@pytest.mark.unit
@pytest.mark.pdf
class PdfAdminActionTest(BaseTestMixin, TestCase):
    """Test the generate_pdf_selected admin action functionality."""

    databases = {"default", "postgres"}

    def setUp(self):
        """Set up test fixtures for PDF admin action tests."""
        super().setUp()
        self.request = self.factory.get("/admin/")
        self.request.user = self.user

    def test_generate_pdf_selected_action_exists(self):
        """Test that the generate_pdf_selected admin action exists and is properly configured."""
        # Verify the action function exists
        self.assertTrue(callable(generate_pdf_selected))

        # Verify the action has the correct description
        expected_description = _("Generate PDF for selected rows")
        self.assertEqual(generate_pdf_selected.short_description, expected_description)

    def test_generate_pdf_selected_delegates_to_modeladmin(self):
        """Test that generate_pdf_selected properly delegates to ModelAdmin.generate_pdf."""
        # Create mock objects
        mock_modeladmin = Mock()
        mock_modeladmin.generate_pdf.return_value = HttpResponse("PDF content", content_type="application/pdf")
        mock_queryset = Mock()

        # Call the action
        result = generate_pdf_selected(mock_modeladmin, self.request, mock_queryset)

        # Verify delegation occurred correctly
        mock_modeladmin.generate_pdf.assert_called_once_with(self.request, mock_queryset)
        self.assertIsInstance(result, HttpResponse)
        self.assertEqual(result.content, b"PDF content")


@pytest.mark.unit
@pytest.mark.pdf
class BasePdfMixinTest(BaseTestMixin, TestCase):
    """Test the BasePdfMixin class functionality."""

    databases = {"default", "postgres"}

    def setUp(self):
        """Set up test fixtures for BasePdfMixin tests."""
        super().setUp()
        self.pdf_mixin = TestModelAdmin()

        # Create test municipality objects
        self.municipality1 = Municipality.objects.create(
            municipality_code="001001",
            municipality_name="Test Municipality 1",
            municipality_name_kana="テストシチョウソン1",
            prefecture_name="Test Prefecture",
            prefecture_name_kana="テストケン",
        )
        self.municipality2 = Municipality.objects.create(
            municipality_code="001002",
            municipality_name="Test Municipality 2",
            municipality_name_kana="テストシチョウソン2",
            prefecture_name="Test Prefecture",
            prefecture_name_kana="テストケン",
        )

    def test_font_configuration(self):
        """Test that font configuration is properly set."""
        self.assertEqual(self.pdf_mixin.regular_font, "ipaexm")
        self.assertEqual(self.pdf_mixin.bold_font, "NotoSansJP-Bold")
        self.assertEqual(self.pdf_mixin.thin_font, "NotoSansJP-Thin")

    def test_font_sizes(self):
        """Test that font sizes are properly configured."""
        self.assertEqual(self.pdf_mixin.title_font_size, 14)
        self.assertEqual(self.pdf_mixin.sub_title_font_size, 12)
        self.assertEqual(self.pdf_mixin.normal_font_size, 10)
        self.assertEqual(self.pdf_mixin.subscript_font_size, 8)

    def test_page_configuration(self):
        """Test that page layout configuration is correct."""
        self.assertEqual(self.pdf_mixin.page_size, A4)
        self.assertEqual(self.pdf_mixin.page_margin_left, 20 * mm)
        self.assertEqual(self.pdf_mixin.page_margin_right, 20 * mm)
        self.assertEqual(self.pdf_mixin.page_margin_top, 20 * mm)
        self.assertEqual(self.pdf_mixin.page_margin_bottom, 20 * mm)

    def test_cell_styling(self):
        """Test that cell styling configuration is correct."""
        expected_color = HexColor("#CAEBAA")
        self.assertEqual(self.pdf_mixin.cell_label_bg_color, expected_color)

    def test_get_table_style_with_grid(self):
        """Test table style creation with grid lines enabled."""
        style = self.pdf_mixin.get_table_style(has_grid=True)

        self.assertIsInstance(style, TableStyle)
        # Check that grid and box styles are included
        commands = [cmd[0] for cmd in style.getCommands()]
        self.assertIn("GRID", commands)
        self.assertIn("BOX", commands)
        self.assertIn("ALIGN", commands)
        self.assertIn("VALIGN", commands)
        self.assertIn("BOTTOMPADDING", commands)

    def test_get_table_style_without_grid(self):
        """Test table style creation with grid lines disabled."""
        style = self.pdf_mixin.get_table_style(has_grid=False)

        self.assertIsInstance(style, TableStyle)
        # Check that grid and box styles are not included
        commands = [cmd[0] for cmd in style.getCommands()]
        self.assertNotIn("GRID", commands)
        self.assertNotIn("BOX", commands)
        # But basic styles should still be there
        self.assertIn("ALIGN", commands)
        self.assertIn("VALIGN", commands)

    def test_get_table_style_with_extra_styles(self):
        """Test table style creation with additional custom styles."""
        extra_styles = [
            ("BACKGROUND", (0, 0), (-1, 0), HexColor("#FF0000")),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ]

        style = self.pdf_mixin.get_table_style(extra_styles=extra_styles)

        self.assertIsInstance(style, TableStyle)
        commands = [cmd[0] for cmd in style.getCommands()]
        self.assertIn("BACKGROUND", commands)
        self.assertIn("FONTNAME", commands)

    def test_create_table_with_string_data(self):
        """Test table creation with simple string data."""
        data = [["Header 1", "Header 2"], ["Cell 1", "Cell 2"], ["Cell 3", "Cell 4"]]
        colWidths = [50 * mm, 50 * mm]

        table = self.pdf_mixin.create_table(data, colWidths)

        self.assertIsInstance(table, Table)
        self.assertEqual(len(table._argW), 2)  # Column count
        self.assertEqual(table._argW, colWidths)

    def test_create_table_with_tuple_data(self):
        """Test table creation with tuple data for custom styling."""
        data = [[("Bold Header", "Normal"), ("Normal Header", "Normal")], ["Regular Cell", ("Bold Cell", "Normal")]]
        colWidths = [50 * mm, 50 * mm]

        table = self.pdf_mixin.create_table(data, colWidths)

        self.assertIsInstance(table, Table)
        # Verify that the table was created successfully
        self.assertEqual(len(table._argW), 2)

    def test_create_table_with_paragraph_objects(self):
        """Test table creation with pre-formatted Paragraph objects."""
        styles = self.pdf_mixin.get_default_styles()
        paragraph = Paragraph("Test Paragraph", styles["Normal"])

        data = [["String Cell", paragraph], [paragraph, "Another String"]]
        colWidths = [50 * mm, 50 * mm]

        table = self.pdf_mixin.create_table(data, colWidths)

        self.assertIsInstance(table, Table)
        self.assertEqual(len(table._argW), 2)

    def test_create_table_with_mixed_data_types(self):
        """Test table creation with mixed cell data types."""
        styles = self.pdf_mixin.get_default_styles()
        paragraph = Paragraph("Test Paragraph", styles["Normal"])

        data = [
            ["String", ("Tuple Style", "Normal")],
            [paragraph, 123],  # Non-string converted to string
            [None, ""],  # None converted to string
        ]
        colWidths = [50 * mm, 50 * mm]

        table = self.pdf_mixin.create_table(data, colWidths)

        self.assertIsInstance(table, Table)
        self.assertEqual(len(table._argW), 2)

    def test_create_table_custom_alignment(self):
        """Test table creation with custom horizontal alignment."""
        data = [["Cell 1", "Cell 2"]]
        colWidths = [50 * mm, 50 * mm]

        table = self.pdf_mixin.create_table(data, colWidths, hAlign="CENTER")

        self.assertIsInstance(table, Table)
        self.assertEqual(table.hAlign, "CENTER")

    def test_create_table_custom_style(self):
        """Test table creation with custom table style."""
        data = [["Cell 1", "Cell 2"]]
        colWidths = [50 * mm, 50 * mm]
        custom_style = TableStyle([("BACKGROUND", (0, 0), (-1, -1), HexColor("#CCCCCC"))])

        table = self.pdf_mixin.create_table(data, colWidths, table_style=custom_style)

        self.assertIsInstance(table, Table)

    def test_create_table_repeat_rows(self):
        """Test table creation with header row repetition."""
        data = [["Header 1", "Header 2"], ["Row 1", "Row 2"], ["Row 3", "Row 4"]]
        colWidths = [50 * mm, 50 * mm]

        table = self.pdf_mixin.create_table(data, colWidths, repeatRows=2)

        self.assertIsInstance(table, Table)
        self.assertEqual(table.repeatRows, 2)

    @patch("sfd.views.common.pdf.settings")
    def test_get_pdf_temporary_path(self, mock_settings):
        """Test PDF temporary path retrieval."""
        mock_settings.TEMP_DIR = "/tmp/test"

        path = self.pdf_mixin.get_pdf_temporary_path()

        self.assertEqual(path, "/tmp/test")

    @patch("sfd.views.common.pdf.datetime")
    def test_get_zip_file_name_default(self, mock_datetime):
        """Test ZIP file name generation with default model name."""
        mock_datetime.now.return_value.strftime.return_value = "20240115_143045"

        request = self.factory.get("/")
        filename = self.pdf_mixin.get_zip_file_name(request)

        expected = f"{self.pdf_mixin.model._meta.verbose_name}_20240115_143045.zip"
        self.assertEqual(filename, expected)

    @patch("sfd.views.common.pdf.datetime")
    def test_get_zip_file_name_custom(self, mock_datetime):
        """Test ZIP file name generation with custom name."""
        mock_datetime.now.return_value.strftime.return_value = "20240115_143045"

        request = self.factory.get("/")
        filename = self.pdf_mixin.get_zip_file_name(request, name="カスタム名")

        expected = "カスタム名_20240115_143045.zip"
        self.assertEqual(filename, expected)

    def test_create_pdf_files_not_implemented(self):
        """Test that create_pdf_files raises NotImplementedError in base class."""

        # Create a direct instance of BasePdfMixin (not the mock)
        class TestPdfMixin(BasePdfMixin):
            model = Municipality

        mixin = TestPdfMixin()
        request = self.factory.get("/")

        with self.assertRaises(NotImplementedError) as context:
            mixin.create_pdf_files(request, None)

        self.assertIn("create_pdf_files() must be implemented", str(context.exception))

    def test_get_table_style_multiple_extra_styles(self):
        """Test table style creation with multiple extra styles."""
        extra_styles = [
            ("BACKGROUND", (0, 0), (-1, 0), HexColor("#FF0000")),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 12),
            ("ALIGN", (1, 1), (2, 2), "CENTER"),
        ]

        style = self.pdf_mixin.get_table_style(has_grid=True, extra_styles=extra_styles)

        self.assertIsInstance(style, TableStyle)
        commands = [cmd[0] for cmd in style.getCommands()]
        self.assertIn("BACKGROUND", commands)
        self.assertIn("FONTNAME", commands)
        self.assertIn("FONTSIZE", commands)
        # Should have multiple ALIGN commands (base + extra)
        align_count = commands.count("ALIGN")
        self.assertGreaterEqual(align_count, 2)

    def test_create_table_with_image_objects(self):
        """Test table creation with ReportLab Image objects."""
        from reportlab.platypus import Image

        # Create mock Image object
        mock_image = Mock(spec=Image)
        mock_image.__class__ = Image

        data = [["Text Cell", mock_image], [mock_image, "Another Text"]]
        colWidths = [50 * mm, 50 * mm]

        table = self.pdf_mixin.create_table(data, colWidths)

        self.assertIsInstance(table, Table)
        self.assertEqual(len(table._argW), 2)

    def test_create_table_with_numeric_data(self):
        """Test table creation with various numeric data types."""
        data = [
            ["Label", "Value"],
            ["Integer", 42],
            ["Float", 3.14159],
            ["Negative", -100],
            ["Zero", 0],
            ["Large Number", 1234567890],
        ]
        colWidths = [40 * mm, 30 * mm]

        table = self.pdf_mixin.create_table(data, colWidths)

        self.assertIsInstance(table, Table)
        self.assertEqual(len(table._argW), 2)

    def test_create_table_with_boolean_and_none_data(self):
        """Test table creation with boolean and None data types."""
        data = [
            ["Field", "Value"],
            ["True", True],
            ["False", False],
            ["None", None],
            ["Empty String", ""],
        ]
        colWidths = [40 * mm, 30 * mm]

        table = self.pdf_mixin.create_table(data, colWidths)

        self.assertIsInstance(table, Table)
        self.assertEqual(len(table._argW), 2)

    def test_create_table_with_right_alignment(self):
        """Test table creation with RIGHT horizontal alignment."""
        data = [["Header 1", "Header 2"], ["Cell 1", "Cell 2"]]
        colWidths = [50 * mm, 50 * mm]

        table = self.pdf_mixin.create_table(data, colWidths, hAlign="RIGHT")

        self.assertIsInstance(table, Table)
        self.assertEqual(table.hAlign, "RIGHT")

    def test_create_table_with_center_alignment(self):
        """Test table creation with CENTER horizontal alignment."""
        data = [["Header 1", "Header 2"], ["Cell 1", "Cell 2"]]
        colWidths = [50 * mm, 50 * mm]

        table = self.pdf_mixin.create_table(data, colWidths, hAlign="CENTER")

        self.assertIsInstance(table, Table)
        self.assertEqual(table.hAlign, "CENTER")

    def test_create_table_with_zero_repeat_rows(self):
        """Test table creation with no header row repetition."""
        data = [["Header 1", "Header 2"], ["Row 1", "Row 2"], ["Row 3", "Row 4"]]
        colWidths = [50 * mm, 50 * mm]

        table = self.pdf_mixin.create_table(data, colWidths, repeatRows=0)

        self.assertIsInstance(table, Table)
        self.assertEqual(table.repeatRows, 0)

    def test_create_table_with_large_repeat_rows(self):
        """Test table creation with large repeat rows value."""
        data = [["H1", "H2"], ["H3", "H4"], ["R1", "R2"], ["R3", "R4"]]
        colWidths = [50 * mm, 50 * mm]

        table = self.pdf_mixin.create_table(data, colWidths, repeatRows=3)

        self.assertIsInstance(table, Table)
        self.assertEqual(table.repeatRows, 3)

    def test_create_table_single_column(self):
        """Test table creation with single column data."""
        data = [["Header"], ["Cell 1"], ["Cell 2"], ["Cell 3"]]
        colWidths = [100 * mm]

        table = self.pdf_mixin.create_table(data, colWidths)

        self.assertIsInstance(table, Table)
        self.assertEqual(len(table._argW), 1)
        self.assertEqual(table._argW[0], 100 * mm)

    def test_create_table_single_row(self):
        """Test table creation with single row data."""
        data = [["Cell 1", "Cell 2", "Cell 3"]]
        colWidths = [30 * mm, 40 * mm, 50 * mm]

        table = self.pdf_mixin.create_table(data, colWidths)

        self.assertIsInstance(table, Table)
        self.assertEqual(len(table._argW), 3)

    def test_create_table_with_inconsistent_row_lengths(self):
        """Test table creation with rows of different lengths."""
        data = [
            ["H1", "H2", "H3"],
            ["Cell 1", "Cell 2"],  # Missing third column
            ["Cell 3", "Cell 4", "Cell 5", "Cell 6"],  # Extra columns
            ["Cell 7"],  # Single column
        ]
        colWidths = [30 * mm, 30 * mm, 30 * mm]

        table = self.pdf_mixin.create_table(data, colWidths)

        self.assertIsInstance(table, Table)
        # ReportLab may adjust columns based on actual data, so just verify table creation
        self.assertGreaterEqual(len(table._argW), 3)
        # The table should accommodate the largest row (4 columns)
        self.assertEqual(len(table._argW), 4)

    @patch("sfd.views.common.pdf.settings")
    def test_get_pdf_temporary_path_custom_setting(self, mock_settings):
        """Test PDF temporary path with custom TEMP_DIR setting."""
        mock_settings.TEMP_DIR = "/custom/temp/directory"

        path = self.pdf_mixin.get_pdf_temporary_path()

        self.assertEqual(path, "/custom/temp/directory")

    @patch("sfd.views.common.pdf.datetime")
    def test_get_zip_file_name_with_queryset(self, mock_datetime):
        """Test ZIP file name generation with queryset parameter."""
        mock_datetime.now.return_value.strftime.return_value = "20240115_143045"

        request = self.factory.get("/")
        queryset = Municipality.objects.all()
        filename = self.pdf_mixin.get_zip_file_name(request, queryset=queryset)

        expected = f"{self.pdf_mixin.model._meta.verbose_name}_20240115_143045.zip"
        self.assertEqual(filename, expected)

    @patch("sfd.views.common.pdf.datetime")
    def test_get_zip_file_name_with_empty_name(self, mock_datetime):
        """Test ZIP file name generation with empty string name."""
        mock_datetime.now.return_value.strftime.return_value = "20240115_143045"

        request = self.factory.get("/")
        filename = self.pdf_mixin.get_zip_file_name(request, name="")

        expected = f"{self.pdf_mixin.model._meta.verbose_name}_20240115_143045.zip"
        self.assertEqual(filename, expected)

    def test_create_pdf_files_with_empty_queryset(self):
        """Test that create_pdf_files raises NotImplementedError with empty queryset."""

        # Create a direct instance of BasePdfMixin (not the mock)
        class TestPdfMixin(BasePdfMixin):
            model = Municipality

        mixin = TestPdfMixin()
        request = self.factory.get("/")
        empty_queryset = Municipality.objects.none()

        with self.assertRaises(NotImplementedError) as context:
            mixin.create_pdf_files(request, empty_queryset)

        self.assertIn("create_pdf_files() must be implemented", str(context.exception))

    def test_font_attribute_types(self):
        """Test that font attributes are strings."""
        self.assertIsInstance(self.pdf_mixin.regular_font, str)
        self.assertIsInstance(self.pdf_mixin.bold_font, str)
        self.assertIsInstance(self.pdf_mixin.thin_font, str)

    def test_font_size_attribute_types(self):
        """Test that font size attributes are integers."""
        self.assertIsInstance(self.pdf_mixin.title_font_size, int)
        self.assertIsInstance(self.pdf_mixin.sub_title_font_size, int)
        self.assertIsInstance(self.pdf_mixin.normal_font_size, int)
        self.assertIsInstance(self.pdf_mixin.subscript_font_size, int)

    def test_font_size_hierarchy(self):
        """Test that font sizes follow expected hierarchy."""
        self.assertGreater(self.pdf_mixin.title_font_size, self.pdf_mixin.sub_title_font_size)
        self.assertGreater(self.pdf_mixin.sub_title_font_size, self.pdf_mixin.normal_font_size)
        self.assertGreater(self.pdf_mixin.normal_font_size, self.pdf_mixin.subscript_font_size)

    def test_page_margin_types(self):
        """Test that page margin attributes are numeric."""
        self.assertTrue(isinstance(self.pdf_mixin.page_margin_left, int | float))
        self.assertTrue(isinstance(self.pdf_mixin.page_margin_right, int | float))
        self.assertTrue(isinstance(self.pdf_mixin.page_margin_top, int | float))
        self.assertTrue(isinstance(self.pdf_mixin.page_margin_bottom, int | float))

    def test_page_margins_positive_values(self):
        """Test that page margins have positive values."""
        self.assertGreater(self.pdf_mixin.page_margin_left, 0)
        self.assertGreater(self.pdf_mixin.page_margin_right, 0)
        self.assertGreater(self.pdf_mixin.page_margin_top, 0)
        self.assertGreater(self.pdf_mixin.page_margin_bottom, 0)

    def test_cell_label_bg_color_type(self):
        """Test that cell background color is HexColor instance."""
        self.assertIsInstance(self.pdf_mixin.cell_label_bg_color, type(HexColor("#FFFFFF")))

    def test_get_urls_includes_pdf_url(self):
        """Test that custom PDF URL is included in admin URLs."""
        # Get the URLs from the mixin
        urls = self.pdf_mixin.get_urls()

        # Check that we have at least one URL (the PDF generation URL)
        self.assertGreaterEqual(len(urls), 1)

        # Find the PDF URL among the returned URLs
        pdf_url = None
        for url in urls:
            if hasattr(url.pattern, "_route") and url.pattern._route == "generate_pdf/":
                pdf_url = url
                break

        self.assertIsNotNone(pdf_url, "PDF URL not found in returned URLs")

        expected_name = f"{self.pdf_mixin.model._meta.app_label}_{self.pdf_mixin.model._meta.model_name}_generate_pdf"
        self.assertEqual(pdf_url.name, expected_name)

    def test_get_actions_includes_pdf_action(self):
        """Test that PDF generation action is included in admin actions."""
        request = self.factory.get("/")
        request.user = self.user

        # Get actions from the mixin
        actions = self.pdf_mixin.get_actions(request)

        self.assertIn("generate_pdf_selected", actions)

        action_func, action_name, action_description = actions["generate_pdf_selected"]
        self.assertEqual(action_func, generate_pdf_selected)
        self.assertEqual(action_name, "generate_pdf_selected")
        self.assertEqual(action_description, generate_pdf_selected.short_description)
        self.assertEqual(action_func, generate_pdf_selected)
        self.assertEqual(action_name, "generate_pdf_selected")
        self.assertEqual(action_description, generate_pdf_selected.short_description)

    @patch("django.contrib.admin.ModelAdmin.changelist_view")
    def test_changelist_view_adds_pdf_context(self, mock_super_changelist):
        """Test that changelist view adds PDF-related context variables."""
        # Setup mocks
        mock_super_changelist.return_value = Mock()

        request = self.factory.get("/?search=test&status=active")
        request.user = self.user

        self.pdf_mixin.changelist_view(request)

        # Verify super().changelist_view was called with extra context
        mock_super_changelist.assert_called_once()
        args, kwargs = mock_super_changelist.call_args
        extra_context = kwargs.get("extra_context", {})

        self.assertIn("generate_pdf_url", extra_context)  # Note: typo preserved for compatibility
        self.assertIn("pdf_title", extra_context)
        self.assertIn("pdf_message", extra_context)
        self.assertIn("pdf_button", extra_context)

        # Verify URL includes query parameters
        expected_url = "/admin/sfd/municipality/generate_pdf/?search=test&status=active"
        self.assertEqual(extra_context["generate_pdf_url"], expected_url)

    @patch("django.contrib.admin.ModelAdmin.changelist_view")
    def test_changelist_view_no_query_params(self, mock_super_changelist):
        """Test changelist view without query parameters."""
        # Setup mocks
        mock_super_changelist.return_value = Mock()

        request = self.factory.get("/")  # No query parameters
        request.user = self.user

        self.pdf_mixin.changelist_view(request)

        # Verify super().changelist_view was called with extra context
        args, kwargs = mock_super_changelist.call_args
        extra_context = kwargs.get("extra_context", {})

        # URL should not have query string
        self.assertEqual(extra_context["generate_pdf_url"], "/admin/sfd/municipality/generate_pdf/")

    @patch("django.contrib.admin.ModelAdmin.changelist_view")
    def test_changelist_view_with_existing_extra_context(self, mock_super_changelist):
        """Test changelist view with existing extra_context parameter."""
        # Setup mocks
        mock_super_changelist.return_value = Mock()

        request = self.factory.get("/?filter=active")
        request.user = self.user

        # Pass existing extra_context
        existing_context = {"existing_key": "existing_value", "another_key": 123}

        self.pdf_mixin.changelist_view(request, extra_context=existing_context)

        # Verify super().changelist_view was called with merged context
        args, kwargs = mock_super_changelist.call_args
        extra_context = kwargs.get("extra_context", {})

        # Should preserve existing context
        self.assertEqual(extra_context["existing_key"], "existing_value")
        self.assertEqual(extra_context["another_key"], 123)

        # Should add PDF-related context
        self.assertIn("generate_pdf_url", extra_context)
        self.assertIn("pdf_title", extra_context)
        self.assertIn("pdf_message", extra_context)
        self.assertIn("pdf_button", extra_context)

    @patch("django.contrib.admin.ModelAdmin.changelist_view")
    def test_changelist_view_with_complex_query_params(self, mock_super_changelist):
        """Test changelist view with complex query parameters."""
        # Setup mocks
        mock_super_changelist.return_value = Mock()

        # Complex query with multiple filters, search, and special characters
        request = self.factory.get("/?search=テスト&status__in=active,pending&created__gte=2024-01-01&page=2")
        request.user = self.user

        self.pdf_mixin.changelist_view(request)

        # Verify super().changelist_view was called with extra context
        args, kwargs = mock_super_changelist.call_args
        extra_context = kwargs.get("extra_context", {})

        # URL should include all query parameters
        pdf_url = extra_context["generate_pdf_url"]
        self.assertTrue(pdf_url.startswith("/admin/sfd/municipality/generate_pdf/?"))
        self.assertIn("search=%E3%83%86%E3%82%B9%E3%83%88", pdf_url)  # URL-encoded Japanese
        self.assertIn("status__in=active%2Cpending", pdf_url)
        self.assertIn("created__gte=2024-01-01", pdf_url)
        self.assertIn("page=2", pdf_url)

    def test_get_urls_url_pattern_details(self):
        """Test detailed URL pattern configuration."""
        urls = self.pdf_mixin.get_urls()

        # Find the PDF URL
        pdf_url = None
        for url in urls:
            if hasattr(url.pattern, "_route") and url.pattern._route == "generate_pdf/":
                pdf_url = url
                break

        self.assertIsNotNone(pdf_url)

        # Test URL name format
        expected_name = f"{self.pdf_mixin.model._meta.app_label}_{self.pdf_mixin.model._meta.model_name}_generate_pdf"
        self.assertEqual(pdf_url.name, expected_name)

        # Test URL pattern
        self.assertEqual(pdf_url.pattern._route, "generate_pdf/")

    def test_get_actions_action_properties(self):
        """Test detailed properties of the PDF generation action."""
        request = self.factory.get("/")
        request.user = self.user

        actions = self.pdf_mixin.get_actions(request)

        self.assertIn("generate_pdf_selected", actions)

        action_func, action_name, action_description = actions["generate_pdf_selected"]

        # Test action function
        self.assertEqual(action_func, generate_pdf_selected)
        self.assertTrue(callable(action_func))

        # Test action name
        self.assertEqual(action_name, "generate_pdf_selected")
        self.assertIsInstance(action_name, str)

        # Test action description
        self.assertEqual(action_description, generate_pdf_selected.short_description)
        self.assertEqual(action_description, _("Generate PDF for selected rows"))

    def test_get_actions_preserves_existing_actions(self):
        """Test that PDF action is added without removing existing actions."""
        # Mock existing actions
        self.pdf_mixin.get_actions = Mock(wraps=self.pdf_mixin.get_actions)

        # Create mock parent actions
        parent_actions = {
            "delete_selected": (Mock(), "delete_selected", "Delete selected items"),
            "custom_action": (Mock(), "custom_action", "Custom action"),
        }

        # Mock the super().get_actions call
        with patch.object(admin.ModelAdmin, "get_actions", return_value=parent_actions):
            request = self.factory.get("/")
            request.user = self.user

            actions = self.pdf_mixin.get_actions(request)

            # Should preserve existing actions
            self.assertIn("delete_selected", actions)
            self.assertIn("custom_action", actions)

            # Should add PDF action
            self.assertIn("generate_pdf_selected", actions)

            # Total should be original + 1
            self.assertEqual(len(actions), 3)

    def test_admin_site_integration(self):
        """Test integration with Django admin site."""
        # Test that the mixin properly inherits from admin.ModelAdmin
        self.assertIsInstance(self.pdf_mixin, admin.ModelAdmin)

        # Test that model is properly set
        self.assertEqual(self.pdf_mixin.model, Municipality)

        # Test that admin_site is available
        self.assertIsNotNone(self.pdf_mixin.admin_site)

    def test_create_table_with_invalid_styles_dict(self):
        """Test table creation when get_default_styles returns incomplete dict."""
        # Create a proper mock style object that mimics ParagraphStyle

        # Use a real ParagraphStyle to avoid Mock attribute issues
        mock_normal_style = ParagraphStyle(
            "Normal",
            fontName="Helvetica",
            fontSize=10,
            leading=12,
        )

        # Override get_default_styles to return incomplete styles but with proper Normal style
        self.pdf_mixin.get_default_styles = Mock(return_value={"Normal": mock_normal_style})

        data = [["Cell with unknown style"]]
        colWidths = [50 * mm]

        # This should handle the case gracefully by falling back to Normal style
        table = self.pdf_mixin.create_table(data, colWidths)
        self.assertIsInstance(table, Table)

    def test_create_table_empty_data(self):
        """Test table creation with empty data."""
        data = []
        colWidths = []

        table = self.pdf_mixin.create_table(data, colWidths)
        self.assertIsInstance(table, Table)

    def test_create_table_none_cell_values(self):
        """Test table creation with None cell values."""
        data = [[None, "Valid Cell"], ["Another Cell", None]]
        colWidths = [50 * mm, 50 * mm]

        table = self.pdf_mixin.create_table(data, colWidths)
        self.assertIsInstance(table, Table)

    def test_get_table_style_none_extra_styles(self):
        """Test table style creation with None extra_styles parameter."""
        style = self.pdf_mixin.get_table_style(extra_styles=None)
        self.assertIsInstance(style, TableStyle)

    def test_get_table_style_empty_extra_styles(self):
        """Test table style creation with empty extra_styles list."""
        style = self.pdf_mixin.get_table_style(extra_styles=[])
        self.assertIsInstance(style, TableStyle)

    def test_zip_filename_with_special_characters(self):
        """Test ZIP filename generation with special characters in model name."""
        # Mock a model with special characters in verbose_name
        mock_model = Mock()
        mock_model._meta.verbose_name = "請求書/見積書 (特殊文字)"
        self.pdf_mixin.model = mock_model

        with patch("sfd.views.common.pdf.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "20240115_143045"

            request = self.factory.get("/")
            filename = self.pdf_mixin.get_zip_file_name(request)

            expected = "請求書/見積書 (特殊文字)_20240115_143045.zip"
            self.assertEqual(filename, expected)

    def test_create_table_with_unknown_tuple_style(self):
        """Test table creation with tuple containing unknown style name."""
        # Create a proper mock style object that mimics ParagraphStyle

        # Use a real ParagraphStyle to avoid Mock attribute issues
        mock_normal_style = ParagraphStyle(
            "Normal",
            fontName="Helvetica",
            fontSize=10,
            leading=12,
        )

        # Override get_default_styles to return limited styles
        self.pdf_mixin.get_default_styles = Mock(return_value={"Normal": mock_normal_style})

        data = [[("Text with unknown style", "UnknownStyle")]]
        colWidths = [50 * mm]

        # Should raise KeyError when style is not found (current implementation behavior)
        with self.assertRaises(KeyError):
            self.pdf_mixin.create_table(data, colWidths)

    def test_create_table_with_complex_mixed_data(self):
        """Test table creation with complex mixed data types in a single table."""
        from reportlab.platypus import Image

        # Create mock objects
        mock_normal_style = ParagraphStyle("Normal", fontName="Helvetica", fontSize=10, leading=12)
        mock_bold_style = ParagraphStyle("Normal", fontName="Helvetica-Bold", fontSize=10, leading=12)

        self.pdf_mixin.get_default_styles = Mock(return_value={"Normal": mock_bold_style})

        mock_paragraph = Paragraph("Pre-formatted", mock_normal_style)
        mock_image = Mock(spec=Image)
        mock_image.__class__ = Image

        data = [
            ["String", ("Tuple Bold", "Normal"), mock_paragraph, mock_image, 42],
            [None, True, False, 0, 3.14],
            ["", "Normal Text", mock_paragraph, ("Another Tuple", "Normal"), -100],
        ]
        colWidths = [20 * mm, 25 * mm, 30 * mm, 25 * mm, 20 * mm]

        table = self.pdf_mixin.create_table(data, colWidths)

        self.assertIsInstance(table, Table)
        self.assertEqual(len(table._argW), 5)

    def test_get_table_style_with_malformed_extra_styles(self):
        """Test table style creation with malformed extra styles."""
        # Test with various malformed extra styles
        malformed_styles = [
            ("INVALID_COMMAND",),  # Missing required parameters
            ("BACKGROUND",),  # Incomplete command
            None,  # None in the list
        ]

        # Should handle malformed styles gracefully
        try:
            style = self.pdf_mixin.get_table_style(extra_styles=malformed_styles)
            self.assertIsInstance(style, TableStyle)
        except (TypeError, ValueError):
            # Expected behavior when ReportLab encounters malformed styles
            pass

    def test_create_table_with_very_large_data(self):
        """Test table creation with large amount of data."""
        # Create large dataset (100 rows x 5 columns)
        data = []
        for i in range(100):
            row = [f"Cell_{i}_{j}" for j in range(5)]
            data.append(row)

        colWidths = [20 * mm] * 5

        table = self.pdf_mixin.create_table(data, colWidths)

        self.assertIsInstance(table, Table)
        self.assertEqual(len(table._argW), 5)

    def test_create_table_with_unicode_characters(self):
        """Test table creation with various Unicode characters."""
        data = [
            ["普通", "中文", "한글", "العربية", "Русский"],
            ["🎯", "💡", "📊", "🔍", "📈"],
            ["①②③", "αβγ", "∑∏∆", "≤≥≠", "∞±×"],
            ["▲▼◆", "★☆♪", "→←↑↓", "■□●○", "♠♣♥♦"],
        ]
        colWidths = [25 * mm] * 5

        table = self.pdf_mixin.create_table(data, colWidths)

        self.assertIsInstance(table, Table)
        self.assertEqual(len(table._argW), 5)

    def test_create_table_empty_list_rows(self):
        """Test table creation with empty list as row data."""
        data = [
            ["Header 1", "Header 2"],
            [],  # Empty row
            ["Cell 1", "Cell 2"],
            [],  # Another empty row
        ]
        colWidths = [50 * mm, 50 * mm]

        table = self.pdf_mixin.create_table(data, colWidths)

        self.assertIsInstance(table, Table)
        self.assertEqual(len(table._argW), 2)

    def test_create_table_nested_list_data(self):
        """Test table creation with nested list data (should be flattened)."""
        data = [
            ["Header", ["Nested", "List"]],  # Nested list in cell
            [["Another", "Nested"], "Normal Cell"],
        ]
        colWidths = [50 * mm, 50 * mm]

        table = self.pdf_mixin.create_table(data, colWidths)

        self.assertIsInstance(table, Table)
        self.assertEqual(len(table._argW), 2)

    def test_create_table_with_dictionary_data(self):
        """Test table creation with dictionary data (should convert to string)."""
        data = [
            ["String", {"key": "value"}],
            [{"another": "dict"}, "Normal Text"],
        ]
        colWidths = [50 * mm, 50 * mm]

        table = self.pdf_mixin.create_table(data, colWidths)

        self.assertIsInstance(table, Table)
        self.assertEqual(len(table._argW), 2)

    def test_font_configuration_values(self):
        """Test specific font configuration values."""
        # Test exact font name values
        self.assertEqual(self.pdf_mixin.regular_font, "ipaexm")
        self.assertEqual(self.pdf_mixin.bold_font, "NotoSansJP-Bold")
        self.assertEqual(self.pdf_mixin.thin_font, "NotoSansJP-Thin")

        # Test font names are not empty
        self.assertNotEqual(self.pdf_mixin.regular_font, "")
        self.assertNotEqual(self.pdf_mixin.bold_font, "")
        self.assertNotEqual(self.pdf_mixin.thin_font, "")

    def test_font_size_values(self):
        """Test specific font size values."""
        # Test exact font size values
        self.assertEqual(self.pdf_mixin.title_font_size, 14)
        self.assertEqual(self.pdf_mixin.sub_title_font_size, 12)
        self.assertEqual(self.pdf_mixin.normal_font_size, 10)
        self.assertEqual(self.pdf_mixin.subscript_font_size, 8)

        # Test all font sizes are positive
        self.assertGreater(self.pdf_mixin.title_font_size, 0)
        self.assertGreater(self.pdf_mixin.sub_title_font_size, 0)
        self.assertGreater(self.pdf_mixin.normal_font_size, 0)
        self.assertGreater(self.pdf_mixin.subscript_font_size, 0)

    def test_page_size_configuration(self):
        """Test page size configuration."""
        from reportlab.lib.pagesizes import A4

        self.assertEqual(self.pdf_mixin.page_size, A4)
        self.assertIsInstance(self.pdf_mixin.page_size, tuple)
        self.assertEqual(len(self.pdf_mixin.page_size), 2)  # Width and height

    def test_margin_equality(self):
        """Test that left and right margins are equal, top and bottom are equal."""
        # Standard practice: left and right margins should be equal
        self.assertEqual(self.pdf_mixin.page_margin_left, self.pdf_mixin.page_margin_right)

        # Standard practice: top and bottom margins should be equal
        self.assertEqual(self.pdf_mixin.page_margin_top, self.pdf_mixin.page_margin_bottom)

        # All margins should be 20mm
        expected_margin = 20 * mm
        self.assertEqual(self.pdf_mixin.page_margin_left, expected_margin)
        self.assertEqual(self.pdf_mixin.page_margin_right, expected_margin)
        self.assertEqual(self.pdf_mixin.page_margin_top, expected_margin)
        self.assertEqual(self.pdf_mixin.page_margin_bottom, expected_margin)

    def test_cell_label_bg_color_value(self):
        """Test cell label background color specific value."""
        expected_color = HexColor("#CAEBAA")
        self.assertEqual(self.pdf_mixin.cell_label_bg_color, expected_color)

        # Test that the color represents the correct hex value
        actual_color = self.pdf_mixin.cell_label_bg_color
        self.assertIsInstance(actual_color, type(expected_color))
        # Check that colors are equivalent (may have different string representations)
        self.assertEqual(actual_color.red, expected_color.red)
        self.assertEqual(actual_color.green, expected_color.green)
        self.assertEqual(actual_color.blue, expected_color.blue)

    def test_class_inheritance(self):
        """Test that TestModelAdmin properly inherits from BasePdfMixin."""
        self.assertIsInstance(self.pdf_mixin, BasePdfMixin)
        self.assertTrue(hasattr(self.pdf_mixin, "get_table_style"))
        self.assertTrue(hasattr(self.pdf_mixin, "create_table"))
        self.assertTrue(hasattr(self.pdf_mixin, "get_pdf_temporary_path"))
        self.assertTrue(hasattr(self.pdf_mixin, "get_zip_file_name"))
        self.assertTrue(hasattr(self.pdf_mixin, "generate_pdf"))
        self.assertTrue(hasattr(self.pdf_mixin, "create_pdf_files"))

    def test_required_methods_exist(self):
        """Test that all required BasePdfMixin methods exist."""
        required_methods = [
            "get_table_style",
            "create_table",
            "get_pdf_temporary_path",
            "get_zip_file_name",
            "generate_pdf",
            "create_pdf_files",
            "get_urls",
            "get_actions",
            "changelist_view",
        ]

        for method_name in required_methods:
            self.assertTrue(hasattr(self.pdf_mixin, method_name), f"Method {method_name} is missing")
            self.assertTrue(callable(getattr(self.pdf_mixin, method_name)), f"Method {method_name} is not callable")

    def test_japanese_font_configuration(self):
        """Test that Japanese fonts are properly configured."""
        # Test regular font for Japanese text
        self.assertEqual(self.pdf_mixin.regular_font, "ipaexm")

        # Test that NotoSans fonts are available for bold/thin
        self.assertTrue(self.pdf_mixin.bold_font.startswith("NotoSansJP"))
        self.assertTrue(self.pdf_mixin.thin_font.startswith("NotoSansJP"))

    def test_create_table_with_japanese_text(self):
        """Test table creation with Japanese text content."""
        japanese_data = [["項目名", "値段"], ["商品A", "¥1,000"], ["商品B", "¥2,500"], ["合計", "¥3,500"]]
        colWidths = [50 * mm, 30 * mm]

        table = self.pdf_mixin.create_table(japanese_data, colWidths)

        self.assertIsInstance(table, Table)
        self.assertEqual(len(table._argW), 2)

    def test_create_table_with_japanese_styling(self):
        """Test table creation with Japanese text and custom styling."""
        japanese_data = [
            [("見出し１", "Normal"), ("見出し２", "Normal")],
            ["内容１", ("重要な内容", "Normal")],
            [("小計", "Normal"), "¥10,000"],
        ]
        colWidths = [60 * mm, 40 * mm]

        table = self.pdf_mixin.create_table(japanese_data, colWidths)

        self.assertIsInstance(table, Table)
        self.assertEqual(len(table._argW), 2)

    def test_japanese_zip_filename_encoding(self):
        """Test ZIP filename generation with Japanese characters."""
        mock_model = Mock()
        mock_model._meta.verbose_name = "月次請求書データ"
        self.pdf_mixin.model = mock_model

        with patch("sfd.views.common.pdf.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "20240115_143045"

            request = self.factory.get("/")
            filename = self.pdf_mixin.get_zip_file_name(request)

            expected = "月次請求書データ_20240115_143045.zip"
            self.assertEqual(filename, expected)

            # Verify the filename can be properly URL-encoded
            encoded = quote(filename)
            self.assertIsInstance(encoded, str)
            self.assertIn("20240115_143045.zip", encoded)

    def test_japanese_text_edge_cases(self):
        """Test Japanese text with edge cases like long lines and mixed scripts."""
        edge_case_data = [
            ["項目", "非常に長い日本語のテキストです。これは改行処理とフォント処理のテストケースとして使用されます。"],
            ["Mixed", "日本語とEnglishの混合テキスト with 数字123 and symbols!@#"],
            ["Katakana", "カタカナテキストのテストケース：ソフトウェア・コンピュータ・プログラム"],
            ["Hiragana", "ひらがなテキストのテストけーす：あいうえお・かきくけこ・さしすせそ"],
            ["Special", "特殊文字：①②③④⑤⑥⑦⑧⑨⑩"],
        ]
        colWidths = [30 * mm, 80 * mm]

        table = self.pdf_mixin.create_table(edge_case_data, colWidths)

        self.assertIsInstance(table, Table)
        self.assertEqual(len(table._argW), 2)

    def test_japanese_corporate_terms(self):
        """Test table creation with common Japanese corporate terminology."""
        corporate_data = [
            ["会社名", "株式会社テストコーポレーション"],
            ["事業内容", "ソフトウェア開発・システム構築・運用保守"],
            ["所在地", "〒100-0001 東京都千代田区千代田1-1-1"],
            ["電話番号", "03-1234-5678"],
            ["設立年月日", "令和6年1月15日"],
            ["資本金", "1,000万円"],
            ["代表取締役", "田中太郎"],
        ]
        colWidths = [40 * mm, 70 * mm]

        table = self.pdf_mixin.create_table(corporate_data, colWidths)

        self.assertIsInstance(table, Table)
        self.assertEqual(len(table._argW), 2)

    def test_japanese_dates_and_numbers(self):
        """Test Japanese date and number formatting."""
        date_number_data = [
            ["和暦", "令和6年7月31日"],
            ["西暦", "2025年7月31日"],
            ["金額", "¥1,234,567"],
            ["割合", "85.5%"],
            ["時刻", "午後2時30分"],
            ["数量", "1,000個"],
            ["期間", "2024年4月1日〜2025年3月31日"],
        ]
        colWidths = [30 * mm, 60 * mm]

        table = self.pdf_mixin.create_table(date_number_data, colWidths)

        self.assertIsInstance(table, Table)
        self.assertEqual(len(table._argW), 2)

    def test_japanese_business_terms_styling(self):
        """Test Japanese business terms with various styling options."""
        business_data = [
            [("見積書", "Normal"), ("作成日", "Normal")],
            ["お客様名", ("重要顧客株式会社", "Normal")],
            ["件名", "システム開発業務委託契約"],
            [("小計", "Normal"), "¥5,000,000"],
            [("消費税（10%）", "Normal"), "¥500,000"],
            [("合計金額", "Normal"), ("¥5,500,000", "Normal")],
        ]
        colWidths = [40 * mm, 50 * mm]

        table = self.pdf_mixin.create_table(business_data, colWidths)

        self.assertIsInstance(table, Table)
        self.assertEqual(len(table._argW), 2)

    def test_japanese_government_terms(self):
        """Test Japanese government and administrative terminology."""
        government_data = [
            ["都道府県", "東京都"],
            ["市区町村", "千代田区"],
            ["官公庁", "デジタル庁"],
            ["法令名", "個人情報保護法"],
            ["年度", "令和6年度"],
            ["予算", "1億2,000万円"],
            ["担当部署", "情報システム部情報企画課"],
        ]
        colWidths = [35 * mm, 65 * mm]

        table = self.pdf_mixin.create_table(government_data, colWidths)

        self.assertIsInstance(table, Table)
        self.assertEqual(len(table._argW), 2)

    @patch("os.path.join")
    @patch("builtins.open")
    def test_generate_pdf_with_none_queryset_uses_changelist(self, mock_open, mock_path_join):
        """Test generate_pdf when queryset is None - should use changelist queryset with filters."""
        # Setup mocks
        mock_path_join.return_value = "/tmp/test_file.pdf"
        mock_file_data = b"Mock PDF content from changelist"
        mock_open.return_value.__enter__.return_value.read.return_value = mock_file_data

        # Mock changelist behavior
        mock_changelist_class = Mock()
        mock_changelist_instance = Mock()
        mock_changelist_instance.get_queryset.return_value = Municipality.objects.filter(id=self.municipality1.id)
        mock_changelist_class.return_value = mock_changelist_instance

        self.pdf_mixin.get_changelist = Mock(return_value=mock_changelist_class)
        self.pdf_mixin.create_pdf_files = Mock(return_value=["changelist_file.pdf"])
        self.pdf_mixin.get_pdf_temporary_path = Mock(return_value="/tmp")

        request = self.factory.get("/?search=test&status=active")
        request.user = self.user

        response = self.pdf_mixin.generate_pdf(request, queryset=None)

        # Verify changelist was created with proper parameters
        self.pdf_mixin.get_changelist.assert_called_once_with(request)
        mock_changelist_class.assert_called_once_with(
            request,
            self.pdf_mixin.model,
            self.pdf_mixin.list_display,
            self.pdf_mixin.list_display_links,
            self.pdf_mixin.list_filter,
            self.pdf_mixin.date_hierarchy,
            self.pdf_mixin.search_fields,
            self.pdf_mixin.list_select_related,
            self.pdf_mixin.list_per_page,
            self.pdf_mixin.list_max_show_all,
            self.pdf_mixin.list_editable,
            self.pdf_mixin,
            sortable_by=self.pdf_mixin.get_sortable_by(request),
            search_help_text=self.pdf_mixin.search_help_text,
        )

        # Verify queryset was obtained from changelist
        mock_changelist_instance.get_queryset.assert_called_once_with(request)

        # Verify response
        self.assertIsInstance(response, HttpResponse)
        self.assertEqual(response["Content-Type"], "application/pdf")

    def test_generate_pdf_empty_queryset_with_none_queryset(self):
        """Test generate_pdf when None queryset results in empty changelist queryset."""
        # Mock changelist behavior to return empty queryset
        mock_changelist_class = Mock()
        mock_changelist_instance = Mock()
        mock_changelist_instance.get_queryset.return_value = Municipality.objects.none()
        mock_changelist_class.return_value = mock_changelist_instance

        self.pdf_mixin.get_changelist = Mock(return_value=mock_changelist_class)
        self.pdf_mixin.message_user = Mock()

        request = self.factory.get("/")
        request.user = self.user
        request.get_full_path = Mock(return_value="/admin/test/")

        with patch("sfd.views.common.pdf.redirect") as mock_redirect:
            self.pdf_mixin.generate_pdf(request, queryset=None)

            # Verify warning message and redirect for empty changelist
            self.pdf_mixin.message_user.assert_called_once_with(request, _("No data available for PDF generation."), level="warning")
            mock_redirect.assert_called_once_with("/admin/test/")

    @patch("os.path.join")
    @patch("builtins.open")
    def test_generate_pdf_single_file_with_japanese_filename(self, mock_open, mock_path_join):
        """Test generate_pdf for single file with Japanese characters in filename."""
        # Setup mocks
        mock_path_join.return_value = "/tmp/請求書_001.pdf"
        mock_file_data = b"Mock Japanese PDF content"
        mock_open.return_value.__enter__.return_value.read.return_value = mock_file_data

        self.pdf_mixin.create_pdf_files = Mock(return_value=["請求書_001.pdf"])
        self.pdf_mixin.get_pdf_temporary_path = Mock(return_value="/tmp")

        request = self.factory.get("/")
        request.user = self.user
        queryset = Municipality.objects.filter(id=self.municipality1.id)

        response = self.pdf_mixin.generate_pdf(request, queryset)

        # Verify response
        self.assertIsInstance(response, HttpResponse)
        self.assertEqual(response["Content-Type"], "application/pdf")

        # Verify Japanese filename is properly URL-encoded in Content-Disposition
        content_disposition = response["Content-Disposition"]
        self.assertIn("attachment", content_disposition)
        # Japanese characters should be URL-encoded in the filename
        encoded_filename = quote("請求書_001.pdf")
        self.assertIn(encoded_filename, content_disposition)

    @patch("os.path.join")
    @patch("zipfile.ZipFile")
    def test_generate_pdf_multiple_files_with_japanese_filenames(self, mock_zipfile, mock_path_join):
        """Test generate_pdf for multiple files with Japanese characters in filenames."""
        # Setup mocks
        mock_path_join.side_effect = lambda base, filename: f"{base}/{filename}"
        mock_zip_instance = Mock()
        mock_zipfile.return_value.__enter__.return_value = mock_zip_instance

        japanese_filenames = ["請求書_001.pdf", "見積書_002.pdf", "納品書_003.pdf"]
        self.pdf_mixin.create_pdf_files = Mock(return_value=japanese_filenames)
        self.pdf_mixin.get_pdf_temporary_path = Mock(return_value="/tmp")

        request = self.factory.get("/")
        request.user = self.user
        queryset = Municipality.objects.all()

        response = self.pdf_mixin.generate_pdf(request, queryset)

        # Verify response
        self.assertIsInstance(response, HttpResponse)
        self.assertEqual(response["Content-Type"], "application/zip")

        # Verify all Japanese files were added to ZIP
        self.assertEqual(mock_zip_instance.write.call_count, 3)

        # Verify each file was added with correct path and archive name
        expected_calls = [
            (("/tmp/請求書_001.pdf",), {"arcname": "請求書_001.pdf"}),
            (("/tmp/見積書_002.pdf",), {"arcname": "見積書_002.pdf"}),
            (("/tmp/納品書_003.pdf",), {"arcname": "納品書_003.pdf"}),
        ]
        actual_calls = mock_zip_instance.write.call_args_list
        for expected, actual in zip(expected_calls, actual_calls, strict=True):
            self.assertEqual(expected[0], actual[0])
            self.assertEqual(expected[1], actual[1])

    @patch("os.path.join")
    @patch("zipfile.ZipFile")
    def test_generate_pdf_large_queryset_performance(self, mock_zipfile, mock_path_join):
        """Test generate_pdf performance with large queryset (simulated)."""
        # Setup mocks for large number of files
        mock_path_join.side_effect = lambda base, filename: f"{base}/{filename}"
        mock_zip_instance = Mock()
        mock_zipfile.return_value.__enter__.return_value = mock_zip_instance

        # Simulate 100 PDF files
        large_file_list = [f"document_{i:03d}.pdf" for i in range(100)]
        self.pdf_mixin.create_pdf_files = Mock(return_value=large_file_list)
        self.pdf_mixin.get_pdf_temporary_path = Mock(return_value="/tmp")

        request = self.factory.get("/")
        request.user = self.user

        # Create a larger queryset (simulate with existing municipalities)
        queryset = Municipality.objects.all()

        response = self.pdf_mixin.generate_pdf(request, queryset)

        # Verify response
        self.assertIsInstance(response, HttpResponse)
        self.assertEqual(response["Content-Type"], "application/zip")

        # Verify all 100 files were processed
        self.assertEqual(mock_zip_instance.write.call_count, 100)

    def test_generate_pdf_create_pdf_files_exception_handling(self):
        """Test generate_pdf when create_pdf_files raises an exception."""
        # Mock create_pdf_files to raise an exception
        self.pdf_mixin.create_pdf_files = Mock(side_effect=Exception("PDF creation failed"))

        request = self.factory.get("/")
        request.user = self.user
        queryset = Municipality.objects.filter(id=self.municipality1.id)

        # The method should allow the exception to propagate
        with self.assertRaises(Exception) as context:
            self.pdf_mixin.generate_pdf(request, queryset)

        self.assertEqual(str(context.exception), "PDF creation failed")

    @patch("os.path.join")
    @patch("builtins.open")
    def test_generate_pdf_file_read_error(self, mock_open, mock_path_join):
        """Test generate_pdf when file reading fails."""
        # Setup mocks
        mock_path_join.return_value = "/tmp/test_file.pdf"
        mock_open.side_effect = FileNotFoundError("File not found")

        self.pdf_mixin.create_pdf_files = Mock(return_value=["missing_file.pdf"])
        self.pdf_mixin.get_pdf_temporary_path = Mock(return_value="/tmp")

        request = self.factory.get("/")
        request.user = self.user
        queryset = Municipality.objects.filter(id=self.municipality1.id)

        # The method should allow the exception to propagate
        with self.assertRaises(FileNotFoundError):
            self.pdf_mixin.generate_pdf(request, queryset)

    @patch("os.path.join")
    @patch("zipfile.ZipFile")
    def test_generate_pdf_zipfile_creation_error(self, mock_zipfile, mock_path_join):
        """Test generate_pdf when ZIP file creation fails."""
        # Setup mocks
        mock_path_join.side_effect = lambda base, filename: f"{base}/{filename}"
        mock_zipfile.side_effect = OSError("Cannot create ZIP file")

        self.pdf_mixin.create_pdf_files = Mock(return_value=["file1.pdf", "file2.pdf"])
        self.pdf_mixin.get_pdf_temporary_path = Mock(return_value="/tmp")

        request = self.factory.get("/")
        request.user = self.user
        queryset = Municipality.objects.all()

        # The method should allow the exception to propagate
        with self.assertRaises(OSError) as context:
            self.pdf_mixin.generate_pdf(request, queryset)

        self.assertEqual(str(context.exception), "Cannot create ZIP file")

    @patch("os.path.join")
    @patch("builtins.open")
    def test_generate_pdf_content_disposition_encoding(self, mock_open, mock_path_join):
        """Test generate_pdf Content-Disposition header encoding for various characters."""
        # Setup mocks
        mock_path_join.return_value = "/tmp/complex_filename.pdf"
        mock_file_data = b"Mock PDF content"
        mock_open.return_value.__enter__.return_value.read.return_value = mock_file_data

        # Test filename with various special characters
        complex_filename = "請求書_2024年1月_顧客名#001_最終版.pdf"
        self.pdf_mixin.create_pdf_files = Mock(return_value=[complex_filename])
        self.pdf_mixin.get_pdf_temporary_path = Mock(return_value="/tmp")

        request = self.factory.get("/")
        request.user = self.user
        queryset = Municipality.objects.filter(id=self.municipality1.id)

        response = self.pdf_mixin.generate_pdf(request, queryset)

        # Verify Content-Disposition header is properly formatted
        content_disposition = response["Content-Disposition"]

        # Should contain both quoted filename and UTF-8 encoded filename
        self.assertIn("attachment", content_disposition)
        self.assertIn(f'filename="{quote(complex_filename)}"', content_disposition)
        self.assertIn(f"filename*=UTF-8''{quote(complex_filename)}", content_disposition)

    def test_generate_pdf_zero_files_warning_message(self):
        """Test generate_pdf specific warning message when zero files are created."""
        # Override create_pdf_files to return empty list
        self.pdf_mixin.create_pdf_files = Mock(return_value=[])
        self.pdf_mixin.message_user = Mock()

        request = self.factory.get("/")
        request.user = self.user
        queryset = Municipality.objects.filter(id=self.municipality1.id)

        self.pdf_mixin.generate_pdf(request, queryset)

        # Verify specific warning message for zero files
        self.pdf_mixin.message_user.assert_called_once_with(request, _("No PDFs were created. Please check the related data."), level="warning")

    @patch("os.path.join")
    @patch("zipfile.ZipFile")
    def test_generate_pdf_zip_filename_generation(self, mock_zipfile, mock_path_join):
        """Test generate_pdf ZIP filename generation with timestamp."""
        # Setup mocks
        mock_path_join.side_effect = lambda base, filename: f"{base}/{filename}"
        mock_zip_instance = Mock()
        mock_zipfile.return_value.__enter__.return_value = mock_zip_instance

        self.pdf_mixin.create_pdf_files = Mock(return_value=["file1.pdf", "file2.pdf"])
        self.pdf_mixin.get_pdf_temporary_path = Mock(return_value="/tmp")

        # Mock get_zip_file_name to return predictable filename
        expected_zip_name = "テスト文書_20240131_143045.zip"
        self.pdf_mixin.get_zip_file_name = Mock(return_value=expected_zip_name)

        request = self.factory.get("/")
        request.user = self.user
        queryset = Municipality.objects.all()

        response = self.pdf_mixin.generate_pdf(request, queryset)

        # Verify get_zip_file_name was called with correct parameters
        self.pdf_mixin.get_zip_file_name.assert_called_once_with(request, queryset)

        # Verify Content-Disposition uses the generated filename
        content_disposition = response["Content-Disposition"]
        encoded_zip_name = quote(expected_zip_name)
        self.assertIn(encoded_zip_name, content_disposition)

    @patch("os.path.join")
    @patch("builtins.open")
    def test_generate_pdf_binary_data_handling(self, mock_open, mock_path_join):
        """Test generate_pdf handles binary PDF data correctly."""
        # Setup mocks with realistic PDF binary data
        mock_path_join.return_value = "/tmp/binary_test.pdf"

        # Simulate realistic PDF binary data with header
        mock_pdf_data = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj"
        mock_open.return_value.__enter__.return_value.read.return_value = mock_pdf_data

        self.pdf_mixin.create_pdf_files = Mock(return_value=["binary_test.pdf"])
        self.pdf_mixin.get_pdf_temporary_path = Mock(return_value="/tmp")

        request = self.factory.get("/")
        request.user = self.user
        queryset = Municipality.objects.filter(id=self.municipality1.id)

        response = self.pdf_mixin.generate_pdf(request, queryset)

        # Verify binary data is preserved in response
        self.assertEqual(response.content, mock_pdf_data)
        self.assertEqual(response["Content-Type"], "application/pdf")

    def test_get_urls_method_comprehensive(self):
        """Test get_urls method returns correct URL patterns with proper configuration."""
        # Get URLs from the mixin
        urls = self.pdf_mixin.get_urls()

        # Verify we have at least one URL (custom PDF URL + default admin URLs)
        self.assertGreaterEqual(len(urls), 1)

        # Find the PDF generation URL
        pdf_url = None
        for url in urls:
            if hasattr(url.pattern, "_route") and url.pattern._route == "generate_pdf/":
                pdf_url = url
                break

        # Verify PDF URL was found
        self.assertIsNotNone(pdf_url, "PDF generation URL not found in URL patterns")

        # Verify URL name follows the correct pattern
        expected_name = f"{self.pdf_mixin.model._meta.app_label}_{self.pdf_mixin.model._meta.model_name}_generate_pdf"
        self.assertEqual(pdf_url.name, expected_name)

        # Verify URL pattern
        self.assertEqual(pdf_url.pattern._route, "generate_pdf/")

        # Verify the view function is properly wrapped with admin_site.admin_view
        self.assertIsNotNone(pdf_url.callback)
        self.assertTrue(callable(pdf_url.callback))

    def test_get_urls_preserves_parent_urls(self):
        """Test that get_urls preserves all parent admin URLs."""
        # Mock parent URLs
        mock_parent_urls = [
            Mock(pattern=Mock(_route="add/"), name="test_add"),
            Mock(pattern=Mock(_route="<int:object_id>/change/"), name="test_change"),
            Mock(pattern=Mock(_route="<int:object_id>/delete/"), name="test_delete"),
        ]

        with patch.object(admin.ModelAdmin, "get_urls", return_value=mock_parent_urls):
            urls = self.pdf_mixin.get_urls()

            # Should have custom PDF URL + all parent URLs
            self.assertGreaterEqual(len(urls), 4)

            # Verify parent URLs are preserved
            parent_routes = [url.pattern._route for url in mock_parent_urls]
            actual_routes = [url.pattern._route for url in urls if hasattr(url.pattern, "_route")]

            for parent_route in parent_routes:
                self.assertIn(parent_route, actual_routes)

            # Verify custom PDF URL is added
            self.assertIn("generate_pdf/", actual_routes)

    def test_get_urls_custom_url_comes_first(self):
        """Test that custom PDF URL comes before parent URLs in the list."""
        urls = self.pdf_mixin.get_urls()

        # Find the PDF URL index
        pdf_url_index = None
        for i, url in enumerate(urls):
            if hasattr(url.pattern, "_route") and url.pattern._route == "generate_pdf/":
                pdf_url_index = i
                break

        self.assertIsNotNone(pdf_url_index)
        # Custom URL should be at the beginning (index 0)
        self.assertEqual(pdf_url_index, 0)

    def test_get_actions_method_comprehensive(self):
        """Test get_actions method returns correct actions with proper configuration."""
        request = self.factory.get("/")
        request.user = self.user

        # Get actions from the mixin
        actions = self.pdf_mixin.get_actions(request)

        # Verify PDF action is included
        self.assertIn("generate_pdf_selected", actions)

        # Verify action structure
        action_func, action_name, action_description = actions["generate_pdf_selected"]

        # Test action function
        self.assertEqual(action_func, generate_pdf_selected)
        self.assertTrue(callable(action_func))

        # Test action name
        self.assertEqual(action_name, "generate_pdf_selected")
        self.assertIsInstance(action_name, str)

        # Test action description
        self.assertEqual(action_description, generate_pdf_selected.short_description)
        self.assertEqual(action_description, _("Generate PDF for selected rows"))

    def test_get_actions_preserves_parent_actions(self):
        """Test that get_actions preserves all parent admin actions."""
        # Mock parent actions
        mock_parent_actions = {
            "delete_selected": (Mock(), "delete_selected", "Delete selected items"),
            "custom_action": (Mock(), "custom_action", "Custom action"),
            "export_csv": (Mock(), "export_csv", "Export as CSV"),
        }

        with patch.object(admin.ModelAdmin, "get_actions", return_value=mock_parent_actions):
            request = self.factory.get("/")
            request.user = self.user

            actions = self.pdf_mixin.get_actions(request)

            # Should have custom PDF action + all parent actions
            self.assertEqual(len(actions), 4)

            # Verify parent actions are preserved
            for action_name in mock_parent_actions.keys():
                self.assertIn(action_name, actions)

            # Verify custom PDF action is added
            self.assertIn("generate_pdf_selected", actions)

    def test_get_actions_with_none_parent_actions(self):
        """Test get_actions when parent returns None or empty dict."""
        with patch.object(admin.ModelAdmin, "get_actions", return_value=None):
            request = self.factory.get("/")
            request.user = self.user

            actions = self.pdf_mixin.get_actions(request)

            # Should handle None gracefully and still add PDF action
            self.assertIsNotNone(actions)
            self.assertIn("generate_pdf_selected", actions)

        with patch.object(admin.ModelAdmin, "get_actions", return_value={}):
            request = self.factory.get("/")
            request.user = self.user

            actions = self.pdf_mixin.get_actions(request)

            # Should handle empty dict and add PDF action
            self.assertIsNotNone(actions)
            self.assertEqual(len(actions), 1)
            self.assertIn("generate_pdf_selected", actions)

    @patch("django.contrib.admin.ModelAdmin.changelist_view")
    def test_changelist_view_method_comprehensive(self, mock_super_changelist):
        """Test changelist_view method adds correct PDF context variables."""
        from django.utils import translation

        # Setup mocks
        mock_response = Mock()
        mock_super_changelist.return_value = mock_response

        request = self.factory.get("/?search=test&filter=active")
        request.user = self.user

        with translation.override("en"):
            result = self.pdf_mixin.changelist_view(request)

            # Verify super().changelist_view was called
            mock_super_changelist.assert_called_once()
            args, kwargs = mock_super_changelist.call_args

            # Verify extra_context was passed
            self.assertIn("extra_context", kwargs)
            extra_context = kwargs["extra_context"]

            # Verify required context variables are present
            self.assertIn("generate_pdf_url", extra_context)  # Note: typo preserved for compatibility
            self.assertIn("pdf_title", extra_context)
            self.assertIn("pdf_message", extra_context)
            self.assertIn("pdf_button", extra_context)

            # Verify URL includes query parameters
            expected_url = "/admin/sfd/municipality/generate_pdf/?search=test&filter=active"
            self.assertEqual(extra_context["generate_pdf_url"], expected_url)

            # Verify extra_context variables
            self.assertEqual(extra_context["pdf_title"], "Generate Municipality PDF")
            self.assertEqual(extra_context["pdf_message"], "Are you sure you want to generate the PDF file?")
            self.assertEqual(extra_context["pdf_button"], "Generate PDF")

            # Verify the result is returned from super()
            self.assertEqual(result, mock_response)

    @patch("django.contrib.admin.ModelAdmin.changelist_view")
    def test_changelist_view_preserves_existing_extra_context(self, mock_super_changelist):
        """Test changelist_view preserves existing extra_context."""
        # Setup mocks
        mock_response = Mock()
        mock_super_changelist.return_value = mock_response

        request = self.factory.get("/")
        request.user = self.user

        # Provide existing extra_context
        existing_context = {"existing_key": "existing_value", "another_key": 123, "custom_data": {"nested": "value"}}

        self.pdf_mixin.changelist_view(request, extra_context=existing_context)

        # Verify super().changelist_view was called
        args, kwargs = mock_super_changelist.call_args
        extra_context = kwargs["extra_context"]

        # Verify existing context is preserved
        self.assertEqual(extra_context["existing_key"], "existing_value")
        self.assertEqual(extra_context["another_key"], 123)
        self.assertEqual(extra_context["custom_data"], {"nested": "value"})

        # Verify PDF context is added
        self.assertIn("generate_pdf_url", extra_context)
        self.assertIn("pdf_title", extra_context)
        self.assertIn("pdf_message", extra_context)
        self.assertIn("pdf_button", extra_context)

    @patch("django.contrib.admin.ModelAdmin.changelist_view")
    def test_changelist_view_with_empty_query_params(self, mock_super_changelist):
        """Test changelist_view with no query parameters."""
        # Setup mocks
        mock_super_changelist.return_value = Mock()

        request = self.factory.get("/")  # No query parameters
        request.user = self.user

        self.pdf_mixin.changelist_view(request)

        # Verify super().changelist_view was called
        args, kwargs = mock_super_changelist.call_args
        extra_context = kwargs["extra_context"]

        # URL should not have query string when no params
        self.assertEqual(extra_context["generate_pdf_url"], "/admin/sfd/municipality/generate_pdf/")

    @patch("django.contrib.admin.ModelAdmin.changelist_view")
    def test_changelist_view_with_complex_query_params_including_japanese(self, mock_super_changelist):
        """Test changelist_view with complex query parameters including Japanese text."""
        # Setup mocks
        mock_super_changelist.return_value = Mock()

        # Complex query with multiple filters, search, and Japanese characters
        request = self.factory.get("/?search=テスト&status__in=active,pending&created__gte=2024-01-01&page=2&ordering=-created")
        request.user = self.user

        self.pdf_mixin.changelist_view(request)

        # Verify super().changelist_view was called
        args, kwargs = mock_super_changelist.call_args
        extra_context = kwargs["extra_context"]

        # URL should include all query parameters
        pdf_url = extra_context["generate_pdf_url"]
        self.assertTrue(pdf_url.startswith("/admin/sfd/municipality/generate_pdf/?"))

        # Verify Japanese text is URL-encoded
        self.assertIn("search=%E3%83%86%E3%82%B9%E3%83%88", pdf_url)  # URL-encoded "テスト"

        # Verify other parameters are preserved
        self.assertIn("status__in=active%2Cpending", pdf_url)  # URL-encoded comma
        self.assertIn("created__gte=2024-01-01", pdf_url)
        self.assertIn("page=2", pdf_url)
        self.assertIn("ordering=-created", pdf_url)

    @patch("django.contrib.admin.ModelAdmin.changelist_view")
    def test_changelist_view_url_encoding_special_characters(self, mock_super_changelist):
        """Test changelist_view properly encodes special characters in URLs."""
        # Setup mocks
        mock_super_changelist.return_value = Mock()

        # Query with special characters that need URL encoding
        request = self.factory.get("/?search=test@example.com&filter=name with spaces&tags=tag1,tag2&special=100%")
        request.user = self.user

        self.pdf_mixin.changelist_view(request)

        # Verify super().changelist_view was called
        args, kwargs = mock_super_changelist.call_args
        extra_context = kwargs["extra_context"]

        pdf_url = extra_context["generate_pdf_url"]

        # Verify special characters are properly encoded
        self.assertIn("search=test%40example.com", pdf_url)  # @ encoded as %40
        self.assertIn("filter=name+with+spaces", pdf_url)  # spaces encoded as +
        self.assertIn("tags=tag1%2Ctag2", pdf_url)  # comma encoded as %2C
        self.assertIn("special=100%25", pdf_url)  # % encoded as %25

    def test_get_actions_action_callable_verification(self):
        """Test that the PDF action function is properly callable and functional."""
        request = self.factory.get("/")
        request.user = self.user

        actions = self.pdf_mixin.get_actions(request)
        action_func, action_name, action_description = actions["generate_pdf_selected"]

        # Verify action function signature
        import inspect

        sig = inspect.signature(action_func)
        param_names = list(sig.parameters.keys())

        # Should accept (modeladmin, request, queryset)
        self.assertEqual(len(param_names), 3)
        expected_params = ["modeladmin", "request", "queryset"]
        self.assertEqual(param_names, expected_params)

        # Test that action can be called (mock the generate_pdf method)
        mock_queryset = Municipality.objects.none()
        self.pdf_mixin.generate_pdf = Mock(return_value=HttpResponse("test"))

        result = action_func(self.pdf_mixin, request, mock_queryset)

        # Verify the action properly delegates to generate_pdf
        self.pdf_mixin.generate_pdf.assert_called_once_with(request, mock_queryset)
        self.assertIsInstance(result, HttpResponse)

    def test_method_integration_consistency(self):
        """Test that get_urls, get_actions, and changelist_view work together consistently."""
        # Test URL generation and action integration
        request = self.factory.get("/?test=integration")
        request.user = self.user

        # Get URLs and actions
        urls = self.pdf_mixin.get_urls()
        actions = self.pdf_mixin.get_actions(request)

        # Verify PDF URL exists
        pdf_url = next((url for url in urls if hasattr(url.pattern, "_route") and url.pattern._route == "generate_pdf/"), None)
        self.assertIsNotNone(pdf_url)

        # Verify PDF action exists
        self.assertIn("generate_pdf_selected", actions)

        # Test changelist_view context
        with patch("django.contrib.admin.ModelAdmin.changelist_view") as mock_super:
            mock_super.return_value = Mock()

            self.pdf_mixin.changelist_view(request)

            # Verify context includes both URL and button name
            args, kwargs = mock_super.call_args
            extra_context = kwargs["extra_context"]

            self.assertIn("generate_pdf_url", extra_context)
            self.assertIn("pdf_title", extra_context)
            self.assertIn("pdf_message", extra_context)
            self.assertIn("pdf_button", extra_context)

            # URL should include query parameters
            self.assertIn("test=integration", extra_context["generate_pdf_url"])

    def test_write_page_header(self):
        from reportlab.lib import colors

        # Arrange: Create mocks
        canvas_mock = Mock()
        canvas_mock.getPageNumber.return_value = 3

        doc_mock = Mock()
        doc_mock.leftMargin = 50
        doc_mock.height = 700
        doc_mock.bottomMargin = 50

        # Act
        self.pdf_mixin.write_page_header(canvas_mock, doc_mock)

        # Assert
        canvas_mock.saveState.assert_called_once()
        canvas_mock.restoreState.assert_called_once()
        canvas_mock.setFont.assert_called_once_with(self.pdf_mixin.regular_font, self.pdf_mixin.normal_font_size)
        canvas_mock.setFillColor.assert_called_once_with(colors.black)
        self.assertEqual(canvas_mock.drawRightString.call_count, 2)


@pytest.mark.integration
@pytest.mark.pdf
class PdfGenerationIntegrationTest(BaseTestMixin, TestCase):
    """Integration tests for PDF generation functionality."""

    databases = {"default", "postgres"}

    def setUp(self):
        """Set up test fixtures for PDF generation integration tests."""
        super().setUp()
        self.pdf_mixin = TestModelAdmin()

        # Create test municipality objects
        self.municipality1 = Municipality.objects.create(
            municipality_code="001001",
            municipality_name="Test Municipality 1",
            municipality_name_kana="テストシチョウソン1",
            prefecture_name="Test Prefecture",
            prefecture_name_kana="テストケン",
        )
        self.municipality2 = Municipality.objects.create(
            municipality_code="001002",
            municipality_name="Test Municipality 2",
            municipality_name_kana="テストシチョウソン2",
            prefecture_name="Test Prefecture",
            prefecture_name_kana="テストケン",
        )

        # Mock the get_changelist method
        self.pdf_mixin.get_changelist = Mock()
        self.pdf_mixin.list_display = ["municipality_name", "prefecture_name"]
        self.pdf_mixin.list_display_links = ["municipality_name"]
        self.pdf_mixin.list_filter = []
        self.pdf_mixin.date_hierarchy = None
        self.pdf_mixin.search_fields = ["municipality_name"]
        self.pdf_mixin.list_select_related = []
        self.pdf_mixin.list_per_page = 100
        self.pdf_mixin.list_max_show_all = 200
        self.pdf_mixin.list_editable = []
        self.pdf_mixin.get_sortable_by = Mock(return_value=[])
        self.pdf_mixin.search_help_text = None
        self.pdf_mixin.message_user = Mock()

    @patch("os.path.join")
    @patch("builtins.open")
    def test_generate_pdf_single_file(self, mock_open, mock_path_join):
        """Test PDF generation for a single file."""
        # Setup mocks
        mock_path_join.return_value = "/tmp/test_file.pdf"
        mock_file_data = b"Mock PDF content"
        mock_open.return_value.__enter__.return_value.read.return_value = mock_file_data

        # Override create_pdf_files to return single file
        self.pdf_mixin.create_pdf_files = Mock(return_value=["single_file.pdf"])
        self.pdf_mixin.get_pdf_temporary_path = Mock(return_value="/tmp")

        request = self.factory.get("/")
        request.user = self.user
        queryset = Municipality.objects.filter(id=self.municipality1.id)

        response = self.pdf_mixin.generate_pdf(request, queryset)

        # Verify response
        self.assertIsInstance(response, HttpResponse)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertIn("single_file.pdf", response["Content-Disposition"])

    @patch("os.path.join")
    @patch("zipfile.ZipFile")
    def test_generate_pdf_multiple_files(self, mock_zipfile, mock_path_join):
        """Test PDF generation for multiple files creating a ZIP archive."""
        # Setup mocks
        mock_path_join.return_value = "/tmp/test_file.pdf"
        mock_zip_instance = Mock()
        mock_zipfile.return_value.__enter__.return_value = mock_zip_instance

        # Override create_pdf_files to return multiple files
        self.pdf_mixin.create_pdf_files = Mock(return_value=["file1.pdf", "file2.pdf"])
        self.pdf_mixin.get_pdf_temporary_path = Mock(return_value="/tmp")

        request = self.factory.get("/")
        request.user = self.user
        queryset = Municipality.objects.all()

        response = self.pdf_mixin.generate_pdf(request, queryset)

        # Verify response
        self.assertIsInstance(response, HttpResponse)
        self.assertEqual(response["Content-Type"], "application/zip")
        self.assertIn("attachment", response["Content-Disposition"])

        # Verify ZIP file operations
        self.assertEqual(mock_zip_instance.write.call_count, 2)

    def test_generate_pdf_empty_queryset(self):
        """Test PDF generation with empty queryset."""
        request = self.factory.get("/")
        request.user = self.user
        request.get_full_path = Mock(return_value="/admin/test/")

        empty_queryset = Municipality.objects.none()

        with patch("sfd.views.common.pdf.redirect") as mock_redirect:
            self.pdf_mixin.generate_pdf(request, empty_queryset)

            # Verify warning message and redirect
            self.pdf_mixin.message_user.assert_called_once_with(request, _("No data available for PDF generation."), level="warning")
            mock_redirect.assert_called_once_with("/admin/test/")

    def test_generate_pdf_no_files_created(self):
        """Test PDF generation when no files are created."""
        # Override create_pdf_files to return empty list
        self.pdf_mixin.create_pdf_files = Mock(return_value=[])

        request = self.factory.get("/")
        request.user = self.user
        queryset = Municipality.objects.filter(id=self.municipality1.id)

        # Note: The method doesn't handle empty file list in current implementation
        # This test documents the current behavior
        self.pdf_mixin.generate_pdf(request, queryset)

        # Verify warning message is called
        self.pdf_mixin.message_user.assert_called_once_with(request, _("No PDFs were created. Please check the related data."), level="warning")
