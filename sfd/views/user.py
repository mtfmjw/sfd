import logging
from typing import Any

from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _

from sfd.models import UserUpload
from sfd.views.common import ModelAdminMixin
from sfd.views.common.download import DownloadMixin
from sfd.views.common.upload import UploadMixin

logger = logging.getLogger(__name__)


class SfdUserAdmin(UploadMixin, DownloadMixin, ModelAdminMixin, UserAdmin):
    """Django User admin with CSV upload and download functionality.

    This admin class provides CSV upload and download capabilities for Django Users
    with their associated groups. It allows bulk creation and updating of users
    through CSV files containing user information and group assignments.

    Features:
        - CSV upload support for bulk user creation and group assignment
        - CSV download for exporting user and group data
        - Automatic group lookup and assignment by group name
        - Password generation for new users
        - Validation to ensure groups exist before assignment
        - Bulk operations with transaction safety

    CSV Format:
        Expected CSV columns:
        - Username: Unique username for the user
        - First Name: User's first name (optional)
        - Last Name: User's last name (optional)
        - Email: User's email address (optional)
        - Is Active: Whether the user account is active (True/False)
        - Is Staff: Whether the user has staff privileges (True/False)
        - Is Superuser: Whether the user has superuser privileges (True/False)
        - Group Names: Comma-separated list of group names to assign

    Upload Behavior:
        - Creates new users if they don't exist
        - Updates existing users with new information and groups
        - Generates temporary passwords for new users
        - Assigns users to specified groups
        - Uses bulk operations for performance
        - Atomic transactions ensure data consistency
    """

    # Upload configuration
    upload_model = UserUpload
    is_skip_existing = False  # Allow updates to existing users

    # List display configuration
    list_display = ("username", "email", "last_name", "first_name", "is_superuser", "is_staff", "is_active")
    list_filter = ("is_staff", "is_superuser", "is_active", "groups")

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "password1", "password2"),
            },
        ),
    )

    # Ensure proper form is used for adding users
    add_form = UserCreationForm

    def get_fieldsets(self, request, obj=None) -> list[tuple[str | None, dict[str, Any]]]:
        """Override get_fieldsets to properly handle add_fieldsets for User creation.

        This method ensures that the add_fieldsets is used when adding a new user,
        while falling back to the parent UserAdmin's behavior for editing existing users.
        The ModelAdminMixin.get_fieldsets() is bypassed for User model to maintain
        Django's standard user creation behavior.

        Args:
            request (HttpRequest): The current HTTP request
            obj (User, optional): The User instance being edited, None for add form

        Returns:
            tuple: Fieldsets configuration for the admin form
        """
        if not obj:
            # Adding a new user - use add_fieldsets
            return self.add_fieldsets

        # Editing existing user - use UserAdmin's default behavior
        return UserAdmin.get_fieldsets(self, request, obj)

    def get_download_columns(self, request) -> dict[str, str]:
        """Define columns for CSV download.

        Returns a mapping of model field paths to human-readable column names
        for CSV export functionality.

        Args:
            request: HTTP request object

        Returns:
            dict: Mapping of field paths to column names for CSV export
        """
        return {
            "username": _("Username"),
            "first_name": _("First Name"),
            "last_name": _("Last Name"),
            "last_login": _("Last Login"),
            "email": _("Email"),
            "is_superuser": _("Is Superuser"),
            "is_staff": _("Is Staff"),
            "is_active": _("Is Active"),
            "date_joined": _("Date Joined"),
            "groups__name": _("Group Name"),
            "user_permissions__codename": _("Permission Codename"),
            "user_permissions__content_type__app_label": _("App Label"),
            "user_permissions__content_type__model": _("Model"),
        }

    def post_upload(self, request, cleaned_data=None) -> None:
        for uploaded in UserUpload.objects.all():
            user, created = User.objects.get_or_create(username=uploaded.username)
            user.set_password(user.username)
            if uploaded.app_label and uploaded.model and uploaded.codename:
                content_type = ContentType.objects.get(app_label=uploaded.app_label, model=uploaded.model)
                permission = Permission.objects.get(codename=uploaded.codename, content_type=content_type)
                if not user.user_permissions.filter(id=permission.id).exists():  # type: ignore
                    user.user_permissions.add(permission)
            if uploaded.group_name:
                group = Group.objects.get(name=uploaded.group_name)
                user.groups.add(group)
            user.save()
