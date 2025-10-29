import logging

from django.contrib.admin import ModelAdmin

from sfd.views.common import (
    BaseModelAdminMixin,
    BaseModelDownloadMixin,
    DownloadMixin,
    MasterModelDownloadMixin,
    MasterModelUploadMixin,
    ModelAdminMixin,
    UploadMixin,
)
from sfd.views.common.mixins import MasterModelAdminMixin
from sfd.views.common.upload import BaseModelUploadMixin

logger = logging.getLogger(__name__)


class SfdModelAdmin(UploadMixin, DownloadMixin, ModelAdminMixin, ModelAdmin):
    """Admin class for SFD mode."""

    pass


class BaseModelAdmin(BaseModelUploadMixin, BaseModelDownloadMixin, BaseModelAdminMixin, SfdModelAdmin):
    """Base class for sfd model admin classes.

    This base admin class provides common functionality and settings for all
    sfd-related models. It integrates CSV download capabilities through
    DownloadMixin and implements configurable read-only mode for models
    that should not be modified through the admin interface.

    The class provides permission controls that can be globally enabled or
    disabled through the is_readonly attribute, making it easy to switch
    models between read-only and editable modes.

    Attributes:
        change_list_template (str): Custom template for the changelist view
        change_form_template (str): Custom template for the change form view
        is_readonly (bool): Controls whether the model allows modifications

    Features:
        - CSV download functionality inherited from DownloadMixin
        - Configurable read-only mode for data protection
        - Custom admin templates for consistent UI
        - Permission controls for add/change/delete operations
        - Action filtering for read-only models

    Usage:
        ```python
        class MyModelAdmin(BaseModelAdmin):
            is_readonly = True  # Make model read-only
            list_display = ['field1', 'field2']
        ```
    """


class MasterModelAdmin(MasterModelUploadMixin, MasterModelDownloadMixin, MasterModelAdminMixin, BaseModelAdmin):
    """Base class for MasterModel admin classes.

    This class combines MasterModel-specific functionality with standard SFD admin
    features. It provides:
    - MasterModel validity period management (via MasterModelAdminMixin)
    - BaseModel audit fields and concurrent update protection (via BaseModelAdminMixin, inherited)
    - Upload/Download functionality (via SfdModelAdmin)
    - Master-specific CSV upload handling (via MasterModelUploadMixin)

    The inheritance chain automatically includes:
    - MasterModelAdminMixin → BaseModelAdminMixin → ModelAdminMixin
    - SfdModelAdmin → UploadMixin, DownloadMixin, ModelAdminMixin

    Usage:
        ```python
        @admin.register(MyMasterModel)
        class MyMasterModelAdmin(MasterModelAdmin):
            list_display = ['name', 'valid_from', 'valid_to']
        ```

    Note:
        Changed from inheriting BaseModelAdmin to SfdModelAdmin to avoid
        redundant BaseModelAdminMixin inheritance (now via MasterModelAdminMixin).
    """
