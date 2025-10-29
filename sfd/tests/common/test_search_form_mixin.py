# type: ignore
"""Test cases for sfd.forms package."""

import pytest
from django import forms
from django.test import TestCase
from django.utils.translation import gettext_lazy as _

from sfd.forms.search import SearchFormMixin
from sfd.tests.unittest import BaseTestMixin


@pytest.mark.unit
@pytest.mark.common
class TestSearchFormMixin(TestCase):
    """Test cases for SearchFormMixin functionality."""

    def setUp(self):
        """Set up test fixtures for SearchFormMixin tests."""

        # Create a test form class that inherits from both forms.Form and SearchFormMixin
        class TestSearchForm(SearchFormMixin, forms.Form):
            """Test form class that uses SearchFormMixin."""

            name = forms.CharField(max_length=100, required=False)
            email = forms.EmailField(required=False)

        self.TestSearchForm = TestSearchForm

    def test_mixin_adds_deleted_flg_field(self):
        """Test that SearchFormMixin automatically adds deleted_flg field."""
        # Arrange & Act
        form = self.TestSearchForm()

        # Assert
        self.assertIn("deleted_flg", form.fields)
        self.assertIsInstance(form.fields["deleted_flg"], forms.BooleanField)

    def test_deleted_flg_field_properties(self):
        """Test that deleted_flg field has correct properties."""
        # Arrange & Act
        form = self.TestSearchForm()
        deleted_flg_field = form.fields["deleted_flg"]

        # Assert
        self.assertEqual(deleted_flg_field.label, _("delete"))
        self.assertFalse(deleted_flg_field.required)
        self.assertFalse(deleted_flg_field.initial)

    def test_mixin_preserves_existing_fields(self):
        """Test that SearchFormMixin preserves existing form fields."""
        # Arrange & Act
        form = self.TestSearchForm()

        # Assert
        self.assertIn("name", form.fields)
        self.assertIn("email", form.fields)
        self.assertIsInstance(form.fields["name"], forms.CharField)
        self.assertIsInstance(form.fields["email"], forms.EmailField)

    def test_mixin_does_not_override_existing_deleted_flg(self):
        """Test that SearchFormMixin does not override existing deleted_flg field."""

        # Arrange
        class TestFormWithDeletedFlg(SearchFormMixin, forms.Form):
            """Test form with pre-existing deleted_flg field."""

            deleted_flg = forms.BooleanField(label="Custom Delete", required=True, initial=True)
            name = forms.CharField(max_length=50)

        # Act
        form = TestFormWithDeletedFlg()

        # Assert
        self.assertIn("deleted_flg", form.fields)
        self.assertEqual(form.fields["deleted_flg"].label, "Custom Delete")
        self.assertTrue(form.fields["deleted_flg"].required)
        self.assertTrue(form.fields["deleted_flg"].initial)

    def test_form_initialization_with_data(self):
        """Test form initialization with data including deleted_flg."""
        # Arrange
        form_data = {"name": "Test User", "email": "test@example.com", "deleted_flg": True}

        # Act
        form = self.TestSearchForm(data=form_data)

        # Assert
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["name"], "Test User")
        self.assertEqual(form.cleaned_data["email"], "test@example.com")
        self.assertTrue(form.cleaned_data["deleted_flg"])

    def test_form_validation_with_invalid_data(self):
        """Test form validation with invalid data."""
        # Arrange
        form_data = {
            "name": "Test User",
            "email": "invalid-email",  # Invalid email format
            "deleted_flg": True,
        }

        # Act
        form = self.TestSearchForm(data=form_data)

        # Assert
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)
        # deleted_flg should still be valid since it's a boolean field
        self.assertNotIn("deleted_flg", form.errors)

    def test_form_without_deleted_flg_data(self):
        """Test form validation when deleted_flg is not provided in data."""
        # Arrange
        form_data = {
            "name": "Test User",
            "email": "test@example.com",
            # deleted_flg not provided
        }

        # Act
        form = self.TestSearchForm(data=form_data)

        # Assert
        self.assertTrue(form.is_valid())
        self.assertFalse(form.cleaned_data["deleted_flg"])  # Should default to False

    def test_empty_form_initialization(self):
        """Test initialization of empty form."""
        # Arrange & Act
        form = self.TestSearchForm()

        # Assert
        self.assertIn("deleted_flg", form.fields)
        self.assertFalse(form.is_bound)
        # Test initial value through field initial property
        self.assertFalse(form.fields["deleted_flg"].initial)

    def test_multiple_inheritance_compatibility(self):
        """Test that SearchFormMixin works correctly with multiple inheritance."""

        # Arrange
        class AnotherMixin:
            """Another mixin for testing multiple inheritance."""

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                if hasattr(self, "fields") and "custom_field" not in self.fields:
                    self.fields["custom_field"] = forms.CharField(required=False)

        class MultiInheritanceForm(SearchFormMixin, AnotherMixin, forms.Form):
            """Form with multiple mixins."""

            base_field = forms.CharField(max_length=100)

        # Act
        form = MultiInheritanceForm()

        # Assert
        self.assertIn("deleted_flg", form.fields)
        self.assertIn("custom_field", form.fields)
        self.assertIn("base_field", form.fields)

    def test_deleted_flg_field_widget(self):
        """Test that deleted_flg field uses correct widget."""
        # Arrange & Act
        form = self.TestSearchForm()
        deleted_flg_field = form.fields["deleted_flg"]

        # Assert
        self.assertIsInstance(deleted_flg_field.widget, forms.CheckboxInput)

    @pytest.mark.integration
    def test_form_rendering_includes_deleted_flg(self):
        """Test that form rendering includes the deleted_flg field."""
        # Arrange
        form = self.TestSearchForm()

        # Act
        form_html = str(form)

        # Assert
        self.assertIn('name="deleted_flg"', form_html)
        self.assertIn('type="checkbox"', form_html)

    def test_mixin_with_form_subclass_inheritance(self):
        """Test SearchFormMixin with form subclass inheritance."""

        # Arrange
        class BaseSearchForm(SearchFormMixin, forms.Form):
            """Base search form with mixin."""

            common_field = forms.CharField(max_length=50)

        class ExtendedSearchForm(BaseSearchForm):
            """Extended search form inheriting from base."""

            extended_field = forms.IntegerField()

        # Act
        form = ExtendedSearchForm()

        # Assert
        self.assertIn("deleted_flg", form.fields)
        self.assertIn("common_field", form.fields)
        self.assertIn("extended_field", form.fields)

    def test_mixin_initialization_args_kwargs_passing(self):
        """Test that SearchFormMixin properly passes args and kwargs to super()."""
        # Arrange
        initial_data = {"name": "Initial Name"}
        form_data = {"name": "Form Data", "deleted_flg": True}

        # Act
        form_with_initial = self.TestSearchForm(initial=initial_data)
        form_with_data = self.TestSearchForm(data=form_data)

        # Assert
        # Test initial data
        self.assertEqual(form_with_initial.initial["name"], "Initial Name")

        # Test form data
        self.assertTrue(form_with_data.is_bound)
        self.assertTrue(form_with_data.is_valid())
        self.assertEqual(form_with_data.cleaned_data["name"], "Form Data")
        self.assertTrue(form_with_data.cleaned_data["deleted_flg"])


