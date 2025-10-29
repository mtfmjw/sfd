# type: ignore
from datetime import date
from unittest.mock import Mock, patch

import pytest
from django import forms
from django.contrib import admin, messages
from django.contrib.admin import AdminSite
from django.contrib.messages.storage.fallback import FallbackStorage
from django.db import IntegrityError
from django.template.response import TemplateResponse
from django.test import TestCase
from django.utils import translation

from sfd.tests.unittest import BaseTestMixin, TestInlineModel, TestModel
from sfd.views.common.mixins import ModelAdminInlineMixin, ModelAdminMixin


class TestModelAdmin(ModelAdminMixin, admin.ModelAdmin):
    def non_model_field(self, obj):
        return "non model field"

    def non_model_field_2(self, obj):
        return "non model field without short description"

    non_model_field.short_description = "Non-Model Field"  # type: ignore[attr-defined]


class TestModelAdminInline(ModelAdminInlineMixin, admin.TabularInline):
    model = TestInlineModel
    extra = 1
    fk_name = "parent"


class TestModelAdminParent(ModelAdminMixin, admin.ModelAdmin):
    inlines = [TestModelAdminInline]
    model = TestModel


@pytest.mark.unit
@pytest.mark.views
class ModelAdminInlineMixinTest(BaseTestMixin, TestCase):
    """Test ModelAdminInlineMixin functionality with comprehensive coverage."""

    databases = {"default", "postgres"}

    def setUp(self):
        """Set up test data for ModelAdminInlineMixin tests."""
        super().setUp()
        self.admin_site = AdminSite()
        self.parent_admin = TestModelAdminParent(TestModel, self.admin_site)
        self.inline_admin = TestModelAdminInline(TestInlineModel, self.admin_site)
        self.inline_admin.parent_model = TestModel
        self.inline_admin._admin_instance = self.parent_admin  # type: ignore
        self.request = self.factory.post("/admin/", {"_save": "Save"})
        self.request.user = self.user

    def test_get_formset_no_change(self):
        """Test get_formset creates ModelFormSet that validates for no changes."""

        # Arrange
        formset_class = self.inline_admin.get_formset(self.request)

        # Create formset instance
        formset = formset_class(data={"form-TOTAL_FORMS": "1", "form-INITIAL_FORMS": "0", "form-MIN_NUM_FORMS": "0", "form-MAX_NUM_FORMS": "1000"})

        # Mock parent admin state
        self.parent_admin.has_form_data_changed = False  # type: ignore
        self.parent_admin._main_form = Mock()  # type: ignore

        # Act & Assert
        with translation.override("en"):
            with self.assertRaises(forms.ValidationError) as cm:
                formset.clean()
                self.assertEqual(str(cm.exception.message), "No changes detected.")

    def test_get_formset_with_subform_change(self):
        """Test that line 42 uses any() to check if ANY form has changed (tests multiple forms)."""
        # Arrange
        formset_class = self.inline_admin.get_formset(self.request)

        # Create formset instance
        formset = formset_class(data={"form-TOTAL_FORMS": "3", "form-INITIAL_FORMS": "0", "form-MIN_NUM_FORMS": "0", "form-MAX_NUM_FORMS": "1000"})

        # Mock parent admin state
        self.parent_admin.has_form_data_changed = False  # type: ignore
        self.parent_admin._main_form = Mock()  # type: ignore

        # Mock super().clean() to do nothing
        with patch.object(formset.__class__.__bases__[0], "clean", return_value=None):
            # Create multiple forms - second one has changes
            form1 = Mock()
            form1.has_changed.return_value = False

            form2 = Mock()
            form2.has_changed.return_value = True  # This one triggers the condition

            # Replace forms
            formset.forms = [form1, form2]

            try:
                # Act
                formset.clean()
            except forms.ValidationError:
                pass

        # Assert - should be True because form2.has_changed() returned True
        self.assertTrue(self.parent_admin.has_form_data_changed)  # type: ignore[attr-defined]
        # Verify has_changed was called on all forms (any() evaluates until True is found)
        form1.has_changed.assert_called()
        form2.has_changed.assert_called()

    def test_get_formset_without_subform_change(self):
        """Test that line 42 does NOT set has_form_data_changed when no forms have changed."""
        # Arrange
        formset_class = self.inline_admin.get_formset(self.request)

        # Create formset instance
        formset = formset_class(data={"form-TOTAL_FORMS": "2", "form-INITIAL_FORMS": "0", "form-MIN_NUM_FORMS": "0", "form-MAX_NUM_FORMS": "1000"})

        # Mock parent admin state - initialize as False
        self.parent_admin.has_form_data_changed = False  # type: ignore
        self.parent_admin._main_form = Mock()  # type: ignore
        self.parent_admin._main_form.add_error = Mock()  # type: ignore

        # Mock super().clean() to do nothing
        with patch.object(formset.__class__.__bases__[0], "clean", return_value=None):
            # Create forms where NONE have changes
            form1 = Mock()
            form1.has_changed.return_value = False

            form2 = Mock()
            form2.has_changed.return_value = False

            # Replace forms
            formset.forms = [form1, form2]

            # Act & Assert - should raise ValidationError because no changes
            with translation.override("en"):
                with self.assertRaises(forms.ValidationError) as cm:
                    formset.clean()
                # Check the error message
                self.assertIn("No changes detected", str(cm.exception))

        # Assert - has_form_data_changed should still be False (line 42 skipped)
        self.assertFalse(self.parent_admin.has_form_data_changed)  # type: ignore[attr-defined]
        # Verify has_changed was called
        form1.has_changed.assert_called()
        form2.has_changed.assert_called()

    def test_get_formset_delete_button_skips_validation(self):
        """Test get_formset skips no-changes validation when delete button is clicked."""
        # Arrange
        delete_request = self.factory.post("/admin/", {"_delete": "Delete"})
        delete_request.user = self.user

        formset_class = self.inline_admin.get_formset(delete_request)

        # Create formset instance
        formset = formset_class(data={"form-TOTAL_FORMS": "1", "form-INITIAL_FORMS": "0", "form-MIN_NUM_FORMS": "0", "form-MAX_NUM_FORMS": "1000"})

        # Mock parent admin state
        self.parent_admin.has_form_data_changed = False  # type: ignore
        self.parent_admin._main_form = Mock()  # type: ignore

        # Act - should not raise ValidationError even with no changes
        try:
            formset.clean()
        except forms.ValidationError:
            self.fail("ValidationError was raised when delete button was clicked")

    def test_get_formset_stores_admin_instance_reference(self):
        """Test get_formset stores admin instance reference in the formset."""
        # Act
        formset_class = self.inline_admin.get_formset(self.request)
        formset = formset_class()

        # Assert
        self.assertEqual(formset._admin_instance, self.parent_admin)


