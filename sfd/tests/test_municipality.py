# type: ignore
import io
from datetime import date
from unittest.mock import Mock, patch

import pandas as pd
import pytest
from django.contrib.admin import AdminSite
from django.db import IntegrityError
from django.db.models import QuerySet
from django.test import TestCase
from django.utils.translation import gettext_lazy as _

from sfd.models import MasterModel, Municipality
from sfd.tests.unittest import BaseTestMixin
from sfd.views.base import MasterModelAdmin
from sfd.views.municipality import MunicipalityAdmin, get_municipalities_by_prefecture


@pytest.mark.unit
@pytest.mark.models
class MunicipalityModelTest(TestCase):
    """Test cases for the Municipality model."""

    databases = {"default", "postgres"}

    def setUp(self):
        """Set up test environment with sample municipality data."""
        self.municipality_data = {
            "municipality_code": "131016",
            "municipality_name": "世田谷区",
            "municipality_name_kana": "セタガヤク",
            "prefecture_name": "東京都",
            "prefecture_name_kana": "トウキョウト",
            "valid_from": date(2024, 1, 1),
        }

    def test_municipality_model_inherits_master_model(self):
        """Test that Municipality model inherits from MasterModel."""
        self.assertTrue(issubclass(Municipality, MasterModel))

    def test_municipality_creation_success(self):
        """Test successful municipality creation with valid data."""
        municipality = Municipality.objects.create(**self.municipality_data)
        self.assertEqual(municipality.municipality_code, "131016")
        self.assertEqual(municipality.municipality_name, "世田谷区")
        self.assertEqual(municipality.municipality_name_kana, "セタガヤク")
        self.assertEqual(municipality.prefecture_name, "東京都")
        self.assertEqual(municipality.prefecture_name_kana, "トウキョウト")
        self.assertEqual(municipality.valid_from, date(2024, 1, 1))
        self.assertEqual(municipality.valid_to, date(2222, 12, 31))
        self.assertFalse(municipality.deleted_flg)

    def test_municipality_string_representation(self):
        """Test Municipality model string representation."""
        municipality = Municipality.objects.create(**self.municipality_data)
        expected_str = "東京都世田谷区"
        self.assertEqual(str(municipality), expected_str)

    def test_municipality_code_uniqueness(self):
        """Test that municipality codes must be unique."""
        Municipality.objects.create(**self.municipality_data)
        duplicate_data = self.municipality_data.copy()
        duplicate_data["municipality_name"] = "渋谷区"
        with self.assertRaises(IntegrityError):
            Municipality.objects.create(**duplicate_data)

    def test_municipality_field_properties(self):
        """Test Municipality model field properties and constraints."""
        # Test municipality_code field
        code_field = Municipality._meta.get_field("municipality_code")
        self.assertEqual(code_field.__class__.__name__, "CharField")
        self.assertEqual(code_field.max_length, 10)

        # Test municipality_name field
        name_field = Municipality._meta.get_field("municipality_name")
        self.assertEqual(name_field.__class__.__name__, "CharField")
        self.assertEqual(name_field.max_length, 100)
        self.assertTrue(name_field.blank)
        self.assertTrue(name_field.null)

        # Test prefecture_name field
        prefecture_field = Municipality._meta.get_field("prefecture_name")
        self.assertEqual(prefecture_field.__class__.__name__, "CharField")
        self.assertEqual(prefecture_field.max_length, 100)

    def test_municipality_unique_constraint(self):
        """Test Municipality model unique constraint on municipality_code."""
        constraints = Municipality._meta.constraints
        unique_constraint = None
        for constraint in constraints:
            if hasattr(constraint, "fields") and "municipality_code" in constraint.fields:
                unique_constraint = constraint
                break
        self.assertIsNotNone(unique_constraint)
        self.assertEqual(unique_constraint.name, "unique_municipality_code_valid_from")
        self.assertEqual(list(unique_constraint.fields), ["municipality_code", "valid_from"])