@pytest.mark.unit
@pytest.mark.common
class TestSearchFormMixinEdgeCases(BaseTestMixin, TestCase):
    """Test edge cases and error conditions for SearchFormMixin."""

    def test_mixin_with_modelform_simulation(self):
        """Test SearchFormMixin compatibility with ModelForm-like structure."""

        # Since BaseModel is abstract, we'll simulate ModelForm behavior
        class TestModelForm(SearchFormMixin, forms.Form):
            """Simulated ModelForm with SearchFormMixin."""

            name = forms.CharField(max_length=100)

        # Act
        form = TestModelForm()

        # Assert
        self.assertIn("deleted_flg", form.fields)
        self.assertIn("name", form.fields)

    def test_mixin_field_order(self):
        """Test that deleted_flg field is added in correct order."""

        # Arrange
        class OrderTestForm(SearchFormMixin, forms.Form):
            """Form to test field ordering."""

            field_a = forms.CharField()
            field_b = forms.CharField()

        # Act
        form = OrderTestForm()
        field_names = list(form.fields.keys())

        # Assert
        self.assertIn("deleted_flg", field_names)
        # deleted_flg should be added after existing fields
        self.assertEqual(field_names[:2], ["field_a", "field_b"])
        self.assertEqual(field_names[-1], "deleted_flg")
