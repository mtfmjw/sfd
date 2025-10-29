# type: ignore
from datetime import date
from unittest.mock import Mock, patch

import pytest
from django.db.models import Q
from django.test import TestCase

from sfd.models.holiday import Holiday
from sfd.tests.unittest import BaseTestMixin, TestModel
from sfd.views.common.search import BaseSearchView


@pytest.mark.unit
@pytest.mark.common
class BaseSearchViewTest(BaseTestMixin, TestCase):
    """Test BaseSearchView functionality with comprehensive coverage."""

    def setUp(self):
        """Set up test data for BaseSearchView tests."""
        super().setUp()

        # Create a mock form class for testing
        self.mock_form_class = Mock()
        self.mock_form_instance = Mock()
        self.mock_form_class.return_value = self.mock_form_instance

        self.view = BaseSearchView()
        self.view.model = TestModel
        self.view.form_class = self.mock_form_class

        request = self.factory.get("/")
        self.view.setup(request)

        # Store original ordering to restore it later
        self.original_ordering = self.view.model._meta.ordering

    def tearDown(self):
        """Clean up test data and restore original state."""
        # Restore original ordering to prevent test pollution
        self.view.model._meta.ordering = self.original_ordering
        super().tearDown()

    def test_base_search_view_initialization(self):
        """Test BaseSearchView initialization and default attributes."""

        # Assert
        self.assertEqual(self.view.template_name, "sfd/search.html")
        self.assertEqual(self.view.paginate_by, 10)
        self.assertEqual(self.view.on_each_side, 2)
        self.assertEqual(self.view.on_ends, 2)
        self.assertTrue(self.view.is_popup)
        self.assertEqual(self.view.list_display, ())
        self.assertEqual(self.view.fieldsets, [])

    def test_get_search_result_columns(self):
        """Test get_search_result_columns method returns field verbose names."""
        # Arrange
        self.view.list_display = ("date", "name")

        # Act
        headers = self.view.get_search_result_columns()

        # Assert
        expected_headers = {"date": "Date", "name": "Name"}
        self.assertEqual(headers, expected_headers)

    def test_get_search_result_columns_with_select(self):
        """Test get_search_result_columns method returns field verbose names."""
        # Arrange
        self.view.list_display = ("date", "name", "select")

        # Act
        headers = self.view.get_search_result_columns()

        # Assert
        expected_header_columns = ["date", "name", "select"]
        self.assertEqual(list(headers.keys()), expected_header_columns)

    def test_get_search_result_columns_without_list_display(self):
        """Test get_search_result_columns method returns field verbose names."""
        # Arrange
        self.view.list_display = ()

        # Act
        headers = self.view.get_search_result_columns()

        # Assert
        expected_headers = {}
        self.assertEqual(headers, expected_headers)

    def test_get_query(self):
        """Test get_query method creates Q object from cleaned data."""
        # Arrange
        form = Mock()
        form.cleaned_data = {"date": "2024-01-01"}

        # Act
        query = self.view.get_query(form)

        # Assert
        self.assertIsInstance(query, Q)
        self.assertFalse(query)

    def test_get_query_with_list_display(self):
        """Test get_query method creates Q object from cleaned data."""
        # Arrange
        self.view.list_display = ("date", "name")
        form = Mock()
        form.cleaned_data = {"date": "2024-01-01"}

        # Act
        query = self.view.get_query(form)

        # Assert
        self.assertIsInstance(query, Q)
        self.assertTrue(query)

    @patch("sfd.views.common.search.BaseSearchView.get_query")
    def test_get_queryset_with_valid_form(self, mock_get_query):
        """Test get_queryset method with valid form data."""

        # Setup mocks
        self.mock_form_instance.is_valid.return_value = True
        self.mock_form_instance.cleaned_data = {"date": "2024-01-01"}
        mock_query = Q(date="2024-01-01")
        mock_get_query.return_value = mock_query

        # Act
        with patch("sfd.views.common.search.super") as mock_super:
            mock_queryset = Mock()
            mock_queryset.ordered = True  # Already ordered
            mock_super.return_value.get_queryset.return_value = mock_queryset
            self.view.get_queryset()

            # Assert
            mock_queryset.filter.assert_called_once_with(mock_query)
            mock_get_query.assert_called_once_with(self.mock_form_instance)

    def test_get_queryset_with_invalid_form(self):
        """Test get_queryset method with invalid form data."""

        # Setup mocks
        self.mock_form_instance.is_valid.return_value = False

        # Act
        with patch("sfd.views.common.search.super") as mock_super:
            mock_queryset = Mock()
            mock_super.return_value.get_queryset.return_value = mock_queryset
            self.view.get_queryset()

            # Assert
            # Should return unfiltered queryset
            mock_queryset.filter.assert_not_called()

    def test_get_queryset_without_form_class(self):
        """Test get_queryset method when form_class is None."""
        # Arrange
        self.view.form_class = None

        # Act & Assert
        with self.assertRaises(TypeError):
            self.view.get_queryset()

    def test_get_queryset_with_empty_get_params(self):
        """Test get_queryset method with empty GET parameters."""

        # Setup mocks - empty form data
        self.mock_form_instance.is_valid.return_value = True
        self.mock_form_instance.cleaned_data = {}

        # Act
        with patch("sfd.views.common.search.super") as mock_super:
            mock_queryset = Mock()
            mock_queryset.ordered = True  # Already ordered
            mock_queryset.none.return_value = Mock()
            mock_super.return_value.get_queryset.return_value = mock_queryset

            with patch.object(self.view, "get_query") as mock_get_query:
                mock_get_query.return_value = Q()  # Empty query
                result = self.view.get_queryset()

                # Assert
                mock_get_query.assert_called_once_with(self.mock_form_instance)
                mock_queryset.none.assert_called_once()
                self.assertEqual(result, mock_queryset.none.return_value)

    def test_get_queryset_ordering_with_model_meta_ordering(self):
        """Test get_queryset method applies model meta ordering when queryset is unordered."""

        # Setup mocks
        self.mock_form_instance.is_valid.return_value = True
        self.mock_form_instance.cleaned_data = {"date": "2024-01-01"}

        # TestModel has ordering = ["-date"] in its Meta class
        # Verify the model actually has meta ordering
        self.assertIsNotNone(self.view.model._meta.ordering)
        self.assertEqual(self.view.model._meta.ordering, ["-date"])

        # Act
        with patch("sfd.views.common.search.super") as mock_super:
            mock_queryset = Mock()
            mock_queryset.ordered = False  # Not ordered
            mock_filtered_queryset = Mock()
            mock_queryset.filter.return_value = mock_filtered_queryset
            mock_filtered_queryset.ordered = False  # Still not ordered after filter
            mock_super.return_value.get_queryset.return_value = mock_queryset

            with patch.object(self.view, "get_query") as mock_get_query:
                mock_get_query.return_value = Q(date="2024-01-01")
                self.view.get_queryset()

                # Assert
                # Should apply model's default ordering from _meta.ordering
                mock_filtered_queryset.order_by.assert_called_once_with("-date")

    def test_get_queryset_ordering_with_date_field_fallback(self):
        """Test get_queryset method uses date field for ordering when model has no meta ordering."""
        # Create a mock model without meta ordering but with date field
        self.view.model._meta.ordering = None

        # Setup mocks
        self.mock_form_instance.is_valid.return_value = True
        self.mock_form_instance.cleaned_data = {"date": "2024-01-01"}

        # Act
        with patch("sfd.views.common.search.super") as mock_super:
            mock_queryset = Mock()
            mock_queryset.ordered = False
            mock_filtered_queryset = Mock()
            mock_filtered_queryset.ordered = False
            mock_queryset.filter.return_value = mock_filtered_queryset
            mock_super.return_value.get_queryset.return_value = mock_queryset

            with patch.object(self.view, "get_query") as mock_get_query:
                with patch("builtins.hasattr") as mock_hasattr:
                    # Mock hasattr calls: has _meta, no ordering, has date field
                    mock_hasattr.side_effect = lambda obj, attr: {
                        (self.view.model, "_meta"): True,
                        (self.view.model, "date"): True,
                    }.get((obj, attr), False)

                    mock_get_query.return_value = Q(date="2024-01-01")

                    self.view.get_queryset()

                    # Assert
                    mock_filtered_queryset.order_by.assert_called_once_with("date")

    def test_get_queryset_ordering_with_created_at_fallback(self):
        """Test get_queryset method uses created_at field for ordering when no date field exists."""

        self.view.model._meta.ordering = None

        # Setup mocks
        self.mock_form_instance.is_valid.return_value = True
        self.mock_form_instance.cleaned_data = {"name": "test"}

        # Act
        with patch("sfd.views.common.search.super") as mock_super:
            mock_queryset = Mock()
            mock_queryset.ordered = False
            mock_filtered_queryset = Mock()
            mock_filtered_queryset.ordered = False
            mock_queryset.filter.return_value = mock_filtered_queryset
            mock_super.return_value.get_queryset.return_value = mock_queryset

            with patch.object(self.view, "get_query") as mock_get_query:
                with patch("builtins.hasattr") as mock_hasattr:
                    # Mock hasattr calls: has _meta, no date, has created_at
                    mock_hasattr.side_effect = lambda obj, attr: {
                        (self.view.model, "_meta"): True,
                        (self.view.model, "date"): False,
                        (self.view.model, "created_at"): True,
                    }.get((obj, attr), False)

                    mock_get_query.return_value = Q(name="test")

                    self.view.get_queryset()

                    # Assert
                    mock_filtered_queryset.order_by.assert_called_once_with("created_at")

    def test_get_queryset_ordering_with_pk_fallback(self):
        """Test get_queryset method uses pk for ordering when no other fields exist."""
        self.view.model._meta.ordering = None
        # Setup mocks
        self.mock_form_instance.is_valid.return_value = True
        self.mock_form_instance.cleaned_data = {"name": "test"}

        # Act
        with patch("sfd.views.common.search.super") as mock_super:
            mock_queryset = Mock()
            mock_queryset.ordered = False
            mock_filtered_queryset = Mock()
            mock_filtered_queryset.ordered = False
            mock_queryset.filter.return_value = mock_filtered_queryset
            mock_super.return_value.get_queryset.return_value = mock_queryset

            with patch.object(self.view, "get_query") as mock_get_query:
                with patch("builtins.hasattr") as mock_hasattr:
                    # Mock hasattr calls: has _meta, no date, no created_at
                    mock_hasattr.side_effect = lambda obj, attr: {
                        (self.view.model, "_meta"): True,
                        (self.view.model, "date"): False,
                        (self.view.model, "created_at"): False,
                    }.get((obj, attr), False)

                    mock_get_query.return_value = Q(name="test")

                    self.view.get_queryset()

                    # Assert
                    mock_filtered_queryset.order_by.assert_called_once_with("pk")

    def test_get_queryset_no_ordering_when_already_ordered(self):
        """Test get_queryset method does not apply ordering when queryset is already ordered."""

        # Setup mocks
        self.mock_form_instance.is_valid.return_value = True
        self.mock_form_instance.cleaned_data = {"date": "2024-01-01"}

        # Act
        with patch("sfd.views.common.search.super") as mock_super:
            mock_queryset = Mock()
            mock_queryset.ordered = True  # Already ordered
            mock_filtered_queryset = Mock()
            mock_filtered_queryset.ordered = True  # Still ordered after filter
            mock_queryset.filter.return_value = mock_filtered_queryset
            mock_super.return_value.get_queryset.return_value = mock_queryset

            with patch.object(self.view, "get_query") as mock_get_query:
                mock_get_query.return_value = Q(date="2024-01-01")
                result = self.view.get_queryset()

                # Assert
                mock_filtered_queryset.order_by.assert_not_called()
                self.assertEqual(result, mock_filtered_queryset)

    def test_get_queryset_with_complex_query(self):
        """Test get_queryset method with complex search criteria."""

        # Setup mocks
        self.mock_form_instance.is_valid.return_value = True
        complex_data = {"date": "2024-01-01", "name": "New Year"}
        self.mock_form_instance.cleaned_data = complex_data

        request = self.factory.get("/?date=2024-01-01&name=New%20Year")
        self.view.setup(request)

        # Act
        with patch("sfd.views.common.search.super") as mock_super:
            mock_queryset = Mock()
            mock_queryset.ordered = True
            mock_filtered_queryset = Mock()
            mock_filtered_queryset.ordered = True
            mock_queryset.filter.return_value = mock_filtered_queryset
            mock_super.return_value.get_queryset.return_value = mock_queryset

            with patch.object(self.view, "get_query") as mock_get_query:
                complex_query = Q(date="2024-01-01", name="New Year")
                mock_get_query.return_value = complex_query
                result = self.view.get_queryset()

                # Assert
                mock_get_query.assert_called_once_with(self.mock_form_instance)
                mock_queryset.filter.assert_called_once_with(complex_query)
                self.assertEqual(result, mock_filtered_queryset)

    def test_get_context_data_structure(self):
        """Test get_context_data method returns correct context structure."""
        self.view.list_display = ("date", "name")

        request = self.factory.get("/search/?q=test")
        self.view.setup(request)

        # Set up object_list to ensure pagination context
        self.view.object_list = []

        # Act
        with patch("sfd.views.common.search.super") as mock_super:
            mock_context = {"object_list": [], "page_obj": None}
            mock_super.return_value.get_context_data.return_value = mock_context

            context = self.view.get_context_data()

            # Assert
            self.assertIn("search_url", context)
            self.assertIn("page_link_url", context)
            self.assertIn("search_form", context)
            self.assertIn("is_popup", context)
            self.assertIn("headers", context)
            self.assertIn("list_display", context)

    def test_get_context_data_values(self):
        """Test get_context_data method returns correct context values."""
        # Arrange
        self.view.list_display = ("date", "name")
        self.view.is_popup = True

        request = self.factory.get("/search/?q=test")
        self.view.setup(request)

        # Set up object_list to ensure pagination context
        self.view.object_list = []

        # Act
        with patch("sfd.views.common.search.super") as mock_super:
            mock_context = {"object_list": [], "page_obj": None}
            mock_super.return_value.get_context_data.return_value = mock_context

            context = self.view.get_context_data()

            # Assert
            self.assertEqual(context["search_url"], "/search/")
            self.assertEqual(context["page_link_url"], "/search/?q=test")
            self.assertTrue(context["is_popup"])
            self.assertEqual(context["list_display"], ("date", "name"))

    def test_base_search_view_inheritance(self):
        """Test that BaseSearchView inherits from required mixins."""

        # Assert
        from django.views.generic import ListView
        from django.views.generic.edit import FormMixin

        self.assertTrue(isinstance(self.view, FormMixin))
        self.assertTrue(isinstance(self.view, ListView))


