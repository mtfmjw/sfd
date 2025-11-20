# type: ignore
from unittest.mock import Mock, patch

import pytest
from django.contrib.admin.sites import AdminSite
from django.test import TestCase
from django.utils.translation import gettext_lazy as _

from sfd.forms.person import PersonAdminForm
from sfd.models import GenderType, Person, Postcode
from sfd.models.municipality import Municipality
from sfd.tests.unittest import BaseTestMixin
from sfd.views.person import PersonAdmin


@pytest.mark.unit
@pytest.mark.models
class GenderTypeTest(TestCase):
    def test_gender_type_values(self):
        """Test that gender type constants have correct values."""
        self.assertEqual(GenderType.MALE, "Male")
        self.assertEqual(GenderType.FEMALE, "Female")
        self.assertEqual(GenderType.OTHER, "Other")

    def test_gender_type_labels(self):
        """Test that gender type labels are properly internationalized."""
        self.assertEqual(GenderType.MALE.label, _("Male"))
        self.assertEqual(GenderType.FEMALE.label, _("Female"))
        self.assertEqual(GenderType.OTHER.label, _("Other"))


@pytest.mark.unit
@pytest.mark.models
@pytest.mark.django_db
class PersonModelTest(TestCase):
    databases = {"default", "postgres"}

    def setUp(self):
        """Set up test environment with sample person data."""
        self.municipality = Municipality.objects.create(
            municipality_code="131016",
            municipality_name="世田谷区",
            municipality_name_kana="セタガヤク",
            prefecture_name="東京都",
            prefecture_name_kana="トウキョウト",
        )
        self.postcode = Postcode.objects.create(postcode="1234567", municipality=self.municipality, town_name="Central", town_name_kana="セントラル")
        self.person = Person.objects.create(
            family_name="Doe",
            family_name_kana="ドウ",
            name="John",
            name_kana="ジョン",
            gender=GenderType.MALE,
            postcode=self.postcode,
            municipality=self.municipality,
        )

    def test_str_representation(self):
        """Test string representation of the Person model."""
        self.assertEqual(str(self.person), "Doe John")

    def test_required_fields(self):
        person = Person(
            family_name="Doe",
            family_name_kana="ドウ",
            name="John",
            name_kana="ジョン",
            gender=GenderType.MALE,
            postcode=self.postcode,
            municipality=self.municipality,
        )
        person.full_clean()  # should not raise ValidationError

    def test_blank_and_null_fields_allowed(self):
        person = Person.objects.create(
            family_name="Smith",
            family_name_kana="スミス",
            name="Anna",
            name_kana="アンナ",
            gender=GenderType.FEMALE,
            postcode=self.postcode,
            municipality=self.municipality,
            family_name_romaji=None,
            name_romaji=None,
            birthday=None,
            email=None,
            phone_number=None,
            mobile_number=None,
            address_detail=None,
        )
        self.assertEqual(person.family_name_romaji, None)
        self.assertEqual(person.email, None)

    def test_meta_options(self):
        self.assertEqual(Person._meta.verbose_name, _("Person"))
        self.assertEqual(Person._meta.verbose_name_plural, _("People"))
        self.assertEqual(Person._meta.ordering, ["family_name", "name", "valid_from"])


