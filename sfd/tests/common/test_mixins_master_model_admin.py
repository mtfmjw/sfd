# type: ignore[attr-defined]
import datetime
from itertools import chain
from unittest.mock import Mock, patch

import pytest
from django.contrib import admin
from django.contrib.admin import AdminSite
from django.contrib.messages.storage.fallback import FallbackStorage
from django.http import HttpResponseRedirect
from django.test import TestCase
from django.utils import timezone, translation

from sfd.tests.unittest import BaseTestMixin, TestBaseModel, TestMasterModel
from sfd.views.common.mixins import MasterModelAdminMixin


class TestMasterModelAdmin(MasterModelAdminMixin, admin.ModelAdmin):
    """Test admin class that inherits from MasterModelAdminMixin.

    Note: BaseModelAdminMixin and ModelAdminMixin are now automatically included
    via MasterModelAdminMixin inheritance chain.
    """

    pass


@pytest.mark.unit
@pytest.mark.views
class BaseModelAdminMixinTest(BaseTestMixin, TestCase):
    """Test BaseModelAdmin functionality with comprehensive coverage."""

    databases = {"default", "postgres"}

    def setUp(self):
        """Set up test data for BaseModelAdmin tests."""
        super().setUp()
        self.admin_site = AdminSite()
        self.model_admin = TestMasterModelAdmin(TestMasterModel, self.admin_site)
        self.request = self.factory.get("/admin/")
        self.request.user = self.user
        self.model_admin._is_delete_action = False
        self.model_admin._is_undelete_action = False

    def test_master_model_admin_mixin_initialization(self):
        """Test model_class returns correct model class."""
        # Act
        with self.assertRaisesMessage(TypeError, "MasterModelAdminMixin can only be used with MasterModel subclasses"):
            TestMasterModelAdmin(TestBaseModel, self.admin_site)

    @patch("sfd.views.common.mixins.super")
    def test_get_actions(self, mock_super):
        """Test get_actions returns delete_selected action."""
        mock_super.return_value.get_actions.return_value = {
            "delete_selected": (Mock(), "delete_selected", "Delete selected items"),
            "delete_selected_popup": (Mock(), "delete_selected", "Delete selected items"),
        }
        actions = self.model_admin.get_actions(self.request)
        self.assertNotIn("delete_selected", actions)
        self.assertNotIn("delete_selected_popup", actions)

    def test_get_non_inherited_model_fields(self):
        """Test get_non_inherited_model_fields returns correct fields."""
        fields = self.model_admin.get_non_inherited_model_fields(self.request)
        self.assertNotIn("valid_from", fields)
        self.assertNotIn("valid_to", fields)

    def test_get_fieldsets(self):
        """Test get_fieldsets returns correct fieldsets."""
        with translation.override("en"):
            fieldsets = self.model_admin.get_fieldsets(self.request)
            self.assertIn(("Validation Info", {"fields": (("valid_from", "valid_to"),)}), fieldsets)
            self.assertNotIn("deleted", list(chain.from_iterable(fieldsets)))

    def test_get_fieldsets_with_list(self):
        """Test get_fieldsets returns correct fieldsets."""
        self.model_admin.fieldsets = [
            ("Edit Info", {"fields": ["name", "email", "deleted"]}),
        ]
        with translation.override("en"):
            fieldsets = self.model_admin.get_fieldsets(self.request)
            self.assertNotIn("deleted", list(chain.from_iterable(fieldsets)))

    def test_get_list_display(self):
        """Test get_list_display returns correct list display."""
        list_display = self.model_admin.get_list_display(self.request)
        self.assertEqual(list_display, ["name", "email", "is_active", "date", "valid_from", "valid_to", "updated_by", "update_timestamp"])

    def test_get_form_clean_new_obj(self):
        """Test get_form returns a form instance."""
        obj = TestMasterModel.objects.create(name="Test1", email="test1@example.com", is_active=True, valid_from=datetime.date(2023, 1, 1))
        current_timestamp = int(obj.updated_at.timestamp() * 1_000_000)

        # Act
        form_type = self.model_admin.get_form(self.request)
        form_data = {
            "name": "Test1",
            "email": "test1@example.com",
            "is_active": True,
            "timestamp": current_timestamp,
            "valid_from": datetime.date(2023, 1, 1).isoformat(),
        }
        form = form_type(data=form_data, instance=obj)
        form._admin_instance = self.model_admin  # type: ignore[attr-defined]

        self.assertTrue(form.is_valid())
        self.assertEqual(form.errors, {})
        self.assertEqual(form.cleaned_data["timestamp"], current_timestamp)
        self.assertEqual(form.cleaned_data["valid_from"], datetime.date(2023, 1, 1))

    def test_get_form_clean_existing_obj(self):
        """Test get_form returns a form instance."""
        next_day = timezone.now() + datetime.timedelta(days=1)
        obj = TestMasterModel(name="Test1", email="test1@example.com", is_active=True, valid_from=next_day.date(), updated_at=timezone.now())
        current_timestamp = int(obj.updated_at.timestamp() * 1_000_000)

        # Act
        form_type = self.model_admin.get_form(self.request, obj=obj)
        form_data = {
            "name": "Test1",
            "email": "test1@example.com",
            "is_active": True,
            "timestamp": current_timestamp,
            "valid_from": next_day.date().isoformat(),
        }
        form = form_type(data=form_data, instance=obj)
        form._admin_instance = self.model_admin  # type: ignore[attr-defined]

        self.assertTrue(form.is_valid())
        self.assertEqual(form.errors, {})
        self.assertEqual(form.cleaned_data["timestamp"], current_timestamp)
        self.assertEqual(form.cleaned_data["valid_from"], next_day.date())

    def test_get_form_not_deletable(self):
        """Test get_form returns a form instance."""
        obj = TestMasterModel.objects.create(name="Test1", email="test1@example.com", is_active=True, valid_from=datetime.date(2023, 1, 1))
        current_timestamp = int(obj.updated_at.timestamp() * 1_000_000)
        self.model_admin._is_delete_action = True

        # Act
        with translation.override("en"):
            form_type = self.model_admin.get_form(self.request, obj=obj)
            form_data = {
                "name": "Test1",
                "email": "test1@example.com",
                "is_active": True,
                "timestamp": current_timestamp,
                "valid_from": "2023-01-01",
            }
            form = form_type(data=form_data, instance=obj)
            form._admin_instance = self.model_admin  # type: ignore[attr-defined]

            self.assertFalse(form.is_valid())
            self.assertEqual(form.errors, {"valid_from": ["Master data that has already been effective cannot be deleted."]})

    def test_get_form_not_changeable(self):
        """Test get_form returns a form instance."""
        obj = TestMasterModel.objects.create(name="Test1", email="test1@example.com", is_active=True, valid_from=datetime.date(2023, 1, 1))
        current_timestamp = int(obj.updated_at.timestamp() * 1_000_000)

        # Act
        with translation.override("en"):
            form_type = self.model_admin.get_form(self.request, obj=obj)
            form_data = {
                "name": "Test1",
                "email": "test1@example.com",
                "is_active": True,
                "timestamp": current_timestamp,
                "valid_from": "2023-01-01",
            }
            form = form_type(data=form_data, instance=obj)
            form._admin_instance = self.model_admin  # type: ignore[attr-defined]

            self.assertFalse(form.is_valid())
            self.assertEqual(form.errors, {"valid_from": ["Master data that has already been effective cannot be changed."]})

    def test_get_form_no_new_past_date(self):
        """Test get_form returns a form instance."""
        TestMasterModel.objects.create(name="Test1", email="test1@example.com", is_active=True, valid_from=datetime.date(2023, 1, 1))
        obj = TestMasterModel(
            name="Test1", email="test1@example.com", is_active=True, valid_from=datetime.date(2025, 1, 1), updated_at=timezone.now()
        )
        current_timestamp = int(obj.updated_at.timestamp() * 1_000_000)

        # Act
        with translation.override("en"):
            form_type = self.model_admin.get_form(self.request)
            form_data = {
                "name": "Test1",
                "email": "test1@example.com",
                "is_active": True,
                "timestamp": current_timestamp,
                "valid_from": "2025-01-01",
            }
            form = form_type(data=form_data, instance=obj)
            form._admin_instance = self.model_admin  # type: ignore[attr-defined]

            self.assertFalse(form.is_valid())
            self.assertEqual(form.errors, {"valid_from": ["There is already master data effective in the past. Please set a future start date."]})

    @patch("sfd.views.common.mixins.reverse")
    def test_changeform_view_delete_button_with_future_valid_from(self, mock_reverse):
        """Test changeform_view handles delete button click with future valid_from (should succeed)."""
        # Setup mock
        mock_reverse.return_value = "/admin/sfd/testmastermodel/"

        # Create a future-dated master record
        future_date = timezone.now().date() + datetime.timedelta(days=30)
        obj = TestMasterModel.objects.create(name="Test Future", email="future@example.com", is_active=True, valid_from=future_date)
        current_timestamp = int(obj.updated_at.timestamp() * 1_000_000)

        # Create POST request with _delete button
        post_data = {
            "name": "Test Future",
            "email": "future@example.com",
            "is_active": True,
            "timestamp": current_timestamp,
            "valid_from": future_date.isoformat(),
            "_delete": "Delete",
        }
        request = self.factory.post(f"/admin/sfd/testmastermodel/{obj.pk}/change/", data=post_data)
        request.user = self.user
        request.session = {}
        request._messages = FallbackStorage(request)

        # Act
        with translation.override("en"):
            response = self.model_admin.changeform_view(request, str(obj.pk))

        # Assert
        self.assertIsInstance(response, HttpResponseRedirect)
        self.assertEqual(response.status_code, 302)
        self.assertIn("testmastermodel", response["Location"])
        self.assertFalse(TestMasterModel.objects.filter(pk=obj.pk).exists())

    @patch("sfd.views.common.mixins.admin.ModelAdmin.changeform_view")
    def test_changeform_view_delete_button_with_past_valid_from(self, mock_super_changeform):
        """Test changeform_view handles delete button click with past valid_from (delegates to parent for validation error display)."""
        # Setup mock - return a simple response
        from django.template.response import TemplateResponse

        mock_super_changeform.return_value = TemplateResponse(None, "admin/change_form.html", {})

        # Create a past-dated master record
        past_date = datetime.date(2023, 1, 1)
        obj = TestMasterModel.objects.create(name="Test Past", email="past@example.com", is_active=True, valid_from=past_date)
        current_timestamp = int(obj.updated_at.timestamp() * 1_000_000)

        # Create POST request with _delete button
        post_data = {
            "name": "Test Past",
            "email": "past@example.com",
            "is_active": True,
            "timestamp": current_timestamp,
            "valid_from": past_date.isoformat(),
            "_delete": "Delete",
        }
        request = self.factory.post(f"/admin/sfd/testmastermodel/{obj.pk}/change/", data=post_data)
        request.user = self.user
        request.session = {}
        request._messages = FallbackStorage(request)

        # Act
        with translation.override("en"):
            self.model_admin._is_delete_action = True
            self.model_admin.changeform_view(request, str(obj.pk))

        # Assert - Should delegate to parent because form validation fails
        mock_super_changeform.assert_called_once()
        self.assertTrue(TestMasterModel.objects.filter(pk=obj.pk).exists())

    @patch("sfd.views.common.mixins.reverse")
    def test_changeform_view_delete_with_previous_record(self, mock_reverse):
        """Test changeform_view deletes and updates previous record's valid_to."""
        # Setup mock
        mock_reverse.return_value = "/admin/sfd/testmastermodel/"

        # Create previous record
        previous_date = datetime.date(2023, 1, 1)
        previous_obj = TestMasterModel.objects.create(
            name="Test Chain", email="chain@example.com", is_active=True, valid_from=previous_date, valid_to=datetime.date(2025, 11, 30)
        )

        # Create current record (to be deleted)
        future_date = timezone.now().date() + datetime.timedelta(days=30)

        obj = TestMasterModel.objects.create(
            name="Test Chain", email="chain@example.com", is_active=True, valid_from=future_date, valid_to=datetime.date(2026, 12, 31)
        )
        current_timestamp = int(obj.updated_at.timestamp() * 1_000_000)

        # Create POST request with _delete button
        post_data = {
            "name": "Test Chain",
            "email": "chain@example.com",
            "is_active": True,
            "timestamp": current_timestamp,
            "valid_from": future_date.isoformat(),
            "_delete": "Delete",
        }
        request = self.factory.post(f"/admin/sfd/testmastermodel/{obj.pk}/change/", data=post_data)
        request.user = self.user
        request.session = {}
        request._messages = FallbackStorage(request)

        # Act
        with translation.override("en"):
            response = self.model_admin.changeform_view(request, str(obj.pk))

        # Assert
        self.assertIsInstance(response, HttpResponseRedirect)
        self.assertFalse(TestMasterModel.objects.filter(pk=obj.pk).exists())

        # Check previous record was updated
        previous_obj.refresh_from_db()
        self.assertEqual(previous_obj.valid_to, datetime.date(2026, 12, 31))  # Inherited from deleted record
        self.assertEqual(previous_obj.updated_by, self.user.username)

    @patch("sfd.views.common.mixins.reverse")
    def test_changeform_view_delete_without_previous_record(self, mock_reverse):
        """Test changeform_view deletes record without previous record."""
        # Setup mock
        mock_reverse.return_value = "/admin/sfd/testmastermodel/"

        # Create a future-dated master record (no previous record)
        future_date = timezone.now().date() + datetime.timedelta(days=30)

        obj = TestMasterModel.objects.create(name="Test Standalone", email="standalone@example.com", is_active=True, valid_from=future_date)
        current_timestamp = int(obj.updated_at.timestamp() * 1_000_000)

        # Create POST request with _delete button
        post_data = {
            "name": "Test Standalone",
            "email": "standalone@example.com",
            "is_active": True,
            "timestamp": current_timestamp,
            "valid_from": future_date.isoformat(),
            "_delete": "Delete",
        }
        request = self.factory.post(f"/admin/sfd/testmastermodel/{obj.pk}/change/", data=post_data)
        request.user = self.user
        request.session = {}
        request._messages = FallbackStorage(request)

        # Act
        with translation.override("en"):
            response = self.model_admin.changeform_view(request, str(obj.pk))

        # Assert
        self.assertIsInstance(response, HttpResponseRedirect)
        self.assertFalse(TestMasterModel.objects.filter(pk=obj.pk).exists())

    def test_changeform_view_normal_save(self):
        """Test changeform_view handles normal save (no delete button)."""
        # Create a future-dated master record
        future_date = timezone.now().date() + datetime.timedelta(days=30)
        obj = TestMasterModel.objects.create(name="Test Save", email="save@example.com", is_active=True, valid_from=future_date)
        current_timestamp = int(obj.updated_at.timestamp() * 1_000_000)

        # Create POST request without _delete button (normal save)
        post_data = {
            "name": "Test Save Updated",
            "email": "save@example.com",
            "is_active": False,
            "timestamp": current_timestamp,
            "valid_from": future_date.isoformat(),
            "_save": "Save",
        }
        request = self.factory.post(f"/admin/sfd/testmastermodel/{obj.pk}/change/", data=post_data)
        request.user = self.user
        request.session = "session"
        request._messages = FallbackStorage(request)

        # Act - Should call parent changeform_view
        with patch.object(admin.ModelAdmin, "changeform_view") as mock_super_changeform:
            mock_super_changeform.return_value = HttpResponseRedirect("/admin/")
            self.model_admin.changeform_view(request, str(obj.pk))

        # Assert - Should delegate to parent class
        mock_super_changeform.assert_called_once()

    def test_changeform_view_get_request(self):
        """Test changeform_view handles GET request (display form)."""
        # Create a future-dated master record
        future_date = timezone.now().date() + datetime.timedelta(days=30)

        obj = TestMasterModel.objects.create(name="Test Display", email="display@example.com", is_active=True, valid_from=future_date)

        # Create GET request
        request = self.factory.get(f"/admin/sfd/testmastermodel/{obj.pk}/change/")
        request.user = self.user

        # Act - Should call parent changeform_view
        with patch.object(admin.ModelAdmin, "changeform_view") as mock_super_changeform:
            mock_super_changeform.return_value = HttpResponseRedirect("/admin/")
            self.model_admin.changeform_view(request, str(obj.pk))

        # Assert - Should delegate to parent class
        mock_super_changeform.assert_called_once()

    def test_changeform_view_delete_invalid_form(self):
        """Test changeform_view handles delete button with invalid form data."""
        # Create a past-dated master record
        past_date = datetime.date(2023, 1, 1)
        obj = TestMasterModel.objects.create(name="Test Invalid", email="invalid@example.com", is_active=True, valid_from=past_date)
        current_timestamp = int(obj.updated_at.timestamp() * 1_000_000)

        # Create POST request with _delete button but past valid_from (invalid)
        post_data = {
            "name": "Test Invalid",
            "email": "invalid@example.com",
            "is_active": True,
            "timestamp": current_timestamp,
            "valid_from": past_date.isoformat(),
            "_delete": "Delete",
        }
        request = self.factory.post(f"/admin/sfd/testmastermodel/{obj.pk}/change/", data=post_data)
        request.user = self.user
        request.session = "session"
        request._messages = FallbackStorage(request)

        # Act - Should call parent changeform_view when validation fails
        with translation.override("en"):
            with patch.object(admin.ModelAdmin, "changeform_view") as mock_super_changeform:
                mock_super_changeform.return_value = HttpResponseRedirect("/admin/")
                self.model_admin._is_delete_action = True
                self.model_admin.changeform_view(request, str(obj.pk))

        # Assert - Should delegate to parent class (validation failed)
        mock_super_changeform.assert_called_once()
        self.assertTrue(TestMasterModel.objects.filter(pk=obj.pk).exists())

    def test_list_filter(self):
        """Test list_filter includes valid_from and valid_to."""
        list_filter = self.model_admin.get_list_filter(self.request)
        self.assertIn("valid_from", list_filter)