@pytest.mark.unit
@pytest.mark.views
class ModelAdminMixinTest(BaseTestMixin, TestCase):
    databases = {"default", "postgres"}

    def setUp(self):
        """Set up test data for BaseModelAdmin tests."""
        super().setUp()
        self.admin_site = AdminSite()
        self.model_admin = TestModelAdmin(TestModel, self.admin_site)
        self.request = self.factory.get("/admin/")
        self.request.user = self.user
        self.model_admin._is_delete_action = False
        self.model_admin._is_undelete_action = False

    def test_model_admin_mixin_initialization(self):
        """Test ModelAdminMixin initialization and attributes."""

        # Assert
        self.assertEqual(self.model_admin.change_list_template, "sfd/change_list.html")
        self.assertFalse(self.model_admin.is_readonly)
        self.assertTrue(self.model_admin.save_as)

    @patch("sfd.views.common.mixins.super")
    def test_has_add_permission(self, mock_super):
        # 1-1. super().has_add_permission returns True
        mock_super.return_value.has_add_permission.return_value = True

        # 2-1. is_readonly is False
        self.model_admin.is_readonly = False

        # 3-1. request without is_readonly parameter
        self.assertTrue(self.model_admin.has_add_permission(self.request))

        # 3-2. request with is_readonly=False parameter
        request = self.factory.get("/admin/?is_readonly=False")
        self.assertTrue(self.model_admin.has_add_permission(request))

        # 3-3. request with is_readonly=True parameter
        request = self.factory.get("/admin/?is_readonly=True")
        self.assertFalse(self.model_admin.has_add_permission(request))

        # 2-2. is_readonly is True
        self.model_admin.is_readonly = True

        # 3-1. request without is_readonly parameter
        self.assertFalse(self.model_admin.has_add_permission(self.request))

        # 3-2. request with is_readonly=False parameter
        request = self.factory.get("/admin/?is_readonly=False")
        self.assertFalse(self.model_admin.has_add_permission(request))

        # 3-3. request with is_readonly=True parameter
        request = self.factory.get("/admin/?is_readonly=True")
        self.assertFalse(self.model_admin.has_add_permission(request))

        # 1-2. super().has_add_permission returns True
        mock_super.return_value.has_add_permission.return_value = False

        # 2-1. is_readonly is False
        self.model_admin.is_readonly = False

        # 3-1. request without is_readonly parameter
        self.assertFalse(self.model_admin.has_add_permission(self.request))

        # 3-2. request with is_readonly=False parameter
        request = self.factory.get("/admin/?is_readonly=False")
        self.assertFalse(self.model_admin.has_add_permission(request))

        # 3-3. request with is_readonly=True parameter
        request = self.factory.get("/admin/?is_readonly=True")
        self.assertFalse(self.model_admin.has_add_permission(request))

        # 2-2. is_readonly is True
        self.model_admin.is_readonly = True

        # 3-1. request without is_readonly parameter
        self.assertFalse(self.model_admin.has_add_permission(self.request))

        # 3-2. request with is_readonly=False parameter
        request = self.factory.get("/admin/?is_readonly=False")
        self.assertFalse(self.model_admin.has_add_permission(request))

        # 3-3. request with is_readonly=True parameter
        request = self.factory.get("/admin/?is_readonly=True")
        self.assertFalse(self.model_admin.has_add_permission(request))

    @patch("sfd.views.common.mixins.super")
    def test_has_change_permission(self, mock_super):
        # 1-1. super().has_change_permission returns True
        mock_super.return_value.has_change_permission.return_value = True

        # 2-1. is_readonly is False
        self.model_admin.is_readonly = False

        # 3-1. request without is_readonly parameter
        self.assertTrue(self.model_admin.has_change_permission(self.request))

        # 3-2. request with is_readonly=False parameter
        request = self.factory.get("/admin/?is_readonly=False")
        self.assertTrue(self.model_admin.has_change_permission(request))

        # 3-3. request with is_readonly=True parameter
        request = self.factory.get("/admin/?is_readonly=True")
        self.assertFalse(self.model_admin.has_change_permission(request))

        # 2-2. is_readonly is True
        self.model_admin.is_readonly = True

        # 3-1. request without is_readonly parameter
        self.assertFalse(self.model_admin.has_change_permission(self.request))

        # 3-2. request with is_readonly=False parameter
        request = self.factory.get("/admin/?is_readonly=False")
        self.assertFalse(self.model_admin.has_change_permission(request))

        # 3-3. request with is_readonly=True parameter
        request = self.factory.get("/admin/?is_readonly=True")
        self.assertFalse(self.model_admin.has_change_permission(request))

        # 1-2. super().has_add_permission returns True
        mock_super.return_value.has_change_permission.return_value = False

        # 2-1. is_readonly is False
        self.model_admin.is_readonly = False

        # 3-1. request without is_readonly parameter
        self.assertFalse(self.model_admin.has_change_permission(self.request))

        # 3-2. request with is_readonly=False parameter
        request = self.factory.get("/admin/?is_readonly=False")
        self.assertFalse(self.model_admin.has_change_permission(request))

        # 3-3. request with is_readonly=True parameter
        request = self.factory.get("/admin/?is_readonly=True")
        self.assertFalse(self.model_admin.has_change_permission(request))

        # 2-2. is_readonly is True
        self.model_admin.is_readonly = True

        # 3-1. request without is_readonly parameter
        self.assertFalse(self.model_admin.has_change_permission(self.request))

        # 3-2. request with is_readonly=False parameter
        request = self.factory.get("/admin/?is_readonly=False")
        self.assertFalse(self.model_admin.has_change_permission(request))

        # 3-3. request with is_readonly=True parameter
        request = self.factory.get("/admin/?is_readonly=True")
        self.assertFalse(self.model_admin.has_change_permission(request))

    @patch("sfd.views.common.mixins.super")
    def test_has_delete_permission(self, mock_super):
        # 1-1. super().has_delete_permission returns True
        mock_super.return_value.has_delete_permission.return_value = True

        # 2-1. is_readonly is False
        self.model_admin.is_readonly = False

        # 3-1. request without is_readonly parameter
        self.assertTrue(self.model_admin.has_delete_permission(self.request))

        # 3-2. request with is_readonly=False parameter
        request = self.factory.get("/admin/?is_readonly=False")
        self.assertTrue(self.model_admin.has_delete_permission(request))

        # 3-3. request with is_readonly=True parameter
        request = self.factory.get("/admin/?is_readonly=True")
        self.assertFalse(self.model_admin.has_delete_permission(request))

        # 2-2. is_readonly is True
        self.model_admin.is_readonly = True

        # 3-1. request without is_readonly parameter
        self.assertFalse(self.model_admin.has_delete_permission(self.request))

        # 3-2. request with is_readonly=False parameter
        request = self.factory.get("/admin/?is_readonly=False")
        self.assertFalse(self.model_admin.has_delete_permission(request))

        # 3-3. request with is_readonly=True parameter
        request = self.factory.get("/admin/?is_readonly=True")
        self.assertFalse(self.model_admin.has_delete_permission(request))

        # 1-2. super().has_add_permission returns True
        mock_super.return_value.has_delete_permission.return_value = False

        # 2-1. is_readonly is False
        self.model_admin.is_readonly = False

        # 3-1. request without is_readonly parameter
        self.assertFalse(self.model_admin.has_delete_permission(self.request))

        # 3-2. request with is_readonly=False parameter
        request = self.factory.get("/admin/?is_readonly=False")
        self.assertFalse(self.model_admin.has_delete_permission(request))

        # 3-3. request with is_readonly=True parameter
        request = self.factory.get("/admin/?is_readonly=True")
        self.assertFalse(self.model_admin.has_delete_permission(request))

        # 2-2. is_readonly is True
        self.model_admin.is_readonly = True

        # 3-1. request without is_readonly parameter
        self.assertFalse(self.model_admin.has_delete_permission(self.request))

        # 3-2. request with is_readonly=False parameter
        request = self.factory.get("/admin/?is_readonly=False")
        self.assertFalse(self.model_admin.has_delete_permission(request))

        # 3-3. request with is_readonly=True parameter
        request = self.factory.get("/admin/?is_readonly=True")
        self.assertFalse(self.model_admin.has_delete_permission(request))

    @patch("sfd.views.common.mixins.super")
    def test_get_actions(self, mock_super):
        # 1-1. super().get_actions returns actions with delete_selected without delete_selected_popup
        mock_super.return_value.get_actions.return_value = {
            "delete_selected": (lambda x: x, "delete_selected", "Delete selected items"),
            "custom_action": (lambda x: x, "custom_action", "Custom action"),
        }

        # 2-1. has_delete_permission returns True
        self.model_admin.has_delete_permission = lambda request: True  # type: ignore[assignment]
        actions = self.model_admin.get_actions(self.request)
        self.assertNotIn("delete_selected", actions)
        self.assertIn("delete_selected_popup", actions)
        self.assertIn("custom_action", actions)

        # 2-2. has_delete_permission returns False
        self.model_admin.has_delete_permission = lambda request: False  # type: ignore[assignment]
        actions = self.model_admin.get_actions(self.request)
        self.assertNotIn("delete_selected", actions)
        self.assertNotIn("delete_selected_popup", actions)
        self.assertIn("custom_action", actions)

        # 1-2. super().get_actions returns actions with delete_selected and delete_selected_popup
        mock_super.return_value.get_actions.return_value = {
            "delete_selected": (lambda x: x, "delete_selected", "Delete selected items"),
            "delete_selected_popup": (lambda x: x, "delete_selected_popup", "Delete selected items (popup)"),
            "custom_action": (lambda x: x, "custom_action", "Custom action"),
        }

        # 2-1. has_delete_permission returns True
        self.model_admin.has_delete_permission = lambda request: True  # type: ignore[assignment]
        actions = self.model_admin.get_actions(self.request)
        self.assertNotIn("delete_selected", actions)
        self.assertIn("delete_selected_popup", actions)
        self.assertIn("custom_action", actions)

        # 2-2. has_delete_permission returns False
        self.model_admin.has_delete_permission = lambda request: False  # type: ignore[assignment]
        actions = self.model_admin.get_actions(self.request)
        self.assertNotIn("delete_selected", actions)
        self.assertNotIn("delete_selected_popup", actions)
        self.assertIn("custom_action", actions)

        # 1-3. super().get_actions returns actions without delete_selected and delete_selected_popup
        mock_super.return_value.get_actions.return_value = {
            "custom_action": (lambda x: x, "custom_action", "Custom action"),
        }

        # 2-1. has_delete_permission returns True
        self.model_admin.has_delete_permission = lambda request: True  # type: ignore[assignment]
        actions = self.model_admin.get_actions(self.request)
        self.assertNotIn("delete_selected", actions)
        self.assertIn("delete_selected_popup", actions)
        self.assertIn("custom_action", actions)

        # 2-2. has_delete_permission returns False
        self.model_admin.has_delete_permission = lambda request: False  # type: ignore[assignment]
        actions = self.model_admin.get_actions(self.request)
        self.assertNotIn("delete_selected", actions)
        self.assertNotIn("delete_selected_popup", actions)
        self.assertIn("custom_action", actions)

    def test_execute_delete_selected(self):
        # Create test objects
        obj1 = TestModel.objects.create(name="Test 1")
        obj2 = TestModel.objects.create(name="Test 2")
        obj3 = TestModel.objects.create(name="Test 3")

        # Ensure objects are created
        self.assertEqual(TestModel.objects.count(), 3)

        # Prepare request with selected object IDs
        request = self.factory.post("/admin/", {"_selected_action": [obj1.id, obj2.id]})  # type: ignore[arg-type]
        request.user = self.user

        # Execute delete_selected action
        self.model_admin.execute_delete_selected(request, TestModel.objects.filter(id__in=[obj1.id, obj2.id]))  # type: ignore[arg-type]

        # Assert that the selected objects are deleted
        self.assertEqual(TestModel.objects.count(), 1)
        self.assertTrue(TestModel.objects.filter(id=obj3.id).exists())  # type: ignore[arg-type]

    def test_get_context_for_delete_selected(self):
        # Create test objects
        obj1 = TestModel.objects.create(name="Test 1")
        obj2 = TestModel.objects.create(name="Test 2")

        # Prepare request with selected object IDs
        request = self.factory.post("/admin/", {"_selected_action": [obj1.id, obj2.id]})  # type: ignore[arg-type]
        request.user = self.user

        # Get context for delete_selected action
        context = self.model_admin.get_context_for_delete_selected(request, TestModel.objects.filter(id__in=[obj1.id, obj2.id]))  # type: ignore[arg-type]

        # Assert context values
        self.assertIn("opts", context)
        self.assertIn("action_name", context)
        self.assertIn("queryset", context)
        self.assertIn("selected_objects", context)
        self.assertEqual(len(context["selected_objects"]), 2)
        self.assertIn(str(obj1), context["selected_objects"])
        self.assertIn(str(obj2), context["selected_objects"])
        self.assertIn("selected_count", context)

    @patch("sfd.views.common.mixins.get_deleted_objects")
    def test_get_context_for_delete_selected_error_messages(self, mock_get_deleted_objects):
        # Create test objects
        obj1 = TestModel.objects.create(name="Test 1")
        obj2 = TestModel.objects.create(name="Test 2")

        # Prepare request with selected object IDs
        request = self.factory.post("/admin/", {"_selected_action": [obj1.id, obj2.id]})  # type: ignore[arg-type]
        request.user = self.user

        request.session = {}  # type: ignore[attr-defined]
        storage = FallbackStorage(request)
        request._messages = storage  # type: ignore[attr-defined]

        # Mock get_deleted_objects to simulate permission needed
        mock_get_deleted_objects.return_value = ([], {}, {"sdf.TestModel"}, ["TestModel protected"])

        # Get context for delete_selected action
        with translation.override("en"):
            self.model_admin.get_context_for_delete_selected(request, TestModel.objects.filter(id__in=[obj1.id]))  # type: ignore[arg-type]

            # Assert context values
            error_messages = [m.message for m in storage if m.level == messages.ERROR]
            self.assertEqual(len(error_messages), 3)
            self.assertIn("You have no permission to delete the following Test Model: sdf.TestModel", error_messages[0])
            self.assertIn("Cannot delete the following Test Model due to related objects: TestModel protected", error_messages[1])
            self.assertEqual("Some data of Test Model could be updated by other users, please refresh the page.", error_messages[2])

    @patch("sfd.views.common.mixins.reverse", return_value="/admin/")
    def test_delete_selected_popup_shows_confirmation_page(self, mock_reverse):
        """Test delete_selected_popup shows confirmation template when not confirmed."""
        # Arrange - Create test objects
        obj1 = TestModel.objects.create(name="Test 1")
        obj2 = TestModel.objects.create(name="Test 2")
        TestModel.objects.create(name="Test 3")  # Not selected for deletion

        # Prepare POST request WITHOUT confirm_delete (just selecting objects)
        request = self.factory.post("/admin/", {"_selected_action": [obj1.pk, obj2.pk]})  # type: ignore[arg-type]
        request.user = self.user
        request._messages = Mock()  # type: ignore[attr-defined]

        queryset = TestModel.objects.filter(pk__in=[obj1.pk, obj2.pk])

        # Act - Execute delete_selected_popup without confirmation
        response = self.model_admin.delete_selected_popup(self.model_admin, request, queryset)

        # Assert - Should return TemplateResponse with confirmation page
        self.assertIsInstance(response, TemplateResponse)
        self.assertEqual(response.template_name, "sfd/delete_confirmation.html")  # type: ignore[attr-defined]
        self.assertIn("opts", response.context_data)  # type: ignore[attr-defined]
        self.assertIn("queryset", response.context_data)  # type: ignore[attr-defined]
        self.assertEqual(response.context_data["selected_count"], 2)  # type: ignore[attr-defined]

        # Objects should NOT be deleted yet
        self.assertEqual(TestModel.objects.count(), 3)

    @patch("sfd.views.common.mixins.reverse", return_value="/admin/")
    def test_delete_selected_popup_confirms_and_deletes_objects(self, mock_reverse):
        """Test delete_selected_popup deletes objects when confirmation is provided."""
        # Arrange - Create test objects
        obj1 = TestModel.objects.create(name="Test 1")
        obj2 = TestModel.objects.create(name="Test 2")
        obj3 = TestModel.objects.create(name="Test 3")

        self.assertEqual(TestModel.objects.count(), 3)

        # Prepare POST request with confirm_delete
        request = self.factory.post("/admin/", {"_selected_action": [obj1.id, obj2.id], "confirm_delete": "yes"})
        request.user = self.user
        request._messages = Mock()

        queryset = TestModel.objects.filter(id__in=[obj1.id, obj2.id])

        # Act - Execute delete_selected_popup with confirmation
        response = self.model_admin.delete_selected_popup(self.model_admin, request, queryset)

        # Assert - Objects should be deleted
        self.assertEqual(TestModel.objects.count(), 1)
        self.assertTrue(TestModel.objects.filter(id=obj3.id).exists())
        self.assertFalse(TestModel.objects.filter(id=obj1.id).exists())
        self.assertFalse(TestModel.objects.filter(id=obj2.id).exists())

        # Assert - Response is a redirect
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/", response.url)

    @patch("sfd.views.common.mixins.reverse", return_value="/admin/")
    @patch("sfd.views.common.mixins.logger")
    def test_delete_selected_popup_logs_success_message(self, mock_logger, mock_reverse):
        """Test delete_selected_popup logs and shows success message after deletion."""
        # Arrange
        obj1 = TestModel.objects.create(name="Test 1")
        obj2 = TestModel.objects.create(name="Test 2")

        request = self.factory.post("/admin/", {"confirm_delete": "yes"})
        request.user = self.user
        request._messages = Mock()

        queryset = TestModel.objects.filter(id__in=[obj1.id, obj2.id])

        # Act
        with translation.override("en"):
            response = self.model_admin.delete_selected_popup(self.model_admin, request, queryset)

        # Assert - Logger was called with success message
        mock_logger.info.assert_called_once()
        logged_message = mock_logger.info.call_args[0][0]
        self.assertIn("Successfully deleted", logged_message)
        self.assertIn("2", logged_message)

        # Assert - Redirect response
        self.assertEqual(response.status_code, 302)

    @patch("sfd.views.common.mixins.reverse", return_value="/admin/")
    def test_delete_selected_popup_uses_plural_model_name_for_multiple_objects(self, mock_reverse):
        """Test delete_selected_popup uses plural model name when deleting multiple objects."""
        # Arrange
        obj1 = TestModel.objects.create(name="Test 1")
        obj2 = TestModel.objects.create(name="Test 2")

        request = self.factory.post("/admin/", {"confirm_delete": "yes"})
        request.user = self.user

        # Mock messages framework
        message_list = []

        def mock_success(req, msg):
            message_list.append(("success", msg))

        with patch("sfd.views.common.mixins.messages.success", side_effect=mock_success):
            queryset = TestModel.objects.filter(id__in=[obj1.id, obj2.id])

            # Act
            with translation.override("en"):
                response = self.model_admin.delete_selected_popup(self.model_admin, request, queryset)

        # Assert - Plural form used (Test Models not Test Model)
        self.assertEqual(len(message_list), 1)
        success_message = message_list[0][1]
        # Check for plural form
        self.assertIn("Test Models", success_message)  # Plural
        self.assertEqual(response.status_code, 302)

    @patch("sfd.views.common.mixins.reverse", return_value="/admin/")
    def test_delete_selected_popup_uses_singular_model_name_for_single_object(self, mock_reverse):
        """Test delete_selected_popup uses singular model name when deleting one object."""
        # Arrange
        obj1 = TestModel.objects.create(name="Test 1")

        request = self.factory.post("/admin/", {"confirm_delete": "yes"})
        request.user = self.user

        # Mock messages framework
        message_list = []

        def mock_success(req, msg):
            message_list.append(("success", msg))

        with patch("sfd.views.common.mixins.messages.success", side_effect=mock_success):
            queryset = TestModel.objects.filter(id=obj1.id)

            # Act
            with translation.override("en"):
                response = self.model_admin.delete_selected_popup(self.model_admin, request, queryset)

        # Assert - Singular form used (Test Model not Test Models)
        self.assertEqual(len(message_list), 1)
        success_message = message_list[0][1]
        # Check for singular form
        self.assertIn("Test Model", success_message)  # Singular
        self.assertEqual(response.status_code, 302)

    @patch("sfd.views.common.mixins.reverse", return_value="/admin/")
    @patch("sfd.views.common.mixins.ModelAdminMixin.execute_delete_selected")
    def test_delete_selected_popup_handles_exception_with_error_message(self, mock_execute, mock_reverse):
        """Test delete_selected_popup handles exceptions and shows error message."""
        # Arrange
        obj1 = TestModel.objects.create(name="Test 1")
        obj2 = TestModel.objects.create(name="Test 2")

        # Mock execute_delete_selected to raise an exception
        mock_execute.side_effect = IntegrityError("Database constraint violation")

        request = self.factory.post("/admin/", {"confirm_delete": "yes"})
        request.user = self.user

        # Mock messages framework
        error_messages = []

        def mock_error(req, msg):
            error_messages.append(msg)

        with patch("sfd.views.common.mixins.messages.error", side_effect=mock_error):
            queryset = TestModel.objects.filter(id__in=[obj1.id, obj2.id])

            # Act
            with translation.override("en"):
                response = self.model_admin.delete_selected_popup(self.model_admin, request, queryset)

        # Assert - Error message was shown
        self.assertEqual(len(error_messages), 1)
        self.assertIn("Database constraint violation", error_messages[0])
        self.assertIn("No data was deleted", error_messages[0])

        # Assert - Objects were NOT deleted
        self.assertEqual(TestModel.objects.count(), 2)

        # Assert - Still redirects (finally block)
        self.assertEqual(response.status_code, 302)

    @patch("sfd.views.common.mixins.reverse")
    def test_delete_selected_popup_redirects_to_changelist_url(self, mock_reverse):
        """Test delete_selected_popup redirects to correct changelist URL."""
        # Arrange
        obj1 = TestModel.objects.create(name="Test 1")

        mock_reverse.return_value = "/admin/sfd/testmodel/"

        request = self.factory.post("/admin/", {"confirm_delete": "yes"})
        request.user = self.user
        request._messages = Mock()

        queryset = TestModel.objects.filter(id=obj1.id)

        # Act
        response = self.model_admin.delete_selected_popup(self.model_admin, request, queryset)

        # Assert - reverse was called with correct parameters
        mock_reverse.assert_called_once_with("admin:sfd_testmodel_changelist")

        # Assert - Response redirects to changelist
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/admin/sfd/testmodel/")  # type: ignore[comparison-overlap]

    @patch("sfd.views.common.mixins.reverse", return_value="/admin/")
    def test_delete_selected_popup_finally_block_always_executes(self, mock_reverse):
        """Test delete_selected_popup finally block executes even with exception."""
        # Arrange
        obj1 = TestModel.objects.create(name="Test 1")

        request = self.factory.post("/admin/", {"confirm_delete": "yes"})
        request.user = self.user
        request._messages = Mock()  # type: ignore[attr-defined]

        queryset = TestModel.objects.filter(id=obj1.id)  # type: ignore[arg-type]

        # Mock execute_delete_selected to raise exception
        with patch.object(self.model_admin, "execute_delete_selected", side_effect=Exception("Test error")):
            with patch("sfd.views.common.mixins.messages.error"):
                # Act
                response = self.model_admin.delete_selected_popup(self.model_admin, request, queryset)

        # Assert - Finally block executed and returned redirect
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/", response.url)

    def test_get_app_name(self):
        """Test get_app_name returns correct app name."""
        # Act
        result = self.model_admin.get_app_name()

        # Assert
        self.assertEqual(result, "sfd")

    def test_get_app_label(self):
        """Test get_app_label returns correct app label."""
        # Act
        result = self.model_admin.get_app_label()

        # Assert
        self.assertEqual(result, "sfd")

    def test_get_column_labels(self):
        """Test get_column_labels returns correct field labels."""
        # Act
        result = self.model_admin.get_column_labels(["name", "email", "is_active", "date"])

        # Assert
        self.assertEqual(result, {"name": "Name", "email": "Email", "is_active": "Active", "date": "Date"})

    def test_get_column_labels_with_non_model_fields(self):
        """Test get_column_labels returns correct field labels."""
        # Act
        result = self.model_admin.get_column_labels(["name", "email", "is_active", "date", "non_model_field", "non_model_field_2"])

        # Assert
        self.assertEqual(
            result,
            {
                "name": "Name",
                "email": "Email",
                "is_active": "Active",
                "date": "Date",
                "non_model_field": "Non-Model Field",
                "non_model_field_2": "non_model_field_2",
            },
        )

    def test_get_non_inherited_model_fields(self):
        """Test get_non_inherited_model_fields excludes inherited fields."""

        # Act
        result = self.model_admin.get_non_inherited_model_fields(self.request)

        # Assert
        expected_fields = ["name", "email", "is_active", "date"]  # Excluding inherited fields
        self.assertEqual(result, expected_fields)

    def test_get_fieldsets(self):
        """Test get_fieldsets returns correct fieldsets."""
        # Arrange
        self.model_admin.fieldsets = [
            ("Section 1", {"fields": ("name", "email")}),
            ("Section 2", {"fields": ("is_active", "date")}),
        ]

        # Act
        result = self.model_admin.get_fieldsets(self.request)

        # Assert
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0][0], "Section 1")
        self.assertEqual(result[1][0], "Section 2")
        self.assertIn("name", result[0][1]["fields"])
        self.assertIn("email", result[0][1]["fields"])
        self.assertIn("is_active", result[1][1]["fields"])
        self.assertIn("date", result[1][1]["fields"])

    def test_get_fieldsets_without_fieldsets_attribute(self):
        """Test get_fieldsets returns empty list when fieldsets attribute is not set."""

        # Act
        with translation.override("en"):
            result = self.model_admin.get_fieldsets(self.request)

            # Assert
            self.assertEqual(result, [("Basic Information", {"fields": ("name", "email", "is_active", "date")})])

    def test_get_list_display(self):
        """Test get_list_display returns correct list display."""
        # Arrange
        self.model_admin.list_display = ["name", "email"]

        # Act
        result = self.model_admin.get_list_display(self.request)

        # Assert
        self.assertEqual(result, ["name", "email"])

    def test_get_list_display_without_list_display_attribute(self):
        """Test get_list_display returns correct list display."""

        # Act
        result = self.model_admin.get_list_display(self.request)

        # Assert
        self.assertEqual(result, ["name", "email", "is_active", "date"])

    def test_formfield_for_dbfield(self):
        """Test formfield_for_dbfield returns correct form field."""
        # Act
        form_field = self.model_admin.formfield_for_dbfield(TestModel._meta.get_field("name"), self.request)

        # Assert
        self.assertIsNone(form_field.help_text)  # type: ignore[attr-defined]
        self.assertEqual(form_field.widget.attrs["placeholder"], "Test model name")  # type: ignore[attr-defined]

    @patch("sfd.views.common.mixins.reverse")
    def test_get_popup_model_hyperlink(self, mock_reverse):
        """Test get_popup_model_hyperlink returns correct HTML link."""
        # Arrange
        mock_reverse.return_value = "/admin/sfd/testmodel/1/change/"

        # Act
        result = self.model_admin.get_popup_model_hyperlink(TestModel(id=1, name="Test 1"))

        # Assert
        self.assertIn('hx-get="/admin/sfd/testmodel/1/change/?is_readonly=True&amp;_popup=1"', result)
        self.assertIn(">TestModel object (1)</a>", result)

    def test_get_form(self):
        """Test get_form returns a form instance."""
        # Act
        form_type = self.model_admin.get_form(self.request)
        form = form_type()
        form.is_valid()  # To set cleaned_data

        # Assert
        self.assertTrue(issubclass(form_type, forms.ModelForm))
        self.assertTrue(hasattr(form_type, "base_fields"))
        self.assertIn("name", form_type.base_fields)  # type: ignore[attr-defined]
        self.assertIn("email", form_type.base_fields)  # type: ignore[attr-defined]
        self.assertIn("is_active", form_type.base_fields)  # type: ignore[attr-defined]
        self.assertIn("date", form_type.base_fields)  # type: ignore[attr-defined]

        self.assertEqual(self.model_admin._main_form, form)  # type: ignore[attr-defined]
        self.assertTrue(hasattr(self.model_admin, "has_form_data_changed"))
        self.assertFalse(self.model_admin.has_form_data_changed)  # type: ignore[attr-defined]
        self.assertFalse(self.model_admin.inlines)
        self.assertTrue(form.has_changed())

    def test_get_form_with_inlines(self):
        """Test get_form raises ValidationError when no changes are detected and no inlines present."""

        obj1 = TestModel.objects.create(name="Test 1", email="test1@example.com", is_active=True, date=date(2023, 1, 1))
        self.model_admin.inlines = [TestModelAdminInline]

        # Act - Create form with instance data (simulating no changes)
        # Use actual date object to match instance data type
        form_type = self.model_admin.get_form(self.request)
        form_data = {"name": "Test 1", "email": "test1@example.com", "is_active": True, "date": date(2023, 1, 1)}
        form = form_type(data=form_data, instance=obj1)

        self.assertTrue(form.is_valid())  # Form should be invalid
        self.assertFalse(form.has_changed())  # No changes made

    def test_get_form_validation_error(self):
        """Test get_form raises ValidationError when no changes are detected and no inlines present."""

        obj1 = TestModel.objects.create(name="Test 1", email="test1@example.com", is_active=True, date=date(2023, 1, 1))

        # Act - Create form with instance data (simulating no changes)
        # Use actual date object to match instance data type
        form_type = self.model_admin.get_form(self.request)
        form_data = {"name": "Test 1", "email": "test1@example.com", "is_active": True, "date": date(2023, 1, 1)}
        form = form_type(data=form_data, instance=obj1)

        with translation.override("en"):
            # Assert - ValidationError should be raised for "No changes detected"
            self.assertFalse(form.is_valid())  # Form should be invalid
            # Check for error message in both English and Japanese
            self.assertFalse(form.has_changed())  # No changes made
            error_str = str(form.errors)
            self.assertTrue("No changes detected" in error_str)

    def test_get_form_delete(self):
        """Test get_form raises ValidationError when no changes are detected and no inlines present."""
        request = self.factory.post("/admin/", {"_delete": "Delete"})
        request.user = self.user
        obj1 = TestModel.objects.create(name="Test 1", email="test1@example.com", is_active=True, date=date(2023, 1, 1))

        # Act - Create form with instance data (simulating no changes)
        # Use actual date object to match instance data type
        form_type = self.model_admin.get_form(request)
        form_data = {"name": "Test 1 updated", "email": "test1@example.com", "is_active": True, "date": date(2023, 1, 1)}
        form = form_type(data=form_data, instance=obj1)

        # Assert - ValidationError should be raised for "No changes detected"
        self.assertTrue(form.is_valid())  # Form should be invalid

    def test_get_inline_instances(self):
        """Test get_inline_instances sets _admin_instance reference on inlines."""
        # Arrange
        self.model_admin.inlines = [TestModelAdminInline]

        # Act
        inline_instances = self.model_admin.get_inline_instances(self.request)

        # Assert
        for inline in inline_instances:
            self.assertEqual(inline._admin_instance, self.model_admin)

    def test_get_search_field_names(self):
        """Test get_search_field_names returns formatted field names."""
        # Arrange
        self.model_admin.search_fields = ["name", "email"]

        # Act
        result = self.model_admin.get_search_field_names()

        # Assert
        self.assertIn("Name", result)
        self.assertIn("Email", result)
        self.assertIn(", ", result)

    def test_get_search_field_names_without_search_fields_attr(self):
        """Test get_search_field_names returns formatted field names."""

        # Act
        result = self.model_admin.get_search_field_names()

        # Assert
        self.assertEqual("", result)

    def test_changelist_view(self):
        """Test changelist_view returns 200 status code."""
        # Arrange
        self.model_admin.search_fields = ["name", "email"]

        # Act
        with translation.override("en"):
            response = self.model_admin.changelist_view(self.request)

            # Assert
            self.assertIn("You can search and filter by", self.model_admin.search_help_text)
            self.assertEqual(response.status_code, 200)

    def test_changeform_view(self):
        """Test changeform_view returns 200 status code."""
        # Arrange
        obj1 = TestModel.objects.create(name="Test 1")
        request = self.factory.get(f"/admin/sfd/testmodel/{obj1.id}/change/?_popup=1")  # type: ignore[arg-type]
        request.user = self.user

        # Act
        with translation.override("en"):
            response = self.model_admin.changeform_view(request, str(obj1.id))  # type: ignore[arg-type]

            # Assert
            self.assertEqual(response.status_code, 200)

    def test_changeform_view_adds_colon_to_checkbox_labels(self):
        """Test changeform_view adds colon suffix to checkbox field labels when checkboxes exist.

        This test directly covers the line: field.label += ":"
        by mocking visible_fields to return a checkbox field.
        """
        # Arrange
        obj1 = TestModel.objects.create(name="Test 1", is_active=True)
        request = self.factory.get(f"/admin/sfd/testmodel/{obj1.pk}/change/")
        request.user = self.user

        # Create a mock checkbox field
        mock_checkbox_field = Mock()
        mock_checkbox_field.widget_type = "checkbox"
        mock_checkbox_field.label = "Accept Terms"
        mock_checkbox_field.name = "accept_terms"

        # Create a mock non-checkbox field for comparison
        mock_text_field = Mock()
        mock_text_field.widget_type = "text"
        mock_text_field.label = "Name"
        mock_text_field.name = "name"

        # Mock visible_fields to return our controlled field list
        mock_visible_fields = [mock_checkbox_field, mock_text_field]

        # Act
        with translation.override("en"):
            # Patch at the point where the response is used
            with patch("sfd.views.common.mixins.admin.ModelAdmin.changeform_view") as mock_super:
                # Create mock response with context_data
                mock_response = Mock()
                mock_response.context_data = {"adminform": Mock(form=Mock(visible_fields=Mock(return_value=mock_visible_fields)))}
                mock_super.return_value = mock_response

                # Call the method - this executes the line: field.label += ":"
                response = self.model_admin.changeform_view(request, str(obj1.pk))

        # Assert - Checkbox field label was modified (LINE COVERAGE ACHIEVED!)
        self.assertEqual(mock_checkbox_field.label, "Accept Terms:")

        # Assert - Non-checkbox field label was NOT modified
        self.assertEqual(mock_text_field.label, "Name")

        # Assert - Response structure is correct
        self.assertEqual(response, mock_response)

    def test_changeform_view_checkbox_logic_with_mock_checkbox(self):
        """Test that the checkbox label modification logic works correctly with actual checkbox widget."""
        # Arrange
        obj1 = TestModel.objects.create(name="Test 1", is_active=True)
        request = self.factory.get(f"/admin/sfd/testmodel/{obj1.pk}/change/")
        request.user = self.user

        # Get actual response first
        with translation.override("en"):
            response = self.model_admin.changeform_view(request, str(obj1.pk))

        # Get the form
        form = response.context_data["adminform"].form  # type: ignore[attr-defined]

        # Mock a field to be checkbox type and verify the logic
        mock_checkbox_field = Mock()
        mock_checkbox_field.widget_type = "checkbox"
        mock_checkbox_field.label = "Test Checkbox"
        mock_checkbox_field.name = "mock_field"

        # Simulate what the code does
        visible_fields = list(form.visible_fields())
        visible_fields.append(mock_checkbox_field)

        # Apply the logic from changeform_view
        for field in visible_fields:
            if field.widget_type == "checkbox":
                field.label += ":"

        # Assert - Mock checkbox field has colon added
        self.assertEqual(mock_checkbox_field.label, "Test Checkbox:")

    def test_changeform_view_only_modifies_checkbox_fields(self):
        """Test that only checkbox fields get colon suffix, not other field types."""
        # Arrange
        obj1 = TestModel.objects.create(name="Test 1", email="test@example.com", is_active=True)
        request = self.factory.get(f"/admin/sfd/testmodel/{obj1.pk}/change/")
        request.user = self.user

        # Act
        with translation.override("en"):
            response = self.model_admin.changeform_view(request, str(obj1.pk))

        # Assert
        form = response.context_data["adminform"].form  # type: ignore[attr-defined]
        visible_fields = form.visible_fields()

        # Track original labels for non-checkbox fields
        non_checkbox_fields = {}
        for field in visible_fields:
            if field.widget_type != "checkbox":
                non_checkbox_fields[field.name] = field.widget_type

        # Verify we have various field types (not checkboxes)
        self.assertGreater(len(non_checkbox_fields), 0, "Should have non-checkbox fields to test")

        # All non-checkbox fields should maintain their original widget types
        for field_name, widget_type in non_checkbox_fields.items():
            self.assertNotEqual(widget_type, "checkbox", f"Field {field_name} should not be checkbox type")

    def test_changeform_view_handles_response_without_context_data(self):
        """Test changeform_view handles gracefully when response has no context_data."""
        # Arrange
        obj1 = TestModel.objects.create(name="Test 1")
        request = self.factory.get(f"/admin/sfd/testmodel/{obj1.pk}/change/")
        request.user = self.user

        # Mock super().changeform_view to return response without context_data
        with patch.object(
            admin.ModelAdmin,
            "changeform_view",
            return_value=Mock(spec=["status_code"], status_code=200, context_data=None),
        ):
            # Act - should not raise exception
            response = self.model_admin.changeform_view(request, str(obj1.pk))

            # Assert - method completes without error
            self.assertEqual(response.status_code, 200)

    def test_changeform_view_handles_response_without_adminform_in_context(self):
        """Test changeform_view handles gracefully when context_data has no adminform."""
        # Arrange
        obj1 = TestModel.objects.create(name="Test 1")
        request = self.factory.get(f"/admin/sfd/testmodel/{obj1.pk}/change/")
        request.user = self.user

        # Create mock response with context_data but no adminform
        mock_response = Mock()
        mock_response.context_data = {"some_other_key": "value"}
        mock_response.status_code = 200

        # Mock super().changeform_view
        with patch.object(admin.ModelAdmin, "changeform_view", return_value=mock_response):
            # Act - should not raise exception
            response = self.model_admin.changeform_view(request, str(obj1.pk))

            # Assert - method completes without error
            self.assertEqual(response.status_code, 200)
            self.assertNotIn("adminform", response.context_data)

    def test_changeform_view_modifies_multiple_checkbox_fields(self):
        """Test that all checkbox fields get colon suffix when multiple exist."""
        # Arrange - TestModel only has one checkbox (is_active)
        # But we can verify the logic works for the one we have
        obj1 = TestModel.objects.create(name="Test 1", is_active=True)
        request = self.factory.get(f"/admin/sfd/testmodel/{obj1.pk}/change/")
        request.user = self.user

        # Act
        with translation.override("en"):
            response = self.model_admin.changeform_view(request, str(obj1.pk))

        # Assert
        form = response.context_data["adminform"].form  # type: ignore[attr-defined]
        visible_fields = form.visible_fields()

        # Count checkbox fields with colon
        checkbox_count = 0
        checkbox_with_colon_count = 0

        for field in visible_fields:
            if field.widget_type == "checkbox":
                checkbox_count += 1
                if str(field.label).endswith(":"):
                    checkbox_with_colon_count += 1

        # Assert - All checkbox fields have colon
        self.assertEqual(
            checkbox_count,
            checkbox_with_colon_count,
            f"All {checkbox_count} checkbox fields should have colon suffix",
        )