@pytest.mark.unit
@pytest.mark.views
class FilterPrefectureTest(BaseTestMixin, TestCase):
    """Test FilterPrefecture functionality with comprehensive coverage."""

    databases = {"default", "postgres"}

    def setUp(self):
        """Set up test data for MunicipalityAdmin tests."""
        super().setUp()
        self.site = AdminSite()
        self.admin = MunicipalityAdmin(Municipality, self.site)
        self.request = self.factory.get("/admin/")
        self.request.user = self.user

        self.municipality = Municipality.objects.create(
            municipality_code="01001",
            municipality_name="",
            municipality_name_kana="",
            prefecture_name="北海道",
            prefecture_name_kana="ホッカイドウ",
        )
        self.municipality = Municipality.objects.create(
            municipality_code="01901",
            municipality_name="",
            municipality_name_kana="",
            prefecture_name="テスト県",
            prefecture_name_kana="テストケン",
        )

    def test_lookups(self):
        """Test lookups method returns correct year choices."""
        # Arrange - Get the filter class from list_filter
        filter_class = self.admin.list_filter[0]
        filter_instance = filter_class(self.request, {}, Municipality, self.admin)

        # Act
        prefectures = filter_instance.lookups(self.request, self.admin)

        # Assert
        self.assertTrue(isinstance(prefectures, list))
        self.assertGreater(len(prefectures), 0)

        self.assertEqual(len(prefectures), 2)
        self.assertEqual(prefectures[0], ("北海道", "北海道"))
        self.assertEqual(prefectures[1], ("テスト県", "テスト県"))

    def test_queryset_without_value(self):
        """Test queryset method returns correct queryset."""
        # Arrange - Get the filter class from list_filter
        filter_class = self.admin.list_filter[0]
        filter_instance = filter_class(self.request, {}, Municipality, self.admin)

        # Act
        original_queryset = Municipality.objects.all()
        queryset = filter_instance.queryset(self.request, original_queryset)
        # Assert
        self.assertTrue(isinstance(queryset, QuerySet))
        self.assertEqual(queryset.model, Municipality)
        self.assertEqual(queryset, original_queryset)
        self.assertEqual(queryset.count(), 2)

    def test_queryset_with_value(self):
        """Test queryset method returns correct queryset."""
        # Arrange - Get the filter class from list_filter
        filter_class = self.admin.list_filter[0]
        filter_instance = filter_class(self.request, {}, Municipality, self.admin)
        filter_instance.value = lambda: "北海道"

        # Act
        original_queryset = Municipality.objects.all()
        queryset = filter_instance.queryset(self.request, original_queryset)
        # Assert
        self.assertTrue(isinstance(queryset, QuerySet))
        self.assertEqual(queryset.model, Municipality)
        self.assertTrue(queryset.filter(prefecture_name="北海道").exists())
        self.assertEqual(queryset.count(), 1)


