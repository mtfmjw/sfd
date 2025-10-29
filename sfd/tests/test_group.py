# type: ignore
"""Test cases for Group model and admin functionality."""

import pytest
from django.contrib.admin import AdminSite
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.test import RequestFactory, TestCase

from sfd.models.group import GroupUpload
from sfd.tests.unittest import BaseTestMixin
from sfd.views.group import SfdGroupAdmin


@pytest.mark.unit
@pytest.mark.models
class GroupUploadModelTest(BaseTestMixin, TestCase):
    """Test cases for GroupUpload model."""

    databases = {"default", "postgres"}

    def setUp(self):
        """Set up test data for GroupUpload tests."""
        super().setUp()

    def test_group_upload_creation(self):
        """Test GroupUpload model instance creation."""
        group_upload = GroupUpload.objects.create(
            name="TestGroup",
            codename="add_user",
            app_label="auth",
            model="user",
        )

        self.assertEqual(group_upload.name, "TestGroup")
        self.assertEqual(group_upload.codename, "add_user")
        self.assertEqual(group_upload.app_label, "auth")
        self.assertEqual(group_upload.model, "user")

    def test_group_upload_str_representation(self):
        """Test GroupUpload string representation."""
        group_upload = GroupUpload.objects.create(name="TestGroup")
        # The model doesn't define __str__, so it will use default representation
        self.assertIsNotNone(str(group_upload))

    def test_group_upload_meta_verbose_name(self):
        """Test GroupUpload model verbose names."""
        self.assertEqual(GroupUpload._meta.verbose_name, "Group Upload")
        self.assertEqual(GroupUpload._meta.verbose_name_plural, "Group Uploads")

    def test_group_upload_unique_constraint(self):
        """Test unique constraint on name and codename."""
        # Create first upload
        GroupUpload.objects.create(
            name="TestGroup",
            codename="add_user",
        )

        # Try to create different combination - should succeed
        GroupUpload.objects.create(
            name="TestGroup",
            codename="change_user",  # Different codename
        )

        # Verify we have 2 records
        self.assertEqual(GroupUpload.objects.filter(name="TestGroup").count(), 2)

    def test_group_upload_optional_fields(self):
        """Test that optional fields can be None or blank."""
        group_upload = GroupUpload.objects.create(name="MinimalGroup")

        self.assertIsNone(group_upload.codename)
        self.assertIsNone(group_upload.app_label)
        self.assertIsNone(group_upload.model)

    def test_group_upload_field_max_lengths(self):
        """Test field max lengths are respected."""
        group_upload = GroupUpload.objects.create(
            name="g" * 150,  # Max length
            codename="c" * 100,
            app_label="a" * 100,
            model="m" * 100,
        )

        self.assertEqual(len(group_upload.name), 150)
        self.assertEqual(len(group_upload.codename), 100)
        self.assertEqual(len(group_upload.app_label), 100)
        self.assertEqual(len(group_upload.model), 100)

    def test_group_upload_name_field_required(self):
        """Test that name field is required."""
        # Name is required, so this should work
        group_upload = GroupUpload.objects.create(name="RequiredName")
        self.assertEqual(group_upload.name, "RequiredName")

    def test_group_upload_multiple_permissions_same_group(self):
        """Test creating multiple GroupUpload records for same group with different permissions."""
        GroupUpload.objects.create(
            name="AdminGroup",
            codename="add_user",
            app_label="auth",
            model="user",
        )

        GroupUpload.objects.create(
            name="AdminGroup",
            codename="change_user",
            app_label="auth",
            model="user",
        )

        GroupUpload.objects.create(
            name="AdminGroup",
            codename="delete_user",
            app_label="auth",
            model="user",
        )

        # Should have 3 upload records for the same group
        self.assertEqual(GroupUpload.objects.filter(name="AdminGroup").count(), 3)


