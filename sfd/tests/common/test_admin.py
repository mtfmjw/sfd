# type: ignore
"""Test cases for sfd.admin module.

This module contains comprehensive test cases for the SfdAdminSite class
and admin configuration, including custom permissions, app/model ordering,
and admin site customization features.
"""

from unittest.mock import Mock, patch

import pytest
from django.contrib.admin import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Group
from django.contrib.auth.views import LoginView
from django.http import HttpResponseRedirect
from django.test import TestCase
from django.urls import reverse_lazy

from sfd.admin import SfdAdminSite, admin_site
from sfd.tests.unittest import BaseTestMixin

User = get_user_model()


@pytest.mark.unit
@pytest.mark.common
class SfdAdminSiteTest(BaseTestMixin, TestCase):
    """Test cases for the SfdAdminSite class.

    Tests the custom Django admin site functionality including permissive
    authentication, custom app/model ordering, and admin interface
    customization. The custom admin site allows any authenticated user
    to access the admin interface and provides business-logical ordering
    of applications and models.

    Features:
        - Permissive authentication (any authenticated user can access)
        - Japanese localization support
        - Custom branding and titles

    Usage:
        ```python
        admin_site = SfdAdminSite(name="sfdadmin")
        has_access = admin_site.has_permission(request)
        app_list = admin_site.get_app_list(request)
        ```
    """

    def setUp(self):
        """Set up test fixtures for each test method.

        Creates a fresh SfdAdminSite instance, request factory, and test users
        for testing admin site functionality.
        """
        super().setUp()
        self.admin_site = SfdAdminSite(name="test_sfd_admin")
        self.request = self.factory.get("/admin/")

        # Create test users
        self.authenticated_user = self.user_factory.create_user(username="testuser")
        self.request.user = self.authenticated_user

    def test_admin_site_initialization(self):
        """Test that SfdAdminSite initializes with correct configuration."""
        # Test instance type
        self.assertIsInstance(self.admin_site, AdminSite)
        self.assertIsInstance(self.admin_site, SfdAdminSite)

        # Test site branding attributes - they should be translation objects
        # The actual translated text may vary based on language settings
        site_header_str = str(self.admin_site.site_header)
        site_title_str = str(self.admin_site.site_title)
        index_title_str = str(self.admin_site.index_title)

        # Should contain "sfd" in the text (regardless of language)
        self.assertIn("sfd", site_header_str.lower())
        self.assertIn("sfd", site_title_str.lower())
        self.assertIn("sfd", index_title_str.lower())

        # Test custom name
        self.assertEqual(self.admin_site.name, "test_sfd_admin")

    def test_has_permission_authenticated_user(self):
        """Test has_permission allows any authenticated user."""

        # Should allow access for authenticated user
        result = self.admin_site.has_permission(self.request)
        self.assertTrue(result)

    def test_has_permission_staff_user(self):
        """Test has_permission allows staff users."""
        self.request.user = self.staff_user

        result = self.admin_site.has_permission(self.request)
        self.assertTrue(result)

    def test_has_permission_superuser(self):
        """Test has_permission allows superusers."""
        self.request.user = self.superuser

        result = self.admin_site.has_permission(self.request)
        self.assertTrue(result)

    def test_has_permission_anonymous_user(self):
        """Test has_permission denies anonymous users."""
        self.request.user = AnonymousUser()

        result = self.admin_site.has_permission(self.request)
        self.assertFalse(result)

    def test_has_permission_unauthenticated_user(self):
        """Test has_permission denies unauthenticated users."""
        # Create user but don't authenticate
        user = Mock()
        user.is_authenticated = False
        self.request.user = user

        result = self.admin_site.has_permission(self.request)
        self.assertFalse(result)

    def test_custom_admin_site_instance_creation(self):
        """Test that module-level admin_site instance is created correctly."""
        # Test that admin_site is instance of SfdAdminSite
        self.assertIsInstance(admin_site, SfdAdminSite)
        self.assertEqual(admin_site.name, "sfdadmin")

    def test_default_admin_site_customization(self):
        """Test that default admin site is customized with proper branding."""
        from django.contrib import admin

        # Test that default admin site has custom branding
        # Values may be translated based on language settings
        site_header_str = str(admin.site.site_header)
        site_title_str = str(admin.site.site_title)
        index_title_str = str(admin.site.index_title)

        # Should contain "sfd" regardless of language
        self.assertIn("sfd", site_header_str.lower())
        self.assertIn("sfd", site_title_str.lower())
        self.assertIn("sfd", index_title_str.lower())

    def test_user_admin_registration(self):
        """Test that User and Group models are registered with custom admin site."""
        # Check that User model is registered
        self.assertIn(User, admin_site._registry)

        # Check that Group model is registered
        self.assertIn(Group, admin_site._registry)

    def test_sfd_models_registration(self):
        """Test that SFD models are registered with custom admin site."""
        from sfd.models.holiday import Holiday
        from sfd.models.municipality import Municipality

        # Check that Holiday model is registered
        self.assertIn(Holiday, admin_site._registry)

        # Check that Municipality model is registered
        self.assertIn(Municipality, admin_site._registry)

    def test_admin_classes_registration(self):
        """Test that proper admin classes are used for registered models."""
        from sfd.models.holiday import Holiday
        from sfd.models.municipality import Municipality
        from sfd.views.holiday import HolidayAdmin
        from sfd.views.municipality import MunicipalityAdmin

        # Check that correct admin classes are used
        self.assertIsInstance(admin_site._registry[Holiday], HolidayAdmin)
        self.assertIsInstance(admin_site._registry[Municipality], MunicipalityAdmin)

    def test_site_branding_internationalization(self):
        """Test that site branding uses internationalization."""
        # Test that branding attributes are using gettext_lazy
        # This is done by checking if they're wrapped translation objects
        site_header = self.admin_site.site_header
        site_title = self.admin_site.site_title
        index_title = self.admin_site.index_title

        # Should be able to convert to string (indicates lazy translation)
        site_header_str = str(site_header)
        site_title_str = str(site_title)
        index_title_str = str(index_title)

        # Should contain "sfd" regardless of language
        self.assertIn("sfd", site_header_str.lower())
        self.assertIn("sfd", site_title_str.lower())
        self.assertIn("sfd", index_title_str.lower())

        # Should not be empty (translation working)
        self.assertTrue(len(site_header_str) > 0)
        self.assertTrue(len(site_title_str) > 0)
        self.assertTrue(len(index_title_str) > 0)

    def test_has_permission_edge_cases(self):
        """Test has_permission method with edge cases."""
        # Test with None user
        request = self.factory.get("/admin/")
        request.user = None

        # Should handle None user gracefully
        with self.assertRaises(AttributeError):
            self.admin_site.has_permission(request)

    def test_admin_site_inheritance(self):
        """Test that SfdAdminSite properly inherits from AdminSite."""
        # Test method resolution order
        self.assertTrue(issubclass(SfdAdminSite, AdminSite))

        # Test that we can call parent methods
        self.assertTrue(hasattr(self.admin_site, "_build_app_dict"))
        self.assertTrue(callable(self.admin_site._build_app_dict))

    def test_admin_site_complete_workflow(self):
        """Test complete admin site workflow from authentication to app list."""
        # Create request
        request = self.factory.get("/admin/")
        request.user = self.authenticated_user

        # Test permission check
        has_permission = self.admin_site.has_permission(request)
        self.assertTrue(has_permission)

        # Test app list generation
        app_list = self.admin_site.get_app_list(request)
        self.assertIsInstance(app_list, list)

        # Test that we can access the admin interface elements
        # Values may be translated based on language settings
        site_header_str = str(self.admin_site.site_header)
        site_title_str = str(self.admin_site.site_title)
        index_title_str = str(self.admin_site.index_title)

        # Should contain "sfd" regardless of language
        self.assertIn("sfd", site_header_str.lower())
        self.assertIn("sfd", site_title_str.lower())
        self.assertIn("sfd", index_title_str.lower())

    def test_module_level_configuration(self):
        """Test module-level admin configuration and registrations."""
        from django.contrib import admin

        # Test that admin.site has been replaced
        self.assertIsInstance(admin.site, SfdAdminSite)
        self.assertIsInstance(admin.sites.site, SfdAdminSite)

        # Test fallback configuration on default admin site
        # Values may be translated based on language settings
        site_header_str = str(admin.site.site_header)
        site_title_str = str(admin.site.site_title)
        index_title_str = str(admin.site.index_title)

        # Should contain "sfd" regardless of language
        self.assertIn("sfd", site_header_str.lower())
        self.assertIn("sfd", site_title_str.lower())
        self.assertIn("sfd", index_title_str.lower())

    def test_login_authenticated_user_redirects(self):
        self.request.user.is_authenticated = True
        response = self.admin_site.login(self.request)

        assert isinstance(response, HttpResponseRedirect)
        assert response.url == reverse_lazy("admin:index")

    @patch.object(LoginView, "as_view")
    def test_login_unauthenticated_calls_loginview(self, mock_as_view):
        self.request.user = AnonymousUser()
        mock_view_callable = Mock(return_value="mock-response")
        mock_as_view.return_value = mock_view_callable

        response = admin_site.login(self.request, extra_context={"foo": "bar"})

        # Check that LoginView.as_view was called with the right args
        mock_as_view.assert_called_once()
        kwargs = mock_as_view.call_args.kwargs
        assert kwargs["template_name"] == admin_site.login_template
        assert "foo" in kwargs["extra_context"]

        # Check that the callable returned by as_view was called with request
        mock_view_callable.assert_called_once_with(self.request)

        # The method should return the result of that callable
        assert response == "mock-response"

    def test_get_app_list_with_specific_app_label(self):
        """Test get_app_list when called with a specific app_label parameter."""
        # Create request with authenticated user
        request = self.factory.get("/admin/")
        request.user = self.authenticated_user

        # Test with a specific app (this will return only that app if it exists)
        result = self.admin_site.get_app_list(request, app_label="sfd")

        # Should return a list (may be empty if app not registered)
        self.assertIsInstance(result, list)

        # If app exists, check structure
        if result:
            app = result[0]
            self.assertIsInstance(app, dict)
            self.assertIn("app_label", app)
            self.assertEqual(app["app_label"], "sfd")
            self.assertIn("models", app)

    @patch.object(SfdAdminSite, "_build_app_dict")
    def test_get_app_list_with_specific_app_label_mock(self, mock_build_app_dict):
        """Test get_app_list with specific app_label using mock to ensure consistent behavior."""
        # Mock app_dict with a specific app
        mock_app_dict = {"auth": {"app_label": "auth", "name": "Authentication", "models": []}}
        mock_build_app_dict.return_value = mock_app_dict

        request = self.factory.get("/admin/")
        request.user = self.authenticated_user

        # Test with specific app_label
        result = self.admin_site.get_app_list(request, app_label="auth")

        # Should return list containing only the requested app
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["app_label"], "auth")

        # Verify _build_app_dict was called with the app_label
        mock_build_app_dict.assert_called_once_with(request, "auth")