@pytest.mark.unit
@pytest.mark.views
class PersonAdminTest(BaseTestMixin, TestCase):
    """Test PersonAdmin functionality with comprehensive coverage."""

    databases = {"default", "postgres"}

    def setUp(self):
        """Set up test data for PersonAdmin tests."""
        super().setUp()

        self.site = AdminSite()
        self.admin = PersonAdmin(Person, self.site)
        self.request = self.factory.get("/admin/")
        self.request.user = self.user

        self.municipality = Municipality.objects.create(municipality_code="01000", municipality_name="札幌市", prefecture_name="北海道")
        self.postcode = Postcode.objects.create(postcode="1234567", municipality=self.municipality, town_name="本町", town_name_kana="ホンチョウ")
        self.person = Person.objects.create(
            family_name="Doe",
            family_name_kana="ドウ",
            family_name_romaji="Doe",
            name="John",
            name_kana="ジョン",
            name_romaji="John",
            gender="unknown",
            postcode=self.postcode,
            municipality=self.municipality,
        )

    def test_full_name(self):
        """Test full name generation for PersonAdmin."""
        self.assertEqual(self.admin.full_name(self.person), "Doe John")

    def test_full_name_kana(self):
        """Test full name kana generation for PersonAdmin."""
        self.assertEqual(self.admin.full_name_kana(self.person), "ドウ ジョン")

    def test_full_name_romaji(self):
        """Test full name romaji generation for PersonAdmin."""
        self.assertEqual(self.admin.full_name_romaji(self.person), "Doe John")

    def test_postcode_link(self):
        """Test postcode link generation for PersonAdmin."""
        self.assertIn("123-4567", self.admin.postcode_link(self.person))

    def test_postcode_link_with_none(self):
        """Test postcode link generation for PersonAdmin."""
        self.person.postcode = None
        self.assertIn("", self.admin.postcode_link(self.person))

    def test_municipality_link(self):
        """Test municipality link generation for PersonAdmin."""
        self.assertIn("北海道札幌市", self.admin.municipality_link(self.person))

    def test_municipality_link_with_none(self):
        """Test municipality link generation for PersonAdmin."""
        self.person.municipality = None
        self.assertIn("", self.admin.municipality_link(self.person))

    def test_municipality_link_with_blank_name(self):
        """Test municipality link generation for PersonAdmin."""
        self.municipality.prefecture_name = ""
        self.municipality.municipality_name = ""
        self.assertIn("", self.admin.municipality_link(self.person))

    @patch("sfd.views.person.super")
    def test_convert2upload_fields(self, mock_super):
        """Test convert2upload_fields method for PersonAdmin."""
        row = {"postcode": "123-4567", "address": "北海道札幌市本町1-2-3"}
        upload_fields = Mock()
        mock_super.return_value.convert2upload_fields.return_value = {"gender": "unknown"}

        converted = self.admin.convert2upload_fields(self.request, row, upload_fields)

        self.assertEqual(converted["gender"], GenderType.OTHER)
        self.assertEqual(converted["postcode"].postcode, "1234567")
        self.assertEqual(converted["municipality"].municipality_name, "札幌市")
        self.assertEqual(converted["address_detail"], "本町1-2-3")

    @patch("sfd.views.person.super")
    def test_convert2upload_fields_tokyo(self, mock_super):
        """Test convert2upload_fields method for PersonAdmin."""
        row = {"postcode": "333-4444", "address": "東京都新宿区西新宿2-8-1"}
        upload_fields = Mock()
        mock_super.return_value.convert2upload_fields.return_value = {}
        municipality = Municipality.objects.create(municipality_code="13001", municipality_name="新宿区", prefecture_name="東京都")
        Postcode.objects.create(postcode="2345678", municipality=municipality, town_name="西新宿", town_name_kana="セントラル")

        converted = self.admin.convert2upload_fields(self.request, row, upload_fields)

        self.assertEqual(converted["gender"], GenderType.OTHER)
        self.assertEqual(converted["postcode"].postcode, "2345678")
        self.assertEqual(converted["municipality"].municipality_name, "新宿区")
        self.assertEqual(converted["address_detail"], "西新宿2-8-1")

    @patch("sfd.views.person.super")
    def test_convert2upload_fields_hokkaido(self, mock_super):
        """Test convert2upload_fields method for PersonAdmin."""
        row = {"postcode": "333-4444", "address": "北海道札幌市西区2-8-1"}
        upload_fields = Mock()
        mock_super.return_value.convert2upload_fields.return_value = {}

        converted = self.admin.convert2upload_fields(self.request, row, upload_fields)

        self.assertEqual(converted["gender"], GenderType.OTHER)
        self.assertEqual(converted["postcode"].postcode, "1234567")
        self.assertEqual(converted["municipality"].municipality_name, "札幌市")
        self.assertEqual(converted["address_detail"], "西区2-8-1")

    @patch("sfd.views.person.super")
    def test_convert2upload_fields_oosaka(self, mock_super):
        """Test convert2upload_fields method for PersonAdmin."""
        row = {"postcode": "333-4444", "address": "大阪府大阪市北区2-8-1"}
        upload_fields = Mock()
        mock_super.return_value.convert2upload_fields.return_value = {}
        municipality = Municipality.objects.create(municipality_code="27001", municipality_name="大阪市", prefecture_name="大阪府")
        Postcode.objects.create(postcode="2345678", municipality=municipality, town_name="北区", town_name_kana="キタク")

        converted = self.admin.convert2upload_fields(self.request, row, upload_fields)

        self.assertEqual(converted["gender"], GenderType.OTHER)
        self.assertEqual(converted["postcode"].postcode, "2345678")
        self.assertEqual(converted["municipality"].municipality_name, "大阪市")
        self.assertEqual(converted["address_detail"], "北区2-8-1")

    @patch("sfd.views.person.super")
    def test_convert2upload_fields_kyoto(self, mock_super):
        """Test convert2upload_fields method for PersonAdmin."""
        row = {"postcode": "333-4444", "address": "京都府京都市中京区2-8-1"}
        upload_fields = Mock()
        mock_super.return_value.convert2upload_fields.return_value = {}
        municipality = Municipality.objects.create(municipality_code="26001", municipality_name="京都市", prefecture_name="京都府")
        Postcode.objects.create(postcode="2345678", municipality=municipality, town_name="中京区", town_name_kana="チュウキョウク")

        converted = self.admin.convert2upload_fields(self.request, row, upload_fields)

        self.assertEqual(converted["gender"], GenderType.OTHER)
        self.assertEqual(converted["postcode"].postcode, "2345678")
        self.assertEqual(converted["municipality"].municipality_name, "京都市")
        self.assertEqual(converted["address_detail"], "中京区2-8-1")

    @patch("sfd.views.person.super")
    def test_convert2upload_fields_chiba(self, mock_super):
        """Test convert2upload_fields method for PersonAdmin."""
        row = {"postcode": "333-4444", "address": "千葉県千葉市中央区2-8-1"}
        upload_fields = Mock()
        mock_super.return_value.convert2upload_fields.return_value = {}
        municipality = Municipality.objects.create(municipality_code="12001", municipality_name="千葉市", prefecture_name="千葉県")
        Postcode.objects.create(postcode="2345678", municipality=municipality, town_name="中央区", town_name_kana="チュウオウク")

        converted = self.admin.convert2upload_fields(self.request, row, upload_fields)

        self.assertEqual(converted["gender"], GenderType.OTHER)
        self.assertEqual(converted["postcode"].postcode, "2345678")
        self.assertEqual(converted["municipality"].municipality_name, "千葉市")
        self.assertEqual(converted["address_detail"], "中央区2-8-1")

    @patch("sfd.views.person.super")
    def test_convert2upload_fields_no_municipality(self, mock_super):
        """Test convert2upload_fields method for PersonAdmin."""
        row = {"postcode": "333-4444", "address": "千葉県実在無市中央区2-8-1"}
        upload_fields = Mock()
        mock_super.return_value.convert2upload_fields.return_value = {}
        municipality = Municipality.objects.create(municipality_code="12001", municipality_name="千葉市", prefecture_name="千葉県")
        Postcode.objects.create(postcode="2345678", municipality=municipality, town_name="中央区", town_name_kana="チュウオウク")

        converted = self.admin.convert2upload_fields(self.request, row, upload_fields)

        self.assertEqual(converted["gender"], GenderType.OTHER)
        self.assertEqual(converted["postcode"].postcode, "2345678")
        self.assertEqual(converted["municipality"].municipality_name, "千葉市")
        self.assertEqual(converted["address_detail"], "千葉県実在無市中央区2-8-1")

    @patch("sfd.views.person.super")
    def test_convert2upload_fields_no_postcode_no_municipality_other_prefecture(self, mock_super):
        """Test convert2upload_fields with address in other prefecture when no postcode/municipality exists."""
        row = {"postcode": "999-9999", "address": "愛知県名古屋市中区2-8-1"}
        upload_fields = Mock()
        mock_super.return_value.convert2upload_fields.return_value = {}

        # Create a postcode for a different prefecture
        other_municipality = Municipality.objects.create(municipality_code="23001", municipality_name="名古屋市", prefecture_name="愛知県")
        other_postcode = Postcode.objects.create(postcode="9999999", municipality=other_municipality, town_name="中区", town_name_kana="ナカク")

        converted = self.admin.convert2upload_fields(self.request, row, upload_fields)

        # Should fall back to first postcode in the prefecture
        self.assertEqual(converted["postcode"], other_postcode)
        self.assertEqual(converted["municipality"], other_municipality)
        # Address detail should have prefecture+municipality removed
        self.assertEqual(converted["address_detail"], "中区2-8-1")

    @patch("sfd.views.person.super")
    def test_convert2upload_fields_no_postcode_but_municipality_found(self, mock_super):
        """Test convert2upload_fields when postcode not found but municipality matches."""
        row = {"postcode": "999-9999", "address": "東京都新宿区西新宿2-8-1"}
        upload_fields = Mock()
        mock_super.return_value.convert2upload_fields.return_value = {}

        # Create municipality and postcode for it
        municipality = Municipality.objects.create(municipality_code="13001", municipality_name="新宿区", prefecture_name="東京都")
        postcode = Postcode.objects.create(postcode="1112222", municipality=municipality, town_name="西新宿", town_name_kana="ニシシンジュク")

        converted = self.admin.convert2upload_fields(self.request, row, upload_fields)

        # Should find the municipality by name and use its postcode
        self.assertEqual(converted["postcode"], postcode)
        self.assertEqual(converted["municipality"], municipality)
        self.assertEqual(converted["address_detail"], "西新宿2-8-1")

    @patch("sfd.views.person.super")
    def test_convert2upload_fields_prefecture_but_no_municipality_no_postcode(self, mock_super):
        """Test convert2upload_fields when prefecture exists but no municipality or postcode."""
        row = {"postcode": "999-9999", "address": "福岡県存在しない市中央区2-8-1"}
        upload_fields = Mock()
        mock_super.return_value.convert2upload_fields.return_value = {}

        # Create a municipality and postcode for Fukuoka prefecture
        municipality = Municipality.objects.create(municipality_code="40001", municipality_name="福岡市", prefecture_name="福岡県")
        postcode = Postcode.objects.create(postcode="8000000", municipality=municipality, town_name="中央区", town_name_kana="チュウオウク")

        converted = self.admin.convert2upload_fields(self.request, row, upload_fields)

        # Should fall back to first postcode in the prefecture
        self.assertEqual(converted["postcode"], postcode)
        self.assertEqual(converted["municipality"], municipality)
        # Full address should be preserved since municipality name didn't match
        self.assertEqual(converted["address_detail"], "福岡県存在しない市中央区2-8-1")

    @patch("sfd.views.person.super")
    def test_convert2upload_fields_no_postcode_completely_unknown_address(self, mock_super):
        """Test convert2upload_fields with completely unknown address format."""
        row = {"postcode": "999-9999", "address": "全く存在しない県不明市不明区1-2-3"}
        upload_fields = Mock()
        mock_super.return_value.convert2upload_fields.return_value = {}

        converted = self.admin.convert2upload_fields(self.request, row, upload_fields)

        # Should set postcode and municipality to None and keep full address
        self.assertIsNone(converted["postcode"])
        self.assertIsNone(converted["municipality"])
        self.assertEqual(converted["address_detail"], "全く存在しない県不明市不明区1-2-3")

    @patch("sfd.views.person.super")
    def test_convert2upload_fields_empty_address(self, mock_super):
        """Test convert2upload_fields with empty address."""
        row = {"postcode": "123-4567", "address": ""}
        upload_fields = Mock()
        mock_super.return_value.convert2upload_fields.return_value = {}

        converted = self.admin.convert2upload_fields(self.request, row, upload_fields)

        # Should find postcode but address_detail should be empty
        self.assertEqual(converted["postcode"].postcode, "1234567")
        self.assertEqual(converted["municipality"].municipality_name, "札幌市")
        self.assertEqual(converted["address_detail"], "")

    @patch("sfd.views.person.super")
    def test_convert2upload_fields_gender_already_valid(self, mock_super):
        """Test convert2upload_fields when gender is already a valid value."""
        row = {"postcode": "123-4567", "address": "北海道札幌市本町1-2-3"}
        upload_fields = Mock()
        mock_super.return_value.convert2upload_fields.return_value = {"gender": GenderType.MALE}

        converted = self.admin.convert2upload_fields(self.request, row, upload_fields)

        # Should preserve valid gender value
        self.assertEqual(converted["gender"], GenderType.MALE)

    @patch("sfd.views.person.super")
    def test_convert2upload_fields_prefecture_with_ken(self, mock_super):
        """Test convert2upload_fields with prefecture ending in 県."""
        row = {"postcode": "999-9999", "address": "神奈川県横浜市中区2-8-1"}
        upload_fields = Mock()
        mock_super.return_value.convert2upload_fields.return_value = {}

        # Create municipality and postcode
        municipality = Municipality.objects.create(municipality_code="14001", municipality_name="横浜市", prefecture_name="神奈川県")
        postcode = Postcode.objects.create(postcode="2310000", municipality=municipality, town_name="中区", town_name_kana="ナカク")

        converted = self.admin.convert2upload_fields(self.request, row, upload_fields)

        # Should correctly parse prefecture ending with 県
        self.assertEqual(converted["postcode"], postcode)
        self.assertEqual(converted["municipality"], municipality)
        self.assertEqual(converted["address_detail"], "中区2-8-1")

    @patch("sfd.views.person.super")
    def test_convert2upload_fields_municipality_not_in_remained_address(self, mock_super):
        """Test convert2upload_fields when municipality name not in remained address."""
        row = {"postcode": "999-9999", "address": "東京都異なる区西新宿2-8-1"}
        upload_fields = Mock()
        mock_super.return_value.convert2upload_fields.return_value = {}

        # Create a municipality that won't match
        municipality = Municipality.objects.create(municipality_code="13999", municipality_name="実在しない区", prefecture_name="東京都")
        postcode = Postcode.objects.create(postcode="9998888", municipality=municipality, town_name="不明", town_name_kana="フメイ")

        converted = self.admin.convert2upload_fields(self.request, row, upload_fields)

        # Should fall back to first postcode in prefecture
        self.assertEqual(converted["postcode"], postcode)
        self.assertEqual(converted["municipality"], municipality)
        # Should preserve original address since municipality name didn't match
        self.assertEqual(converted["address_detail"], "東京都異なる区西新宿2-8-1")

    @patch("sfd.views.person.super")
    def test_convert2upload_fields_municipality_empty_name(self, mock_super):
        """Test convert2upload_fields when municipality has empty name."""
        row = {"postcode": "999-9999", "address": "東京都新宿区西新宿2-8-1"}
        upload_fields = Mock()
        mock_super.return_value.convert2upload_fields.return_value = {}

        # Create municipality with empty name
        municipality = Municipality.objects.create(municipality_code="13999", municipality_name="", prefecture_name="東京都")
        Postcode.objects.create(postcode="9998888", municipality=municipality, town_name="不明", town_name_kana="フメイ")

        converted = self.admin.convert2upload_fields(self.request, row, upload_fields)

        # Should handle empty municipality name gracefully
        self.assertIsNone(converted["postcode"])
        self.assertIsNone(converted["municipality"])
        self.assertEqual(converted["address_detail"], "東京都新宿区西新宿2-8-1")

    @patch("sfd.views.person.super")
    def test_convert2upload_fields_no_prefecture_in_address(self, mock_super):
        """Test convert2upload_fields when address has no recognizable prefecture."""
        row = {"postcode": "999-9999", "address": "不明地域中央区2-8-1"}
        upload_fields = Mock()
        mock_super.return_value.convert2upload_fields.return_value = {}

        converted = self.admin.convert2upload_fields(self.request, row, upload_fields)

        # Should set everything to None/original address
        self.assertIsNone(converted["postcode"])
        self.assertIsNone(converted["municipality"])
        self.assertEqual(converted["address_detail"], "不明地域中央区2-8-1")

    @patch("sfd.views.person.super")
    def test_fieldsets(self, mock_super):
        """Test fieldsets property for PersonAdmin."""
        mock_super.return_value.get_fieldsets.return_value = (
            ("基本情報", {"fields": ("name", "gender", "age")}),
            ("住所情報", {"fields": ("postcode", "address")}),
        )

        fieldsets = self.admin.get_fieldsets(request=self.request)

        expected = (
            ("family_name", "name"),
            ("family_name_kana", "name_kana"),
            ("family_name_romaji", "name_romaji"),
            ("birthday", "gender"),
            ("email", "phone_number", "mobile_number"),
            ("postcode_search", "municipality_display", "address_detail"),
        )
        self.assertEqual(fieldsets[1][1]["fields"], expected)


