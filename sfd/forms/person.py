"""Forms for Person model with search popup functionality.

This module provides Django forms for the Person model that implement
search popup functionality for postcode and municipality fields instead
of dropdown lists. This is useful when there are too many items to display
in dropdowns efficiently.

Forms:
    PersonAdminForm: Admin form with search popup buttons for postcode/municipality

Features:
    - Search popup windows for postcode and municipality selection
    - JavaScript-powered modal dialogs
    - Maintains existing selection values when editing
    - Proper validation and error handling
"""

from django import forms
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from sfd.common.forms import SearchFieldWidget
from sfd.models.person import Person


class PersonAdminForm(forms.ModelForm):
    # デフォルトの郵便番号外部キー実装を回避するため、postcode_searchフィールドを追加
    postcode_search = forms.CharField(label=_("Postcode"), required=False, help_text=_("Search and select postcode, town name, and municipality."))

    # デフォルトの市区町村外部キー実装を回避するため、municipality_displayフィールドを追加
    municipality_display = forms.CharField(
        label=_("Municipality"),
        required=False,
        widget=forms.TextInput(attrs={"readonly": True, "id": "id_municipality_display"}),
    )

    class Meta:
        model = Person
        fields = [
            "family_name",
            "family_name_kana",
            "family_name_romaji",
            "name",
            "name_kana",
            "name_romaji",
            "birthday",
            "gender",
            "email",
            "phone_number",
            "mobile_number",
            "postcode",
            "municipality",
            "address_detail",
        ]
        widgets = {
            "birthday": forms.DateInput(attrs={"type": "date"}),
        }

    class Media:
        """Media files for the form.

        Includes necessary JavaScript files for search popup functionality.
        """

        js = ("sfd/js/search_postcode.js",)

    def __init__(self, *args, **kwargs):
        """Initialize form with search popup functionality.

        Sets up the form fields and adds custom display fields for
        postcode and municipality that show the current selection
        with search buttons.

        Args:
            *args: Variable length argument list passed to parent
            **kwargs: Arbitrary keyword arguments passed to parent
        """
        super().__init__(*args, **kwargs)

        # Set up search widget for postcode field
        self.fields["postcode_search"].widget = SearchFieldWidget(
            search_url=reverse("sfd:search_postcode"),
            attrs={"id": "id_postcode_search", "placeholder": _("Search postcode...")},
        )

        # Set initial values for display fields if editing existing record
        if self.instance and self.instance.pk:
            if self.instance.postcode:
                postcode = self.instance.postcode.postcode
                self.initial["postcode_search"] = f"{postcode[0:3]}-{postcode[3:]}"

            if self.instance.municipality:
                self.initial["municipality_display"] = str(self.instance.municipality)

    def clean(self):
        """Validate form data.

        Performs additional validation to ensure data consistency
        between postcode and municipality fields.

        Returns:
            dict: Cleaned form data

        Raises:
            ValidationError: When data validation fails
        """
        cleaned_data = super().clean()
        postcode = cleaned_data.get("postcode_search").replace("-", "") if cleaned_data.get("postcode_search") else None  # type: ignore
        if postcode:
            try:
                postcode_instance = Person._meta.get_field("postcode").related_model.objects.get(postcode=postcode)  # type: ignore
                self.instance.postcode = postcode_instance
                self.instance.municipality = postcode_instance.municipality

            except Person._meta.get_field("postcode").related_model.DoesNotExist as e:  # type: ignore
                raise forms.ValidationError(_("Selected postcode does not exist.")) from e

        return cleaned_data