@pytest.mark.unit
@pytest.mark.integration
class BaseSearchViewIntegrationTest(BaseTestMixin, TestCase):
    databases = {"default", "postgres"}

    def setUp(self):
        """Set up test data for BaseSearchView tests."""
        super().setUp()

        from django import forms

        class TestSearchForm(forms.ModelForm):
            class Meta:
                model = Holiday
                fields = ["date", "name"]

        self.view = BaseSearchView()
        self.view.model = Holiday
        self.view.form_class = TestSearchForm

        request = self.factory.get("/")
        self.view.setup(request)

    def test_get_queryset_real_database_integration(self):
        """Test get_queryset method with real database data and form."""
        # Create test data
        Holiday.objects.create(date=date(2024, 1, 1), name="New Year")
        Holiday.objects.create(date=date(2024, 7, 4), name="Independence")
        Holiday.objects.create(date=date(2024, 12, 25), name="Christmas")

        # Act
        queryset = self.view.get_queryset()

        # Assert
        self.assertEqual(queryset.count(), 3)

    def test_base_search_view_with_real_model(self):
        """Test BaseSearchView with real Holiday model data."""
        # Arrange
        Holiday.objects.create(date="2024-01-01", name="New Year")
        Holiday.objects.create(date="2024-07-04", name="Independence")

        self.view.list_display = ("date", "name")

        # Set up a proper request with GET data to test form functionality
        request = self.factory.get("/?date=2024-01-01")
        self.view.setup(request)

        # Act
        queryset = self.view.get_queryset()
        self.view.object_list = queryset  # Set object_list before calling get_context_data
        context = self.view.get_context_data()

        # Assert
        self.assertEqual(queryset.count(), 2)  # No matching records without proper form validation
        self.assertIn("search_form", context)
        self.assertEqual(len(context["headers"]), 2)
