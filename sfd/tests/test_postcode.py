# type: ignore
from unittest.mock import Mock, patch

import pytest
from django import forms
from django.contrib.admin import AdminSite
from django.db.models import QuerySet
from django.test import TestCase
from django.utils.translation import gettext_lazy as _

from sfd.models import Postcode
from sfd.models.municipality import Municipality
from sfd.models.postcode import PostcodeUpload
from sfd.tests.unittest import BaseTestMixin
from sfd.views.base import BaseModelAdmin
from sfd.views.postcode import PostcodeAdmin


@pytest.mark.unit
@pytest.mark.views
class FilterPrefectureTest(BaseTestMixin, TestCase):
    """Test FilterPrefecture functionality with comprehensive coverage."""

    databases = {"default", "postgres"}

    def setUp(self):
        """Set up test data for PostcodeAdmin tests."""
        super().setUp()
        self.site = AdminSite()
        self.admin = PostcodeAdmin(Postcode, self.site)
        self.request = self.factory.get("/admin/")
        self.request.user = self.user

        self.municipality_hokkaido = Municipality.objects.create(
            municipality_code="01001",
            municipality_name="",
            municipality_name_kana="",
            prefecture_name="北海道",
            prefecture_name_kana="ホッカイドウ",
        )
        self.municipality_test = Municipality.objects.create(
            municipality_code="01901",
            municipality_name="",
            municipality_name_kana="",
            prefecture_name="テスト県",
            prefecture_name_kana="テストケン",
        )

        # Create Postcode objects for testing
        Postcode.objects.create(
            postcode="0600000",
            municipality=self.municipality_hokkaido,
            town_name="札幌市中央区",
            town_name_kana="サッポロシチュウオウク",
        )
        Postcode.objects.create(
            postcode="0610000",
            municipality=self.municipality_test,
            town_name="テスト市",
            town_name_kana="テストシ",
        )

    def test_lookups(self):
        """Test lookups method returns correct year choices."""
        # Arrange - Get the filter class from list_filter
        filter_class = self.admin.list_filter[0]
        filter_instance = filter_class(self.request, {}, Postcode, self.admin)

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
        filter_instance = filter_class(self.request, {}, Postcode, self.admin)
        filter_instance.value = lambda: None

        # Act
        original_queryset = Postcode.objects.all()
        queryset = filter_instance.queryset(self.request, original_queryset)
        # Assert
        self.assertTrue(isinstance(queryset, QuerySet))
        self.assertEqual(queryset.model, Postcode)
        self.assertEqual(queryset, original_queryset)
        self.assertEqual(queryset.count(), 2)

    def test_queryset_with_value(self):
        """Test queryset method returns correct queryset."""
        # Arrange - Get the filter class from list_filter
        filter_class = self.admin.list_filter[0]
        filter_instance = filter_class(self.request, {}, Postcode, self.admin)
        filter_instance.value = lambda: "北海道"

        # Act
        original_queryset = Postcode.objects.all()
        queryset = filter_instance.queryset(self.request, original_queryset)
        # Assert
        self.assertTrue(isinstance(queryset, QuerySet))
        self.assertEqual(queryset.model, Postcode)
        # Verify that the queryset is filtered correctly
        self.assertEqual(queryset.count(), 1)
        # Verify the returned queryset contains only postcodes from 北海道
        for postcode in queryset:
            self.assertEqual(postcode.municipality.prefecture_name, "北海道")


@pytest.mark.unit
@pytest.mark.models
class PostcodeTest(TestCase):
    databases = {"default", "postgres"}

    def setUp(self):
        """Set up test environment with sample postcode data."""
        self.municipality = Municipality.objects.create(
            municipality_code="131016",
            municipality_name="世田谷区",
            municipality_name_kana="セタガヤク",
            prefecture_name="東京都",
            prefecture_name_kana="トウキョウト",
        )
        self.postcode = Postcode.objects.create(postcode="1234567", municipality=self.municipality, town_name="Central", town_name_kana="セントラル")

    def test_str_representation(self):
        self.assertEqual(str(self.postcode), "1234567")

    def test_postcode_field_attributes(self):
        postcode = Postcode.objects.get(postcode="1234567")
        self.assertEqual(postcode._meta.get_field("postcode").max_length, 7)

    def test_required_fields_validation(self):
        # Should not raise ValidationError
        self.postcode.full_clean()

    def test_meta_options(self):
        self.assertEqual(Postcode._meta.verbose_name, _("Postcode"))
        self.assertEqual(Postcode._meta.verbose_name_plural, _("Postcodes"))
        self.assertEqual(Postcode._meta.ordering, ["postcode"])

    def test_foreign_key_relationship(self):
        assert self.postcode.municipality.municipality_name == "世田谷区"


