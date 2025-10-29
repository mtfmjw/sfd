"""Test cases for common forms widgets and fields.

This module provides comprehensive test coverage for custom Django form
widgets and fields defined in sfd.common.forms, including:
- SearchFieldWidget: Custom widget for search popup functionality
- DurationTimeField: Field for time duration input/storage
- FormattedNumberInput: Widget for number formatting with separators
"""

import datetime

import pytest
from django.test import TestCase

from sfd.common.forms import DurationTimeField, FormattedNumberInput, SearchFieldWidget


@pytest.mark.unit
@pytest.mark.forms
class SearchFieldWidgetTest(TestCase):
    """Test cases for SearchFieldWidget custom widget."""

    def test_widget_initialization(self):
        """Test that SearchFieldWidget initializes with search_url."""
        search_url = "/search/postcode/"
        widget = SearchFieldWidget(search_url=search_url)

        self.assertEqual(widget.search_url, search_url)

    def test_widget_initialization_with_attrs(self):
        """Test widget initialization with additional attributes."""
        search_url = "/search/municipality/"
        attrs = {"class": "custom-class", "data-test": "value"}
        widget = SearchFieldWidget(search_url=search_url, attrs=attrs)

        self.assertEqual(widget.search_url, search_url)
        self.assertEqual(widget.attrs["class"], "custom-class")
        self.assertEqual(widget.attrs["data-test"], "value")

    def test_render_with_value(self):
        """Test widget rendering with a value."""
        search_url = "/search/postcode/"
        widget = SearchFieldWidget(search_url=search_url)

        html = widget.render("postcode_search", "123-4567", attrs={"id": "id_postcode_search"})

        # Check that the output contains expected elements
        self.assertIn('id="id_postcode_search"', html)
        self.assertIn('value="123-4567"', html)
        self.assertIn("readonly", html)
        self.assertIn("search-field", html)
        self.assertIn("open-popup-modal-dynamic-btn", html)
        self.assertIn('hx-get="/search/postcode/"', html)
        self.assertIn('hx-target="#popupModalDynamicContent"', html)
        self.assertIn('hx-swap="innerHTML"', html)
        self.assertIn('hx-on::after-swap="openPopupModalDynamic()"', html)
        self.assertIn("🔍", html)
        self.assertIn("search-button-container", html)

    def test_render_without_value(self):
        """Test widget rendering without a value."""
        search_url = "/search/municipality/"
        widget = SearchFieldWidget(search_url=search_url)

        html = widget.render("municipality_search", None, attrs={"id": "id_municipality_search"})

        # Check that the output contains expected elements
        self.assertIn('id="id_municipality_search"', html)
        self.assertIn("readonly", html)
        self.assertIn("search-field", html)
        self.assertIn("open-popup-modal-dynamic-btn", html)
        self.assertIn('hx-get="/search/municipality/"', html)
        self.assertIn("🔍", html)

    def test_render_without_attrs(self):
        """Test widget rendering without custom attrs."""
        search_url = "/search/test/"
        widget = SearchFieldWidget(search_url=search_url)

        html = widget.render("test_field", "test_value")

        # Check that default attributes are applied
        self.assertIn("readonly", html)
        self.assertIn("search-field", html)
        self.assertIn('value="test_value"', html)

    def test_render_search_button_content(self):
        """Test that search button is rendered with correct HTMX attributes."""
        search_url = "/api/search/"
        widget = SearchFieldWidget(search_url=search_url)

        html = widget.render("field", "value")

        # Verify button structure
        self.assertIn('<button type="button"', html)
        self.assertIn('class="open-popup-modal-dynamic-btn"', html)
        self.assertIn('hx-get="/api/search/"', html)
        self.assertIn('hx-target="#popupModalDynamicContent"', html)
        self.assertIn('hx-swap="innerHTML"', html)
        self.assertIn('hx-on::after-swap="openPopupModalDynamic()"', html)
        self.assertIn(">🔍</button>", html)

    def test_render_container_div(self):
        """Test that rendered HTML is wrapped in container div."""
        search_url = "/search/"
        widget = SearchFieldWidget(search_url=search_url)

        html = widget.render("field", "value")

        # Verify container structure
        self.assertIn('<div class="search-button-container">', html)
        self.assertIn("</div>", html)
        # Input should come before button
        input_pos = html.find("<input")
        button_pos = html.find("<button")
        self.assertLess(input_pos, button_pos)


