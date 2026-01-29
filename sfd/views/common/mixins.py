import logging
from collections import OrderedDict
from typing import Any
from urllib.parse import urlencode

from django import forms
from django.contrib import admin, messages
from django.contrib.admin import site
from django.contrib.admin.utils import get_deleted_objects
from django.db import IntegrityError, transaction
from django.forms import ValidationError
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext as _

from sfd.models.base import BaseModel, MasterModel, default_valid_from_date, default_valid_to_date

logger = logging.getLogger(__name__)


class ModelAdminInlineMixin:
    """Mixin for Django ModelAdmin classes to add inline functionality.

    This mixin is designed to be used with Django's ModelAdmin classes.
    """

    def get_formset(self, request, obj=None, **kwargs):
        formset_class = super().get_formset(request, obj, **kwargs)  # type: ignore[misc]
        admin_instance = self._admin_instance  # type: ignore[attr-defined]

        class ModelFormSet(formset_class):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                # Store admin instance reference for formset access
                self._admin_instance = admin_instance

            def clean(self):
                super().clean()

                if any(form.has_changed() for form in self.forms):
                    self._admin_instance.has_form_data_changed = True

                if (
                    "_delete" not in request.POST
                    and hasattr(self._admin_instance, "has_form_data_changed")
                    and not self._admin_instance.has_form_data_changed
                ):
                    self._admin_instance._main_form.add_error(None, _("No changes detected."))
                    raise forms.ValidationError(_("No changes detected."))

        return ModelFormSet


