# type: ignore
"""Test cases for sfd.models package."""

import pytest
from django.db import models
from django.forms import ValidationError
from django.test import TestCase

from sfd.models import BaseModel, MasterModel
from sfd.tests.unittest import TestMasterModel


@pytest.mark.unit
@pytest.mark.models
class BaseModelTest(TestCase):
    """Test cases for the BaseModel abstract base class."""

    def test_base_model_is_abstract(self):
        """Test that BaseModel is properly configured as abstract."""
        self.assertTrue(BaseModel._meta.abstract)

    @pytest.mark.models
    def test_base_model_fields_exist(self):
        """Test that BaseModel contains all required fields."""
        expected_fields = ["created_at", "updated_at", "created_by", "updated_by", "deleted_flg"]
        model_fields = [field.name for field in BaseModel._meta.get_fields()]
        for field_name in expected_fields:
            self.assertIn(field_name, model_fields)

    def test_base_model_field_types(self):
        """Test that BaseModel fields have correct types and properties."""
        # Test created_at field
        created_at_field = BaseModel._meta.get_field("created_at")
        self.assertEqual(created_at_field.__class__.__name__, "DateTimeField")

        # Test updated_at field
        updated_at_field = BaseModel._meta.get_field("updated_at")
        self.assertEqual(updated_at_field.__class__.__name__, "DateTimeField")

        # Test deleted_flg field
        deleted_flg_field = BaseModel._meta.get_field("deleted_flg")
        self.assertEqual(deleted_flg_field.__class__.__name__, "BooleanField")
        self.assertFalse(deleted_flg_field.default)

    def test_get_unique_field_names_UniqueConstraint(self):
        """Test get_unique_field_names returns fields from UniqueConstraint."""

        class TestModel1(BaseModel):
            class Meta:
                constraints = [models.UniqueConstraint(fields=["created_by", "updated_by"], name="unique_created_updated")]

        unique_fields = TestModel1.get_unique_field_names()
        self.assertEqual(unique_fields, ["created_by", "updated_by"])

    def test_get_unique_field_names_unique_together(self):
        """Test get_unique_field_names returns fields from unique_together."""

        class TestModel2(BaseModel):
            class Meta:
                unique_together = (("created_by", "updated_by"),)

        unique_fields = TestModel2.get_unique_field_names()
        self.assertEqual(unique_fields, ["created_by", "updated_by"])

    def test_get_unique_field_names_unique_field(self):
        """Test get_unique_field_names returns fields from unique_field."""

        class TestModel3(BaseModel):
            unique_field = models.CharField(max_length=255, unique=True)

        unique_fields = TestModel3.get_unique_field_names()
        self.assertEqual(unique_fields, ["unique_field"])

    def test_get_unique_field_names_pk(self):
        """Test get_unique_field_names returns fields from pk."""

        class TestModel4(BaseModel):
            code = models.CharField(max_length=255, primary_key=True)

        unique_fields = TestModel4.get_unique_field_names()
        self.assertEqual(unique_fields, ["code"])

    def test_get_unique_field_names_without_unique(self):
        """Test get_unique_field_names returns empty list when no unique fields are defined."""

        class TestModel5(BaseModel):
            pass

        unique_fields = TestModel5.get_unique_field_names()
        self.assertEqual(unique_fields, [])

    def test_get_base_model_fields(self):
        """Test get_base_model_fields returns correct fields."""

        class TestModel6(BaseModel):
            pass

        base_fields = [f.name for f in TestModel6.get_base_model_fields()]
        expected_field_names = ["created_by", "created_at", "updated_by", "updated_at", "deleted_flg"]
        self.assertEqual(set(base_fields), set(expected_field_names))

    def test_get_local_concrete_fields_empty_model(self):
        """Test get_local_concrete_fields returns empty dict for model without custom fields."""

        class TestModel7(BaseModel):
            pass

        local_fields = [f.name for f in TestModel7.get_local_concrete_fields()]
        # Should not include BaseModel fields (created_by, created_at, updated_by, updated_at, deleted_flg)
        # Should not include auto-created fields (id)
        self.assertEqual(local_fields, [])

    def test_get_local_concrete_fields_with_custom_fields(self):
        """Test get_local_concrete_fields returns only custom fields."""

        class TestModel8(BaseModel):
            name = models.CharField(max_length=100)
            code = models.CharField(max_length=50)
            is_active = models.BooleanField(default=True)

        local_fields = [f.name for f in TestModel8.get_local_concrete_fields()]
        expected_field_names = ["name", "code", "is_active"]
        self.assertEqual(set(local_fields), set(expected_field_names))

    def test_get_local_concrete_fields_excludes_base_fields(self):
        """Test get_local_concrete_fields excludes BaseModel fields."""

        class TestModel9(BaseModel):
            custom_field = models.CharField(max_length=100)

        local_fields = [f.name for f in TestModel9.get_local_concrete_fields()]
        base_field_names = ["created_by", "created_at", "updated_by", "updated_at", "deleted_flg"]

        # Verify base fields are not included
        for base_field in base_field_names:
            self.assertNotIn(base_field, local_fields)

        # Verify custom field is included
        self.assertIn("custom_field", local_fields)

    def test_get_local_concrete_fields_excludes_auto_created(self):
        """Test get_local_concrete_fields excludes auto-created fields like reverse relations."""

        class TestModel10(BaseModel):
            name = models.CharField(max_length=100)

        class TestModel11(BaseModel):
            test_model = models.ForeignKey(TestModel10, on_delete=models.CASCADE, related_name="related_models")

        # TestModel10 should not include the reverse relation 'related_models'
        local_fields_10 = [f.name for f in TestModel10.get_local_concrete_fields()]
        self.assertNotIn("related_models", local_fields_10)
        self.assertIn("name", local_fields_10)

        # TestModel11 should include the FK field 'test_model'
        local_fields_11 = [f.name for f in TestModel11.get_local_concrete_fields()]
        self.assertIn("test_model", local_fields_11)

    def test_get_local_concrete_fields_with_foreign_key(self):
        """Test get_local_concrete_fields includes foreign key fields."""

        class TestModel12(BaseModel):
            name = models.CharField(max_length=100)

        class TestModel13(BaseModel):
            reference = models.ForeignKey(TestModel12, on_delete=models.CASCADE)
            description = models.TextField()

        local_fields = [f.name for f in TestModel13.get_local_concrete_fields()]

        # Should include FK field and regular field
        self.assertIn("reference", local_fields)
        self.assertIn("description", local_fields)