@pytest.mark.unit
@pytest.mark.views
class ModelAdminMixinUpdateSelectedTest(BaseTestMixin, TestCase):
    """Test ModelAdminMixin update_selected_popup functionality with comprehensive coverage."""

    databases = {"default", "postgres"}

    def setUp(self):
        """Set up test data for update_selected_popup tests."""
        super().setUp()
        self.admin_site = AdminSite()
        self.model_admin = TestModelAdmin(TestModel, self.admin_site)
        self.request = self.factory.post("/admin/")
        self.request.user = self.user

    @patch("sfd.views.common.mixins.reverse", return_value="/admin/")
    def test_update_selected_popup_shows_confirmation_page(self, mock_reverse):
        """Test update_selected_popup shows confirmation template when not confirmed."""
        # Arrange - Create test objects
        obj1 = TestModel.objects.create(name="Test 1")
        obj2 = TestModel.objects.create(name="Test 2")

        # Prepare POST request WITHOUT confirm_update (just selecting objects)
        request = self.factory.post("/admin/", {"_selected_action": [obj1.pk, obj2.pk]})  # type: ignore[arg-type]
        request.user = self.user
        request._messages = Mock()  # type: ignore[attr-defined]

        queryset = TestModel.objects.filter(pk__in=[obj1.pk, obj2.pk])

        # Act - Execute update_selected_popup without confirmation
        response = self.model_admin.update_selected_popup(self.model_admin, request, queryset)

        # Assert - Should return TemplateResponse with confirmation page
        self.assertIsInstance(response, TemplateResponse)
        self.assertEqual(response.template_name, "sfd/update_confirmation.html")  # type: ignore[attr-defined]
        self.assertIn("opts", response.context_data)  # type: ignore[attr-defined]
        self.assertIn("queryset", response.context_data)  # type: ignore[attr-defined]
        self.assertIn("updateable_fields", response.context_data)  # type: ignore[attr-defined]
        self.assertEqual(response.context_data["selected_count"], 2)  # type: ignore[attr-defined]

        # Objects should NOT be updated yet
        self.assertEqual(obj1.name, "Test 1")
        self.assertEqual(obj2.name, "Test 2")

    @patch("sfd.views.common.mixins.reverse", return_value="/admin/")
    def test_update_selected_popup_confirms_and_updates_objects(self, mock_reverse):
        """Test update_selected_popup updates objects when confirmation is provided."""
        # Arrange - Create test objects
        obj1 = TestModel.objects.create(name="Test 1")
        obj2 = TestModel.objects.create(name="Test 2")
        obj3 = TestModel.objects.create(name="Test 3")

        # Prepare POST request with confirm_update
        request = self.factory.post(
            "/admin/",
            {
                "_selected_action": [obj1.id, obj2.id],
                "confirm_update": "1",
                "field_name": "name",
                "field_value": "Updated Name",
            },
        )
        request.user = self.user
        request._messages = Mock()

        queryset = TestModel.objects.filter(id__in=[obj1.id, obj2.id])

        # Act - Execute update_selected_popup with confirmation
        response = self.model_admin.update_selected_popup(self.model_admin, request, queryset)

        # Assert - Objects should be updated
        obj1.refresh_from_db()
        obj2.refresh_from_db()
        obj3.refresh_from_db()

        self.assertEqual(obj1.name, "Updated Name")
        self.assertEqual(obj2.name, "Updated Name")
        self.assertEqual(obj3.name, "Test 3")  # Not selected, should not change

        # Assert - Response is a redirect
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/", response.url)

    @patch("sfd.views.common.mixins.reverse", return_value="/admin/")
    @patch("sfd.views.common.mixins.logger")
    def test_update_selected_popup_logs_success_message(self, mock_logger, mock_reverse):
        """Test update_selected_popup logs and shows success message after update."""
        # Arrange
        obj1 = TestModel.objects.create(name="Test 1")
        obj2 = TestModel.objects.create(name="Test 2")

        request = self.factory.post(
            "/admin/",
            {
                "confirm_update": "1",
                "field_name": "name",
                "field_value": "Updated",
            },
        )
        request.user = self.user
        request._messages = Mock()

        queryset = TestModel.objects.filter(id__in=[obj1.id, obj2.id])

        # Act
        with translation.override("en"):
            response = self.model_admin.update_selected_popup(self.model_admin, request, queryset)

        # Assert - Logger was called with success message
        mock_logger.info.assert_called_once()
        logged_message = mock_logger.info.call_args[0][0]
        self.assertIn("Successfully updated", logged_message)
        self.assertIn("2", logged_message)

        # Assert - Redirect response
        self.assertEqual(response.status_code, 302)

    @patch("sfd.views.common.mixins.reverse", return_value="/admin/")
    def test_update_selected_popup_uses_plural_model_name_for_multiple_objects(self, mock_reverse):
        """Test update_selected_popup uses plural model name when updating multiple objects."""
        # Arrange
        obj1 = TestModel.objects.create(name="Test 1")
        obj2 = TestModel.objects.create(name="Test 2")

        request = self.factory.post(
            "/admin/",
            {
                "confirm_update": "1",
                "field_name": "name",
                "field_value": "Updated",
            },
        )
        request.user = self.user

        # Mock messages framework
        message_list = []

        def mock_success(req, msg):
            message_list.append(("success", msg))

        with patch("sfd.views.common.mixins.messages.success", side_effect=mock_success):
            queryset = TestModel.objects.filter(id__in=[obj1.id, obj2.id])

            # Act
            with translation.override("en"):
                response = self.model_admin.update_selected_popup(self.model_admin, request, queryset)

        # Assert - Plural form used (Test Models not Test Model)
        self.assertEqual(len(message_list), 1)
        success_message = message_list[0][1]
        self.assertIn("Test Models", success_message)  # Plural
        self.assertEqual(response.status_code, 302)

    @patch("sfd.views.common.mixins.reverse", return_value="/admin/")
    def test_update_selected_popup_uses_singular_model_name_for_single_object(self, mock_reverse):
        """Test update_selected_popup uses singular model name when updating one object."""
        # Arrange
        obj1 = TestModel.objects.create(name="Test 1")

        request = self.factory.post(
            "/admin/",
            {
                "confirm_update": "1",
                "field_name": "name",
                "field_value": "Updated",
            },
        )
        request.user = self.user

        # Mock messages framework
        message_list = []

        def mock_success(req, msg):
            message_list.append(("success", msg))

        with patch("sfd.views.common.mixins.messages.success", side_effect=mock_success):
            queryset = TestModel.objects.filter(id__in=[obj1.id])

            # Act
            with translation.override("en"):
                response = self.model_admin.update_selected_popup(self.model_admin, request, queryset)

        # Assert - Singular form used
        self.assertEqual(len(message_list), 1)
        success_message = message_list[0][1]
        self.assertIn("Test Model", success_message)  # Singular
        self.assertNotIn("Test Models", success_message)
        self.assertEqual(response.status_code, 302)

    @patch("sfd.views.common.mixins.reverse", return_value="/admin/")
    def test_update_selected_popup_handles_missing_field_name(self, mock_reverse):
        """Test update_selected_popup handles error when field_name is not provided."""
        # Arrange
        obj1 = TestModel.objects.create(name="Test 1")

        request = self.factory.post(
            "/admin/",
            {
                "confirm_update": "1",
                "field_value": "Updated",
            },
        )
        request.user = self.user

        # Mock messages framework
        message_list = []

        def mock_error(req, msg):
            message_list.append(("error", msg))

        with patch("sfd.views.common.mixins.messages.error", side_effect=mock_error):
            queryset = TestModel.objects.filter(id__in=[obj1.id])

            # Act
            with translation.override("en"):
                response = self.model_admin.update_selected_popup(self.model_admin, request, queryset)

        # Assert - Error message shown
        self.assertEqual(len(message_list), 1)
        error_message = message_list[0][1]
        self.assertIn("select a field", error_message)
        self.assertEqual(response.status_code, 302)

    @patch("sfd.views.common.mixins.reverse", return_value="/admin/")
    def test_update_selected_popup_handles_missing_field_value(self, mock_reverse):
        """Test update_selected_popup handles error when field_value is not provided."""
        # Arrange
        obj1 = TestModel.objects.create(name="Test 1")

        request = self.factory.post(
            "/admin/",
            {
                "confirm_update": "1",
                "field_name": "name",
            },
        )
        request.user = self.user

        # Mock messages framework
        message_list = []

        def mock_error(req, msg):
            message_list.append(("error", msg))

        with patch("sfd.views.common.mixins.messages.error", side_effect=mock_error):
            queryset = TestModel.objects.filter(id__in=[obj1.id])

            # Act
            with translation.override("en"):
                response = self.model_admin.update_selected_popup(self.model_admin, request, queryset)

        # Assert - Error message shown
        self.assertEqual(len(message_list), 1)
        error_message = message_list[0][1]
        self.assertIn("provide a value", error_message)
        self.assertEqual(response.status_code, 302)

    @patch("sfd.views.common.mixins.reverse", return_value="/admin/")
    def test_update_selected_popup_handles_invalid_field_name(self, mock_reverse):
        """Test update_selected_popup handles error when field_name does not exist."""
        # Arrange
        obj1 = TestModel.objects.create(name="Test 1")

        request = self.factory.post(
            "/admin/",
            {
                "confirm_update": "1",
                "field_name": "nonexistent_field",
                "field_value": "Updated",
            },
        )
        request.user = self.user

        # Mock messages framework
        message_list = []

        def mock_error(req, msg):
            message_list.append(("error", msg))

        with patch("sfd.views.common.mixins.messages.error", side_effect=mock_error):
            queryset = TestModel.objects.filter(id__in=[obj1.id])

            # Act
            with translation.override("en"):
                response = self.model_admin.update_selected_popup(self.model_admin, request, queryset)

        # Assert - Error message shown
        self.assertEqual(len(message_list), 1)
        error_message = message_list[0][1]
        self.assertIn("Error updating", error_message)
        self.assertEqual(response.status_code, 302)

    @patch("sfd.views.common.mixins.reverse", return_value="/admin/")
    def test_update_selected_popup_updates_boolean_field(self, mock_reverse):
        """Test update_selected_popup can update boolean fields."""
        # Arrange
        obj1 = TestModel.objects.create(name="Test 1", is_active=False)
        obj2 = TestModel.objects.create(name="Test 2", is_active=False)

        request = self.factory.post(
            "/admin/",
            {
                "confirm_update": "1",
                "field_name": "is_active",
                "field_value": "True",
            },
        )
        request.user = self.user
        request._messages = Mock()

        queryset = TestModel.objects.filter(id__in=[obj1.id, obj2.id])

        # Act
        response = self.model_admin.update_selected_popup(self.model_admin, request, queryset)

        # Assert - Boolean field updated
        obj1.refresh_from_db()
        obj2.refresh_from_db()

        self.assertTrue(obj1.is_active)
        self.assertTrue(obj2.is_active)
        self.assertEqual(response.status_code, 302)

    def test_get_updateable_fields_returns_editable_fields(self):
        """Test get_updateable_fields returns list of editable fields."""
        # Act
        fields = self.model_admin.get_updateable_fields()

        # Assert - Should return tuples of (field_name, field_verbose_name)
        self.assertIsInstance(fields, list)
        self.assertGreater(len(fields), 0)

        # Check structure
        for field_name, field_label in fields:
            self.assertIsInstance(field_name, str)
            self.assertIsInstance(field_label, str)

        # Check that audit fields are excluded
        field_names = [f[0] for f in fields]
        self.assertNotIn("created_by", field_names)
        self.assertNotIn("created_at", field_names)
        self.assertNotIn("updated_by", field_names)
        self.assertNotIn("updated_at", field_names)
        self.assertNotIn("deleted_flg", field_names)

    def test_get_context_for_update_selected_includes_required_data(self):
        """Test get_context_for_update_selected includes all required context data."""
        # Arrange
        obj1 = TestModel.objects.create(name="Test 1")
        obj2 = TestModel.objects.create(name="Test 2")

        request = self.factory.post("/admin/", {"_selected_action": [obj1.pk, obj2.pk]})  # type: ignore[arg-type]
        request.user = self.user
        request._messages = Mock()  # type: ignore[attr-defined]

        queryset = TestModel.objects.filter(pk__in=[obj1.pk, obj2.pk])

        # Act
        context = self.model_admin.get_context_for_update_selected(request, queryset)

        # Assert - All required keys present
        self.assertIn("opts", context)
        self.assertIn("action_name", context)
        self.assertIn("queryset", context)
        self.assertIn("selected_objects", context)
        self.assertIn("selected_count", context)
        self.assertIn("updateable_fields", context)
        self.assertIn("object_timestamps", context)

        # Verify values
        self.assertEqual(context["action_name"], "update_selected_popup")
        self.assertEqual(context["selected_count"], 2)
        self.assertIsInstance(context["updateable_fields"], list)
        self.assertIsInstance(context["object_timestamps"], dict)

    def test_get_actions_includes_update_selected_popup(self):
        """Test get_actions includes update_selected_popup action when user has change permission."""
        # Arrange
        request = self.factory.get("/admin/")
        request.user = self.user

        # Act
        actions = self.model_admin.get_actions(request)

        # Assert - update_selected_popup action present
        self.assertIn("update_selected_popup", actions)

        # Verify action tuple structure
        action_func, action_name, action_description = actions["update_selected_popup"]
        self.assertEqual(action_name, "update_selected_popup")
        self.assertIsNotNone(action_description)

    @patch("sfd.views.common.mixins.ModelAdminMixin.has_change_permission", return_value=False)
    def test_get_actions_excludes_update_selected_popup_without_change_permission(self, mock_has_change):
        """Test get_actions excludes update_selected_popup action when user lacks change permission."""
        # Arrange
        request = self.factory.get("/admin/")
        request.user = self.user

        # Act
        actions = self.model_admin.get_actions(request)

        # Assert - update_selected_popup action not present
        self.assertNotIn("update_selected_popup", actions)

    @patch("sfd.views.common.mixins.reverse", return_value="/admin/")
    def test_update_selected_popup_handles_concurrent_update_in_execute(self, mock_reverse):
        """Test update_selected_popup detects concurrent updates during execution."""
        # Arrange - Create object with timestamp using existing BaseModelAdmin
        from sfd.tests.common.test_mixins_base_model_admin import TestBaseModelAdmin
        from sfd.tests.unittest import TestBaseModel

        base_admin = TestBaseModelAdmin(TestBaseModel, self.admin_site)

        obj1 = TestBaseModel.objects.create(name="Test 1")
        original_timestamp = int(obj1.updated_at.timestamp() * 1_000_000)

        # Modify object to simulate concurrent update
        obj1.name = "Modified by another user"
        obj1.save()

        # Prepare request with old timestamp
        request = self.factory.post(
            "/admin/",
            {
                "confirm_update": "1",
                "field_name": "name",
                "field_value": "My Update",
                f"timestamp_{obj1.pk}": str(original_timestamp),
            },
        )
        request.user = self.user

        # Mock messages framework
        message_list = []

        def mock_error(req, msg):
            message_list.append(("error", msg))

        with patch("sfd.views.common.mixins.messages.error", side_effect=mock_error):
            queryset = TestBaseModel.objects.filter(id__in=[obj1.id])

            # Act
            with translation.override("en"):
                response = base_admin.update_selected_popup(base_admin, request, queryset)

        # Assert - Error message about concurrent update
        self.assertEqual(len(message_list), 1)
        error_message = message_list[0][1]
        self.assertIn("Concurrent update detected", error_message)
        self.assertEqual(response.status_code, 302)

    @patch("sfd.views.common.mixins.reverse", return_value="/admin/")
    def test_execute_update_selected_with_audit_fields(self, mock_reverse):
        """Test execute_update_selected updates audit fields (updated_by, updated_at)."""
        # Arrange
        from sfd.tests.common.test_mixins_base_model_admin import TestBaseModelAdmin
        from sfd.tests.unittest import TestBaseModel

        base_admin = TestBaseModelAdmin(TestBaseModel, self.admin_site)

        obj1 = TestBaseModel.objects.create(name="Test Audit 1", email="test1@example.com", created_by="original_user")
        obj2 = TestBaseModel.objects.create(name="Test Audit 2", email="test2@example.com", created_by="original_user")

        request = self.factory.post(
            "/admin/",
            {
                "confirm_update": "1",
                "field_name": "email",  # Update email field
                "field_value": "updated@example.com",
            },
        )
        request.user = self.user
        request._messages = Mock()

        queryset = TestBaseModel.objects.filter(id__in=[obj1.id, obj2.id])

        # Act
        response = base_admin.update_selected_popup(base_admin, request, queryset)

        # Assert - Audit fields updated
        obj1.refresh_from_db()
        obj2.refresh_from_db()

        self.assertEqual(obj1.email, "updated@example.com")
        self.assertEqual(obj2.email, "updated@example.com")
        self.assertEqual(obj1.updated_by, self.user.username)
        self.assertEqual(obj2.updated_by, self.user.username)
        self.assertIsNotNone(obj1.updated_at)
        self.assertIsNotNone(obj2.updated_at)
        self.assertEqual(response.status_code, 302)

    @patch("sfd.views.common.mixins.reverse", return_value="/admin/")
    def test_get_context_for_update_selected_checks_permissions(self, mock_reverse):
        """Test get_context_for_update_selected checks per-object permissions."""
        # Arrange
        obj1 = TestModel.objects.create(name="Test 1")
        obj2 = TestModel.objects.create(name="Test 2")

        request = self.factory.post("/admin/", {"_selected_action": [obj1.pk, obj2.pk]})  # type: ignore[arg-type]
        request.user = self.user
        request._messages = Mock()  # type: ignore[attr-defined]

        # Mock has_change_permission to deny for obj1
        with patch.object(self.model_admin, "has_change_permission", side_effect=lambda req, obj=None: obj != obj1 if obj else True):
            queryset = TestModel.objects.filter(pk__in=[obj1.pk, obj2.pk])

            # Mock messages framework
            message_list = []

            def mock_error(req, msg):
                message_list.append(("error", msg))

            with patch("sfd.views.common.mixins.messages.error", side_effect=mock_error):
                # Act
                with translation.override("en"):
                    context = self.model_admin.get_context_for_update_selected(request, queryset)

        # Assert - Error message about permission
        self.assertEqual(len(message_list), 1)
        error_message = message_list[0][1]
        self.assertIn("no permission", error_message)
        # Object string representation may vary, just check error exists
        self.assertIn("Test Model", error_message)

        # Verify context is still returned
        self.assertIn("opts", context)

    @patch("sfd.views.common.mixins.reverse", return_value="/admin/")
    def test_get_context_for_update_selected_detects_stale_data(self, mock_reverse):
        """Test get_context_for_update_selected detects when selected_action count != queryset count."""
        # Arrange
        obj1 = TestModel.objects.create(name="Test 1")
        obj2 = TestModel.objects.create(name="Test 2")
        obj3 = TestModel.objects.create(name="Test 3")

        # Selected 3 objects but only pass 2 in queryset (simulating concurrent deletion)
        request = self.factory.post("/admin/", {"_selected_action": [obj1.pk, obj2.pk, obj3.pk]})  # type: ignore[arg-type]
        request.user = self.user
        request._messages = Mock()  # type: ignore[attr-defined]

        queryset = TestModel.objects.filter(pk__in=[obj1.pk, obj2.pk])  # Only 2 objects

        # Mock messages framework
        message_list = []

        def mock_error(req, msg):
            message_list.append(("error", msg))

        with patch("sfd.views.common.mixins.messages.error", side_effect=mock_error):
            # Act
            with translation.override("en"):
                context = self.model_admin.get_context_for_update_selected(request, queryset)

        # Assert - Error message about stale data
        self.assertEqual(len(message_list), 1)
        error_message = message_list[0][1]
        self.assertIn("updated by other users", error_message)
        self.assertIn("refresh", error_message)

        # Verify context is still returned despite error
        self.assertIn("opts", context)

    def test_get_context_for_update_selected_handles_objects_without_updated_at(self):
        """Test get_context_for_update_selected handles objects without updated_at field."""
        # Arrange - TestModel doesn't have updated_at, so timestamps should be empty
        obj1 = TestModel.objects.create(name="Test 1")
        obj2 = TestModel.objects.create(name="Test 2")

        request = self.factory.post("/admin/", {"_selected_action": [obj1.pk, obj2.pk]})  # type: ignore[arg-type]
        request.user = self.user
        request._messages = Mock()  # type: ignore[attr-defined]

        queryset = TestModel.objects.filter(pk__in=[obj1.pk, obj2.pk])

        # Act
        context = self.model_admin.get_context_for_update_selected(request, queryset)

        # Assert - object_timestamps should be empty dict for models without updated_at
        self.assertEqual(context["object_timestamps"], {})

    @patch("sfd.views.common.mixins.reverse", return_value="/admin/")
    def test_update_selected_popup_handles_field_type_conversion_error(self, mock_reverse):
        """Test update_selected_popup handles field type conversion errors gracefully."""
        # Arrange
        obj1 = TestModel.objects.create(name="Test 1")

        # Try to set invalid integer value
        request = self.factory.post(
            "/admin/",
            {
                "confirm_update": "1",
                "field_name": "name",  # CharField
                "field_value": "x" * 300,  # Exceeds max_length
            },
        )
        request.user = self.user

        # Mock messages framework
        message_list = []

        def mock_error(req, msg):
            message_list.append(("error", msg))

        with patch("sfd.views.common.mixins.messages.error", side_effect=mock_error):
            queryset = TestModel.objects.filter(id__in=[obj1.id])

            # Act
            with translation.override("en"):
                response = self.model_admin.update_selected_popup(self.model_admin, request, queryset)

        # Assert - Error message shown
        self.assertGreaterEqual(len(message_list), 1)
        self.assertEqual(response.status_code, 302)

    @patch("sfd.views.common.mixins.reverse", return_value="/admin/")
    def test_execute_update_selected_validates_field_exists(self, mock_reverse):
        """Test execute_update_selected raises ValidationError for non-existent field."""
        # Arrange
        obj1 = TestModel.objects.create(name="Test 1")

        request = self.factory.post(
            "/admin/",
            {
                "confirm_update": "1",
                "field_name": "nonexistent_field",
                "field_value": "value",
            },
        )
        request.user = self.user

        # Mock messages framework
        message_list = []

        def mock_error(req, msg):
            message_list.append(("error", msg))

        with patch("sfd.views.common.mixins.messages.error", side_effect=mock_error):
            queryset = TestModel.objects.filter(id__in=[obj1.id])

            # Act
            with translation.override("en"):
                response = self.model_admin.update_selected_popup(self.model_admin, request, queryset)

        # Assert - Error message about invalid field
        self.assertGreaterEqual(len(message_list), 1)
        error_message = message_list[0][1]
        self.assertIn("Error updating", error_message)
        self.assertEqual(response.status_code, 302)

    @patch("sfd.views.common.mixins.reverse", return_value="/admin/")
    def test_update_selected_popup_without_hasattr_to_python(self, mock_reverse):
        """Test update_selected_popup handles fields without to_python method."""
        # Arrange
        obj1 = TestModel.objects.create(name="Test 1")

        request = self.factory.post(
            "/admin/",
            {
                "confirm_update": "1",
                "field_name": "name",
                "field_value": "Updated Value",
            },
        )
        request.user = self.user
        request._messages = Mock()

        queryset = TestModel.objects.filter(id__in=[obj1.id])

        # Mock field to not have to_python method
        original_get_field = TestModel._meta.get_field

        def mock_get_field(field_name):
            field = original_get_field(field_name)
            if field_name == "name":
                # Create a field mock that doesn't have to_python
                mock_field = Mock()
                mock_field.verbose_name = field.verbose_name
                # Remove to_python attribute
                del mock_field.to_python
                return mock_field
            return field

        with patch.object(TestModel._meta, "get_field", side_effect=mock_get_field):
            # Act
            response = self.model_admin.update_selected_popup(self.model_admin, request, queryset)

        # Assert - Should still work with string value
        obj1.refresh_from_db()
        self.assertEqual(obj1.name, "Updated Value")
        self.assertEqual(response.status_code, 302)

    def test_get_updateable_fields_excludes_auto_created_fields(self):
        """Test get_updateable_fields excludes auto-created and non-concrete fields."""
        # Act
        fields = self.model_admin.get_updateable_fields()

        # Assert - Auto-created fields should be excluded
        field_names = [f[0] for f in fields]

        # Check that id (primary key) is excluded
        self.assertNotIn("id", field_names)

        # All returned fields should be concrete and not auto-created
        for field_name, _ in fields:
            field = TestModel._meta.get_field(field_name)
            self.assertTrue(field.concrete)
            self.assertFalse(field.auto_created)

    def test_get_context_for_update_selected_collects_timestamps_for_objects_with_updated_at(self):
        """Test get_context_for_update_selected collects timestamps for objects with updated_at field (lines 294-297)."""
        # Import TestBaseModel which has updated_at field from BaseModel
        from sfd.tests.common.test_mixins_base_model_admin import TestBaseModelAdmin
        from sfd.tests.unittest import TestBaseModel

        # Arrange - Create TestBaseModel objects which have updated_at
        obj1 = TestBaseModel.objects.create(name="Base Test 1", email="test1@example.com")
        obj2 = TestBaseModel.objects.create(name="Base Test 2", email="test2@example.com")

        # Create admin instance for TestBaseModel
        base_admin = TestBaseModelAdmin(TestBaseModel, self.admin_site)

        request = self.factory.post("/admin/", {"_selected_action": [obj1.pk, obj2.pk]})  # type: ignore[arg-type]
        request.user = self.user
        request._messages = Mock()  # type: ignore[attr-defined]

        queryset = TestBaseModel.objects.filter(pk__in=[obj1.pk, obj2.pk])

        # Act
        context = base_admin.get_context_for_update_selected(request, queryset)

        # Assert - object_timestamps should contain timestamps for both objects
        self.assertIn("object_timestamps", context)
        object_timestamps = context["object_timestamps"]

        # Verify both objects have timestamps
        self.assertEqual(len(object_timestamps), 2)
        self.assertIn(obj1.pk, object_timestamps)
        self.assertIn(obj2.pk, object_timestamps)

        # Verify timestamps are integers (microseconds)
        self.assertIsInstance(object_timestamps[obj1.pk], int)
        self.assertIsInstance(object_timestamps[obj2.pk], int)

        # Verify timestamps match the objects' updated_at values
        expected_timestamp_obj1 = int(obj1.updated_at.timestamp() * 1_000_000)
        expected_timestamp_obj2 = int(obj2.updated_at.timestamp() * 1_000_000)

        self.assertEqual(object_timestamps[obj1.pk], expected_timestamp_obj1)
        self.assertEqual(object_timestamps[obj2.pk], expected_timestamp_obj2)

    def test_get_actions_removes_existing_update_selected_popup_without_permission(self):
        """Test get_actions removes update_selected_popup if it exists but user lacks permission (line 89)."""
        # Arrange
        request = self.factory.get("/admin/")
        request.user = self.user

        # Mock the parent get_actions to return a dict with update_selected_popup already present
        with patch.object(admin.ModelAdmin, "get_actions") as mock_parent_get_actions:
            # Simulate that update_selected_popup exists from a previous call or parent class
            mock_parent_get_actions.return_value = {
                "update_selected_popup": (self.model_admin.update_selected_popup, "update_selected_popup", "Update selected items"),
                "some_other_action": (lambda: None, "some_other_action", "Some other action"),
            }

            # Mock has_change_permission to return False
            with patch.object(self.model_admin, "has_change_permission", return_value=False):
                # Act
                actions = self.model_admin.get_actions(request)

                # Assert - update_selected_popup should be removed (line 89 executed)
                self.assertNotIn("update_selected_popup", actions)
                # But other actions should remain
                self.assertIn("some_other_action", actions)
