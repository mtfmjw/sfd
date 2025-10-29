# type: ignore
"""Test cases for sfd.models package."""

from datetime import date

import pytest
from django.contrib.admin import AdminSite
from django.db import IntegrityError
from django.db.models import QuerySet
from django.test import TestCase
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from sfd.models import BaseModel, Holiday, HolidayType
from sfd.tests.unittest import BaseTestMixin
from sfd.views.base import BaseModelAdmin
from sfd.views.common.pdf import BasePdfMixin
from sfd.views.holiday import HolidayAdmin


@pytest.mark.unit
@pytest.mark.models
class HolidayTypeTest(TestCase):
    """Test cases for the HolidayType TextChoices enumeration."""

    def test_holiday_type_values(self):
        """Test that holiday type constants have correct values."""
        self.assertEqual(HolidayType.NATIONAL_HOLIDAY, "National Holiday")
        self.assertEqual(HolidayType.SUBSTITUTE_HOLIDAY, "Substitute Holiday")
        self.assertEqual(HolidayType.OTHER_HOLIDAY, "Other Holiday")

    def test_holiday_type_labels(self):
        """Test that holiday type labels are properly internationalized."""
        self.assertEqual(HolidayType.NATIONAL_HOLIDAY.label, _("National Holiday"))
        self.assertEqual(HolidayType.SUBSTITUTE_HOLIDAY.label, _("Substitute Holiday"))
        self.assertEqual(HolidayType.OTHER_HOLIDAY.label, _("Other Holiday"))


@pytest.mark.unit
@pytest.mark.models
class HolidayModelTest(TestCase):
    """Test cases for the Holiday model."""

    databases = {"default", "postgres"}

    def setUp(self):
        """Set up test environment with sample holiday data."""
        self.holiday_date = date(2024, 1, 1)
        self.holiday_data = {
            "date": self.holiday_date,
            "holiday_type": HolidayType.NATIONAL_HOLIDAY,
            "name": "New Year's Day",
        }
        self.holiday = Holiday.objects.create(**self.holiday_data)

    def test_holiday_model_inherits_base_model(self):
        """Test that Holiday model inherits from BaseModel."""
        self.assertTrue(issubclass(Holiday, BaseModel))

    def test_holiday_creation_success(self):
        """Test successful holiday creation with valid data."""
        self.assertEqual(self.holiday.date, self.holiday_date)
        self.assertEqual(self.holiday.holiday_type, HolidayType.NATIONAL_HOLIDAY)
        self.assertEqual(self.holiday.name, "New Year's Day")
        self.assertFalse(self.holiday.deleted_flg)

    def test_holiday_string_representation(self):
        """Test Holiday model string representation."""
        self.assertEqual(str(self.holiday), "New Year's Day")

    def test_holiday_date_uniqueness(self):
        """Test that holiday dates must be unique."""
        with self.assertRaises(IntegrityError):
            Holiday.objects.create(**self.holiday_data)

    def test_holiday_field_properties(self):
        """Test Holiday model field properties and constraints."""
        # Test date field
        date_field = Holiday._meta.get_field("date")
        self.assertEqual(date_field.__class__.__name__, "DateField")

        # Test holiday_type field
        holiday_type_field = Holiday._meta.get_field("holiday_type")
        self.assertEqual(holiday_type_field.__class__.__name__, "CharField")
        self.assertEqual(holiday_type_field.max_length, 20)
        self.assertEqual(holiday_type_field.choices, HolidayType.choices)
        self.assertEqual(holiday_type_field.default, HolidayType.NATIONAL_HOLIDAY)

        # Test comment field
        comment_field = Holiday._meta.get_field("comment")
        self.assertEqual(comment_field.__class__.__name__, "CharField")
        self.assertEqual(comment_field.max_length, 255)
        self.assertTrue(comment_field.null)
        self.assertTrue(comment_field.blank)


