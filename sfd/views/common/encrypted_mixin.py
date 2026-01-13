from django import forms


class MaskedWidget(forms.Widget):
    """Widget that displays a masked value."""

    def render(self, name, value, attrs=None, renderer=None):  # type: ignore
        return "********"


class EncryptedFieldAdminMixin:
    """
    Mixin to control visibility of encrypted fields in Django Admin.

    Attributes:
        encrypted_fields (list): List of field names (or list_display method names) that should be masked.
    """

    encrypted_fields = []
    encrypted_view_permission = "sfd.view_encrypted_fields"

    def has_view_encrypted_permission(self, request):
        """Check if user has permission to view encrypted data."""
        return request.user.has_perm(self.encrypted_view_permission) or request.user.is_superuser

    def get_list_display(self, request):
        """
        Override list_display to mask encrypted fields if user lacks permission.
        """
        list_display = list(super().get_list_display(request))  # type: ignore
        if self.has_view_encrypted_permission(request):
            return list_display

        # If user doesn't have permission, we need to wrap the fields
        new_list_display = []
        for field_name in list_display:
            if field_name in self.encrypted_fields:
                new_list_display.append(self._create_masked_callable(field_name))
            else:
                new_list_display.append(field_name)
        return new_list_display

    def _create_masked_callable(self, field_name):
        """Create a callable that returns a masked string."""

        def masked_display(obj):
            return "********"

        # Try to get the short_description from the original method if it exists on self
        if hasattr(self, field_name):
            attr = getattr(self, field_name)
            if hasattr(attr, "short_description"):
                masked_display.short_description = attr.short_description  # type: ignore[attr-defined]
            else:
                masked_display.short_description = field_name  # type: ignore[attr-defined]
        else:
            masked_display.short_description = field_name  # type: ignore[attr-defined]

        return masked_display

    def get_object(self, request, object_id, from_field=None):
        obj = super().get_object(request, object_id, from_field)  # type: ignore
        if obj and not self.has_view_encrypted_permission(request):
            for field_name in self.encrypted_fields:
                if hasattr(obj, field_name):
                    try:
                        setattr(obj, field_name, "********")
                    except AttributeError:
                        pass
        return obj

    def get_form(self, request, obj=None, **kwargs):
        """
        Override form to mask values if user lacks permission.
        """
        form = super().get_form(request, obj, **kwargs)  # type: ignore

        if not self.has_view_encrypted_permission(request):
            for field_name in self.encrypted_fields:
                if field_name in form.base_fields:
                    form.base_fields[field_name].widget = MaskedWidget()
                    form.base_fields[field_name].disabled = True
                    form.base_fields[field_name].required = False
        return form

    def has_add_permission(self, request):
        if not self.has_view_encrypted_permission(request):
            return False
        return super().has_add_permission(request)  # type: ignore

    def has_change_permission(self, request, obj=None):
        if not self.has_view_encrypted_permission(request):
            return False
        return super().has_change_permission(request, obj)  # type: ignore

    def has_delete_permission(self, request, obj=None):
        if not self.has_view_encrypted_permission(request):
            return False
        return super().has_delete_permission(request, obj)  # type: ignore

    def get_actions(self, request):
        actions = super().get_actions(request)  # type: ignore
        if not self.has_view_encrypted_permission(request):
            if "download_selected" in actions:
                del actions["download_selected"]
        return actions

    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(request, extra_context)  # type: ignore
        if not self.has_view_encrypted_permission(request):
            if hasattr(response, "context_data") and response.context_data:
                response.context_data.pop("upload_url", None)
        return response

    def upload_file(self, request):
        if not self.has_view_encrypted_permission(request):
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied
        return super().upload_file(request)  # type: ignore