@pytest.mark.unit
@pytest.mark.models
class MasterModelTest(TestCase):
    """Test cases for the MasterModel abstract base class."""

    databases = {"default", "postgres"}

    def test_master_model_is_abstract(self):
        """Test that MasterModel is properly configured as abstract."""
        self.assertTrue(MasterModel._meta.abstract)

    def test_master_model_inherits_base_model(self):
        """Test that MasterModel inherits from BaseModel."""
        self.assertTrue(issubclass(MasterModel, BaseModel))

    def test_master_model_validity_fields(self):
        """Test that MasterModel validity fields have correct properties."""
        # Test valid_from field
        valid_from_field = MasterModel._meta.get_field("valid_from")
        self.assertEqual(valid_from_field.__class__.__name__, "DateField")

        # Test valid_to field
        valid_to_field = MasterModel._meta.get_field("valid_to")
        self.assertEqual(valid_to_field.__class__.__name__, "DateField")
        self.assertFalse(valid_to_field.null)

    def test_clean(self):
        """Test that clean method raises ValidationError when valid_to < valid_from."""
        instance = TestMasterModel(name="Test", valid_from="2024-01-01", valid_to="2023-12-31")
        with self.assertRaises(ValidationError):
            instance.clean()

    def test_clean_valid_dates(self):
        """Test that clean method passes when valid_to >= valid_from."""
        instance = TestMasterModel(name="Test", valid_from="2024-01-01", valid_to="2024-12-31")
        # Should not raise any exception
        instance.clean()

    def test_default_valid_from_date(self):
        """Test that default_valid_from_date returns tomorrow's date."""
        from django.utils import timezone

        from sfd.models.base import default_valid_from_date

        result = default_valid_from_date()
        expected = timezone.now().date() + timezone.timedelta(days=1)
        self.assertEqual(result, expected)

    def test_default_valid_to_date(self):
        """Test that default_valid_to_date returns maximum date."""
        from django.utils import timezone

        from sfd.models.base import default_valid_to_date

        result = default_valid_to_date()
        expected = timezone.datetime(2222, 12, 31).date()
        self.assertEqual(result, expected)

    def test_get_master_model_fields(self):
        """Test get_master_model_fields returns correct fields."""
        master_fields = [f.name for f in TestMasterModel.get_master_model_fields()]
        expected_field_names = ["valid_from", "valid_to"]
        self.assertEqual(set(master_fields), set(expected_field_names))

    def test_get_local_concrete_fields_master_model(self):
        """Test get_local_concrete_fields excludes MasterModel and BaseModel fields."""
        local_fields = [f.name for f in TestMasterModel.get_local_concrete_fields()]

        # Should not include BaseModel fields
        base_field_names = ["created_by", "created_at", "updated_by", "updated_at", "deleted_flg"]
        for base_field in base_field_names:
            self.assertNotIn(base_field, local_fields)

        # Should not include MasterModel fields
        master_field_names = ["valid_from", "valid_to"]
        for master_field in master_field_names:
            self.assertNotIn(master_field, local_fields)

        # Should include custom field
        self.assertIn("name", local_fields)

    def test_get_unique_fields_without_valid_from(self):
        """Test get_unique_fields_without_valid_from excludes valid_from."""
        # TestMasterModel has unique_together constraint on ('name', 'valid_from')
        unique_fields = list(TestMasterModel.get_unique_fields_without_valid_from())
        self.assertIn("name", unique_fields)
        self.assertNotIn("valid_from", unique_fields)

    def test_get_previous_instance(self):
        """Test get_previous_instance returns the previous record based on valid_from."""
        from django.utils import timezone

        # Create three instances with different valid_from dates
        instance1 = TestMasterModel.objects.create(
            name="Test",
            valid_from=timezone.datetime.strptime("2024-01-01", "%Y-%m-%d").date(),
            valid_to=timezone.datetime.strptime("2024-06-30", "%Y-%m-%d").date(),
        )
        instance2 = TestMasterModel.objects.create(
            name="Test",
            valid_from=timezone.datetime.strptime("2024-07-01", "%Y-%m-%d").date(),
            valid_to=timezone.datetime.strptime("2024-12-31", "%Y-%m-%d").date(),
        )
        instance3 = TestMasterModel.objects.create(
            name="Test",
            valid_from=timezone.datetime.strptime("2025-01-01", "%Y-%m-%d").date(),
            valid_to=timezone.datetime.strptime("2025-12-31", "%Y-%m-%d").date(),
        )

        # Test that instance3 can find instance2 as previous
        previous = instance3.get_previous_instance()
        self.assertEqual(previous.pk, instance2.pk)

        # Test that instance2 can find instance1 as previous
        previous = instance2.get_previous_instance()
        self.assertEqual(previous.pk, instance1.pk)

        # Test that instance1 has no previous
        previous = instance1.get_previous_instance()
        self.assertIsNone(previous)

    def test_get_previous_instance_no_unique_fields(self):
        """Test get_previous_instance returns None when no unique fields are defined."""
        from django.utils import timezone

        # Use a unique model name to avoid registration conflicts
        class TestModelNoUniqueForPrevious(MasterModel):
            class Meta:
                app_label = "sfd"

        instance = TestModelNoUniqueForPrevious(
            valid_from=timezone.datetime.strptime("2024-01-01", "%Y-%m-%d").date(),
            valid_to=timezone.datetime.strptime("2024-12-31", "%Y-%m-%d").date(),
        )
        previous = instance.get_previous_instance()
        self.assertIsNone(previous)

    def test_get_next_instance(self):
        """Test get_next_instance returns the next record based on valid_from."""
        from django.utils import timezone

        # Create three instances with different valid_from dates
        instance1 = TestMasterModel.objects.create(
            name="Test",
            valid_from=timezone.datetime.strptime("2024-01-01", "%Y-%m-%d").date(),
            valid_to=timezone.datetime.strptime("2024-06-30", "%Y-%m-%d").date(),
        )
        instance2 = TestMasterModel.objects.create(
            name="Test",
            valid_from=timezone.datetime.strptime("2024-07-01", "%Y-%m-%d").date(),
            valid_to=timezone.datetime.strptime("2024-12-31", "%Y-%m-%d").date(),
        )
        instance3 = TestMasterModel.objects.create(
            name="Test",
            valid_from=timezone.datetime.strptime("2025-01-01", "%Y-%m-%d").date(),
            valid_to=timezone.datetime.strptime("2025-12-31", "%Y-%m-%d").date(),
        )

        # Test that instance1 can find instance2 as next
        next_instance = instance1.get_next_instance()
        self.assertEqual(next_instance.pk, instance2.pk)

        # Test that instance2 can find instance3 as next
        next_instance = instance2.get_next_instance()
        self.assertEqual(next_instance.pk, instance3.pk)

        # Test that instance3 has no next
        next_instance = instance3.get_next_instance()
        self.assertIsNone(next_instance)

    def test_get_next_instance_no_unique_fields(self):
        """Test get_next_instance returns None when no unique fields are defined."""
        from django.utils import timezone

        # Use a unique model name to avoid registration conflicts
        class TestModelNoUniqueForNext(MasterModel):
            class Meta:
                app_label = "sfd"

        instance = TestModelNoUniqueForNext(
            valid_from=timezone.datetime.strptime("2024-01-01", "%Y-%m-%d").date(),
            valid_to=timezone.datetime.strptime("2024-12-31", "%Y-%m-%d").date(),
        )
        next_instance = instance.get_next_instance()
        self.assertIsNone(next_instance)

    def test_save_adjusts_previous_valid_to(self):
        """Test that save method adjusts previous instance's valid_to when overlapping."""
        from django.utils import timezone

        # Create first instance
        instance1 = TestMasterModel.objects.create(
            name="Test",
            valid_from=timezone.datetime.strptime("2024-01-01", "%Y-%m-%d").date(),
            valid_to=timezone.datetime.strptime("2024-12-31", "%Y-%m-%d").date(),
        )

        # Create second instance with overlapping dates
        # We don't need to reference instance2 directly - we're testing the side effect on instance1
        _instance2 = TestMasterModel.objects.create(
            name="Test",
            valid_from=timezone.datetime.strptime("2024-07-01", "%Y-%m-%d").date(),
            valid_to=timezone.datetime.strptime("2025-12-31", "%Y-%m-%d").date(),
            updated_by="admin",
        )

        # Reload instance1 to get updated values
        instance1.refresh_from_db()

        # Instance1's valid_to should be adjusted to 2024-06-30 (one day before instance2's valid_from)
        expected_valid_to = timezone.datetime.strptime("2024-06-30", "%Y-%m-%d").date()
        self.assertEqual(instance1.valid_to, expected_valid_to)
        # Verify instance2 was created (use the variable to avoid linting warning)
        self.assertIsNotNone(_instance2)

    def test_save_adjusts_current_valid_to_for_next(self):
        """Test that save method adjusts current instance's valid_to when next instance overlaps."""
        from django.utils import timezone

        # Create first instance
        instance1 = TestMasterModel.objects.create(
            name="Test",
            valid_from=timezone.datetime.strptime("2024-01-01", "%Y-%m-%d").date(),
            valid_to=timezone.datetime.strptime("2024-12-31", "%Y-%m-%d").date(),
        )

        # Create third instance (future)
        # We don't need to reference instance3 directly - we're testing the side effect on instance1
        _instance3 = TestMasterModel.objects.create(
            name="Test",
            valid_from=timezone.datetime.strptime("2025-01-01", "%Y-%m-%d").date(),
            valid_to=timezone.datetime.strptime("2025-12-31", "%Y-%m-%d").date(),
        )

        # Update instance1 to extend its valid_to past instance3's valid_from
        instance1.valid_to = timezone.datetime.strptime("2025-06-30", "%Y-%m-%d").date()
        instance1.save()

        # Instance1's valid_to should be adjusted to 2024-12-31 (one day before instance3's valid_from)
        expected_valid_to = timezone.datetime.strptime("2024-12-31", "%Y-%m-%d").date()
        self.assertEqual(instance1.valid_to, expected_valid_to)
        # Verify instance3 was created (use the variable to avoid linting warning)
        self.assertIsNotNone(_instance3)

    def test_save_sets_default_valid_to_when_none(self):
        """Test that save method sets default valid_to when None."""
        from django.utils import timezone

        from sfd.models.base import default_valid_to_date

        # Create instance with valid_to=None
        instance = TestMasterModel(
            name="Test",
            valid_from=timezone.datetime.strptime("2024-01-01", "%Y-%m-%d").date(),
        )
        instance.valid_to = None
        instance.save()

        # valid_to should be set to default
        expected_valid_to = default_valid_to_date()
        self.assertEqual(instance.valid_to, expected_valid_to)

    def test_save_does_not_adjust_same_instance(self):
        """Test that save method doesn't adjust dates when previous/next is the same instance."""
        from django.utils import timezone

        # Create instance
        instance = TestMasterModel.objects.create(
            name="Test",
            valid_from=timezone.datetime.strptime("2024-01-01", "%Y-%m-%d").date(),
            valid_to=timezone.datetime.strptime("2024-12-31", "%Y-%m-%d").date(),
        )

        # Update the same instance
        instance.valid_from = timezone.datetime.strptime("2024-02-01", "%Y-%m-%d").date()
        instance.save()

        # valid_to should remain unchanged
        expected_valid_to = timezone.datetime.strptime("2024-12-31", "%Y-%m-%d").date()
        self.assertEqual(instance.valid_to, expected_valid_to)
