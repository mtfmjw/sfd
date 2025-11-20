from django.db.models.functions import Length
from django.utils.translation import gettext_lazy as _

from sfd.forms.person import PersonAdminForm
from sfd.models.municipality import Municipality
from sfd.models.person import GenderType
from sfd.models.postcode import Postcode
from sfd.views.base import MasterModelAdmin


class PersonAdmin(MasterModelAdmin):
    form = PersonAdminForm
    list_display = [
        "full_name",
        "full_name_kana",
        "full_name_romaji",
        "birthday",
        "gender",
        "email",
        "phone_number",
        "mobile_number",
        "postcode_link",
        "municipality_link",
        "address_detail",
    ]
    search_fields = ["family_name", "name", "family_name_kana", "name_kana"]
    upload_column_names = [
        "family_name",
        "name",
        "family_name_kana",
        "name_kana",
        "family_name_romaji",
        "name_romaji",
        "birthday",
        "gender",
        "email",
        "phone_number",
        "mobile_number",
        "postcode",
        "address",
    ]
    upload_db_field_names = [
        "family_name",
        "name",
        "family_name_kana",
        "name_kana",
        "family_name_romaji",
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
    download_column_names = [
        "family_name",
        "name",
        "family_name_kana",
        "name_kana",
        "family_name_romaji",
        "name_romaji",
        "birthday",
        "gender",
        "email",
        "phone_number",
        "mobile_number",
        "postcode",
        "address_detail",
        "valid_from",
        "valid_to",
        "created_by",
        "created_at",
        "updated_by",
        "updated_at",
    ]

    def full_name(self, obj) -> str:
        """Return the full name of the person."""
        return f"{obj.family_name} {obj.name}"

    def full_name_kana(self, obj) -> str:
        """Return the full name (kana) of the person."""
        return f"{obj.family_name_kana} {obj.name_kana}"

    def full_name_romaji(self, obj) -> str:
        """Return the full name (romaji) of the person."""
        return f"{obj.family_name_romaji} {obj.name_romaji}"

    def postcode_link(self, obj) -> str:
        if not obj.postcode:
            return ""
        return self.get_popup_model_hyperlink(obj.postcode, label=obj.postcode.postcode[:3] + "-" + obj.postcode.postcode[3:])

    def municipality_link(self, obj) -> str:
        if not obj.municipality:
            return ""

        municipality_link = obj.municipality.prefecture_name + obj.municipality.municipality_name
        if not municipality_link:
            return ""

        # Return HTML link with XSS protection
        return self.get_popup_model_hyperlink(obj.municipality)

    full_name.short_description = _("Full Name")  # type: ignore[attr-defined]
    full_name_kana.short_description = _("Full Name (Kana)")  # type: ignore[attr-defined]
    full_name_romaji.short_description = _("Full Name (Romaji)")  # type: ignore[attr-defined]
    postcode_link.short_description = _("Postcode")  # type: ignore[attr-defined]
    municipality_link.short_description = _("Municipality Name")  # type: ignore[attr-defined]
    municipality_link.admin_order_field = "municipality__municipality_name"  # type: ignore[attr-defined]

    def get_search_results(self, request, queryset, search_term):
        """Override search to use hash-based search for encrypted fields.

        Note: Encrypted fields only support exact match searches.
        To search, enter the exact value (e.g., exact family name, name, kana, or email).
        """
        if not search_term:
            return queryset, False

        # Generate hash for the search term
        from sfd.common.encrypted import generate_search_hash

        search_hash = generate_search_hash(search_term)

        # Search across all hash fields for exact matches
        from django.db.models import Q

        search_query = (
            Q(family_name_hash=search_hash)
            | Q(name_hash=search_hash)
            | Q(family_name_kana_hash=search_hash)
            | Q(name_kana_hash=search_hash)
            | Q(family_name_romaji_hash=search_hash)
            | Q(name_romaji_hash=search_hash)
            | Q(email_hash=search_hash)
        )

        # Apply the search to the queryset
        filtered_queryset = queryset.filter(search_query)

        return filtered_queryset, filtered_queryset.exists()

    fieldsets = [
        (
            _("Basic Information"),
            {
                "fields": (
                    ("family_name", "name"),
                    ("family_name_kana", "name_kana"),
                    ("family_name_romaji", "name_romaji"),
                    ("birthday", "gender"),
                    ("email", "phone_number", "mobile_number"),
                    ("postcode_search", "municipality_display", "address_detail"),
                )
            },
        ),
    ]

    def convert2upload_fields(self, request, row_dict, upload_fields) -> dict[str, object]:
        """Convert row data to match the upload fields."""
        converted = super().convert2upload_fields(request, row_dict, upload_fields)

        if converted.get("gender") not in GenderType.values:
            converted["gender"] = GenderType.OTHER

        converted["municipality"] = None
        postcode_value = row_dict.get("postcode").replace("-", "")
        postcode = Postcode.objects.filter(postcode=postcode_value).first()
        if postcode:
            converted["postcode"] = postcode
            converted["municipality"] = postcode.municipality
            address = row_dict.get("address", "")
            full_municipality_name = postcode.municipality.prefecture_name + postcode.municipality.municipality_name  # type: ignore[attr-defined]
            converted["address_detail"] = address.replace(full_municipality_name, "")
        else:
            address = row_dict.get("address", "")
            if "東京都" in address:
                prefecture_name = "東京都"
            elif "北海道" in address:
                prefecture_name = "北海道"
            elif "大阪府" in address:
                prefecture_name = "大阪府"
            elif "京都府" in address:
                prefecture_name = "京都府"
            else:
                prefecture_name = address[: address.find("県") + 1]

            remained_address = address.replace(prefecture_name, "")
            municipalities = Municipality.objects.filter(prefecture_name=prefecture_name).order_by(Length("municipality_name").desc())
            municipality = None
            for municipality in municipalities:
                if municipality.municipality_name and municipality.municipality_name in remained_address:
                    postcode = Postcode.objects.filter(municipality=municipality).first()
                    if postcode:
                        break

            if not postcode:
                postcode = Postcode.objects.filter(municipality__prefecture_name=prefecture_name).first()

            if postcode and postcode.municipality and postcode.municipality.municipality_name:
                address_detail = address.replace(prefecture_name + postcode.municipality.municipality_name, "")
                converted["postcode"] = postcode
                converted["municipality"] = postcode.municipality
                converted["address_detail"] = address_detail
            else:
                converted["postcode"] = None
                converted["municipality"] = None
                converted["address_detail"] = address
        return converted
