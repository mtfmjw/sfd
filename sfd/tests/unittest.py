"""
Test utilities for SFD application tests.

This module provides common utilities, fixtures, and helper functions
for unit and integration tests across the SFD application.
"""

from unittest.mock import Mock

from django.contrib.auth.models import AnonymousUser
from django.db import models
from django.test import RequestFactory

from sfd.common.encrypted import EncryptedCharField, EncryptedEmailField, EncryptedTextField
from sfd.models.base import BaseModel, MasterModel


class TestUserFactory:
    """
    Factory class for creating test users without database operations.

    This factory creates mock user objects that behave like Django User
    instances but don't require database access, making tests faster
    and avoiding database dependency issues.
    """

    @staticmethod
    def create_user(username="testuser", email=None, is_staff=False, is_superuser=False, is_active=True):
        """
        Create a mock user with specified attributes.

        Args:
            username (str): Username for the mock user
            email (str): Email address (defaults to username@test.com)
            is_staff (bool): Whether user is staff
            is_superuser (bool): Whether user is superuser
            is_active (bool): Whether user is active

        Returns:
            Mock: Configured mock user object that behaves like Django User
        """
        user = Mock()
        user.username = username
        user.email = email or f"{username}@test.com"
        user.first_name = username.capitalize()
        user.last_name = "Test"
        user.is_staff = is_staff
        user.is_superuser = is_superuser
        user.is_active = is_active
        user.is_authenticated = True
        user.pk = hash(username) % 10000  # Generate consistent fake ID
        user.id = user.pk

        # Add __str__ method for realistic behavior
        user.__str__ = lambda: username

        return user

    @staticmethod
    def create_superuser(username="admin", email=None):
        """
        Create a mock superuser.

        Args:
            username (str): Username for the superuser
            email (str): Email address (defaults to username@test.com)

        Returns:
            Mock: Configured mock superuser object
        """
        return TestUserFactory.create_user(username=username, email=email, is_staff=True, is_superuser=True)

    @staticmethod
    def create_staff_user(username="staff", email=None):
        """
        Create a mock staff user.

        Args:
            username (str): Username for the staff user
            email (str): Email address (defaults to username@test.com)

        Returns:
            Mock: Configured mock staff user object
        """
        return TestUserFactory.create_user(username=username, email=email, is_staff=True, is_superuser=False)

    @staticmethod
    def create_anonymous_user():
        """
        Create an anonymous user instance.

        Returns:
            AnonymousUser: Django's AnonymousUser instance
        """
        return AnonymousUser()


class BaseTestMixin:
    """
    Mixin class providing common test utilities and setup.

    This mixin can be used with Django TestCase classes to provide
    common functionality like request factory, mock users, and
    utility methods.
    """

    def setUp(self):
        """Set up common test fixtures."""
        super().setUp()  # type: ignore

        self.factory = RequestFactory()
        self.user_factory = TestUserFactory()

        # Create common test users
        self.user = self.user_factory.create_user()
        self.superuser = self.user_factory.create_superuser()
        self.staff_user = self.user_factory.create_staff_user()
        self.anonymous_user = self.user_factory.create_anonymous_user()

    def create_request(self, path="/", method="GET", user=None, **kwargs):
        """
        Create a request with optional user.

        Args:
            path (str): Request path
            method (str): HTTP method
            user: User object to attach to request
            **kwargs: Additional arguments for request factory

        Returns:
            HttpRequest: Configured request object
        """
        factory_method = getattr(self.factory, method.lower())
        request = factory_method(path, **kwargs)

        if user is not None:
            request.user = user
        else:
            request.user = self.anonymous_user

        return request


class TestModel(models.Model):
    name = models.CharField(max_length=100, verbose_name="Name", help_text="Test model name")
    email = models.EmailField(verbose_name="Email", null=True, blank=True)
    is_active = models.BooleanField(default=True, null=True, blank=True, verbose_name="Active", help_text="Active flag")
    date = models.DateField(verbose_name="Date", null=True, blank=True, help_text="Test date field")

    class Meta:
        db_table = "test_model"
        verbose_name = "Test Model"
        verbose_name_plural = "Test Models"
        app_label = "sfd"
        ordering = ["-date"]


class TestInlineModel(models.Model):
    name = models.CharField(max_length=100, verbose_name="Name", help_text="Inline model name")
    parent = models.ForeignKey(TestModel, on_delete=models.CASCADE, related_name="submodels", verbose_name="Parent", help_text="Related TestModel")
    description = models.TextField(verbose_name="Description", help_text="Inline model description")

    class Meta:
        db_table = "test_inline_model"
        verbose_name = "Test Inline Model"
        verbose_name_plural = "Test Inline Models"
        app_label = "sfd"


class TestBaseModel(BaseModel):
    name = models.CharField(max_length=100, verbose_name="Name", help_text="Test model name", unique=True)
    email = models.EmailField(verbose_name="Email", null=True, blank=True)
    is_active = models.BooleanField(default=True, null=True, blank=True, verbose_name="Active", help_text="Active flag")
    date = models.DateField(verbose_name="Date", null=True, blank=True, help_text="Test date field")

    class Meta:  # type: ignore
        # db_table = "test_base_model"
        verbose_name = "Test Base Model"
        verbose_name_plural = "Test Base Models"
        app_label = "sfd"

        constraints = [models.UniqueConstraint(fields=["name"], name="unique_basemodel_name_valid_from")]


class TestMasterModel(MasterModel):
    name = models.CharField(max_length=100, verbose_name="Name", help_text="Test model name")
    email = models.EmailField(verbose_name="Email", null=True, blank=True)
    is_active = models.BooleanField(default=True, null=True, blank=True, verbose_name="Active", help_text="Active flag")
    date = models.DateField(verbose_name="Date", null=True, blank=True, help_text="Test date field")

    class Meta:  # type: ignore
        db_table = "test_master_model"
        verbose_name = "Test Master Model"
        verbose_name_plural = "Test Master Models"
        app_label = "sfd"

        constraints = [models.UniqueConstraint(fields=["name", "valid_from"], name="unique_mastermodel_name_valid_from")]


class TestEncryptedModel(models.Model):
    """Test model with encrypted fields for testing encryption during upload."""

    name = EncryptedCharField(max_length=255, original_max_length=100, verbose_name="Encrypted Name")
    email = EncryptedEmailField(max_length=385, original_max_length=254, verbose_name="Encrypted Email", null=True, blank=True)
    notes = EncryptedTextField(verbose_name="Encrypted Notes", null=True, blank=True)

    class Meta:
        db_table = "test_encrypted_model"
        verbose_name = "Test Encrypted Model"
        verbose_name_plural = "Test Encrypted Models"
        app_label = "sfd"
