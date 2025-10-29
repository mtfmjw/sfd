import time
from unittest.mock import patch

import pytest
from django import forms
from django.contrib import admin
from django.contrib.admin import AdminSite
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone, translation

from sfd.tests.unittest import BaseTestMixin, TestBaseModel, TestModel
from sfd.views.common.mixins import BaseModelAdminMixin, DeleteFlagFilter


class TestBaseModelAdmin(BaseModelAdminMixin, admin.ModelAdmin):
    """Test admin class that inherits from BaseModelAdminMixin.

    Note: ModelAdminMixin is now automatically included via BaseModelAdminMixin inheritance.
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
        self.model_admin = TestBaseModelAdmin(TestBaseModel, self.admin_site)
        self.request = self.factory.get("/admin/")
        self.request.user = self.user
        self.model_admin._is_delete_action = False
        self.model_admin._is_undelete_action = False

    def test_base_model_admin_mixin_initialization(self):
        """Test model_class returns correct model class."""
        # Act
        with self.assertRaisesMessage(TypeError, "BaseModelAdminMixin can only be used with BaseModel subclasses"):
            TestBaseModelAdmin(TestModel, self.admin_site)

        # Assert
        self.assertFalse(self.model_admin.is_show_edit_info_on_list_view)
        self.assertTrue(self.model_admin.is_optimistic_locking_on_list_view)

    def test_deleted(self):
        """Test deleted field is included in list display."""
        obj1 = TestBaseModel.objects.create(name="Test1", email="test1@example.com", is_active=True, date="2023-01-01", deleted_flg=False)
        obj2 = TestBaseModel.objects.create(name="Test2", email="test2@example.com", is_active=False, date="2023-01-02", deleted_flg=True)

        # Assert
        self.assertIn('<input type="checkbox" disabled', self.model_admin.deleted())
        self.assertIn('<input type="checkbox" disabled', self.model_admin.deleted(obj1))
        self.assertIn('<input type="checkbox" class="deleted-row" disabled checked>', self.model_admin.deleted(obj2))

    def test_update_timestamp(self):
        """Test update_timestamp field is formatted correctly."""
        obj = TestBaseModel.objects.create(name="Test1", email="test1@example.com", is_active=True)
        formatted_timestamp = obj.updated_at.strftime("%Y-%m-%d %H:%M:%S")  # type: ignore

        # Assert
        self.assertIn(formatted_timestamp, self.model_admin.update_timestamp(obj))  # type: ignore
        self.assertIsNone(self.model_admin.update_timestamp())  # type: ignore

    def test_get_form_init(self):
        """Test get_form returns a form instance."""
        obj = TestBaseModel.objects.create(name="Test1", email="test1@example.com", is_active=True)

        # Act
        form_type = self.model_admin.get_form(self.request)
        form = form_type(instance=obj)

        # Assert
        self.assertTrue(issubclass(form_type, forms.ModelForm))
        self.assertIn("timestamp", form.fields)  # type: ignore[attr-defined]
        self.assertEqual(form.fields["timestamp"].initial, int(obj.updated_at.timestamp() * 1_000_000))

    def test_get_form_clean(self):
        """Test get_form returns a form instance."""
        obj = TestBaseModel.objects.create(name="Test1", email="test1@example.com", is_active=True)
        current_timestamp = int(obj.updated_at.timestamp() * 1_000_000)

        # Act
        form_type = self.model_admin.get_form(self.request)
        form_data = {"name": "Test1 updated", "email": "test1@example.com", "is_active": True, "timestamp": current_timestamp}
        form = form_type(data=form_data, instance=obj)
        form._admin_instance = self.model_admin  # type: ignore[attr-defined]

        self.assertTrue(form.is_valid())
        self.assertEqual(form.errors, {})
        self.assertEqual(form.cleaned_data["timestamp"], current_timestamp)

    def test_get_form_race_condition(self):
        """Test get_form returns a form instance."""
        obj = TestBaseModel.objects.create(name="Test1", email="test1@example.com", is_active=True)
        current_timestamp = int(obj.updated_at.timestamp() * 1_000_000)

        # Act
        form_type = self.model_admin.get_form(self.request)
        form_data = {"name": "Test1 updated", "email": "test1@example.com", "is_active": True, "timestamp": current_timestamp + 1}
        form = form_type(data=form_data, instance=obj)

        with translation.override("en"):
            self.assertFalse(form.is_valid())
            self.assertEqual(form.errors, {"__all__": ["This record has been modified by another user. Please reload and try again."]})
            self.assertEqual(form.cleaned_data["timestamp"], current_timestamp + 1)

    def test_get_form_update_deleted(self):
        """Test get_form returns a form instance."""
        obj = TestBaseModel.objects.create(name="Test1", email="test1@example.com", is_active=True)
        current_timestamp = int(obj.updated_at.timestamp() * 1_000_000)

        # Act
        form_type = self.model_admin.get_form(self.request)
        form_data = {"name": "Test1 updated", "email": "test1@example.com", "is_active": True, "timestamp": current_timestamp}
        form = form_type(data=form_data, instance=obj)

        obj.delete()
        with translation.override("en"):
            self.assertFalse(form.is_valid())
            self.assertEqual(form.errors, {"__all__": ["This record has been deleted by another user."]})

    def test_get_non_inherited_model_fields(self):
        """Test get_non_inherited_model_fields returns correct fields."""
        # Act
        fields = self.model_admin.get_non_inherited_model_fields(self.request)

        # Assert
        self.assertEqual(fields, ["name", "email", "is_active", "date"])
        self.assertNotIn("created_by", fields)
        self.assertNotIn("created_at", fields)
        self.assertNotIn("updated_by", fields)
        self.assertNotIn("updated_at", fields)
        self.assertNotIn("deleted_flg", fields)

    def test_get_readonly_fields(self):
        """Test get_readonly_fields returns correct fields."""
        # Act
        readonly_fields = self.model_admin.get_readonly_fields(self.request)

        # Assert
        self.assertEqual(readonly_fields, ["deleted", "created_by", "created_at", "updated_by", "updated_at", "update_timestamp"])

    def test_get_fieldsets_none(self):
        """Test get_fieldsets returns correct fieldsets."""

        # Assert
        with translation.override("en"):
            # Act
            fieldsets = self.model_admin.get_fieldsets(self.request, obj=None)

            self.assertEqual(len(fieldsets), 1)
            self.assertEqual(fieldsets[0][0], "Basic Information")
            self.assertEqual(fieldsets[0][1]["fields"], ("name", "email", "is_active", "date"))

    def test_get_fieldsets_popup(self):
        """Test get_fieldsets returns correct fieldsets."""
        request = self.factory.get("/admin/?_popup=1")
        request.user = self.user

        # Assert
        with translation.override("en"):
            # Act
            fieldsets = self.model_admin.get_fieldsets(self.request, obj=None)

            self.assertEqual(len(fieldsets), 1)
            self.assertEqual(fieldsets[0][0], "Basic Information")
            self.assertEqual(fieldsets[0][1]["fields"], ("name", "email", "is_active", "date"))

    def test_get_fieldsets_already_exists_edit_info(self):
        """Test get_fieldsets returns correct fieldsets."""
        obj = TestBaseModel.objects.create(name="Test1", email="test1@example.com", is_active=True)
        self.model_admin.fieldsets = (("Edit Info", {"fields": ("created_by", "created_at", "updated_by", "updated_at", "deleted")}),)

        # Assert
        with translation.override("en"):
            # Act
            fieldsets = self.model_admin.get_fieldsets(self.request, obj=obj)

            self.assertEqual(len(fieldsets), 1)
            self.assertEqual(fieldsets[0][0], "Edit Info")
            self.assertEqual(fieldsets[0][1]["fields"], ("created_by", "created_at", "updated_by", "updated_at", "deleted"))

    def test_get_fieldsets(self):
        """Test get_fieldsets returns correct fieldsets."""
        obj = TestBaseModel.objects.create(name="Test1", email="test1@example.com", is_active=True)

        # Assert
        with translation.override("en"):
            # Act
            fieldsets = self.model_admin.get_fieldsets(self.request, obj=obj)

            self.assertEqual(len(fieldsets), 2)
            self.assertEqual(fieldsets[0][0], "Basic Information")
            self.assertEqual(fieldsets[0][1]["fields"], ("name", "email", "is_active", "date"))
            self.assertEqual(fieldsets[1][0], "Edit Info")
            self.assertEqual(fieldsets[1][1]["fields"], (("created_by", "created_at"), ("updated_by", "updated_at"), "deleted"))

    def test_add_edit_info_list_display(self):
        """Test add_edit_info_list_display modifies list_display correctly."""
        # Act
        self.model_admin.is_show_edit_info_on_list_view = True
        list_display = self.model_admin.get_list_display(self.request)
        self.assertEqual(
            list_display, ["name", "email", "is_active", "date", "created_by", "created_at", "updated_by", "update_timestamp", "deleted"]
        )

        self.model_admin.is_show_edit_info_on_list_view = False
        self.model_admin.is_optimistic_locking_on_list_view = True
        list_display = self.model_admin.get_list_display(self.request)
        self.assertEqual(list_display, ["name", "email", "is_active", "date", "updated_by", "update_timestamp", "deleted"])

        self.model_admin.is_optimistic_locking_on_list_view = False
        self.model_admin.is_show_edit_info_on_list_view = False
        list_display = self.model_admin.get_list_display(self.request)
        self.assertEqual(list_display, ["name", "email", "is_active", "date"])

    def test_get_list_filter(self):
        """Test get_list_filter returns correct filters."""
        # Arrange
        self.model_admin.list_filter = ("is_active",)
        # Act
        list_filter = self.model_admin.get_list_filter(self.request)
        # Assert
        self.assertNotIn(DeleteFlagFilter, list_filter)

        # Arrange
        self.model_admin.list_filter = ("is_active", "deleted_flg")
        # Act
        list_filter = self.model_admin.get_list_filter(self.request)
        # Assert
        self.assertIn(DeleteFlagFilter, list_filter)

    def test_get_list_display(self):
        """Test get_list_display returns correct display fields."""
        # Arrange
        self.model_admin.list_display = ("name", "email")
        # Act
        list_display = self.model_admin.get_list_display(self.request)

        # Assert
        self.assertEqual(list_display, ["name", "email", "updated_by", "update_timestamp", "deleted"])

    def test_save_model_create(self):
        """Test save_model sets created_by and updated_by correctly."""
        obj = TestBaseModel(name="Test1", email="test1@example.com", is_active=True)

        self.model_admin.save_model(self.request, obj, form=None, change=True)
        assert obj.created_by == self.user.username
        assert obj.updated_by == self.user.username

    def test_save_model_update(self):
        """Test save_model sets created_by and updated_by correctly."""
        obj = TestBaseModel.objects.create(name="Test1", email="test1@example.com", is_active=True, created_by="initial", updated_by="initial")

        self.model_admin.save_model(self.request, obj, form=None, change=True)
        assert obj.created_by == "initial"
        assert obj.updated_by == self.user.username

    def test_save_model_delete(self):
        """Test save_model sets created_by and updated_by correctly."""
        obj = TestBaseModel.objects.create(name="Test1", email="test1@example.com", is_active=True, created_by="initial", updated_by="initial")

        request = self.factory.post("/admin/", {"_delete": "1"})
        request.user = self.user
        self.model_admin.save_model(request, obj, form=None, change=True)
        assert obj.updated_by == self.user.username
        assert obj.deleted_flg is True

    def test_save_model_undelete(self):
        """Test save_model sets created_by and updated_by correctly."""
        obj = TestBaseModel.objects.create(name="Test1", email="test1@example.com", is_active=True, created_by="initial", updated_by="initial")

        request = self.factory.post("/admin/", {"_undelete": "1"})
        request.user = self.user
        self.model_admin.save_model(request, obj, form=None, change=True)
        assert obj.updated_by == self.user.username
        assert obj.deleted_flg is False

    def test_execute_delete_selected(self):
        """Test execute_delete_selected marks records as deleted."""
        obj1 = TestBaseModel.objects.create(name="Test1", email="test1@example.com", is_active=True, created_by="initial", updated_by="initial")
        obj2 = TestBaseModel.objects.create(name="Test2", email="test2@example.com", is_active=True, created_by="initial", updated_by="initial")

        queryset = TestBaseModel.objects.filter(id__in=[obj1.id, obj2.id])  # type: ignore[attr-defined]
        count = self.model_admin.execute_delete_selected(self.request, queryset)

        # Refresh objects from database to see saved changes
        obj1.refresh_from_db()
        obj2.refresh_from_db()

        assert count == 2
        assert obj1.updated_by == self.user.username
        assert obj2.updated_by == self.user.username
        assert obj1.deleted_flg is True
        assert obj2.deleted_flg is True

    def test_execute_delete_selected_race_condition(self):
        """Test execute_delete_selected detects concurrent updates and raises IntegrityError."""

        # Create objects with specific timestamps
        obj1 = TestBaseModel.objects.create(name="Test1", email="test1@example.com", is_active=True, created_by="initial", updated_by="initial")
        obj2 = TestBaseModel.objects.create(name="Test2", email="test2@example.com", is_active=True, created_by="initial", updated_by="initial")
        original_timestamp1 = int(obj1.updated_at.timestamp() * 1_000_000)
        original_timestamp2 = int(obj2.updated_at.timestamp() * 1_000_000)

        # Simulate another user updating obj1 in the database
        time.sleep(0.01)  # Ensure timestamp changes
        obj1.updated_by = "another_user"
        obj1.updated_at = timezone.now()
        obj1.save()

        # Create POST request with the old timestamp (simulating race condition)
        request = self.factory.post("/admin/", {f"timestamp_{obj1.pk}": str(original_timestamp1), f"timestamp_{obj2.pk}": str(original_timestamp2)})
        request.user = self.user

        # Get fresh queryset (this would have the old timestamp in memory)
        queryset = TestBaseModel.objects.filter(id__in=[obj1.id, obj2.id])  # type: ignore[attr-defined]

        # Execute delete_selected should raise IntegrityError due to concurrent update
        with translation.override("en"):
            with self.assertRaisesMessage(IntegrityError, f"Concurrent update detected for {obj1}."):
                self.model_admin.execute_delete_selected(request, queryset)

    @patch("sfd.views.common.mixins.super")
    def test_get_context_for_delete_selected(self, mock_super):
        """Test get_context_for_delete_selected provides correct context data."""
        mock_super.return_value.get_context_for_delete_selected.return_value = {}

        # Create objects with specific timestamps
        current_time = timezone.now()
        obj1 = TestBaseModel.objects.create(
            name="Test1", email="test1@example.com", is_active=True, created_by="initial", updated_by="initial", updated_at=current_time
        )
        obj2 = TestBaseModel.objects.create(
            name="Test2", email="test2@example.com", is_active=True, created_by="initial", updated_by="initial", updated_at=current_time
        )

        # Capture the original timestamp in microseconds (as it would be in POST data)
        original_timestamp = int(current_time.timestamp() * 1_000_000)

        # Create POST request with the old timestamp (simulating race condition)
        request = self.factory.post("/admin/", {f"timestamp_{obj1.pk}": str(original_timestamp), f"timestamp_{obj2.pk}": str(original_timestamp)})
        request.user = self.user

        # Get fresh queryset (this would have the old timestamp in memory)
        queryset = TestBaseModel.objects.filter(id__in=[obj1.id, obj2.id])  # type: ignore[attr-defined]

        # Execute delete_selected should raise IntegrityError due to concurrent update
        context = self.model_admin.get_context_for_delete_selected(request, queryset)
        assert obj1.pk in context["object_timestamps"]
        assert obj2.pk in context["object_timestamps"]