@pytest.mark.unit
@pytest.mark.views
class FilterYearTest(BaseTestMixin, TestCase):
    """Test HolidayAdmin functionality with comprehensive coverage."""

    databases = {"default", "postgres"}

    def setUp(self):
        """Set up test data for HolidayAdmin tests."""
        super().setUp()
        self.site = AdminSite()
        self.admin = HolidayAdmin(Holiday, self.site)
        self.request = self.factory.get("/admin/")
        self.request.user = self.user

        Holiday.objects.create(date="2023-01-01", holiday_type=HolidayType.NATIONAL_HOLIDAY)
        Holiday.objects.create(date="2024-01-01", holiday_type=HolidayType.NATIONAL_HOLIDAY)
        Holiday.objects.create(date="2025-01-01", holiday_type=HolidayType.NATIONAL_HOLIDAY)

    def test_lookups(self):
        """Test lookups method returns correct year choices."""
        # Arrange - Get the filter class from list_filter
        filter_class = self.admin.list_filter[0]
        filter_instance = filter_class(self.request, {}, Holiday, self.admin)

        # Act
        years = filter_instance.lookups(self.request, self.admin)

        # Assert
        self.assertTrue(isinstance(years, list))
        self.assertGreater(len(years), 0)
        for year in years:
            self.assertIsInstance(year, tuple)
            self.assertEqual(len(year), 2)
            self.assertIsInstance(year[0], int)
            self.assertIsInstance(year[1], str)

    def test_queryset_without_value(self):
        """Test queryset method returns correct queryset."""
        # Arrange - Get the filter class from list_filter
        filter_class = self.admin.list_filter[0]
        filter_instance = filter_class(self.request, {}, Holiday, self.admin)

        # Act
        original_queryset = Holiday.objects.all()
        queryset = filter_instance.queryset(self.request, original_queryset)
        # Assert
        self.assertTrue(isinstance(queryset, QuerySet))
        self.assertEqual(queryset.model, Holiday)
        self.assertEqual(queryset, original_queryset)
        self.assertEqual(queryset.count(), 3)

    def test_queryset_with_value(self):
        """Test queryset method returns correct queryset."""
        # Arrange - Get the filter class from list_filter
        filter_class = self.admin.list_filter[0]
        filter_instance = filter_class(self.request, {}, Holiday, self.admin)
        filter_instance.value = lambda: "2024"

        # Act
        original_queryset = Holiday.objects.all()
        queryset = filter_instance.queryset(self.request, original_queryset)
        # Assert
        self.assertTrue(isinstance(queryset, QuerySet))
        self.assertEqual(queryset.model, Holiday)
        self.assertTrue(queryset.filter(date__year=2024).exists())
        self.assertEqual(queryset.count(), 1)


@pytest.mark.unit
@pytest.mark.views
class HolidayAdminTest(BaseTestMixin, TestCase):
    """Test HolidayAdmin functionality with comprehensive coverage."""

    databases = {"default", "postgres"}

    def setUp(self):
        """Set up test data for HolidayAdmin tests."""
        super().setUp()
        self.site = AdminSite()
        self.admin = HolidayAdmin(Holiday, self.site)
        self.request = self.factory.get("/admin/")
        self.request.user = self.user

        # Create holiday for current year to match test expectations
        current_year = timezone.now().year
        Holiday.objects.create(date=f"{current_year}-02-01", name="Test", holiday_type=HolidayType.NATIONAL_HOLIDAY)
        Holiday.objects.create(date=f"{current_year}-01-01", name="New Year", holiday_type=HolidayType.NATIONAL_HOLIDAY)
        Holiday.objects.create(date="2024-01-01", name="New Year", holiday_type=HolidayType.NATIONAL_HOLIDAY)
        Holiday.objects.create(date="2023-01-01", name="New Year", holiday_type=HolidayType.NATIONAL_HOLIDAY)

    def test_admin_initialization(self):
        """Test HolidayAdmin initialization and field configuration."""
        # Assert
        self.assertEqual(self.admin.search_fields, ("date__year", "name"))
        self.assertTrue(isinstance(self.admin, BaseModelAdmin))

    def test_admin_inheritance(self):
        """Test that HolidayAdmin properly inherits from BaseModelAdmin."""
        # Assert
        self.assertTrue(isinstance(self.admin, BasePdfMixin))
        self.assertTrue(isinstance(self.admin, BaseModelAdmin))
        self.assertEqual(self.admin.change_list_template, "sfd/change_list.html")

    def test_admin_model_association(self):
        """Test that HolidayAdmin is associated with Holiday model."""
        # Assert
        self.assertEqual(self.admin.model, Holiday)

    def test_get_queryset(self):
        """Test get_queryset method returns correct queryset."""
        # Arrange
        current_year = timezone.now().year

        # Act
        queryset = self.admin.get_queryset(self.request)

        # Assert
        self.assertTrue(isinstance(queryset, QuerySet))
        self.assertEqual(queryset.model, Holiday)
        # Test that holiday exists for current year (since we created one in setUp)
        self.assertTrue(queryset.filter(date__year=current_year).exists())
        self.assertEqual(queryset.count(), 4)  # 4 holidays created in setUp
        self.assertEqual(queryset[0].date.year, current_year)
        self.assertEqual(queryset[0].date.month, 1)
        self.assertEqual(queryset[1].date.month, 2)

    def test_get_queryset_GET(self):
        """Test get_queryset method returns correct queryset for GET requests."""
        # Arrange
        self.request = self.factory.get("/admin/?year=all")

        # Act
        queryset = self.admin.get_queryset(self.request)

        # Assert
        self.assertEqual(self.request.method, "GET")
        self.assertTrue(isinstance(queryset, QuerySet))
        self.assertEqual(queryset.model, Holiday)
        self.assertEqual(queryset.count(), 4)

    def test_get_search_field_names(self):
        """Test get_search_field_names method returns correct field names."""
        # Act
        field_names = self.admin.get_search_field_names()

        # Assert
        self.assertEqual(_("year, name"), field_names)

    @pytest.mark.integration
    def test_create_pdf_files(self):
        """Test create_pdf_files method generates PDF files correctly."""
        # Act
        queryset = Holiday.objects.all()
        pdf_files = self.admin.create_pdf_files(self.request, queryset)

        # Assert
        self.assertTrue(isinstance(pdf_files, list))
        self.assertGreater(len(pdf_files), 0)
        for pdf in pdf_files:
            self.assertIsInstance(pdf, str)
            self.assertTrue(pdf.endswith(".pdf"))