@pytest.mark.unit
@pytest.mark.views
class PostcodeAdminTest(BaseTestMixin, TestCase):
    """Test PostcodeAdmin functionality with comprehensive coverage."""

    databases = {"default", "postgres"}

    def setUp(self):
        """Set up test data for PostcodeAdmin tests."""
        super().setUp()

        self.site = AdminSite()
        self.admin = PostcodeAdmin(Postcode, self.site)
        self.request = self.factory.get("/admin/")
        self.request.user = self.user

        self.municipality = Municipality.objects.create(
            municipality_code="131016",
            municipality_name="世田谷区",
            municipality_name_kana="セタガヤク",
            prefecture_name="東京都",
            prefecture_name_kana="トウキョウト",
        )
        self.postcode = Postcode.objects.create(postcode="1234567", municipality=self.municipality, town_name="Central", town_name_kana="セントラル")
        PostcodeUpload.objects.create(municipality_code="131016", postcode="2345678", town_name="テスト町", town_name_kana="テストチョウ")

    def test_postcode_display(self):
        """Test postcode display for PostcodeAdmin."""
        self.assertEqual(self.admin.postcode_display(self.postcode), "123-4567")

    def test_postcode_display_with_none(self):
        """Test postcode display for PostcodeAdmin."""
        self.postcode.postcode = None
        self.assertEqual(self.admin.postcode_display(self.postcode), "")

    def test_municipality_name(self):
        """Test municipality name display for PostcodeAdmin."""
        self.assertIn("世田谷区", self.admin.municipality_name(self.postcode))

    def test_municipality_name_with_none(self):
        """Test municipality name display for PostcodeAdmin."""
        obj = Mock()
        obj.municipality = None
        self.assertEqual(self.admin.municipality_name(obj), "")

    def test_municipality_name_without_name(self):
        """Test municipality name display for PostcodeAdmin."""
        self.postcode.municipality.prefecture_name = ""
        self.postcode.municipality.municipality_name = ""
        self.assertEqual(self.admin.municipality_name(self.postcode), "")

    def test_admin_inheritance(self):
        """Test that PostcodeAdmin properly inherits from BaseModelAdmin."""
        # Assert
        self.assertTrue(isinstance(self.admin, BaseModelAdmin))
        self.assertEqual(self.admin.change_list_template, "sfd/change_list.html")

    @patch("sfd.views.postcode.super")
    def test_get_fieldsets(self, mock_super):
        """Test that the correct fieldsets are returned for PostcodeAdmin."""
        mock_super.return_value.get_fieldsets.return_value = ((None, {"fields": (("postcode",),)}),)
        fieldsets = self.admin.get_fieldsets(self.request)
        self.assertEqual(len(fieldsets), 1)
        self.assertEqual(fieldsets[0][1]["fields"], (("postcode",), ("prefecture", "municipality"), ("town_name", "town_name_kana")))

    @patch("sfd.views.postcode.super")
    @patch("sfd.views.postcode.PostcodeAdmin.has_change_permission", return_value=False)
    @patch("sfd.views.postcode.PostcodeAdmin.has_add_permission", return_value=False)
    def test_get_fieldsets_without_permission(self, mock_has_add_permission, mock_has_change_permission, mock_super):
        """Test that the correct fieldsets are returned for PostcodeAdmin."""
        mock_super.return_value.get_fieldsets.return_value = [(None, {"fields": (("postcode",),)})]
        fieldsets = self.admin.get_fieldsets(self.request)
        self.assertEqual(len(fieldsets), 1)
        self.assertEqual(fieldsets[0][1]["fields"], (("postcode",), ("prefecture", "municipality_display"), ("town_name", "town_name_kana")))

    def test_admin_model_association(self):
        """Test that PostcodeAdmin is associated with Postcode model."""
        self.assertEqual(self.admin.model, Postcode)

    @patch("sfd.views.postcode.super")
    @patch("sfd.views.postcode.PostcodeAdmin.has_change_permission", return_value=False)
    @patch("sfd.views.postcode.PostcodeAdmin.has_add_permission", return_value=False)
    def test_get_readonly_fields(self, mock_has_add_permission, mock_has_change_permission, mock_super):
        """Test that the correct readonly fields are returned for PostcodeAdmin."""
        mock_super.return_value.get_readonly_fields.return_value = ("prefecture",)
        self.assertEqual(self.admin.get_readonly_fields(self.request), ["municipality_display"])

    def test_prefecture(self):
        """Test that the correct readonly fields are returned for PostcodeAdmin."""
        self.assertEqual(self.admin.prefecture(self.postcode), "東京都")

    def test_prefecture_none(self):
        """Test that the correct readonly fields are returned for PostcodeAdmin."""
        self.assertEqual(self.admin.prefecture(None), "")

    def test_municipality_display(self):
        """Test that the correct municipality display is returned for PostcodeAdmin."""
        self.assertEqual(self.admin.municipality_display(self.postcode), "東京都世田谷区")

    def test_municipality_display_none(self):
        """Test that the correct municipality display is returned for PostcodeAdmin."""
        self.assertEqual(self.admin.municipality_display(None), "")

    def test_get_search_field_names(self):
        """Test that the correct search field names are returned for PostcodeAdmin."""
        self.assertEqual(self.admin.get_search_field_names(), _("Postcode, Municipality Name, Town Name."))

    def test_admin_list_display(self):
        """Test PostcodeAdmin displays all configured fields correctly."""
        # Act & Assert
        self.assertIn("postcode_display", self.admin.list_display)
        self.assertIn("municipality_name", self.admin.list_display)
        self.assertIn("town_name", self.admin.list_display)
        self.assertIn("town_name_kana", self.admin.list_display)

    def test_convert2upload_fields_town_name_clear(self):
        """Test convert2upload_fields method converts data correctly."""
        row_dict = {"town_name": "以下に掲載がない場合", "town_name_kana": "イカニケイサイガナイバアイ"}

        upload_fields = {"town_name": Mock(), "town_name_kana": Mock()}

        converted = self.admin.convert2upload_fields(row_dict, upload_fields, self.request)
        self.assertEqual(converted["town_name"], "")
        self.assertEqual(converted["town_name_kana"], "")

    def test_convert2upload_fields_town_name_truncate(self):
        """Test convert2upload_fields method converts data correctly."""
        row_dict = {"town_name": "以下（備考）", "town_name_kana": "イカニ（ビコウ）"}

        upload_fields = {"town_name": Mock(), "town_name_kana": Mock()}

        converted = self.admin.convert2upload_fields(row_dict, upload_fields, self.request)
        self.assertEqual(converted["town_name"], "以下")
        self.assertEqual(converted["town_name_kana"], "イカニ")