@pytest.mark.unit
@pytest.mark.forms
@pytest.mark.django_db
class PersonAdminFormTest(TestCase):
    """Test PersonAdminForm functionality with comprehensive coverage."""

    databases = {"default", "postgres"}

    def setUp(self):
        """Set up test data for PersonAdminForm tests."""
        self.municipality = Municipality.objects.create(
            municipality_code="131016",
            municipality_name="世田谷区",
            municipality_name_kana="セタガヤク",
            prefecture_name="東京都",
            prefecture_name_kana="トウキョウト",
        )
        self.postcode = Postcode.objects.create(
            postcode="1234567", municipality=self.municipality, town_name="三軒茶屋", town_name_kana="サンゲンヂャヤ"
        )

    def test_form_fields_exist(self):
        """Test that PersonAdminForm contains all required fields."""
        form = PersonAdminForm()

        # Check Meta fields
        expected_fields = [
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

        for field_name in expected_fields:
            self.assertIn(field_name, form.fields)

        # Check custom search fields
        self.assertIn("postcode_search", form.fields)
        self.assertIn("municipality_display", form.fields)

    def test_postcode_search_field_properties(self):
        """Test postcode_search field has correct properties."""
        form = PersonAdminForm()

        postcode_field = form.fields["postcode_search"]
        self.assertEqual(postcode_field.label, _("Postcode"))
        self.assertFalse(postcode_field.required)
        self.assertEqual(postcode_field.help_text, _("Search and select postcode, town name, and municipality."))

    def test_municipality_display_field_properties(self):
        """Test municipality_display field has correct properties."""
        form = PersonAdminForm()

        municipality_field = form.fields["municipality_display"]
        self.assertEqual(municipality_field.label, _("Municipality"))
        self.assertFalse(municipality_field.required)
        self.assertTrue(municipality_field.widget.attrs.get("readonly"))
        self.assertEqual(municipality_field.widget.attrs.get("id"), "id_municipality_display")

    def test_birthday_widget_type(self):
        """Test birthday field has date input widget."""
        form = PersonAdminForm()
        birthday_field = form.fields["birthday"]
        # Check that the widget is DateInput
        self.assertEqual(birthday_field.widget.__class__.__name__, "DateInput")

    def test_form_initialization_without_instance(self):
        """Test form initialization without existing instance."""
        form = PersonAdminForm()

        # postcode_search and municipality_display should not have initial values
        self.assertIsNone(form.initial.get("postcode_search"))
        self.assertIsNone(form.initial.get("municipality_display"))

    def test_form_initialization_with_instance(self):
        """Test form initialization with existing person instance."""
        person = Person.objects.create(
            family_name="山田",
            family_name_kana="ヤマダ",
            name="太郎",
            name_kana="タロウ",
            postcode=self.postcode,
            municipality=self.municipality,
        )

        form = PersonAdminForm(instance=person)

        # Check that initial values are set correctly
        self.assertEqual(form.initial["postcode_search"], "123-4567")
        self.assertEqual(form.initial["municipality_display"], str(self.municipality))

    def test_form_initialization_with_instance_no_postcode(self):
        """Test form initialization with existing person instance without postcode."""
        person = Person.objects.create(
            family_name="山田",
            family_name_kana="ヤマダ",
            name="太郎",
            name_kana="タロウ",
        )

        form = PersonAdminForm(instance=person)

        # Check that initial values are not set
        self.assertIsNone(form.initial.get("postcode_search"))
        self.assertIsNone(form.initial.get("municipality_display"))

    def test_clean_valid_postcode_with_hyphen(self):
        """Test clean method with valid postcode (with hyphen).

        Note: The form includes postcode and municipality in Meta.fields,
        so we need to provide them in form_data. The clean() method will
        update these values based on postcode_search.
        """
        form_data = {
            "family_name": "田中",
            "family_name_kana": "タナカ",
            "name": "花子",
            "name_kana": "ハナコ",
            "postcode": self.postcode.pk,
            "municipality": self.municipality.pk,
            "postcode_search": "123-4567",
            "valid_from": "2025-01-01",
            "valid_to": "9999-12-31",
        }

        form = PersonAdminForm(data=form_data)
        is_valid = form.is_valid()
        if not is_valid:
            print(f"Form errors: {form.errors}")
        self.assertTrue(is_valid)

        # Check that postcode and municipality are set on the instance after clean()
        self.assertEqual(form.instance.postcode, self.postcode)
        self.assertEqual(form.instance.municipality, self.municipality)

    def test_clean_valid_postcode_without_hyphen(self):
        """Test clean method with valid postcode (without hyphen).

        Note: The form includes postcode and municipality in Meta.fields,
        so we need to provide them in form_data. The clean() method will
        update these values based on postcode_search.
        """
        form_data = {
            "family_name": "田中",
            "family_name_kana": "タナカ",
            "name": "花子",
            "name_kana": "ハナコ",
            "postcode": self.postcode.pk,
            "municipality": self.municipality.pk,
            "postcode_search": "1234567",
            "valid_from": "2025-01-01",
            "valid_to": "9999-12-31",
        }

        form = PersonAdminForm(data=form_data)
        is_valid = form.is_valid()
        if not is_valid:
            print(f"Form errors: {form.errors}")
        self.assertTrue(is_valid)

        # Check that postcode and municipality are set on the instance after clean()
        self.assertEqual(form.instance.postcode, self.postcode)
        self.assertEqual(form.instance.municipality, self.municipality)

    def test_clean_empty_postcode(self):
        """Test clean method with empty postcode.

        Note: When postcode_search is empty, the FK fields can be omitted
        and the form should still be valid.
        """
        form_data = {
            "family_name": "田中",
            "family_name_kana": "タナカ",
            "name": "花子",
            "name_kana": "ハナコ",
            "postcode_search": "",
            "valid_from": "2025-01-01",
            "valid_to": "9999-12-31",
        }

        form = PersonAdminForm(data=form_data)
        self.assertTrue(form.is_valid())

        # Check that postcode and municipality remain None (not set by clean())
        self.assertIsNone(form.instance.postcode)
        self.assertIsNone(form.instance.municipality)

    def test_clean_nonexistent_postcode(self):
        """Test clean method with nonexistent postcode.

        Note: The form should raise validation error when postcode_search
        contains a postcode that doesn't exist in the database.
        """
        form_data = {
            "family_name": "田中",
            "family_name_kana": "タナカ",
            "name": "花子",
            "name_kana": "ハナコ",
            "postcode": "",  # Empty FK field
            "municipality": "",  # Empty FK field
            "postcode_search": "999-9999",
            "valid_from": "2025-01-01",
            "valid_to": "9999-12-31",
        }

        form = PersonAdminForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn(str(_("Selected postcode does not exist.")), str(form.errors))

    def test_clean_updates_municipality_automatically(self):
        """Test that clean method automatically sets municipality based on postcode."""
        # Create another municipality and postcode
        another_municipality = Municipality.objects.create(
            municipality_code="131017",
            municipality_name="渋谷区",
            municipality_name_kana="シブヤク",
            prefecture_name="東京都",
            prefecture_name_kana="トウキョウト",
        )
        another_postcode = Postcode.objects.create(postcode="7654321", municipality=another_municipality, town_name="渋谷", town_name_kana="シブヤ")

        form_data = {
            "family_name": "田中",
            "family_name_kana": "タナカ",
            "name": "花子",
            "name_kana": "ハナコ",
            "postcode": another_postcode.pk,
            "municipality": another_municipality.pk,
            "postcode_search": "765-4321",
            "valid_from": "2025-01-01",
            "valid_to": "9999-12-31",
        }

        form = PersonAdminForm(data=form_data)
        is_valid = form.is_valid()
        if not is_valid:
            print(f"Form errors: {form.errors}")
        self.assertTrue(is_valid)

        # Check that municipality is automatically set based on postcode after clean()
        self.assertEqual(form.instance.postcode, another_postcode)
        self.assertEqual(form.instance.municipality, another_municipality)

    def test_form_media_js_files(self):
        """Test that form includes required JavaScript files."""
        form = PersonAdminForm()
        self.assertIn("sfd/js/search_postcode.js", form.media._js)

    def test_postcode_search_widget_type(self):
        """Test that postcode_search field uses SearchFieldWidget."""
        form = PersonAdminForm()
        postcode_field = form.fields["postcode_search"]

        # Check widget class name
        self.assertEqual(postcode_field.widget.__class__.__name__, "SearchFieldWidget")

    def test_postcode_search_widget_attributes(self):
        """Test that postcode_search widget has correct attributes."""
        form = PersonAdminForm()
        postcode_field = form.fields["postcode_search"]

        # Check widget attributes
        self.assertEqual(postcode_field.widget.attrs.get("id"), "id_postcode_search")
        self.assertEqual(postcode_field.widget.attrs.get("placeholder"), _("Search postcode..."))

    def test_form_validation_with_all_fields(self):
        """Test form validation with all fields populated."""
        form_data = {
            "family_name": "佐藤",
            "family_name_kana": "サトウ",
            "family_name_romaji": "Sato",
            "name": "次郎",
            "name_kana": "ジロウ",
            "name_romaji": "Jiro",
            "birthday": "1990-05-15",
            "gender": GenderType.MALE,
            "email": "sato.jiro@example.com",
            "phone_number": "03-1234-5678",
            "mobile_number": "090-1234-5678",
            "postcode": self.postcode.pk,
            "municipality": self.municipality.pk,
            "postcode_search": "123-4567",
            "address_detail": "1-2-3 三軒茶屋ビル",
            "valid_from": "2025-01-01",
            "valid_to": "9999-12-31",
        }

        form = PersonAdminForm(data=form_data)
        is_valid = form.is_valid()
        if not is_valid:
            print(f"Form errors: {form.errors}")
        self.assertTrue(is_valid)

        # Check that all data is correctly set
        self.assertEqual(form.cleaned_data["family_name"], "佐藤")
        self.assertEqual(form.cleaned_data["email"], "sato.jiro@example.com")
        self.assertEqual(form.instance.postcode, self.postcode)
        self.assertEqual(form.instance.municipality, self.municipality)

    def test_form_validation_with_minimal_fields(self):
        """Test form validation with only required fields."""
        form_data = {
            "family_name": "鈴木",
            "family_name_kana": "スズキ",
            "name": "三郎",
            "name_kana": "サブロウ",
            "valid_from": "2025-01-01",
            "valid_to": "9999-12-31",
        }

        form = PersonAdminForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_municipality_display_readonly_attribute(self):
        """Test that municipality_display field is readonly."""
        form = PersonAdminForm()
        municipality_field = form.fields["municipality_display"]

        self.assertTrue(municipality_field.widget.attrs.get("readonly"))

    def test_postcode_formatting_in_initial(self):
        """Test that postcode is formatted with hyphen in initial data."""
        person = Person.objects.create(
            family_name="高橋",
            family_name_kana="タカハシ",
            name="四郎",
            name_kana="シロウ",
            postcode=self.postcode,
            municipality=self.municipality,
        )

        form = PersonAdminForm(instance=person)

        # Check that postcode is formatted with hyphen (123-4567)
        self.assertEqual(form.initial["postcode_search"], "123-4567")
        self.assertNotEqual(form.initial["postcode_search"], "1234567")


@pytest.mark.unit
@pytest.mark.models
@pytest.mark.django_db
class PersonManagerTest(BaseTestMixin, TestCase):
    """Test cases for PersonManager custom manager methods."""

    databases = {"default", "postgres"}

    def setUp(self):
        """Set up test environment with sample person data."""
        self.municipality = Municipality.objects.create(
            municipality_code="131016",
            municipality_name="世田谷区",
            municipality_name_kana="セタガヤク",
            prefecture_name="東京都",
            prefecture_name_kana="トウキョウト",
        )
        self.postcode = Postcode.objects.create(postcode="1234567", municipality=self.municipality, town_name="Central", town_name_kana="セントラル")

        # Create test persons
        self.person1 = Person.objects.create(
            family_name="山田",
            family_name_kana="ヤマダ",
            name="太郎",
            name_kana="タロウ",
            email="yamada@example.com",
            phone_number="03-1234-5678",
            mobile_number="090-1234-5678",
        )
        self.person2 = Person.objects.create(
            family_name="佐藤",
            family_name_kana="サトウ",
            name="花子",
            name_kana="ハナコ",
            email="sato@example.com",
            phone_number="03-9876-5432",
            mobile_number="080-9876-5432",
        )

    def test_search_by_name_with_family_name(self):
        """Test search_by_name method with family name."""
        results = Person.objects.search_by_name("山田")
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first(), self.person1)

    def test_search_by_name_with_name(self):
        """Test search_by_name method with given name."""
        results = Person.objects.search_by_name("花子")
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first(), self.person2)

    def test_search_by_name_with_empty_string(self):
        """Test search_by_name method with empty string returns none."""
        results = Person.objects.search_by_name("")
        self.assertEqual(results.count(), 0)

    def test_search_by_name_with_none(self):
        """Test search_by_name method with None returns none."""
        results = Person.objects.search_by_name(None)
        self.assertEqual(results.count(), 0)

    def test_search_by_email_with_valid_email(self):
        """Test search_by_email method with valid email."""
        results = Person.objects.search_by_email("yamada@example.com")
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first(), self.person1)

    def test_search_by_email_with_empty_string(self):
        """Test search_by_email method with empty string returns none."""
        results = Person.objects.search_by_email("")
        self.assertEqual(results.count(), 0)

    def test_search_by_email_with_none(self):
        """Test search_by_email method with None returns none."""
        results = Person.objects.search_by_email(None)
        self.assertEqual(results.count(), 0)

    def test_search_by_phone_with_phone_number(self):
        """Test search_by_phone method with phone number."""
        results = Person.objects.search_by_phone("03-1234-5678")
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first(), self.person1)

    def test_search_by_phone_with_mobile_number(self):
        """Test search_by_phone method with mobile number."""
        results = Person.objects.search_by_phone("090-1234-5678")
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first(), self.person1)

    def test_search_by_phone_with_empty_string(self):
        """Test search_by_phone method with empty string returns none."""
        results = Person.objects.search_by_phone("")
        self.assertEqual(results.count(), 0)

    def test_search_by_phone_with_none(self):
        """Test search_by_phone method with None returns none."""
        results = Person.objects.search_by_phone(None)
        self.assertEqual(results.count(), 0)

    def test_search_exact_single_field(self):
        """Test search_exact method with single field."""
        results = Person.objects.search_exact(family_name="山田")
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first(), self.person1)

    def test_search_exact_multiple_fields(self):
        """Test search_exact method with multiple fields."""
        results = Person.objects.search_exact(family_name="佐藤", name="花子")
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first(), self.person2)

    def test_search_exact_with_none_value(self):
        """Test search_exact method ignores None values."""
        results = Person.objects.search_exact(family_name="山田", email=None)
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first(), self.person1)

    def test_search_exact_no_match(self):
        """Test search_exact method with no matching results."""
        results = Person.objects.search_exact(family_name="存在しない名前")
        self.assertEqual(results.count(), 0)


