import datetime

from django import forms
from django.utils.html import format_html
from django.utils.safestring import mark_safe


class SearchFieldWidget(forms.TextInput):
    """Custom widget for search display fields.

    This widget creates a read-only text input with a search button
    that opens a popup for selection.
    """

    def __init__(self, search_url, *args, **kwargs):
        """Initialize widget with search type.

        Args:
            search_url (str): Type of search ('postcode' or 'municipality')
        """
        self.search_url = search_url
        super().__init__(*args, **kwargs)

    def render(self, name, value, attrs=None, renderer=None):
        """Render the widget with search button."""
        if attrs is None:
            attrs = {}

        # Add classes and attributes for the search functionality
        attrs.update(
            {
                "readonly": True,
                "class": " search-field",
            }
        )

        # Render the base input
        html = super().render(name, value, attrs, renderer)

        # Add the search button
        button_html = format_html(
            '<button type="button" class="open-popup-modal-dynamic-btn"'
            + ' hx-get="{}" hx-target="#popupModalDynamicContent" hx-swap="innerHTML"'
            + ' hx-on::after-swap="openPopupModalDynamic()">🔍</button>',
            self.search_url,
        )

        # Wrap in container div
        container_html = format_html('<div class="search-button-container">{}{}</div>', mark_safe(html), button_html)

        return container_html


class DurationTimeField(forms.TimeField):
    """Custom field that converts time input to timedelta and back.

    This field handles the conversion between time input (HH:MM) in forms
    and timedelta storage in the model. The conversion logic is properly
    separated from validation logic.
    """

    def to_python(self, value):
        """Convert form input to timedelta.

        Args:
            value: Form input (could be string, time, or timedelta)

        Returns:
            datetime.timedelta: Converted duration value
        """
        if isinstance(value, datetime.timedelta):
            return value

        # First convert to time using parent's to_python
        time_value = super().to_python(value)
        if time_value is None:
            return None

        # Convert time to timedelta
        return datetime.timedelta(hours=time_value.hour, minutes=time_value.minute)

    def prepare_value(self, value):
        """Convert timedelta to time for display in form.

        Args:
            value: timedelta value from model

        Returns:
            datetime.time: Time value for form display
        """
        if isinstance(value, datetime.timedelta):
            total_seconds = int(value.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return datetime.time(hours, minutes)
        return value


class FormattedNumberInput(forms.TextInput):
    """
    A custom widget that includes JavaScript to format a number
    with thousand separators as the user types.
    """

    def render(self, name, value, attrs=None, renderer=None):
        # Add a CSS class for styling and get the standard input HTML
        if attrs is None:
            attrs = {}
        attrs["class"] = "vTextField formatted-number-input"

        html_input = super().render(name, value, attrs, renderer)

        # Get the ID of the input field
        final_attrs = self.build_attrs(self.attrs, attrs)
        input_id = final_attrs.get("id", "")

        # Add the JavaScript snippet to call our formatting function
        js_script = f"""
            <script>
                document.addEventListener('DOMContentLoaded', function() {{
                    formatNumberInput('{input_id}');
                }});
            </script>
        """

        return mark_safe(html_input + js_script)
