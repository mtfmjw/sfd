import logging

from django.contrib.auth.admin import GroupAdmin
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

from sfd.models import GroupUpload
from sfd.views.common import ModelAdminMixin
from sfd.views.common.download import DownloadMixin
from sfd.views.common.upload import UploadMixin

logger = logging.getLogger(__name__)


class SfdGroupAdmin(UploadMixin, DownloadMixin, ModelAdminMixin, GroupAdmin):
    """Django Group admin with CSV upload and download functionality.

    This admin class provides CSV upload and download capabilities for Django Groups
    with their associated permissions. It allows bulk creation and updating of groups
    through CSV files containing group names and permission details.

    Features:
        - CSV upload support for bulk group creation and permission assignment
        - CSV download for exporting group and permission data
        - Automatic permission lookup and assignment by codename and content type
        - Validation to ensure permissions exist before assignment
        - Bulk operations with transaction safety

    CSV Format:
        Expected CSV columns:
        - Group Name: Name of the group
        - Permission Codename: Permission codename (e.g., 'add_user')
        - App Label: Django app label (e.g., 'auth')
        - Model: Model name (e.g., 'user')

    Upload Behavior:
        - Creates new groups if they don't exist
        - Adds permissions to existing groups (doesn't remove existing permissions)
        - Validates permissions exist before assignment
        - Uses bulk operations for performance
        - Atomic transactions ensure data consistency
    """

    # Upload configuration
    upload_model = GroupUpload
    is_skip_existing = False  # Allow updates to existing groups

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
            "name": "Group Name",
            "permissions__codename": "Permission Codename",
            "permissions__content_type__app_label": "App Label",
            "permissions__content_type__model": "Model",
        }

    def post_upload(self, request, cleaned_data=None) -> None:
        for uploaded in GroupUpload.objects.all():
            group, created = Group.objects.get_or_create(name=uploaded.name)
            if uploaded.app_label and uploaded.model and uploaded.codename:
                content_type = ContentType.objects.get(app_label=uploaded.app_label, model=uploaded.model)
                permission = Permission.objects.get(codename=uploaded.codename, content_type=content_type)
                if not group.permissions.filter(id=permission.id).exists():  # type: ignore
                    group.permissions.add(permission)