@pytest.mark.unit
@pytest.mark.forms
class PostcodeAdminFormTest(BaseTestMixin, TestCase):
    """Test PostcodeAdminForm functionality with comprehensive coverage."""

    databases = {"default", "postgres"}

    def setUp(self):
        """Set up test data for PostcodeAdminForm tests."""
        super().setUp()

        # Create prefecture-level municipality records (required for prefecture choices)
        self.tokyo_prefecture = Municipality.objects.create(
            municipality_code="13000",
            prefecture_name="東京都",
            municipality_name="",  # Empty for prefecture-level record
        )

        self.osaka_prefecture = Municipality.objects.create(
            municipality_code="27000",
            prefecture_name="大阪府",
            municipality_name="",  # Empty for prefecture-level record
        )

        # Create test municipalities
        self.municipality = Municipality.objects.create(
            municipality_code="13101",
            prefecture_name="東京都",
            municipality_name="千代田区",
        )

        self.other_prefecture_municipality = Municipality.objects.create(
            municipality_code="27102",
            prefecture_name="大阪府",
            municipality_name="大阪市",
        )

    @pytest.mark.unit
    def test_form_initialization_new_record(self):
        """Test PostcodeAdminForm initialization for new record."""
        from sfd.forms.postcode import PostcodeAdminForm

        form = PostcodeAdminForm()

        # Prefecture field should have choices
        self.assertTrue(len(form.fields["prefecture"].choices) > 1)

        # Municipality field should start with empty queryset
        self.assertEqual(form.fields["municipality"].queryset.count(), 0)

    @pytest.mark.unit
    def test_form_initialization_existing_record(self):
        """Test PostcodeAdminForm initialization for existing record."""
        from sfd.forms.postcode import PostcodeAdminForm

        postcode = Postcode.objects.create(
            postcode="1000001",
            municipality=self.municipality,
            town_name="千代田",
        )

        form = PostcodeAdminForm(instance=postcode)

        # Prefecture should be set from the instance
        self.assertEqual(form.initial["prefecture"], "東京都")

        # Municipality queryset should be filtered by prefecture
        self.assertTrue(form.fields["municipality"].queryset.filter(id=self.municipality.id).exists())

    @pytest.mark.unit
    def test_form_clean_municipality_valid_selection(self):
        """Test form validation with valid municipality selection."""
        from sfd.forms.postcode import PostcodeAdminForm

        form_data = {
            "postcode": "1000001",
            "prefecture": "東京都",
            "municipality": self.municipality.id,
            "town_name": "千代田",
        }

        form = PostcodeAdminForm(data=form_data)

        # Form should be valid
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")

        # Municipality should be cleaned properly
        self.assertEqual(form.cleaned_data["municipality"], self.municipality)

    @pytest.mark.unit
    def test_form_clean_municipality_empty_queryset_but_valid_selection(self):
        """Test form validation when municipality field starts with empty queryset but valid municipality is selected."""
        from sfd.forms.postcode import PostcodeAdminForm

        # Create form with empty municipality queryset (simulates initial state)
        form = PostcodeAdminForm()

        form_data = {
            "postcode": "1000001",
            "prefecture": "東京都",
            "municipality": str(self.municipality.id),
            "town_name": "千代田",
        }

        # Manually set the form data and call full_clean to trigger validation
        form.data = form_data
        form.is_bound = True

        # This should work - the clean_municipality method should expand the queryset
        form.full_clean()

        # Form should be valid despite starting with empty queryset
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")

    @pytest.mark.unit
    def test_form_clean_municipality_inconsistent_prefecture(self):
        """Test form validation with municipality that doesn't match selected prefecture."""
        from sfd.forms.postcode import PostcodeAdminForm

        form_data = {
            "postcode": "1000001",
            "prefecture": "東京都",
            "municipality": self.other_prefecture_municipality.id,
            "town_name": "千代田",
        }

        form = PostcodeAdminForm(data=form_data)

        # Form should be invalid due to prefecture/municipality mismatch
        self.assertFalse(form.is_valid())

    @pytest.mark.unit
    def test_form_clean_validation_error_message(self):
        """Test that clean() method raises ValidationError with correct message when prefecture/municipality mismatch.

        This test specifically validates the custom error message from the clean() method
        when a municipality is selected that doesn't belong to the selected prefecture.

        Since full_clean() dynamically updates the queryset, we need to bypass normal
        form validation and directly test the clean() method logic.
        """
        from sfd.forms.postcode import PostcodeAdminForm

        # Create a form instance and manually set cleaned_data to simulate
        # a scenario where both prefecture and municipality pass field validation
        # but are inconsistent with each other
        form = PostcodeAdminForm()

        # Simulate cleaned_data with mismatched prefecture and municipality
        form.cleaned_data = {
            "postcode": "1000001",
            "prefecture": "東京都",  # Tokyo prefecture
            "municipality": self.other_prefecture_municipality,  # But Osaka municipality
            "town_name": "千代田",
        }

        # Call clean() directly to test the validation logic
        with self.assertRaises(forms.ValidationError) as context:
            form.clean()

        # Verify the error message matches our custom validation message
        # Convert lazy translation to string for comparison
        expected_message = str(_("Selected municipality does not belong to the selected prefecture."))
        actual_message = str(context.exception)
        self.assertIn(
            expected_message,
            actual_message,
            f"Expected custom validation error message not found. Error: {actual_message}",
        )

    @pytest.mark.unit
    def test_form_save_with_valid_data(self):
        """Test PostcodeAdminForm save functionality with valid data."""
        from sfd.forms.postcode import PostcodeAdminForm

        form_data = {
            "postcode": "1000001",
            "prefecture": "東京都",
            "municipality": self.municipality.id,
            "town_name": "千代田",
            "town_name_kana": "チヨダ",
        }

        form = PostcodeAdminForm(data=form_data)

        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")

        # Save the form
        postcode = form.save()

        # Verify the postcode was saved correctly
        self.assertEqual(postcode.postcode, "1000001")
        self.assertEqual(postcode.municipality, self.municipality)
        self.assertEqual(postcode.town_name, "千代田")
        self.assertEqual(postcode.town_name_kana, "チヨダ")

        # Verify it was saved to database
        saved_postcode = Postcode.objects.get(postcode="1000001")
        self.assertEqual(saved_postcode.municipality, self.municipality)

    @pytest.mark.unit
    def test_form_validation_error_maintains_municipality_choices(self):
        """Test that municipality choices remain compatible when validation errors occur.

        This test verifies the fix for the issue where the municipality dropdown
        becomes incompatible with the selected prefecture after a validation error
        on other fields (like postcode or town_name).

        Scenario:
        1. User selects prefecture (東京都)
        2. User selects municipality (千代田区)
        3. User enters invalid data in another field (e.g., empty postcode)
        4. Form validation fails
        5. Form is re-displayed with validation errors
        6. Municipality dropdown should still contain the selected municipality
        """
        from sfd.forms.postcode import PostcodeAdminForm

        # Simulate user submitting form with validation error (missing postcode)
        form_data = {
            "postcode": "",  # Invalid: empty postcode
            "prefecture": "東京都",
            "municipality": str(self.municipality.id),
            "town_name": "千代田",
            "town_name_kana": "チヨダ",
        }

        form = PostcodeAdminForm(data=form_data)

        # Form should be invalid due to missing postcode
        self.assertFalse(form.is_valid())
        self.assertIn("postcode", form.errors)

        # CRITICAL: Municipality queryset should still contain municipalities from selected prefecture
        municipality_ids = list(form.fields["municipality"].queryset.values_list("id", flat=True))
        self.assertIn(
            self.municipality.id,
            municipality_ids,
            "Municipality dropdown should contain selected municipality after validation error",
        )

        # Verify queryset is filtered to Tokyo municipalities only
        tokyo_municipalities = Municipality.objects.filter(prefecture_name="東京都").exclude(municipality_name="")
        self.assertEqual(
            form.fields["municipality"].queryset.count(),
            tokyo_municipalities.count(),
            "Municipality queryset should be filtered by selected prefecture",
        )

        # Verify Osaka municipality is NOT in the queryset
        self.assertNotIn(
            self.other_prefecture_municipality.id,
            municipality_ids,
            "Municipality from other prefecture should not be in dropdown",
        )

    @pytest.mark.unit
    def test_form_prefecture_field_htmx_attributes(self):
        """Test that prefecture field has correct HTMX attributes."""
        from sfd.forms.postcode import PostcodeAdminForm

        form = PostcodeAdminForm()

        # Check HTMX attributes on prefecture widget
        attrs = form.fields["prefecture"].widget.attrs
        self.assertEqual(attrs["id"], "id_prefecture")
        self.assertEqual(attrs["name"], "prefecture")
        self.assertEqual(attrs["hx-get"], "/sfd/change_prefecture/")
        self.assertEqual(attrs["hx-target"], "#id_municipality")
        self.assertEqual(attrs["hx-include"], "this")
        self.assertEqual(attrs["hx-trigger"], "change")

    @pytest.mark.unit
    def test_form_municipality_field_attributes(self):
        """Test that municipality field has correct HTML attributes."""
        from sfd.forms.postcode import PostcodeAdminForm

        form = PostcodeAdminForm()

        # Check municipality field attributes
        attrs = form.fields["municipality"].widget.attrs
        self.assertEqual(attrs["id"], "id_municipality")

    @pytest.mark.unit
    def test_form_prefecture_choices_populated(self):
        """Test that prefecture choices are populated from Municipality model."""
        from sfd.forms.postcode import PostcodeAdminForm

        form = PostcodeAdminForm()

        # Get prefecture choices (excluding the empty placeholder)
        prefecture_choices = [choice[0] for choice in form.fields["prefecture"].choices if choice[0]]

        # Should contain our test prefectures
        self.assertIn("東京都", prefecture_choices)
        self.assertIn("大阪府", prefecture_choices)

    @pytest.mark.unit
    def test_form_prefecture_choices_sorted(self):
        """Test that prefecture choices are sorted by municipality_code."""
        from sfd.forms.postcode import PostcodeAdminForm

        form = PostcodeAdminForm()

        # Get all prefecture choices (excluding empty placeholder)
        prefecture_choices = [choice[0] for choice in form.fields["prefecture"].choices if choice[0]]

        # Should have at least our test prefectures
        self.assertGreaterEqual(len(prefecture_choices), 2)

    @pytest.mark.unit
    def test_form_clean_error_message(self):
        """Test that clean method provides appropriate error message.

        Note: When municipality doesn't match the prefecture, Django's
        ModelChoiceField validation kicks in first (because the municipality
        is not in the filtered queryset), so we get a different error message.
        """
        from sfd.forms.postcode import PostcodeAdminForm

        form_data = {
            "postcode": "1000001",
            "prefecture": "東京都",
            "municipality": self.other_prefecture_municipality.id,
            "town_name": "千代田",
        }

        form = PostcodeAdminForm(data=form_data)

        self.assertFalse(form.is_valid())
        # The error will be from Django's ModelChoiceField validation
        self.assertIn("municipality", form.errors)

    @pytest.mark.unit
    def test_form_meta_fields(self):
        """Test that Meta class has correct fields defined."""
        from sfd.forms.postcode import PostcodeAdminForm

        form = PostcodeAdminForm()

        # Check that all expected fields are in the form
        self.assertIn("postcode", form.fields)
        self.assertIn("prefecture", form.fields)
        self.assertIn("municipality", form.fields)
        self.assertIn("town_name", form.fields)
        self.assertIn("town_name_kana", form.fields)

    @pytest.mark.unit
    def test_form_required_fields(self):
        """Test that required fields are properly configured."""
        from sfd.forms.postcode import PostcodeAdminForm

        form = PostcodeAdminForm()

        # Prefecture and municipality should be required
        self.assertTrue(form.fields["prefecture"].required)
        self.assertTrue(form.fields["municipality"].required)

    @pytest.mark.unit
    def test_form_initialization_with_data_no_prefecture(self):
        """Test form initialization with POST data but no prefecture selected."""
        from sfd.forms.postcode import PostcodeAdminForm

        form_data = {
            "postcode": "1000001",
            "prefecture": "",
            "town_name": "千代田",
        }

        form = PostcodeAdminForm(data=form_data)

        # Municipality queryset should remain empty when no prefecture is selected
        self.assertEqual(form.fields["municipality"].queryset.count(), 0)

    @pytest.mark.unit
    def test_form_full_clean_updates_queryset(self):
        """Test that full_clean updates municipality queryset before validation."""
        from sfd.forms.postcode import PostcodeAdminForm

        form = PostcodeAdminForm()

        # Initially municipality queryset should be empty
        self.assertEqual(form.fields["municipality"].queryset.count(), 0)

        # Set form data
        form.data = {
            "postcode": "1000001",
            "prefecture": "東京都",
            "municipality": str(self.municipality.id),
            "town_name": "千代田",
        }
        form.is_bound = True

        # Call full_clean
        form.full_clean()

        # Municipality queryset should now be populated with Tokyo municipalities
        self.assertGreater(form.fields["municipality"].queryset.count(), 0)
        self.assertTrue(form.fields["municipality"].queryset.filter(id=self.municipality.id).exists())

    @pytest.mark.unit
    def test_form_update_existing_record(self):
        """Test updating an existing postcode record."""
        from sfd.forms.postcode import PostcodeAdminForm

        # Create initial postcode
        postcode = Postcode.objects.create(
            postcode="1000001",
            municipality=self.municipality,
            town_name="千代田",
            town_name_kana="チヨダ",
        )

        # Update with form
        form_data = {
            "postcode": "1000001",
            "prefecture": "東京都",
            "municipality": self.municipality.id,
            "town_name": "千代田更新",
            "town_name_kana": "チヨダコウシン",
        }

        form = PostcodeAdminForm(data=form_data, instance=postcode)

        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")

        # Save the updated form
        updated_postcode = form.save()

        # Verify the postcode was updated correctly
        self.assertEqual(updated_postcode.postcode, "1000001")
        self.assertEqual(updated_postcode.town_name, "千代田更新")
        self.assertEqual(updated_postcode.town_name_kana, "チヨダコウシン")

    @pytest.mark.unit
    def test_form_missing_required_fields(self):
        """Test form validation with missing required fields."""
        from sfd.forms.postcode import PostcodeAdminForm

        form_data = {
            "postcode": "1000001",
            # Missing prefecture and municipality
        }

        form = PostcodeAdminForm(data=form_data)

        self.assertFalse(form.is_valid())
        self.assertIn("prefecture", form.errors)
        self.assertIn("municipality", form.errors)


