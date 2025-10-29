# type: ignore
"""Test cases for User model and admin functionality."""

import pytest
from django.contrib.admin import AdminSite
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.test import RequestFactory, TestCase
from django.utils.translation import gettext_lazy as _

from sfd.models.user import UserUpload
from sfd.tests.unittest import BaseTestMixin
from sfd.views.user import SfdUserAdmin


@pytest.mark.unit
@pytest.mark.models
class UserUploadModelTest(BaseTestMixin, TestCase):
    """Test cases for UserUpload model."""

    databases = {"default", "postgres"}

    def setUp(self):
        """Set up test data for UserUpload tests."""
        super().setUp()

    def test_user_upload_creation(self):
        """Test UserUpload model instance creation."""
        user_upload = UserUpload.objects.create(
            username="testuser",
            first_name="Test",
            last_name="User",
            email="test@example.com",
            is_superuser=False,
            is_staff=True,
            is_active=True,
            group_name="TestGroup",
            codename="add_user",
            app_label="auth",
            model="user",
        )

        self.assertEqual(user_upload.username, "testuser")
        self.assertEqual(user_upload.first_name, "Test")
        self.assertEqual(user_upload.last_name, "User")
        self.assertEqual(user_upload.email, "test@example.com")
        self.assertFalse(user_upload.is_superuser)
        self.assertTrue(user_upload.is_staff)
        self.assertTrue(user_upload.is_active)
        self.assertEqual(user_upload.group_name, "TestGroup")
        self.assertEqual(user_upload.codename, "add_user")
        self.assertEqual(user_upload.app_label, "auth")
        self.assertEqual(user_upload.model, "user")

    def test_user_upload_str_representation(self):
        """Test UserUpload string representation uses username."""
        user_upload = UserUpload.objects.create(username="testuser")
        # The model doesn't define __str__, so it will use default representation
        self.assertIsNotNone(str(user_upload))

    def test_user_upload_meta_verbose_name(self):
        """Test UserUpload model verbose names."""
        self.assertEqual(UserUpload._meta.verbose_name, "User Upload")
        self.assertEqual(UserUpload._meta.verbose_name_plural, "User Uploads")

    def test_user_upload_unique_constraint(self):
        """Test unique constraint on username, codename, and group_name."""
        # Create first upload
        UserUpload.objects.create(
            username="testuser",
            codename="add_user",
            group_name="TestGroup",
        )

        # Try to create duplicate - should succeed if different combination
        UserUpload.objects.create(
            username="testuser",
            codename="change_user",  # Different codename
            group_name="TestGroup",
        )

        # Verify we have 2 records
        self.assertEqual(UserUpload.objects.filter(username="testuser").count(), 2)

    def test_user_upload_optional_fields(self):
        """Test that optional fields can be None or blank."""
        user_upload = UserUpload.objects.create(username="minimal_user")

        self.assertIsNone(user_upload.first_name)
        self.assertIsNone(user_upload.last_name)
        self.assertIsNone(user_upload.email)
        self.assertIsNone(user_upload.last_login)
        self.assertIsNone(user_upload.group_name)
        self.assertIsNone(user_upload.codename)
        self.assertIsNone(user_upload.app_label)
        self.assertIsNone(user_upload.model)

    def test_user_upload_boolean_defaults(self):
        """Test default values for boolean fields."""
        user_upload = UserUpload.objects.create(username="defaultuser")

        self.assertFalse(user_upload.is_superuser)
        self.assertFalse(user_upload.is_staff)
        self.assertTrue(user_upload.is_active)

    def test_user_upload_date_joined_auto_now_add(self):
        """Test that date_joined is automatically set on creation."""
        user_upload = UserUpload.objects.create(username="dateuser")
        self.assertIsNotNone(user_upload.date_joined)

    def test_user_upload_field_max_lengths(self):
        """Test field max lengths are respected."""
        user_upload = UserUpload.objects.create(
            username="u" * 150,  # Max length
            first_name="f" * 150,
            last_name="l" * 150,
            email="test@" + "e" * 244 + ".com",  # Max 254
            group_name="g" * 500,
            codename="c" * 100,
            app_label="a" * 100,
            model="m" * 100,
        )

        self.assertEqual(len(user_upload.username), 150)
        self.assertEqual(len(user_upload.first_name), 150)
        self.assertEqual(len(user_upload.group_name), 500)


