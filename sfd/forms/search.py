from django import forms
from django.utils.translation import gettext_lazy as _


class SearchFormMixin:
    """Mixin to add a 'deleted_flg' field to search forms."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if "deleted_flg" not in self.fields:  # type: ignore
            self.fields["deleted_flg"] = forms.BooleanField(label=_("delete"), required=False, initial=False)  # type: ignore