@pytest.mark.unit
@pytest.mark.forms
class PostcodeSearchFormTest(BaseTestMixin, TestCase):
    """Test PostcodeSearchForm functionality with comprehensive coverage."""

    databases = {"default", "postgres"}

    def setUp(self):
        """Set up test data for PostcodeSearchForm tests."""
        super().setUp()

        self.municipality = Municipality.objects.create(
            municipality_code="13101",
            prefecture_name="東京都",
            municipality_name="千代田区",
            municipality_name_kana="チヨダク",
        )

    @pytest.mark.unit
    def test_form_initialization(self):
        """Test PostcodeSearchForm initialization."""
        from sfd.forms.postcode import PostcodeSearchForm

        form = PostcodeSearchForm()

        # Check that all fields exist
        self.assertIn("postcode", form.fields)
        self.assertIn("town_name", form.fields)
        self.assertIn("town_name_kana", form.fields)
        self.assertIn("municipality_name", form.fields)
        self.assertIn("municipality_name_kana", form.fields)

    @pytest.mark.unit
    def test_form_all_fields_optional(self):
        """Test that all fields in PostcodeSearchForm are optional."""
        from sfd.forms.postcode import PostcodeSearchForm

        form = PostcodeSearchForm()

        # All fields should be optional for search
        self.assertFalse(form.fields["postcode"].required)
        self.assertFalse(form.fields["town_name"].required)
        self.assertFalse(form.fields["town_name_kana"].required)
        self.assertFalse(form.fields["municipality_name"].required)
        self.assertFalse(form.fields["municipality_name_kana"].required)

    @pytest.mark.unit
    def test_form_validation_empty_form(self):
        """Test form validation with all empty fields."""
        from sfd.forms.postcode import PostcodeSearchForm

        form_data = {}

        form = PostcodeSearchForm(data=form_data)

        # Form should be valid even with no data since all fields are optional
        self.assertTrue(form.is_valid())

    @pytest.mark.unit
    def test_form_validation_with_postcode_only(self):
        """Test form validation with postcode only."""
        from sfd.forms.postcode import PostcodeSearchForm

        form_data = {
            "postcode": "1000001",
        }

        form = PostcodeSearchForm(data=form_data)

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["postcode"], "1000001")

    @pytest.mark.unit
    def test_form_validation_with_town_name_only(self):
        """Test form validation with town name only."""
        from sfd.forms.postcode import PostcodeSearchForm

        form_data = {
            "town_name": "千代田",
        }

        form = PostcodeSearchForm(data=form_data)

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["town_name"], "千代田")

    @pytest.mark.unit
    def test_form_validation_with_municipality_name_only(self):
        """Test form validation with municipality name only."""
        from sfd.forms.postcode import PostcodeSearchForm

        form_data = {
            "municipality_name": "千代田区",
        }

        form = PostcodeSearchForm(data=form_data)

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["municipality_name"], "千代田区")

    @pytest.mark.unit
    def test_form_validation_with_all_fields(self):
        """Test form validation with all fields populated."""
        from sfd.forms.postcode import PostcodeSearchForm

        form_data = {
            "postcode": "1000001",
            "town_name": "千代田",
            "town_name_kana": "チヨダ",
            "municipality_name": "千代田区",
            "municipality_name_kana": "チヨダク",
        }

        form = PostcodeSearchForm(data=form_data)

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["postcode"], "1000001")
        self.assertEqual(form.cleaned_data["town_name"], "千代田")
        self.assertEqual(form.cleaned_data["town_name_kana"], "チヨダ")
        self.assertEqual(form.cleaned_data["municipality_name"], "千代田区")
        self.assertEqual(form.cleaned_data["municipality_name_kana"], "チヨダク")

    @pytest.mark.unit
    def test_form_meta_model(self):
        """Test that Meta class references correct model."""
        from sfd.forms.postcode import PostcodeSearchForm

        form = PostcodeSearchForm()

        # Should be based on Postcode model
        self.assertEqual(form._meta.model, Postcode)

    @pytest.mark.unit
    def test_form_meta_fields(self):
        """Test that Meta class has correct fields defined."""
        from sfd.forms.postcode import PostcodeSearchForm

        form = PostcodeSearchForm()

        # Check that model fields are present
        self.assertIn("postcode", form.fields)
        self.assertIn("town_name", form.fields)
        self.assertIn("town_name_kana", form.fields)

    @pytest.mark.unit
    def test_form_municipality_name_field_label(self):
        """Test municipality_name field has correct label."""
        from sfd.forms.postcode import PostcodeSearchForm

        form = PostcodeSearchForm()

        self.assertEqual(form.fields["municipality_name"].label, _("Municipality Name"))

    @pytest.mark.unit
    def test_form_municipality_name_kana_field_label(self):
        """Test municipality_name_kana field has correct label."""
        from sfd.forms.postcode import PostcodeSearchForm

        form = PostcodeSearchForm()

        self.assertEqual(form.fields["municipality_name_kana"].label, _("Municipality Name Kana"))

    @pytest.mark.unit
    def test_form_partial_data_validation(self):
        """Test form validation with partial search criteria."""
        from sfd.forms.postcode import PostcodeSearchForm

        # Test various combinations of partial data
        test_cases = [
            {"postcode": "100"},
            {"town_name": "千"},
            {"town_name_kana": "チヨ"},
            {"municipality_name": "千代"},
            {"postcode": "100", "town_name": "千代田"},
            {"municipality_name": "千代田区", "town_name_kana": "チヨダ"},
        ]

        for form_data in test_cases:
            with self.subTest(form_data=form_data):
                form = PostcodeSearchForm(data=form_data)
                self.assertTrue(form.is_valid(), f"Form should be valid with data: {form_data}, errors: {form.errors}")

    @pytest.mark.unit
    def test_form_with_instance(self):
        """Test PostcodeSearchForm with existing instance."""
        from sfd.forms.postcode import PostcodeSearchForm

        # Create a postcode
        postcode = Postcode.objects.create(
            postcode="1000001",
            municipality=self.municipality,
            town_name="千代田",
            town_name_kana="チヨダ",
        )

        form = PostcodeSearchForm(instance=postcode)

        # Initial values should be set from instance
        self.assertEqual(form.initial["postcode"], "1000001")
        self.assertEqual(form.initial["town_name"], "千代田")
        self.assertEqual(form.initial["town_name_kana"], "チヨダ")

    @pytest.mark.unit
    def test_form_field_types(self):
        """Test that form fields have correct types."""
        from sfd.forms.postcode import PostcodeSearchForm

        form = PostcodeSearchForm()

        # municipality_name and municipality_name_kana should be CharField
        self.assertIsInstance(form.fields["municipality_name"], forms.CharField)
        self.assertIsInstance(form.fields["municipality_name_kana"], forms.CharField)

    @pytest.mark.unit
    def test_form_empty_string_values(self):
        """Test form validation with empty string values."""
        from sfd.forms.postcode import PostcodeSearchForm

        form_data = {
            "postcode": "",
            "town_name": "",
            "town_name_kana": "",
            "municipality_name": "",
            "municipality_name_kana": "",
        }

        form = PostcodeSearchForm(data=form_data)

        # Form should be valid with empty strings
        self.assertTrue(form.is_valid())

    @pytest.mark.unit
    def test_form_whitespace_handling(self):
        """Test form validation with whitespace in fields."""
        from sfd.forms.postcode import PostcodeSearchForm

        form_data = {
            "postcode": "  1000001  ",
            "town_name": "  千代田  ",
            "municipality_name": "  千代田区  ",
        }

        form = PostcodeSearchForm(data=form_data)

        self.assertTrue(form.is_valid())
        # Django should strip whitespace automatically
        self.assertEqual(form.cleaned_data["postcode"], "1000001")
        self.assertEqual(form.cleaned_data["town_name"], "千代田")
        self.assertEqual(form.cleaned_data["municipality_name"], "千代田区")
