from unittest.mock import Mock, patch

from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.test import TestCase

from sfd.tests.unittest import BaseTestMixin, TestEncryptedModel
from sfd.views.common.encrypted_mixin import EncryptedFieldAdminMixin, MaskedWidget


class TestEncryptedAdmin(EncryptedFieldAdminMixin, admin.ModelAdmin):
    encrypted_fields = ["name", "email"]
    # We include notes to verify non-encrypted fields are untouched
    list_display = ["id", "name", "email", "notes"]


class EncryptedFieldAdminMixinTest(BaseTestMixin, TestCase):
    """Test suite for EncryptedFieldAdminMixin."""

    databases = {"default", "postgres"}

    def setUp(self):
        super().setUp()
        self.site = admin.AdminSite()
        self.admin = TestEncryptedAdmin(TestEncryptedModel, self.site)
        self.obj = TestEncryptedModel.objects.create(name="Secret Name", email="secret@example.com", notes="Secret Notes")
        self.request = self.factory.get("/")

    def test_masked_widget(self):
        """Test MaskedWidget render method."""
        widget = MaskedWidget()
        self.assertEqual(widget.render("name", "value"), "********")

    def test_has_view_encrypted_permission(self):
        """Test permission check logic."""
        # Case 1: Superuser (True)
        self.request.user = self.superuser
        self.assertTrue(self.admin.has_view_encrypted_permission(self.request))

        # Case 2: User with specific permission (True)
        self.request.user = self.user
        # Mocking has_perm since we don't want to set up real permissions in DB
        with patch.object(self.user, "has_perm", return_value=True) as mock_perm:
            self.assertTrue(self.admin.has_view_encrypted_permission(self.request))
            mock_perm.assert_called_with("sfd.view_encrypted_fields")

        # Case 3: User without permission (False)
        self.request.user = self.user
        with patch.object(self.user, "has_perm", return_value=False):
            self.assertFalse(self.admin.has_view_encrypted_permission(self.request))

    def test_get_list_display_with_permission(self):
        """Test get_list_display returns original list when user has permission."""
        self.request.user = self.superuser
        display = self.admin.get_list_display(self.request)
        # Should be list of strings
        self.assertEqual(list(display), ["id", "name", "email", "notes"])

    def test_get_list_display_without_permission(self):
        """Test get_list_display masks encrypted fields when user lacks permission."""
        self.request.user = self.user
        with patch.object(self.admin, "has_view_encrypted_permission", return_value=False):
            display = self.admin.get_list_display(self.request)

            # Should match length
            self.assertEqual(len(display), 4)

            # ID and Notes should be untouched strings
            self.assertEqual(display[0], "id")
            self.assertEqual(display[3], "notes")

            # Name and Email should be transformed to callables
            self.assertTrue(callable(display[1]))
            self.assertTrue(callable(display[2]))

            # Check callable behavior
            masked_name = display[1]
            self.assertEqual(masked_name(self.obj), "********")
            self.assertEqual(masked_name.short_description, "name")

    def test_create_masked_callable_attributes(self):
        """Test that masked callable inherits attributes nicely."""

        # Create a method on admin to simulate a method-based list_display
        def custom_method(obj):
            return "value"

        custom_method.short_description = "Custom Label"
        self.admin.custom_method = custom_method

        masked = self.admin._create_masked_callable("custom_method")
        self.assertEqual(masked.short_description, "Custom Label")

        # Test fallback when attribute exists but no short_description
        def simple_method(obj):
            return "value"

        self.admin.simple_method = simple_method

        masked_simple = self.admin._create_masked_callable("simple_method")
        self.assertEqual(masked_simple.short_description, "simple_method")

    def test_get_object_with_permission(self):
        """Test get_object returns real data if user has permission."""
        self.request.user = self.superuser
        obj = self.admin.get_object(self.request, str(self.obj.pk))

        self.assertEqual(obj.name, "Secret Name")
        self.assertEqual(obj.email, "secret@example.com")

    def test_get_object_without_permission(self):
        """Test get_object masks data if user lacks permission."""
        self.request.user = self.user
        with patch.object(self.admin, "has_view_encrypted_permission", return_value=False):
            obj = self.admin.get_object(self.request, str(self.obj.pk))

            self.assertEqual(obj.name, "********")
            self.assertEqual(obj.email, "********")
            # Unencrypted field remains
            self.assertEqual(obj.notes, "Secret Notes")

    def test_get_form_without_permission(self):
        """Test get_form masks widget and disables field without permission."""
        self.request.user = self.user
        with patch.object(self.admin, "has_view_encrypted_permission", return_value=False):
            Form = self.admin.get_form(self.request, self.obj)
            form = Form(instance=self.obj)

            # Check name field (encrypted)
            name_field = form.fields["name"]
            self.assertIsInstance(name_field.widget, MaskedWidget)
            self.assertTrue(name_field.disabled)
            self.assertFalse(name_field.required)

            # Check notes field (not encrypted)
            notes_field = form.fields["notes"]
            self.assertNotIsInstance(notes_field.widget, MaskedWidget)

    def test_crud_permissions_without_view_permission(self):
        """Test add/change/delete permissions are denied without view encrypted permission."""
        self.request.user = self.user
        with patch.object(self.admin, "has_view_encrypted_permission", return_value=False):
            self.assertFalse(self.admin.has_add_permission(self.request))
            self.assertFalse(self.admin.has_change_permission(self.request, self.obj))
            self.assertFalse(self.admin.has_delete_permission(self.request, self.obj))

    def test_crud_permissions_with_view_permission(self):
        """Test add/change/delete permissions default to super implementation with permission."""
        self.request.user = self.superuser
        # Superuser has all permissions by default in ModelAdmin
        self.assertTrue(self.admin.has_add_permission(self.request))
        self.assertTrue(self.admin.has_change_permission(self.request, self.obj))
        self.assertTrue(self.admin.has_delete_permission(self.request, self.obj))

    def test_get_actions_removes_download(self):
        """Test that download_selected action is removed without permission."""
        self.request.user = self.user

        # Simulating actions dictionary from super().get_actions()
        actions = {
            "delete_selected": (Mock(), "delete_selected", "Delete selected"),
            "download_selected": (Mock(), "download_selected", "Download selected"),
        }

        with patch("django.contrib.admin.ModelAdmin.get_actions", return_value=actions):
            with patch.object(self.admin, "has_view_encrypted_permission", return_value=False):
                filtered_actions = self.admin.get_actions(self.request)
                self.assertNotIn("download_selected", filtered_actions)
                self.assertIn("delete_selected", filtered_actions)

    def test_changelist_view_removes_upload_url(self):
        """Test that upload_url is removed from context without permission."""
        self.request.user = self.user

        mock_response = Mock()
        mock_response.context_data = {"upload_url": "/some/url/", "other_context": "value"}

        with patch("django.contrib.admin.ModelAdmin.changelist_view", return_value=mock_response):
            with patch.object(self.admin, "has_view_encrypted_permission", return_value=False):
                response = self.admin.changelist_view(self.request)
                self.assertNotIn("upload_url", response.context_data)
                self.assertIn("other_context", response.context_data)

    def test_upload_file_permission_denied(self):
        """Test upload_file raises PermissionDenied without permission."""
        self.request.user = self.user
        with patch.object(self.admin, "has_view_encrypted_permission", return_value=False):
            with self.assertRaises(PermissionDenied):
                self.admin.upload_file(self.request)

    def test_upload_file_allowed(self):
        """Test upload_file calls super method with permission."""
        self.request.user = self.superuser
        # Verify it attempts to call super().upload_file
        # Since ModelAdmin doesn't have upload_file, calling it directly on our instance
        # (which only has it via Mixin or if we added it)
        # Actually ModelAdmin doesn't have upload_file. The mixin calls super().upload_file().
        # If the base class doesn't have it, it will raise AttributeError.
        # But commonly this mixin is mixed with UploadMixin which has it.
        # Here TestEncryptedAdmin inherits from (EncryptedFieldAdminMixin, ModelAdmin).
        # ModelAdmin does NOT have upload_file. So this call would fail if we don't mock it or add it.

        # Let's mock a class that has upload_file
        class UploadAdmin:
            def upload_file(self, request):
                return "success"

        class TestUploadEncryptedAdmin(EncryptedFieldAdminMixin, UploadAdmin, admin.ModelAdmin):
            encrypted_fields = []

        test_admin = TestUploadEncryptedAdmin(TestEncryptedModel, self.site)
        result = test_admin.upload_file(self.request)
        self.assertEqual(result, "success")

    def test_get_object_attribute_error_handling(self):
        """Test that AttributeError during masking is suppressed."""
        self.request.user = self.user

        class ReadOnlyObject:
            # We need pks for admin to work usually, but get_object might just return it
            pk = 1

            @property
            def name(self):
                return "Secret"

            # No setter for name, so setattr will raise AttributeError

        mock_obj = ReadOnlyObject()

        with patch("django.contrib.admin.ModelAdmin.get_object", return_value=mock_obj):
            with patch.object(self.admin, "has_view_encrypted_permission", return_value=False):
                # 'name' is in self.admin.encrypted_fields
                # This call should catch AttributeError and proceed
                result = self.admin.get_object(self.request, "123")

                self.assertEqual(result, mock_obj)
                self.assertEqual(result.name, "Secret")  # Remains unmasked due to error