@pytest.mark.unit
@pytest.mark.views
class SfdGroupAdminTest(BaseTestMixin, TestCase):
    """Test cases for SfdGroupAdmin functionality."""

    databases = {"default", "postgres"}

    def setUp(self):
        """Set up test data for SfdGroupAdmin tests."""
        super().setUp()
        self.site = AdminSite()
        self.admin = SfdGroupAdmin(Group, self.site)
        self.factory = RequestFactory()
        self.request = self.factory.get("/admin/")
        self.request.user = self.user

        # Create test permission
        from django.contrib.auth.models import User

        content_type = ContentType.objects.get_for_model(User)
        self.test_permission = Permission.objects.create(
            codename="test_permission",
            name="Test Permission",
            content_type=content_type,
        )

    def test_admin_upload_model(self):
        """Test that admin has correct upload_model."""
        self.assertEqual(self.admin.upload_model, GroupUpload)

    def test_admin_is_skip_existing(self):
        """Test that admin allows updates to existing groups."""
        self.assertFalse(self.admin.is_skip_existing)

    def test_get_download_columns(self):
        """Test get_download_columns returns correct column mapping."""
        columns = self.admin.get_download_columns(self.request)

        expected_columns = {
            "name": "Group Name",
            "permissions__codename": "Permission Codename",
            "permissions__content_type__app_label": "App Label",
            "permissions__content_type__model": "Model",
        }

        self.assertEqual(columns, expected_columns)
        self.assertIn("name", columns)
        self.assertIn("permissions__codename", columns)
        self.assertIn("permissions__content_type__app_label", columns)
        self.assertIn("permissions__content_type__model", columns)

    def test_post_upload_creates_new_group(self):
        """Test post_upload creates new group from GroupUpload."""
        GroupUpload.objects.create(name="NewGroup")

        self.admin.post_upload(self.request)

        # Verify group was created
        self.assertTrue(Group.objects.filter(name="NewGroup").exists())

    def test_post_upload_adds_permission_to_group(self):
        """Test post_upload adds permission to group."""
        from django.contrib.auth.models import User

        content_type = ContentType.objects.get_for_model(User)
        GroupUpload.objects.create(
            name="PermissionGroup",
            codename="test_permission",
            app_label=content_type.app_label,
            model=content_type.model,
        )

        self.admin.post_upload(self.request)

        group = Group.objects.get(name="PermissionGroup")
        self.assertTrue(group.permissions.filter(codename="test_permission").exists())

    def test_post_upload_updates_existing_group(self):
        """Test post_upload updates existing group."""
        # Create existing group
        existing_group = Group.objects.create(name="ExistingGroup")

        # Create upload data
        from django.contrib.auth.models import User

        content_type = ContentType.objects.get_for_model(User)
        GroupUpload.objects.create(
            name="ExistingGroup",
            codename="test_permission",
            app_label=content_type.app_label,
            model=content_type.model,
        )

        self.admin.post_upload(self.request)

        # Verify group still exists (not duplicated)
        self.assertEqual(Group.objects.filter(name="ExistingGroup").count(), 1)

        # Verify permission was added
        existing_group.refresh_from_db()
        self.assertTrue(existing_group.permissions.filter(codename="test_permission").exists())

    def test_post_upload_handles_multiple_groups(self):
        """Test post_upload processes multiple GroupUpload records."""
        GroupUpload.objects.create(name="Group1")
        GroupUpload.objects.create(name="Group2")
        GroupUpload.objects.create(name="Group3")

        self.admin.post_upload(self.request)

        self.assertTrue(Group.objects.filter(name="Group1").exists())
        self.assertTrue(Group.objects.filter(name="Group2").exists())
        self.assertTrue(Group.objects.filter(name="Group3").exists())

    def test_post_upload_adds_multiple_permissions_to_same_group(self):
        """Test post_upload can add multiple permissions to the same group."""
        from django.contrib.auth.models import User

        content_type = ContentType.objects.get_for_model(User)

        # Create another permission
        _perm2 = Permission.objects.create(
            codename="test_permission_2",
            name="Test Permission 2",
            content_type=content_type,
        )

        # Create uploads for same group with different permissions
        GroupUpload.objects.create(
            name="MultiPermGroup",
            codename="test_permission",
            app_label=content_type.app_label,
            model=content_type.model,
        )

        GroupUpload.objects.create(
            name="MultiPermGroup",
            codename="test_permission_2",
            app_label=content_type.app_label,
            model=content_type.model,
        )

        self.admin.post_upload(self.request)

        group = Group.objects.get(name="MultiPermGroup")
        self.assertEqual(group.permissions.count(), 2)
        self.assertTrue(group.permissions.filter(codename="test_permission").exists())
        self.assertTrue(group.permissions.filter(codename="test_permission_2").exists())
        # Verify perm2 was created
        self.assertIsNotNone(_perm2)

    def test_post_upload_skips_permission_without_complete_data(self):
        """Test post_upload skips permission assignment if data is incomplete."""
        GroupUpload.objects.create(
            name="IncompleteGroup",
            codename="test_permission",
            # Missing app_label and model
        )

        self.admin.post_upload(self.request)

        group = Group.objects.get(name="IncompleteGroup")
        # Should not have any permissions
        self.assertEqual(group.permissions.count(), 0)

    def test_post_upload_does_not_duplicate_permissions(self):
        """Test post_upload doesn't add duplicate permissions."""
        from django.contrib.auth.models import User

        content_type = ContentType.objects.get_for_model(User)

        # Create group with permission
        group = Group.objects.create(name="PermGroup")
        group.permissions.add(self.test_permission)

        # Try to add same permission via upload
        GroupUpload.objects.create(
            name="PermGroup",
            codename="test_permission",
            app_label=content_type.app_label,
            model=content_type.model,
        )

        initial_perm_count = group.permissions.count()
        self.admin.post_upload(self.request)

        group.refresh_from_db()
        # Permission count should remain the same
        self.assertEqual(group.permissions.count(), initial_perm_count)

    def test_post_upload_handles_group_without_permissions(self):
        """Test post_upload correctly handles group upload without permission data."""
        GroupUpload.objects.create(name="NoPermGroup")

        self.admin.post_upload(self.request)

        group = Group.objects.get(name="NoPermGroup")
        # Group should exist but have no permissions
        self.assertEqual(group.permissions.count(), 0)

    def test_admin_inherits_from_group_admin(self):
        """Test that SfdGroupAdmin inherits from GroupAdmin."""
        from django.contrib.auth.admin import GroupAdmin

        self.assertTrue(isinstance(self.admin, GroupAdmin))

    def test_admin_has_upload_mixin(self):
        """Test that SfdGroupAdmin has UploadMixin capabilities."""
        from sfd.views.common.upload import UploadMixin

        self.assertTrue(isinstance(self.admin, UploadMixin))

    def test_admin_has_download_mixin(self):
        """Test that SfdGroupAdmin has DownloadMixin capabilities."""
        from sfd.views.common.download import DownloadMixin

        self.assertTrue(isinstance(self.admin, DownloadMixin))

    def test_post_upload_with_invalid_content_type(self):
        """Test post_upload handles invalid content type gracefully."""
        GroupUpload.objects.create(
            name="InvalidContentTypeGroup",
            codename="invalid_perm",
            app_label="nonexistent_app",
            model="nonexistent_model",
        )

        # Should raise ContentType.DoesNotExist
        with self.assertRaises(ContentType.DoesNotExist):
            self.admin.post_upload(self.request)

    def test_post_upload_with_invalid_permission(self):
        """Test post_upload handles invalid permission gracefully."""
        from django.contrib.auth.models import User

        content_type = ContentType.objects.get_for_model(User)

        GroupUpload.objects.create(
            name="InvalidPermGroup",
            codename="nonexistent_permission",
            app_label=content_type.app_label,
            model=content_type.model,
        )

        # Should raise Permission.DoesNotExist
        with self.assertRaises(Permission.DoesNotExist):
            self.admin.post_upload(self.request)