@pytest.mark.unit
@pytest.mark.views
class MunicipalityAdminTest(BaseTestMixin, TestCase):
    """Test MunicipalityAdmin functionality with comprehensive coverage."""

    databases = {"default", "postgres"}

    def setUp(self):
        """Set up test data for MunicipalityAdmin tests."""
        super().setUp()

        self.site = AdminSite()
        self.admin = MunicipalityAdmin(Municipality, self.site)
        self.request = self.factory.get("/admin/")
        self.request.user = self.user

        Municipality.objects.create(
            municipality_code="01000",
            municipality_name="",
            municipality_name_kana="",
            prefecture_name="北海道",
            prefecture_name_kana="ホッカイドウ",
        )
        Municipality.objects.create(
            municipality_code="01001",
            municipality_name="札幌市",
            municipality_name_kana="サッポロシ",
            prefecture_name="北海道",
            prefecture_name_kana="ホッカイドウ",
        )
        Municipality.objects.create(
            municipality_code="09001",
            municipality_name="",
            municipality_name_kana="",
            prefecture_name="テスト県",
            prefecture_name_kana="テストケン",
        )
        Municipality.objects.create(
            municipality_code="09901",
            municipality_name="テスト市",
            municipality_name_kana="テストシ",
            prefecture_name="テスト県",
            prefecture_name_kana="テストケン",
        )

    def test_admin_inheritance(self):
        """Test that MunicipalityAdmin properly inherits from BaseModelAdmin."""
        # Assert
        self.assertTrue(isinstance(self.admin, MasterModelAdmin))
        self.assertEqual(self.admin.change_list_template, "sfd/change_list.html")

    def test_admin_model_association(self):
        """Test that MunicipalityAdmin is associated with Municipality model."""
        self.assertEqual(self.admin.model, Municipality)

    def test_sheet_reader(self):
        """Test sheet_reader method handles file uploads correctly."""
        sample_data = {
            "Code": ["131010", "1230", "1234560", 456780],  # Covers string, short int, long int
            "Prefecture": ["Tokyo", "Chiba", "Kanagawa", "Saitama"],
            "Municipality": ["Chiyoda", "Chiba City", "Yokohama", "Saitama City"],
            "Prefecture Kana": ["TOKYO", "CHIBA", "KANAGAWA", None],  # Test a null value
            "Municipality Kana": ["CHIYODA", "CHIBA SHI", "YOKOHAMA", "SAITAMA SHI"],
        }

        df = pd.DataFrame(sample_data)
        output_buffer = io.BytesIO()
        with pd.ExcelWriter(output_buffer, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="TestSheet", index=False)

        # The buffer now contains the raw bytes of an Excel file.
        # We need to reset its "cursor" to the beginning to be read.
        output_buffer.seek(0)
        results = list(self.admin.sheet_reader(output_buffer, "TestSheet", self.request))

        self.assertEqual(len(results), 4)

        # Check the first row (standard case)
        self.assertEqual(
            results[0],
            {
                "municipality_code": "13101",
                "prefecture_name": "Tokyo",
                "municipality_name": "Chiyoda",
                "prefecture_name_kana": "TOKYO",
                "municipality_name_kana": "CHIYODA",
            },
        )

        # Check the second row (testing zfill)
        self.assertEqual(results[1]["municipality_code"], "00123")

        # Check the third row (testing slicing)
        self.assertEqual(results[2]["municipality_code"], "12345")

        # Check the fourth row (testing integer conversion and null handling)
        self.assertEqual(results[3]["municipality_code"], "45678")
        self.assertEqual(results[3]["prefecture_name_kana"], "")

    @pytest.mark.integration
    @patch.object(MunicipalityAdmin, "upload_data")
    def test_excel_upload(self, mock_upload_data):
        """Test excel_upload method handles file uploads correctly."""
        # Arrange
        mock_file = Mock()

        # Act
        self.admin.excel_upload(mock_file, self.request)

        # Assert
        self.assertEqual(mock_upload_data.call_count, 2)

    @pytest.mark.integration
    def test_create_pdf_files(self):
        """Test create_pdf_files method generates PDF files correctly."""

        # Act
        queryset = Municipality.objects.all()
        pdf_files = self.admin.create_pdf_files(self.request, queryset)

        # Assert
        self.assertTrue(isinstance(pdf_files, list))
        self.assertGreater(len(pdf_files), 0)
        for pdf in pdf_files:
            self.assertIsInstance(pdf, str)
            self.assertTrue(pdf.endswith(".pdf"))


@pytest.mark.unit
@pytest.mark.views
class FilterMunicipalityByPrefectureTest(BaseTestMixin, TestCase):
    databases = {"default", "postgres"}

    def setUp(self):
        super().setUp()
        self.request = self.factory.get("/admin/?prefecture=東京都")

    def test_get_municipalities_by_prefecture_without_prefecture(self):
        """Test get_municipalities_by_prefecture view function."""
        request = self.factory.get("/admin/")
        # Act
        response = get_municipalities_by_prefecture(request)

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertIn(str(_("Select Prefecture first")), response.content.decode())

    def test_get_municipalities_by_prefecture(self):
        """Test get_municipalities_by_prefecture view function."""

        # Act
        response = get_municipalities_by_prefecture(self.request)

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertIn(str(_("Select Municipality")), response.content.decode())

    def test_get_municipalities_by_prefecture_data(self):
        """Test get_municipalities_by_prefecture view function."""
        Municipality.objects.create(
            municipality_code="13101",
            municipality_name="千代田区",
            municipality_name_kana="チヨダク",
            prefecture_name="東京都",
            prefecture_name_kana="トウキョウト",
        )

        # Act
        response = get_municipalities_by_prefecture(self.request)

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertIn(str(_("Select Municipality")), response.content.decode())
        self.assertIn("千代田区", response.content.decode())