@pytest.mark.unit
@pytest.mark.forms
class DurationTimeFieldTest(TestCase):
    """Test cases for DurationTimeField custom field."""

    def test_to_python_with_timedelta(self):
        """Test to_python with timedelta input (already converted)."""
        field = DurationTimeField()
        td = datetime.timedelta(hours=2, minutes=30)

        result = field.to_python(td)

        self.assertEqual(result, td)
        self.assertIsInstance(result, datetime.timedelta)

    def test_to_python_with_none(self):
        """Test to_python with None input."""
        field = DurationTimeField()

        result = field.to_python(None)

        self.assertIsNone(result)

    def test_to_python_with_time_string(self):
        """Test to_python with time string input."""
        field = DurationTimeField()

        result = field.to_python("14:30")

        self.assertIsInstance(result, datetime.timedelta)
        self.assertEqual(result, datetime.timedelta(hours=14, minutes=30))

    def test_to_python_with_time_object(self):
        """Test to_python with time object input."""
        field = DurationTimeField()
        time_value = datetime.time(9, 45)

        result = field.to_python(time_value)

        self.assertIsInstance(result, datetime.timedelta)
        self.assertEqual(result, datetime.timedelta(hours=9, minutes=45))

    def test_to_python_with_various_time_formats(self):
        """Test to_python with various time format strings."""
        field = DurationTimeField()

        # Test HH:MM format
        result1 = field.to_python("08:15")
        self.assertEqual(result1, datetime.timedelta(hours=8, minutes=15))

        # Test with leading zeros
        result2 = field.to_python("00:30")
        self.assertEqual(result2, datetime.timedelta(minutes=30))

        # Test midnight
        result3 = field.to_python("00:00")
        self.assertEqual(result3, datetime.timedelta())

        # Test late evening
        result4 = field.to_python("23:59")
        self.assertEqual(result4, datetime.timedelta(hours=23, minutes=59))

    def test_prepare_value_with_timedelta(self):
        """Test prepare_value converts timedelta to time for display."""
        field = DurationTimeField()
        td = datetime.timedelta(hours=3, minutes=45)

        result = field.prepare_value(td)

        self.assertIsInstance(result, datetime.time)
        self.assertEqual(result, datetime.time(3, 45))

    def test_prepare_value_with_zero_duration(self):
        """Test prepare_value with zero duration."""
        field = DurationTimeField()
        td = datetime.timedelta()

        result = field.prepare_value(td)

        self.assertIsInstance(result, datetime.time)
        self.assertEqual(result, datetime.time(0, 0))

    def test_prepare_value_with_large_duration(self):
        """Test prepare_value with duration spanning multiple hours."""
        field = DurationTimeField()
        td = datetime.timedelta(hours=18, minutes=20)

        result = field.prepare_value(td)

        self.assertIsInstance(result, datetime.time)
        self.assertEqual(result, datetime.time(18, 20))

    def test_prepare_value_with_non_timedelta(self):
        """Test prepare_value with non-timedelta input returns as-is."""
        field = DurationTimeField()
        time_value = datetime.time(10, 30)

        result = field.prepare_value(time_value)

        self.assertEqual(result, time_value)

    def test_prepare_value_with_none(self):
        """Test prepare_value with None input."""
        field = DurationTimeField()

        result = field.prepare_value(None)

        self.assertIsNone(result)

    def test_prepare_value_with_string(self):
        """Test prepare_value with string input returns as-is."""
        field = DurationTimeField()
        string_value = "10:30"

        result = field.prepare_value(string_value)

        self.assertEqual(result, string_value)

    def test_round_trip_conversion(self):
        """Test converting from string to timedelta and back to time."""
        field = DurationTimeField()

        # Convert string to timedelta
        td = field.to_python("07:25")
        self.assertEqual(td, datetime.timedelta(hours=7, minutes=25))

        # Convert timedelta back to time
        time_value = field.prepare_value(td)
        self.assertEqual(time_value, datetime.time(7, 25))

    def test_timedelta_with_seconds_truncates(self):
        """Test that seconds are truncated when converting to time."""
        field = DurationTimeField()
        td = datetime.timedelta(hours=5, minutes=30, seconds=45)

        result = field.prepare_value(td)

        # Seconds should be truncated to 0
        self.assertEqual(result, datetime.time(5, 30))

    def test_field_initialization(self):
        """Test that DurationTimeField can be initialized."""
        field = DurationTimeField()

        self.assertIsInstance(field, DurationTimeField)

    def test_field_with_required_true(self):
        """Test field with required=True."""
        field = DurationTimeField(required=True)

        self.assertTrue(field.required)

    def test_field_with_required_false(self):
        """Test field with required=False allows None."""
        field = DurationTimeField(required=False)

        result = field.to_python(None)

        self.assertIsNone(result)
        self.assertFalse(field.required)


