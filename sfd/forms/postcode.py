"""Forms for Postcode model with cascading prefecture/municipality dropdowns.

This module provides Django forms for the Postcode model that implement
cascading dropdown functionality between prefecture and municipality fields.
When a prefecture is selected, the municipality dropdown is dynamically
populated with only the municipalities from that prefecture using HTMX.

Forms:
    PostcodeAdminForm: Admin form with cascading prefecture/municipality dropdowns

Features:
    - Dynamic municipality filtering based on prefecture selection
    - HTMX-powered dropdown population
    - Maintains existing municipality selection when editing
    - Proper error handling and validation
"""

from django import forms
from django.utils.translation import gettext_lazy as _

from sfd.models.municipality import Municipality
from sfd.models.postcode import Postcode


class PostcodeAdminForm(forms.ModelForm):
    """Admin form for Postcode with cascading prefecture/municipality dropdowns.

    This form provides a better user experience for selecting municipalities
    by first choosing a prefecture, which then populates the municipality
    dropdown with only relevant options using HTMX.

    Features:
        - Prefecture dropdown populated from Municipality model
        - Municipality dropdown dynamically filtered by prefecture
        - Maintains selected values when editing existing records
        - HTMX-powered cascading functionality

    Fields:
        prefecture: CharField with ChoiceField widget for prefecture selection
        municipality: ForeignKey to Municipality with filtered choices

    Note:
        Requires HTMX to handle the cascading behavior.
    """

    # Declare prefecture field after Meta class
    prefecture = forms.ChoiceField(
        label=_("Prefecture"),
        choices=[("", _("Select Prefecture"))],
        required=True,
        widget=forms.Select(
            attrs={
                "id": "id_prefecture",
                "name": "prefecture",
                "hx-get": "/sfd/change_prefecture/",
                "hx-target": "#id_municipality",
                "hx-include": "this",
                "hx-trigger": "change",
            }
        ),
    )

    municipality = forms.ModelChoiceField(
        label=_("Municipality"),
        queryset=Municipality.objects.none(),
        required=True,
        widget=forms.Select(attrs={"id": "id_municipality"}),
    )

    class Meta:
        model = Postcode
        # Don't include prefecture in model fields since it's not a model field
        fields = ["postcode", "municipality", "town_name", "town_name_kana"]
        widgets = {
            "municipality": forms.Select(attrs={"id": "id_municipality"}),
        }

    def __init__(self, *args, **kwargs):
        """Initialize form with prefecture choices and municipality filtering.

        Populates the prefecture choices from the Municipality model and
        sets up the municipality field based on the current instance
        (if editing an existing record) or from POST data (when validation errors occur).

        Args:
            *args: Variable length argument list passed to parent
            **kwargs: Arbitrary keyword arguments passed to parent
        """
        super().__init__(*args, **kwargs)

        # Get all prefectures from municipalities
        prefectures = (
            Municipality.objects.filter(municipality_name="").values_list("prefecture_name", flat=True).distinct().order_by("municipality_code")
        )

        # Only update choices if prefecture field exists (it may be omitted in certain readonly admin contexts)
        if "prefecture" in self.fields:
            self.fields["prefecture"].choices = [("", _("Select Prefecture"))] + [(prefecture, prefecture) for prefecture in prefectures]

        # Determine prefecture from either POST data or existing instance
        prefecture_name = None

        # First, check if we have POST data (form submission with potential validation errors)
        if self.data and self.data.get("prefecture"):
            prefecture_name = self.data.get("prefecture")
        # Otherwise, check if we have an existing instance (editing existing record)
        elif self.instance and self.instance.municipality_id:
            prefecture_name = self.instance.municipality.prefecture_name
            # Set the prefecture value in initial data
            if "prefecture" in self.fields:
                self.initial["prefecture"] = prefecture_name

        # If we have a prefecture, filter municipalities accordingly
        if prefecture_name:
            municipalities = Municipality.objects.filter(prefecture_name=prefecture_name).exclude(municipality_name="").order_by("municipality_code")
            self.fields["municipality"].queryset = municipalities  # type: ignore

    def full_clean(self):
        """Override full_clean to dynamically update municipality queryset before validation.

        This method is called before individual field validation, allowing us to
        update the municipality queryset based on the selected prefecture before
        Django validates the municipality field.
        """
        # Get prefecture from submitted data
        prefecture = self.data.get("prefecture") if hasattr(self, "data") and self.data else None
        municipality_id = self.data.get("municipality") if hasattr(self, "data") and self.data else None

        # If we have both prefecture and municipality data, update the queryset
        if prefecture and municipality_id:
            # Update municipality queryset to include municipalities from selected prefecture
            valid_municipalities = (
                Municipality.objects.filter(prefecture_name=prefecture).exclude(municipality_name="").order_by("municipality_code")
            )
            self.fields["municipality"].queryset = valid_municipalities  # type: ignore

        # Call parent's full_clean to proceed with normal validation
        super().full_clean()

    def clean(self):
        """Validate that prefecture and municipality are consistent.

        Ensures that the selected municipality belongs to the selected
        prefecture, preventing data inconsistency.

        Returns:
            dict: Cleaned form data

        Raises:
            ValidationError: When municipality doesn't belong to selected prefecture
        """
        cleaned_data = super().clean()
        prefecture = cleaned_data.get("prefecture")
        municipality = cleaned_data.get("municipality")

        if municipality and prefecture:
            if municipality.prefecture_name != prefecture:
                raise forms.ValidationError(_("Selected municipality does not belong to the selected prefecture."))

        return cleaned_data


class PostcodeSearchForm(forms.ModelForm):
    municipality_name = forms.CharField(label=_("Municipality Name"), required=False)
    municipality_name_kana = forms.CharField(label=_("Municipality Name Kana"), required=False)

    class Meta:
        model = Postcode
        fields = ["postcode", "town_name", "town_name_kana"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["postcode"].required = False
        self.fields["town_name"].required = False
        self.fields["town_name_kana"].required = False