@pytest.mark.unit
@pytest.mark.views
@pytest.mark.django_db
class PersonAdminSearchTest(BaseTestMixin, TestCase):
    """Test cases for PersonAdmin get_search_results method."""

    databases = {"default", "postgres"}

    def setUp(self):
        """Set up test environment."""
        super().setUp()

        self.site = AdminSite()
        self.admin = PersonAdmin(Person, self.site)
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

        # Create test persons
        self.person1 = Person.objects.create(
            family_name="田中",
            family_name_kana="タナカ",
            family_name_romaji="Tanaka",
            name="一郎",
            name_kana="イチロウ",
            name_romaji="Ichiro",
            email="tanaka@example.com",
        )
        self.person2 = Person.objects.create(
            family_name="鈴木",
            family_name_kana="スズキ",
            family_name_romaji="Suzuki",
            name="二郎",
            name_kana="ジロウ",
            name_romaji="Jiro",
            email="suzuki@example.com",
        )

    def test_get_search_results_empty_search_term(self):
        """Test get_search_results with empty search term."""
        queryset = Person.objects.all()
        results, use_distinct = self.admin.get_search_results(self.request, queryset, "")

        self.assertEqual(results.count(), 2)
        self.assertFalse(use_distinct)

    def test_get_search_results_by_family_name(self):
        """Test get_search_results by family name."""
        queryset = Person.objects.all()
        results, use_distinct = self.admin.get_search_results(self.request, queryset, "田中")

        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first(), self.person1)
        self.assertTrue(use_distinct)

    def test_get_search_results_by_name(self):
        """Test get_search_results by given name."""
        queryset = Person.objects.all()
        results, use_distinct = self.admin.get_search_results(self.request, queryset, "二郎")

        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first(), self.person2)
        self.assertTrue(use_distinct)

    def test_get_search_results_by_family_name_kana(self):
        """Test get_search_results by family name kana."""
        queryset = Person.objects.all()
        results, use_distinct = self.admin.get_search_results(self.request, queryset, "タナカ")

        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first(), self.person1)
        self.assertTrue(use_distinct)

    def test_get_search_results_by_name_kana(self):
        """Test get_search_results by given name kana."""
        queryset = Person.objects.all()
        results, use_distinct = self.admin.get_search_results(self.request, queryset, "ジロウ")

        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first(), self.person2)
        self.assertTrue(use_distinct)

    def test_get_search_results_by_family_name_romaji(self):
        """Test get_search_results by family name romaji."""
        queryset = Person.objects.all()
        results, use_distinct = self.admin.get_search_results(self.request, queryset, "Tanaka")

        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first(), self.person1)
        self.assertTrue(use_distinct)

    def test_get_search_results_by_name_romaji(self):
        """Test get_search_results by given name romaji."""
        queryset = Person.objects.all()
        results, use_distinct = self.admin.get_search_results(self.request, queryset, "Jiro")

        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first(), self.person2)
        self.assertTrue(use_distinct)

    def test_get_search_results_by_email(self):
        """Test get_search_results by email."""
        queryset = Person.objects.all()
        results, use_distinct = self.admin.get_search_results(self.request, queryset, "tanaka@example.com")

        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first(), self.person1)
        self.assertTrue(use_distinct)

    def test_get_search_results_no_match(self):
        """Test get_search_results with no matching results."""
        queryset = Person.objects.all()
        results, use_distinct = self.admin.get_search_results(self.request, queryset, "存在しない検索語")

        self.assertEqual(results.count(), 0)
        self.assertFalse(use_distinct)