@pytest.mark.unit
@pytest.mark.forms
class FormattedNumberInputTest(TestCase):
    """Test cases for FormattedNumberInput custom widget."""

    def test_widget_initialization(self):
        """Test that FormattedNumberInput initializes properly."""
        widget = FormattedNumberInput()

        self.assertIsInstance(widget, FormattedNumberInput)

    def test_render_with_value(self):
        """Test widget rendering with a numeric value."""
        widget = FormattedNumberInput()

        html = widget.render("amount", "1000000", attrs={"id": "id_amount"})

        # Check that the output contains expected elements
        self.assertIn('id="id_amount"', html)
        self.assertIn('value="1000000"', html)
        self.assertIn("vTextField", html)
        self.assertIn("formatted-number-input", html)

    def test_render_includes_javascript(self):
        """Test that rendered HTML includes JavaScript for formatting."""
        widget = FormattedNumberInput()

        html = widget.render("price", "5000", attrs={"id": "id_price"})

        # Check for JavaScript elements
        self.assertIn("<script>", html)
        self.assertIn("</script>", html)
        self.assertIn("formatNumberInput", html)
        self.assertIn("'id_price'", html)
        self.assertIn("DOMContentLoaded", html)

    def test_render_without_value(self):
        """Test widget rendering without a value."""
        widget = FormattedNumberInput()

        html = widget.render("quantity", None, attrs={"id": "id_quantity"})

        # Check that the output contains expected elements
        self.assertIn('id="id_quantity"', html)
        self.assertIn("vTextField", html)
        self.assertIn("formatted-number-input", html)
        self.assertIn("formatNumberInput", html)

    def test_render_css_classes_applied(self):
        """Test that CSS classes are properly applied."""
        widget = FormattedNumberInput()

        html = widget.render("field", "100", attrs={"id": "id_field"})

        # Check for CSS classes
        self.assertIn('class="vTextField formatted-number-input"', html)

    def test_render_with_custom_attrs(self):
        """Test widget rendering with custom attributes."""
        widget = FormattedNumberInput()
        attrs = {"id": "custom_id", "data-test": "custom"}

        html = widget.render("field", "999", attrs=attrs)

        # Check custom attributes
        self.assertIn('id="custom_id"', html)
        self.assertIn('data-test="custom"', html)
        self.assertIn("formatNumberInput", html)
        self.assertIn("'custom_id'", html)

    def test_render_without_attrs(self):
        """Test widget rendering without custom attrs."""
        widget = FormattedNumberInput()

        html = widget.render("field", "500")

        # Check that default classes are applied
        self.assertIn("vTextField", html)
        self.assertIn("formatted-number-input", html)
        self.assertIn("<script>", html)

    def test_render_javascript_structure(self):
        """Test that JavaScript structure is correct."""
        widget = FormattedNumberInput()

        html = widget.render("test_field", "123", attrs={"id": "id_test"})

        # Verify JavaScript structure
        self.assertIn("document.addEventListener('DOMContentLoaded', function() {", html)
        self.assertIn("formatNumberInput('id_test');", html)
        self.assertIn("});", html)

    def test_render_input_before_script(self):
        """Test that input element comes before script tag."""
        widget = FormattedNumberInput()

        html = widget.render("field", "1000", attrs={"id": "id_field"})

        # Input should come before script
        input_pos = html.find("<input")
        script_pos = html.find("<script>")
        self.assertLess(input_pos, script_pos)

    def test_render_with_zero_value(self):
        """Test widget rendering with zero value."""
        widget = FormattedNumberInput()

        html = widget.render("field", "0", attrs={"id": "id_field"})

        self.assertIn('value="0"', html)
        self.assertIn("formatNumberInput", html)

    def test_render_with_negative_value(self):
        """Test widget rendering with negative value."""
        widget = FormattedNumberInput()

        html = widget.render("field", "-5000", attrs={"id": "id_field"})

        self.assertIn('value="-5000"', html)
        self.assertIn("formatNumberInput", html)

    def test_widget_with_initial_attrs(self):
        """Test widget initialized with attrs."""
        widget = FormattedNumberInput(attrs={"placeholder": "Enter amount"})

        html = widget.render("amount", "1000", attrs={"id": "id_amount"})

        self.assertIn('placeholder="Enter amount"', html)
        self.assertIn("vTextField", html)
        self.assertIn("formatted-number-input", html)

    def test_multiple_widgets_different_ids(self):
        """Test that multiple widgets generate unique JavaScript calls."""
        widget1 = FormattedNumberInput()
        widget2 = FormattedNumberInput()

        html1 = widget1.render("field1", "100", attrs={"id": "id_field1"})
        html2 = widget2.render("field2", "200", attrs={"id": "id_field2"})

        # Each should have its own ID in the JavaScript
        self.assertIn("formatNumberInput('id_field1');", html1)
        self.assertIn("formatNumberInput('id_field2');", html2)
        self.assertNotIn("id_field2", html1)
        self.assertNotIn("id_field1", html2)