class ModelAdminMixin:
    """Mixin for Django ModelAdmin classes to add custom functionality.

    This mixin is designed to be used with Django's ModelAdmin classes.
    It provides custom actions, readonly support, and enhanced form handling.
    """

    change_list_template = "sfd/change_list.html"
    is_readonly = False
    save_as = True

    def has_add_permission(self, request) -> bool:
        read_only = request.GET.get("is_readonly", "false").lower() == "true" or self.is_readonly
        return not read_only and super().has_add_permission(request)  # type: ignore[misc]

    def has_change_permission(self, request, obj=None) -> bool:
        read_only = request.GET.get("is_readonly", "false").lower() == "true" or self.is_readonly
        return not read_only and super().has_change_permission(request, obj=obj)  # type: ignore[misc]

    def has_delete_permission(self, request, obj=None) -> bool:
        read_only = request.GET.get("is_readonly", "false").lower() == "true" or self.is_readonly
        return not read_only and super().has_delete_permission(request, obj=obj)  # type: ignore[misc]

    def get_actions(self, request) -> OrderedDict[Any, Any]:
        actions = super().get_actions(request)  # type: ignore[misc]
        if self.has_delete_permission(request):
            actions["delete_selected_popup"] = (self.delete_selected_popup, "delete_selected_popup", _("Delete selected items"))
        elif "delete_selected_popup" in actions:
            del actions["delete_selected_popup"]

        if self.has_change_permission(request):
            actions["update_selected_popup"] = (self.update_selected_popup, "update_selected_popup", _("Update selected items"))
        elif "update_selected_popup" in actions:
            del actions["update_selected_popup"]

        if "delete_selected" in actions:
            del actions["delete_selected"]

        return actions

    def execute_delete_selected(self, request, queryset) -> int:
        """Execute the deletion of selected objects."""
        deleted_count = 0
        with transaction.atomic():
            for obj in queryset:
                obj.delete()
                deleted_count += 1
        return deleted_count

    def get_context_for_delete_selected(self, request, queryset) -> dict[str, Any]:
        opts = self.model._meta  # type: ignore[attr-defined]
        deleted_objects, model_count, perms_needed, protected = get_deleted_objects(queryset, request, site)

        selected_objects = request.POST.getlist("_selected_action")

        if perms_needed:
            # Concatenate string representations of objects without permissions
            objects_without_perms = ", ".join(str(obj) for obj in perms_needed)
            message = _("You have no permission to delete the following {model_name}: {objects}.").format(
                model_name=opts.verbose_name_plural if len(perms_needed) > 1 else opts.verbose_name,  # type: ignore[attr-defined]
                objects=objects_without_perms,
            )
            messages.error(request, message)

        if protected:
            # Handle protected objects that cannot be deleted
            protected_objects = ", ".join(str(obj) for obj in protected)
            message = _("Cannot delete the following {model_name} due to related objects: {objects}").format(
                model_name=opts.verbose_name_plural if len(protected) > 1 else opts.verbose_name,  # type: ignore[attr-defined]
                objects=protected_objects,
            )
            messages.error(request, message)

        if len(selected_objects) != queryset.count():
            message = _("Some data of {model_name} could be updated by other users, please refresh the page.").format(
                model_name=opts.verbose_name_plural if len(protected) > 1 else opts.verbose_name,  # type: ignore[attr-defined]
            )
            messages.error(request, message)

        context = {
            "opts": opts,
            "action_name": "delete_selected_popup",
            "queryset": queryset,
            "selected_objects": [str(obj) for obj in queryset],
            "selected_count": queryset.count(),
        }
        return context

    def delete_selected_popup(self, modeladmin, request, queryset):
        opts = self.model._meta  # type: ignore[attr-defined]

        # Handle the actual deletion if confirmed
        if request.method == "POST" and "confirm_delete" in request.POST:
            try:
                deleted_count = self.execute_delete_selected(request, queryset)

                # Log the deletion
                message = _("Successfully deleted {count} {model_name}.").format(
                    count=deleted_count,
                    model_name=opts.verbose_name_plural if deleted_count > 1 else opts.verbose_name,
                )

                logger.info(message)
                messages.success(request, message)
            except Exception as e:
                error_message = str(e) + _("No data was deleted.")
                messages.error(request, error_message)

            # Construct the admin changelist URL for redirect
            changelist_url = reverse(f"{self.admin_site.name}:{opts.app_label}_{opts.model_name}_changelist")  # type: ignore[attr-defined]

            # Regular form submission - redirect normally
            from django.http import HttpResponseRedirect

            return HttpResponseRedirect(changelist_url)

        # Show confirmation popup
        context = self.get_context_for_delete_selected(request, queryset)

        return TemplateResponse(request, "sfd/delete_confirmation.html", context)

    def execute_update_selected(self, request, queryset, field_name: str, field_value: Any) -> int:
        """Execute the update of selected objects.

        Args:
            request (HttpRequest): The HTTP request object
            queryset (QuerySet): The queryset of objects to update
            field_name (str): The name of the field to update
            field_value (Any): The value to set for the field

        Returns:
            int: Number of objects updated

        Raises:
            ValidationError: If field validation fails
            IntegrityError: If concurrent update is detected
        """
        updated_count = 0
        opts = self.model._meta  # type: ignore[attr-defined]

        with transaction.atomic():
            for obj in queryset:
                # Check for concurrent updates if object has updated_at field
                if hasattr(obj, "updated_at") and obj.updated_at:
                    timestamp_field_name = f"timestamp_{obj.pk}"
                    submitted_timestamp = request.POST.get(timestamp_field_name)

                    if submitted_timestamp:
                        submitted_timestamp = int(submitted_timestamp)
                        # Get current object from database to check for concurrent updates
                        current_obj = obj.__class__.objects.get(pk=obj.pk)
                        current_timestamp = int(current_obj.updated_at.timestamp() * 1_000_000)

                        if current_timestamp != submitted_timestamp:
                            raise IntegrityError(_("Concurrent update detected for {obj}.").format(obj=obj))

                # Validate field exists
                try:
                    opts.get_field(field_name)
                except Exception:  # pragma: no cover
                    raise ValidationError(_("Field '{field_name}' does not exist.").format(field_name=field_name)) from None

                # Set the field value
                setattr(obj, field_name, field_value)

                # Update audit fields if they exist
                if hasattr(obj, "updated_by"):
                    obj.updated_by = request.user.username
                if hasattr(obj, "updated_at"):
                    obj.updated_at = timezone.now()

                # Save the object
                obj.save()
                updated_count += 1

        return updated_count

    def get_updateable_fields(self) -> list[tuple[str, str]]:
        """Get list of updateable fields for bulk update.

        Returns:
            list[tuple[str, str]]: List of (field_name, field_verbose_name) tuples

        Note:
            Override this method to customize which fields are available
            for bulk update. By default, returns all editable fields.
        """
        opts = self.model._meta  # type: ignore[attr-defined]
        fields = []

        for field in opts.get_fields():
            # Skip auto-created fields, primary keys, and audit fields
            if (
                field.concrete
                and not field.auto_created
                and not field.primary_key
                and field.name not in ["created_by", "created_at", "updated_by", "updated_at", "deleted_flg"]
            ):
                fields.append((field.name, str(field.verbose_name)))

        return fields

    def get_context_for_update_selected(self, request, queryset) -> dict[str, Any]:
        """Get context data for the update selected confirmation popup.

        Args:
            request (HttpRequest): The HTTP request object
            queryset (QuerySet): The queryset of selected objects

        Returns:
            dict[str, Any]: Context dictionary for template rendering
        """
        opts = self.model._meta  # type: ignore[attr-defined]
        selected_objects = request.POST.getlist("_selected_action")

        # Check for permission issues
        perms_needed = []
        for obj in queryset:
            if not self.has_change_permission(request, obj):
                perms_needed.append(obj)

        if perms_needed:
            objects_without_perms = ", ".join(str(obj) for obj in perms_needed)
            message = _("You have no permission to update the following {model_name}: {objects}.").format(
                model_name=opts.verbose_name_plural if len(perms_needed) > 1 else opts.verbose_name,
                objects=objects_without_perms,
            )
            messages.error(request, message)

        # Check for concurrent updates
        if len(selected_objects) != queryset.count():
            message = _("Some data of {model_name} could be updated by other users, please refresh the page.").format(
                model_name=opts.verbose_name_plural,
            )
            messages.error(request, message)

        # Collect timestamp information for concurrency control
        object_timestamps = {}
        for obj in queryset:
            if hasattr(obj, "updated_at") and obj.updated_at:
                object_timestamps[obj.pk] = int(obj.updated_at.timestamp() * 1_000_000)

        context = {
            "opts": opts,
            "action_name": "update_selected_popup",
            "queryset": queryset,
            "selected_objects": [str(obj) for obj in queryset],
            "selected_count": queryset.count(),
            "updateable_fields": self.get_updateable_fields(),
            "object_timestamps": object_timestamps,
        }
        return context

    def update_selected_popup(self, modeladmin, request, queryset):
        """Admin action to update selected objects via popup.

        This action displays a popup window where users can select a field
        and provide a value to update for all selected objects. The popup
        reuses the same modal structure as delete_selected_popup.

        Args:
            modeladmin: The ModelAdmin instance (same as self)
            request (HttpRequest): The HTTP request object
            queryset (QuerySet): The queryset of selected objects

        Returns:
            TemplateResponse: The popup template response or redirect after update
        """
        opts = self.model._meta  # type: ignore[attr-defined]

        # Handle the actual update if confirmed
        if request.method == "POST" and "confirm_update" in request.POST:
            # Construct the admin changelist URL for redirect
            changelist_url = reverse(f"{self.admin_site.name}:{opts.app_label}_{opts.model_name}_changelist")  # type: ignore[attr-defined]

            try:
                field_name = request.POST.get("field_name", "").strip()
                field_value = request.POST.get("field_value", "").strip()

                if not field_name:
                    raise ValidationError(_("Please select a field to update."))

                if not field_value:
                    raise ValidationError(_("Please provide a value."))

                # Convert field value to appropriate type
                field = opts.get_field(field_name)

                # Handle different field types
                if hasattr(field, "to_python"):
                    try:
                        field_value = field.to_python(field_value)
                    except Exception as e:  # pragma: no cover
                        raise ValidationError(
                            _("Invalid value for field '{field_name}': {error}").format(field_name=field.verbose_name, error=str(e))
                        ) from e

                # Execute the update
                updated_count = self.execute_update_selected(request, queryset, field_name, field_value)

                # Log the update
                message = _("Successfully updated {count} {model_name}.").format(
                    count=updated_count,
                    model_name=opts.verbose_name_plural if updated_count > 1 else opts.verbose_name,
                )

                logger.info(message)
                messages.success(request, message)

            except ValidationError as e:
                messages.error(request, str(e.message) if hasattr(e, "message") else str(e))
            except Exception as e:
                error_message = _("Error updating records: {error}").format(error=str(e))
                messages.error(request, error_message)
                logger.error(error_message)

            # Regular form submission - redirect normally
            from django.http import HttpResponseRedirect

            return HttpResponseRedirect(changelist_url)

        # Show update popup
        context = self.get_context_for_update_selected(request, queryset)

        return TemplateResponse(request, "sfd/update_confirmation.html", context)

    def get_app_name(self) -> str:
        """Get the app_name from the model's app_config.

        This method retrieves the application name from the model's Django
        app configuration. It returns the app_name defined in the app's
        urls.py or falls back to the app_label if app_name is not defined.

        Returns:
            str: The Django application name for URL namespace resolution

        Note:
            This is used for constructing namespaced URLs within the application
            and should correspond to the app_name defined in the app's URLconf.
        """
        return self.model._meta.app_config.name  # type: ignore[attr-defined]

    def get_app_label(self) -> str:
        """Get the app_label of the model.

        This method returns the Django app label for the model associated
        with this admin class. The app label is the lowercase name of the
        Django application containing the model.

        Returns:
            str: The Django app label (e.g., 'sfd', 'auth', 'contenttypes')

        Note:
            This is different from app_name and is used internally by Django
            for model identification and admin site organization.
        """
        return self.model._meta.app_label  # type: ignore[attr-defined]

    def get_client_ip(self, request) -> str | None:
        """Get the client IP address from the request."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip

    def get_column_labels(self, column_names) -> dict[str, str]:
        labels = {}
        for name in column_names:
            if name in [f.name for f in self.model._meta.get_fields()]:  # type: ignore[attr-defined]
                labels[name] = self.model._meta.get_field(name).verbose_name  # type: ignore[attr-defined]
            else:
                # Check for method on ModelAdmin
                method = getattr(self, name, None)
                if method and hasattr(method, "short_description"):
                    labels[name] = str(method.short_description)
                else:
                    labels[name] = str(name)
        return labels

    def get_non_inherited_model_fields(self, request) -> list[str]:
        return [f.name for f in self.model._meta.get_fields() if f.concrete and not f.auto_created]  # type: ignore[attr-defined]

    def get_fieldsets(self, request, obj=None) -> list[tuple[str | None, dict[str, Any]]]:
        if self.fieldsets:  # type: ignore[attr-defined]
            return self.fieldsets  # type: ignore[attr-defined]
        else:
            return [(_("Basic Information"), {"fields": tuple(self.get_non_inherited_model_fields(request))})]

    def get_list_display(self, request) -> list[str]:
        list_display = super().get_list_display(request)  # type: ignore[misc]

        if list_display == ("__str__",):
            return self.get_non_inherited_model_fields(request)
        else:
            return list(list_display)

    def formfield_for_dbfield(self, db_field, request, **kwargs) -> forms.Field | None:
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)  # type: ignore[misc]
        if formfield and formfield.help_text:
            # Move help_text into placeholder
            formfield.widget.attrs["placeholder"] = formfield.help_text
            formfield.help_text = None  # remove default rendering
        return formfield

    def get_popup_model_hyperlink(self, obj, label: str | None = None) -> str:
        """Get the hyperlink for the popup window of a related model.

        Args:
            obj (Model): The model instance for which to get the popup URL.

        Returns:
            str: The HTML for the popup window hyperlink.
        """
        url_name = f"{obj._meta.app_label}_{obj._meta.model_name}_change"
        url_params = {"is_readonly": True, "_popup": 1}
        encoded_params = urlencode(url_params)
        url = reverse(f"{self.admin_site.name}:{url_name}", args=[obj.pk])  # type: ignore

        # Return HTML link with XSS protection
        return format_html(
            '<a href="#" hx-get="{}?{}" class="open-popup-window-dynamic-btn" hx-target="#popupWindowDynamicContent" hx-swap="innerHTML" hx-on::after-swap="openPopupWindowDynamic()">{}</a>',
            url,
            encoded_params,
            label or str(obj),
        )

    def get_form(self, request, obj=None, change=False, **kwargs) -> type[forms.ModelForm]:
        """Override get_form to add concurrent update validation and no-changes validation."""
        form_class = super().get_form(request, obj=obj, change=change, **kwargs)  # type: ignore[misc]
        admin_instance = self  # Store reference to admin instance for formset access

        class ModelForm(form_class):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                # Store admin instance reference for formset access
                admin_instance._main_form = self  # type: ignore[attr-defined]
                admin_instance.has_form_data_changed = False  # type: ignore[attr-defined]
                self._admin_instance = admin_instance  # type: ignore[attr-defined]

            def clean(self):
                cleaned_data = super().clean()

                if not (
                    self._admin_instance._is_delete_action
                    or self._admin_instance._is_undelete_action
                    or self._admin_instance.inlines  # type: ignore[attr-defined]
                    or self.has_changed()
                ):
                    raise ValidationError(_("No changes detected."))

                # Pass change status to admin instance for inline formsets
                self._admin_instance.has_form_data_changed = self.has_changed()  # type: ignore[attr-defined]
                return cleaned_data

        return ModelForm

    def get_inline_instances(self, request, obj=None):
        inline_instances = super().get_inline_instances(request, obj)  # type: ignore[misc]
        for inline in inline_instances:
            inline._admin_instance = self  # type: ignore[attr-defined]
        return inline_instances

    def get_search_field_names(self) -> str:
        """Get search field names with defensive checking."""
        if hasattr(self, "search_fields") and self.search_fields:  # type: ignore[attr-defined]
            _names = [str(f) for f in self.get_column_labels(self.search_fields).values()]  # type: ignore[attr-defined]
            return ", ".join(_names)
        return ""

    def changelist_view(self, request, extra_context=None) -> TemplateResponse:
        """Override the changelist view to add custom context.

        This method customizes the Django admin changelist view by adding
        search help text and custom title for read-only models. It dynamically
        generates search help text based on the model's search fields and
        their verbose names.

        Args:
            request (HttpRequest): The HTTP request object
            extra_context (dict, optional): Additional context data for the view.
                                           Defaults to empty dict if None.

        Returns:
            HttpResponse: The rendered changelist view with custom context

        Custom Context Additions:
            search_help_text (str): Help text showing searchable fields in Japanese
            title (str): Custom title for read-only models using model verbose_name
        """

        if hasattr(self, "search_fields") and self.search_fields:  # type: ignore[attr-defined]
            fields = self.get_search_field_names()
            self.search_help_text = _("You can search and filter by {fields}.").format(fields=fields)  # type: ignore[attr-defined]

        response = super().changelist_view(request, extra_context=extra_context)  # type: ignore[misc]
        if hasattr(response, "context_data"):
            response.context_data["title"] = _("List of {model_name}").format(model_name=self.model._meta.verbose_name)  # type: ignore[attr-defined]

        return response

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None) -> TemplateResponse:
        self._is_delete_action = "_delete" in request.POST
        self._is_undelete_action = "_undelete" in request.POST

        if extra_context is None:
            extra_context = {}

        is_popup = request.GET.get("_popup", None)
        if is_popup is not None:
            extra_context["is_popup"] = "true"
        extra_context["show_close"] = True

        response = super().changeform_view(request, object_id, form_url, extra_context=extra_context)  # type: ignore[misc]

        if hasattr(response, "context_data") and response.context_data and "adminform" in response.context_data:
            visible_fields = response.context_data["adminform"].form.visible_fields()
            for field in visible_fields:
                if field.widget_type == "checkbox":
                    field.label += ":"

        return response


class DeleteFlagFilter(admin.SimpleListFilter):  # pragma: no cover
    """Filter for delete flag field"""

    title = _("Deleted")
    parameter_name = "deleted_flg"

    def lookups(self, request, model_admin):
        return [
            ("false", _("Not Deleted")),
            ("true", _("Deleted")),
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(deleted_flg=self.value())
        return queryset


class BaseModelAdminMixin(ModelAdminMixin):
    """Mixin for Django ModelAdmin classes that work with BaseModel.

    This mixin inherits from ModelAdminMixin and adds BaseModel-specific
    functionality including audit fields (created_by, updated_by, etc.),
    soft delete support (deleted_flg), and concurrent update validation
    using optimistic locking.

    The mixin automatically includes all ModelAdminMixin features such as
    readonly support, custom delete actions, and enhanced form handling.

    Attributes:
        change_form_template (str): Template for change form view
        is_show_edit_info_on_list_view (bool): Show full edit info in list view
        is_optimistic_locking_on_list_view (bool): Show timestamp for locking

    Features:
        - Audit field management (created_by, created_at, updated_by, updated_at)
        - Soft delete support with deleted_flg field
        - Concurrent update detection using timestamps
        - Automatic user tracking on save operations
        - Custom delete actions that set deleted_flg instead of hard delete

    Usage:
        ```python
        @admin.register(MyModel)
        class MyModelAdmin(BaseModelAdminMixin, admin.ModelAdmin):
            list_display = ['name', 'status']
        ```

    Note:
        This mixin can only be used with models that inherit from BaseModel.
        A TypeError will be raised if used with non-BaseModel models.
    """

    change_form_template = "sfd/change_form.html"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not issubclass(self.model, BaseModel):  # type: ignore[attr-defined]
            raise TypeError("BaseModelAdminMixin can only be used with BaseModel subclasses.")

        # Whether to show edit info (created_by, created_at, updated_by, updated_at, deleted) on list view
        self.is_show_edit_info_on_list_view = False
        # Whether to show optimistic locking info (updated_by, updated_at) on list view
        self.is_optimistic_locking_on_list_view = True

    def deleted(self, obj=None) -> str:
        """deleted_flgの代わりに一覧に表示する"""
        # If the model is readonly, do not allow changing existing objects
        if obj and obj.deleted_flg:
            return format_html('<input type="checkbox" class="deleted-row" disabled checked>')
        else:
            return format_html('<input type="checkbox" disabled >')

    deleted.short_description = _("Deleted")  # type: ignore[attr-defined]

    def update_timestamp(self, obj=None) -> str | None:
        """Display the updated_at timestamp in microseconds for concurrency control."""
        if obj and obj.updated_at:
            timestamp = int(obj.updated_at.timestamp() * 1_000_000)
            return format_html(
                '<span data-update-timestamp="{}">{}</span>',
                timestamp,
                obj.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
            )
        return None

    update_timestamp.short_description = _("Updated At")  # type: ignore[attr-defined]

    def get_form(self, request, obj=None, change=False, **kwargs) -> type[forms.ModelForm]:
        """Override get_form to add concurrent update validation and no-changes validation."""
        form_class = super().get_form(request, obj=obj, change=change, **kwargs)  # type: ignore[misc]

        class BaseModelForm(form_class):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                # Add timestamp field for concurrent update validation
                self.fields["timestamp"] = forms.IntegerField(widget=forms.HiddenInput(), required=False)
                # Store original PK in case instance.pk is set to None (e.g., after delete())
                self._original_pk = self.instance.pk if self.instance else None
                if self.instance and self.instance.pk and self.instance.updated_at:
                    self.fields["timestamp"].initial = int(self.instance.updated_at.timestamp() * 1_000_000)

            def clean(self):
                cleaned_data = super().clean()

                if self._admin_instance._is_delete_action or self._admin_instance._is_undelete_action:  # type: ignore[attr-defined]
                    return cleaned_data

                # Only check for concurrent updates when editing existing objects
                # Use _original_pk since instance.pk may be None after delete()
                if self.instance and self._original_pk:
                    timestamp = cleaned_data.get("timestamp")

                    if timestamp:
                        try:
                            # Get the current object from database using original PK
                            current_object = self.instance.__class__.objects.get(pk=self._original_pk)
                            current_timestamp = int(current_object.updated_at.timestamp() * 1_000_000)
                            if current_timestamp != timestamp:
                                raise ValidationError(_("This record has been modified by another user. Please reload and try again.")) from None
                        except self.instance.__class__.DoesNotExist:
                            # Object was deleted by another user
                            raise ValidationError(_("This record has been deleted by another user.")) from None

                return cleaned_data

        return BaseModelForm

    def get_non_inherited_model_fields(self, request) -> list[str]:
        return [f for f in super().get_non_inherited_model_fields(request) if f not in [f.name for f in self.model.get_base_model_fields()]]  # type: ignore[attr-defined]

    def get_readonly_fields(self, request, obj=None) -> list[str]:
        field_names = ["deleted", "created_by", "created_at", "updated_by", "updated_at", "update_timestamp"]
        return list(super().get_readonly_fields(request, obj=obj)) + field_names  # type: ignore[misc]

    def get_fieldsets(self, request, obj=None) -> list[tuple[str | None, dict[str, Any]]]:
        fieldsets = list(super().get_fieldsets(request, obj=obj))  # type: ignore[misc]

        is_popup = request.GET.get("_popup", None)
        if is_popup is None and obj is not None:  # Not in popup and editing existing object
            for fieldset in fieldsets:
                if fieldset[0] == _("Edit Info"):
                    return fieldsets  # Edit Info already exists

            edit_info = (
                _("Edit Info"),
                {
                    "fields": (("created_by", "created_at"), ("updated_by", "updated_at"), "deleted"),
                    "classes": ["collapse"],
                },
            )

            fieldsets.append(edit_info)

        return fieldsets

    def add_edit_info_list_display(self, list_display) -> list[str]:
        field_names = ["created_by", "created_at", "updated_by", "updated_at", "update_timestamp", "deleted_flg", "deleted"]
        list_display = [f for f in list_display if f not in field_names]
        if self.is_show_edit_info_on_list_view:
            list_display += ["created_by", "created_at", "updated_by", "update_timestamp", "deleted"]
        elif self.is_optimistic_locking_on_list_view:
            list_display += ["updated_by", "update_timestamp", "deleted"]
        return list_display

    def get_list_filter(self, request) -> list[str]:
        """Add DeleteFlagFilter to list_filter if not already present."""
        list_filter = super().get_list_filter(request)  # type: ignore[misc]
        if "deleted_flg" in list_filter:
            list_filter = list(list_filter) + [DeleteFlagFilter]
        return list_filter

    def get_list_display(self, request) -> list[str]:
        list_display = super().get_list_display(request)  # type: ignore[misc]
        list_display = self.add_edit_info_list_display(list_display)
        return list_display

    def save_model(self, request, obj, form, change) -> None:
        """Override save_model to set created_by and updated_by fields."""
        obj.updated_by = request.user.username
        obj.updated_at = timezone.now()
        if not obj.created_by:
            obj.created_by = request.user.username
            obj.created_at = timezone.now()

        if "_delete" in request.POST:
            obj.deleted_flg = True
        elif "_undelete" in request.POST:
            obj.deleted_flg = False
        super().save_model(request, obj, form, change)  # type: ignore[misc]

    def execute_delete_selected(self, request, queryset) -> int:
        """Execute the deletion of selected objects."""

        for obj in queryset:
            # Check for concurrent updates if object has updated_at field
            if hasattr(obj, "updated_at") and obj.updated_at:
                timestamp_field_name = f"timestamp_{obj.pk}"
                submitted_timestamp = request.POST.get(timestamp_field_name)

                if submitted_timestamp:
                    submitted_timestamp = int(submitted_timestamp)
                    # Get current object from database to check for concurrent updates
                    current_obj = obj.__class__.objects.get(pk=obj.pk)
                    current_timestamp = int(current_obj.updated_at.timestamp() * 1_000_000)

                    if current_timestamp != submitted_timestamp:
                        raise IntegrityError(_("Concurrent update detected for {obj}.").format(obj=obj))

        deleted_count = 0

        for obj in queryset:
            obj.updated_by = request.user.username
            obj.updated_at = timezone.now()
            obj.deleted_flg = True
            obj.save()
            deleted_count += 1
        return deleted_count

    def get_context_for_delete_selected(self, request, queryset) -> dict[str, Any]:
        """Get context data for the delete selected confirmation popup."""
        context = super().get_context_for_delete_selected(request, queryset)  # type: ignore[misc]

        # Collect timestamp information for concurrency control
        object_timestamps = {}
        for obj in queryset:
            timestamp_field_name = f"timestamp_{obj.pk}"
            timestamp = request.POST.get(timestamp_field_name)
            if timestamp:
                object_timestamps[obj.pk] = int(timestamp)

        context.update({"object_timestamps": object_timestamps})
        return context


class MasterModelAdminMixin(BaseModelAdminMixin):
    """Mixin for Django ModelAdmin classes that work with MasterModel.

    This mixin inherits from BaseModelAdminMixin and adds MasterModel-specific
    functionality including validity period management (valid_from, valid_to),
    historical data protection, and custom deletion rules.

    MasterModel特有の機能：
    - 有効期間開始日と終了日を持つので、論理または物理削除はできない
    - 代わりに、過去データの登録と有効期間の変更を制御する
    - 有効開始日が過去のデータは更新・削除不可（保護される）

    The mixin automatically includes all BaseModelAdminMixin features such as
    audit fields, soft delete support, and concurrent update validation, plus
    MasterModel-specific validity period controls.

    Attributes:
        date_hierarchy (str): Date field for hierarchical navigation in list view

    Features:
        - Validity period management (valid_from, valid_to)
        - Protection of historical data (past valid_from records)
        - Automatic valid_to adjustment when creating new records
        - Prevents deletion of effective master data
        - Custom validation for validity periods
        - Save-as-new functionality for updating historical records

    Usage:
        ```python
        @admin.register(MyMasterModel)
        class MyMasterModelAdmin(MasterModelAdminMixin, admin.ModelAdmin):
            list_display = ['name', 'valid_from', 'valid_to']
        ```

    Note:
        This mixin can only be used with models that inherit from MasterModel.
        A TypeError will be raised if used with non-MasterModel models.
    """

    date_hierarchy = "valid_from"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not issubclass(self.model, MasterModel):  # type: ignore[attr-defined]
            raise TypeError("MasterModelAdminMixin can only be used with MasterModel subclasses.")

    def has_delete_permission(self, request, obj=None) -> bool:
        delete_permission = super().has_delete_permission(request, obj=obj)  # type: ignore[misc]
        if obj and obj.pk and obj.valid_from <= timezone.now().date():
            # 有効期間の開始日が過去のものは削除不可
            return False
        return delete_permission

    def get_actions(self, request) -> OrderedDict[Any, Any]:
        actions = super().get_actions(request)  # type: ignore[misc]
        if "delete_selected" in actions:
            del actions["delete_selected"]
        if "delete_selected_popup" in actions:
            del actions["delete_selected_popup"]
        return actions

    def get_non_inherited_model_fields(self, request) -> list[str]:
        return [f for f in super().get_non_inherited_model_fields(request) if f not in [f.name for f in self.model.get_master_model_fields()]]  # type: ignore[misc]

    def get_fieldsets(self, request, obj=None) -> list[tuple[str | None, dict[str, Any]]]:
        fieldsets = super().get_fieldsets(request, obj=obj)  # type: ignore[misc]
        for fieldset in fieldsets:
            if fieldset[0] == _("Edit Info"):
                # Remove 'deleted' field from the fieldset fields
                fields = fieldset[1]["fields"]
                if isinstance(fields, tuple):
                    # Convert tuple to list, filter out 'deleted', then back to tuple
                    fieldset[1]["fields"] = tuple(
                        field for field in fields if field != "deleted" and (not isinstance(field, tuple) or "deleted" not in field)
                    )
                elif isinstance(fields, list):
                    # Filter out 'deleted' from list
                    fieldset[1]["fields"] = [
                        field for field in fields if field != "deleted" and (not isinstance(field, tuple) or "deleted" not in field)
                    ]
        validation_info = [(_("Validation Info"), {"fields": (("valid_from", "valid_to"),)})]
        return validation_info + fieldsets

    def get_changeform_initial_data(self, request):
        """Pre-populate default validity period for new records."""
        initial = super().get_changeform_initial_data(request)  # type: ignore[misc]

        if "source_id" in request.GET:
            source_id = request.GET.get("source_id")
            try:
                obj = self.model.objects.get(pk=source_id)
                from django.forms.models import model_to_dict

                # Exclude primary keys, audit fields, and validity period
                exclude = ["id", "pk", "created_by", "created_at", "updated_by", "updated_at", "deleted_flg", "valid_from", "valid_to"]
                data = model_to_dict(obj, exclude=exclude)
                initial.update(data)
            except self.model.DoesNotExist:
                pass

        if "valid_from" not in initial:
            initial["valid_from"] = default_valid_from_date()
        if "valid_to" not in initial:
            initial["valid_to"] = default_valid_to_date()
        return initial

    def get_list_display(self, request) -> list[str]:
        list_display = super().get_list_display(request)  # type: ignore[misc]
        field_names = ["valid_from", "valid_to"]
        # valid_from, valid_toを最後に表示するため
        list_display = [f for f in list_display if f not in field_names]
        list_display += field_names
        # 編集情報関連カラムを最後に表示するため
        if hasattr(self, "add_edit_info_list_display"):
            list_display = self.add_edit_info_list_display(list_display)  # type: ignore[attr-defined]
            if "deleted" in list_display:
                list_display.remove("deleted")
        return list_display

    def get_form(self, request, obj=None, change=False, **kwargs) -> type[forms.ModelForm]:
        form_class = super().get_form(request, obj=obj, change=change, **kwargs)  # type: ignore[misc]

        class MasterModelForm(form_class):
            source_id = forms.CharField(widget=forms.HiddenInput(), required=False)

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

                if "source_id" in request.GET:
                    self.fields["source_id"].initial = request.GET.get("source_id")

                # 有効開始日が過去日（今日も含む）の場合、編集不可の旨をヘルプテキストに表示
                if "instance" in kwargs and kwargs["instance"]:
                    valid_from = kwargs["instance"].valid_from
                    if "valid_from" in self.fields and valid_from <= timezone.now().date():
                        self.fields["valid_from"].help_text = _(
                            "Master data that has already been effective cannot be edited but we can update it by copying to a new record with a future start date."
                        )

            def clean(self):
                cleaned_data = super().clean()

                # Fix for "Save as new" creating immutable past records
                if request.method == "POST" and "_saveasnew" in request.POST:
                    cleaned_data["valid_from"] = default_valid_from_date()
                    cleaned_data["valid_to"] = default_valid_to_date()
                    # Also update instance to ensure subsequent checks pass
                    if hasattr(self, "instance"):
                        self.instance.valid_from = cleaned_data["valid_from"]
                        self.instance.valid_to = cleaned_data["valid_to"]

                valid_from = cleaned_data.get("valid_from")

                if obj and obj.pk:
                    if hasattr(self._admin_instance, "_is_delete_action") and self._admin_instance._is_delete_action:  # type: ignore[attr-defined] 削除ボタン押下時
                        if obj.valid_from <= timezone.now().date():
                            # 有効期間の開始日が過去のものは削除不可
                            raise ValidationError({"valid_from": _("Master data that has already been effective cannot be deleted.")})
                    else:  # 保存ボタン押下時
                        if obj.valid_from <= timezone.now().date():
                            # 有効期間の開始日が過去のものは更新不可
                            raise ValidationError({"valid_from": _("Master data that has already been effective cannot be changed.")})

                unique_fields = self.instance.__class__.get_unique_field_names()
                filter_kwargs = {field: cleaned_data.get(field) for field in unique_fields if cleaned_data.get(field) is not None}
                new_obj = self.instance.__class__(**filter_kwargs)
                previous_record = new_obj.get_previous_instance()
                if previous_record and valid_from and valid_from <= timezone.now().date():
                    # 過去日(今日含め)レコードが存在する場合、新規レコードの開始日は未来日のみ設定可能
                    raise ValidationError({"valid_from": _("There is already master data effective in the past. Please set a future start date.")})

                return cleaned_data

        return MasterModelForm

    def save_model(self, request, obj, form, change) -> None:
        """Override save_model to update valid_to of source record during copy."""
        super().save_model(request, obj, form, change)  # type: ignore[misc]

        if not change:
            source_id = form.cleaned_data.get("source_id")
            if source_id:
                try:
                    previous = self.model.objects.get(pk=source_id)
                    if previous.pk != obj.pk and previous.valid_to >= obj.valid_from:
                        # Update the source record's valid_to to be the day before the new record's valid_from(obj.valid_from)
                        previous.valid_to = obj.valid_from - timezone.timedelta(days=1)
                        previous.updated_by = request.user.username
                        previous.updated_at = timezone.now()
                        previous.save()  # type: ignore[misc]
                except self.model.DoesNotExist:
                    pass

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None) -> TemplateResponse:
        """Override changeform view to handle delete button clicks.

        When the delete button is clicked, this method validates the deletion
        rules (e.g., can't delete effective master data), and if valid,
        directly deletes the instance and redirects to the changelist view.

        Args:
            request: HTTP request object
            object_id: Primary key of the object being edited
            form_url: URL for form submission
            extra_context: Additional context for template rendering

        Returns:
            TemplateResponse or HttpResponseRedirect depending on the action
        """
        # Check if delete button was clicked
        if request.method == "POST" and "_delete" in request.POST:
            self._is_delete_action = True  # Explicitly set this for validations relying on it
            # Get the object and form to validate before deleting
            obj = self.get_object(request, object_id) if object_id else None  # type: ignore[attr-defined]
            ModelForm = self.get_form(request, obj)
            form = ModelForm(request.POST, request.FILES, instance=obj)

            if form.is_valid() and obj:
                # If validation passes, delete the object directly
                from django.http import HttpResponseRedirect

                opts = self.model._meta  # type: ignore[attr-defined]

                # Delete the object (this will update previous record's valid_to)
                previous = obj.get_previous_instance()
                if previous:
                    previous.valid_to = obj.valid_to
                    previous.updated_by = request.user.username
                    previous.updated_at = timezone.now()

                obj_name = str(obj)
                obj.delete()
                if previous:
                    previous.save()

                # Add success message
                messages.success(request, _("The {obj_name} was deleted successfully.").format(obj_name=obj_name))

                # Redirect to changelist view
                changelist_url = reverse(f"{self.admin_site.name}:{opts.app_label}_{opts.model_name}_changelist")  # type: ignore[attr-defined]
                return HttpResponseRedirect(changelist_url)  # type: ignore

        if object_id is not None:
            extra_context = extra_context or {}
            extra_context["is_not_savable"] = self.has_delete_permission(request, self.get_object(request, object_id)) is False  # type: ignore[attr-defined]

        return super().changeform_view(request, object_id, form_url, extra_context)  # type: ignore[misc]

    def get_list_filter(self, request) -> list[str]:
        """Add DeleteFlagFilter to list_filter if not already present."""
        list_filter = super().get_list_filter(request)  # type: ignore[misc]
        if "valid_from" not in list_filter:
            list_filter = list(list_filter) + ["valid_from"]
        return list_filter