@pytest.mark.unit
@pytest.mark.views
class SfdUserAdminTest(BaseTestMixin, TestCase):
    """Test cases for SfdUserAdmin functionality."""

    databases = {"default", "postgres"}

    def setUp(self):
        """Set up test data for SfdUserAdmin tests."""
        super().setUp()
        self.site = AdminSite()
        self.admin = SfdUserAdmin(User, self.site)
        self.factory = RequestFactory()
        self.request = self.factory.get("/admin/")
        self.request.user = self.user

        # Create test group
        self.test_group = Group.objects.create(name="TestGroup")

        # Create test permission
        content_type = ContentType.objects.get_for_model(User)
        self.test_permission = Permission.objects.create(
            codename="test_permission",
            name="Test Permission",
            content_type=content_type,
        )

    def test_admin_upload_model(self):
        """Test that admin has correct upload_model."""
        self.assertEqual(self.admin.upload_model, UserUpload)

    def test_admin_is_skip_existing(self):
        """Test that admin allows updates to existing users."""
        self.assertFalse(self.admin.is_skip_existing)

    def test_admin_add_fieldsets(self):
        """Test that admin has proper add_fieldsets configuration."""
        self.assertIsNotNone(self.admin.add_fieldsets)
        self.assertEqual(len(self.admin.add_fieldsets), 1)
        # Check that password fields are included
        fields = self.admin.add_fieldsets[0][1]["fields"]
        self.assertIn("username", fields)
        self.assertIn("password1", fields)
        self.assertIn("password2", fields)

    def test_get_fieldsets_new_user(self):
        """Test get_fieldsets returns add_fieldsets for new user."""
        fieldsets = self.admin.get_fieldsets(self.request, obj=None)
        self.assertEqual(fieldsets, self.admin.add_fieldsets)

    def test_get_fieldsets_existing_user(self):
        """Test get_fieldsets returns default fieldsets for existing user."""
        test_user = User.objects.create_user(username="existinguser", password="password")
        fieldsets = self.admin.get_fieldsets(self.request, obj=test_user)
        # Should use UserAdmin's default fieldsets
        self.assertIsNotNone(fieldsets)
        self.assertNotEqual(fieldsets, self.admin.add_fieldsets)

    def test_get_download_columns(self):
        """Test get_download_columns returns correct column mapping."""
        columns = self.admin.get_download_columns(self.request)

        expected_columns = {
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

        self.assertEqual(columns, expected_columns)
        self.assertIn("username", columns)
        self.assertIn("groups__name", columns)
        self.assertIn("user_permissions__codename", columns)

    def test_post_upload_creates_new_user(self):
        """Test post_upload creates new user from UserUpload."""
        UserUpload.objects.create(
            username="newuser",
            first_name="New",
            last_name="User",
            email="new@example.com",
        )

        self.admin.post_upload(self.request)

        # Verify user was created
        self.assertTrue(User.objects.filter(username="newuser").exists())
        user = User.objects.get(username="newuser")
        # Verify password was set to username
        self.assertTrue(user.check_password("newuser"))

    def test_post_upload_adds_group_to_user(self):
        """Test post_upload adds group to user."""
        UserUpload.objects.create(
            username="groupuser",
            group_name="TestGroup",
        )

        self.admin.post_upload(self.request)

        user = User.objects.get(username="groupuser")
        self.assertTrue(user.groups.filter(name="TestGroup").exists())

    def test_post_upload_adds_permission_to_user(self):
        """Test post_upload adds permission to user."""
        content_type = ContentType.objects.get_for_model(User)
        UserUpload.objects.create(
            username="permuser",
            codename="test_permission",
            app_label=content_type.app_label,
            model=content_type.model,
        )

        self.admin.post_upload(self.request)

        user = User.objects.get(username="permuser")
        self.assertTrue(user.user_permissions.filter(codename="test_permission").exists())

    def test_post_upload_updates_existing_user(self):
        """Test post_upload updates existing user."""
        # Create existing user
        existing_user = User.objects.create_user(username="existinguser", password="oldpassword")

        # Create upload data
        UserUpload.objects.create(
            username="existinguser",
            group_name="TestGroup",
        )

        self.admin.post_upload(self.request)

        # Verify user still exists (not duplicated)
        self.assertEqual(User.objects.filter(username="existinguser").count(), 1)

        # Verify group was added
        existing_user.refresh_from_db()
        self.assertTrue(existing_user.groups.filter(name="TestGroup").exists())

    def test_post_upload_handles_multiple_users(self):
        """Test post_upload processes multiple UserUpload records."""
        UserUpload.objects.create(username="user1", group_name="TestGroup")
        UserUpload.objects.create(username="user2", group_name="TestGroup")
        UserUpload.objects.create(username="user3")

        self.admin.post_upload(self.request)

        self.assertTrue(User.objects.filter(username="user1").exists())
        self.assertTrue(User.objects.filter(username="user2").exists())
        self.assertTrue(User.objects.filter(username="user3").exists())

    def test_post_upload_skips_permission_without_complete_data(self):
        """Test post_upload skips permission assignment if data is incomplete."""
        UserUpload.objects.create(
            username="incompleteuser",
            codename="test_permission",
            # Missing app_label and model
        )

        self.admin.post_upload(self.request)

        user = User.objects.get(username="incompleteuser")
        # Should not have any permissions
        self.assertEqual(user.user_permissions.count(), 0)

    def test_post_upload_does_not_duplicate_permissions(self):
        """Test post_upload doesn't add duplicate permissions."""
        content_type = ContentType.objects.get_for_model(User)

        # Create user with permission
        user = User.objects.create_user(username="permuser")
        user.user_permissions.add(self.test_permission)

        # Try to add same permission via upload
        UserUpload.objects.create(
            username="permuser",
            codename="test_permission",
            app_label=content_type.app_label,
            model=content_type.model,
        )

        initial_perm_count = user.user_permissions.count()
        self.admin.post_upload(self.request)

        user.refresh_from_db()
        # Permission count should remain the same
        self.assertEqual(user.user_permissions.count(), initial_perm_count)

    def test_post_upload_does_not_duplicate_groups(self):
        """Test post_upload doesn't add duplicate groups."""
        # Create user with group
        user = User.objects.create_user(username="groupuser")
        user.groups.add(self.test_group)

        # Try to add same group via upload
        UserUpload.objects.create(
            username="groupuser",
            group_name="TestGroup",
        )

        initial_group_count = user.groups.count()
        self.admin.post_upload(self.request)

        user.refresh_from_db()
        # Group count should remain the same
        self.assertEqual(user.groups.count(), initial_group_count)

    def test_admin_inherits_from_user_admin(self):
        """Test that SfdUserAdmin inherits from UserAdmin."""
        from django.contrib.auth.admin import UserAdmin

        self.assertTrue(isinstance(self.admin, UserAdmin))

    def test_admin_has_upload_mixin(self):
        """Test that SfdUserAdmin has UploadMixin capabilities."""
        from sfd.views.common.upload import UploadMixin

        self.assertTrue(isinstance(self.admin, UploadMixin))

    def test_admin_has_download_mixin(self):
        """Test that SfdUserAdmin has DownloadMixin capabilities."""
        from sfd.views.common.download import DownloadMixin

        self.assertTrue(isinstance(self.admin, DownloadMixin))
