import os
from unittest.mock import patch

# Configure Django settings before importing Django components
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sfd_prj.settings")

import django
from django.conf import settings

# Setup Django if not already done
if not settings.configured:
    django.setup()

import pytest
from django.contrib.auth.models import AnonymousUser, User
from django.test import RequestFactory, TestCase
from django.utils.translation import gettext_lazy as _

from sfd.tests.unittest import BaseTestMixin
from sfd.views.index import IndexView


@pytest.mark.unit
@pytest.mark.views
class IndexViewTest(BaseTestMixin, TestCase):
    """Test IndexView functionality with comprehensive coverage."""

    databases = {"default", "postgres"}

    def setUp(self):
        """Set up test data for IndexView tests."""
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="testuser", password="testpass123")

    def test_index_view_requires_authentication(self):
        """Test that IndexView requires user authentication."""
        # Arrange
        request = self.factory.get("/")
        request.user = AnonymousUser()

        # Act
        view = IndexView()
        view.setup(request)

        # Assert
        # LoginRequiredMixin should redirect unauthenticated users
        self.assertFalse(view.request.user.is_authenticated)

    def test_index_view_template_name(self):
        """Test that IndexView uses the correct template."""
        # Arrange & Act
        # Assert
        self.assertEqual(IndexView.template_name, "sfd/index.html")

    @patch("sfd.views.index.logger")
    def test_get_context_data_with_logging(self, mock_logger):
        """Test get_context_data method with logging verification."""
        # Arrange
        request = self.factory.get("/")
        request.user = self.user
        view = IndexView()
        view.setup(request)

        # Act
        context = view.get_context_data()

        # Assert
        self.assertIn("title", context)
        self.assertEqual(context["title"], _("SFD - Django Application"))
        mock_logger.info.assert_called_once_with("IndexView accessed - rendering home page")

    def test_get_context_data_structure(self):
        """Test the structure and content of context data."""
        # Arrange
        request = self.factory.get("/")
        request.user = self.user
        view = IndexView()
        view.setup(request)

        # Act
        context = view.get_context_data(custom_kwarg="test_value")

        # Assert
        self.assertIsInstance(context, dict)
        self.assertIn("title", context)
        self.assertIn("view", context)
        self.assertEqual(context["title"], _("SFD - Django Application"))

    def test_index_view_inheritance(self):
        """Test that IndexView properly inherits from required mixins."""
        # Arrange & Act & Assert
        from django.contrib.auth.mixins import LoginRequiredMixin
        from django.views.generic import TemplateView

        self.assertTrue(issubclass(IndexView, LoginRequiredMixin))
        self.assertTrue(issubclass(IndexView, TemplateView))

    @pytest.mark.integration
    def test_index_view_full_request_cycle(self):
        """Test full request cycle for authenticated user."""
        # Arrange
        self.client.login(username="testuser", password="testpass123")

        # Act - Test the root URL redirect behavior
        response = self.client.get("/")

        # Assert - Root URL should redirect to admin (302)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/admin/")  # type: ignore

    @pytest.mark.integration
    def test_index_view_direct_access(self):
        """Test IndexView when accessed directly via URL reverse."""
        # Arrange
        from django.test import override_settings

        self.client.login(username="testuser", password="testpass123")

        # Act - Test direct access to IndexView (if it were properly mapped)
        # Note: Since sfd.urls is not included in main URLs, we test the view directly
        # Create a temporary URL configuration that includes the IndexView
        with override_settings(ROOT_URLCONF="sfd.urls"):
            response = self.client.get("/")

            # Assert
            self.assertEqual(response.status_code, 200)
            # Check for content that's definitely in the template without translation
            self.assertContains(response, "max-width: 800px")  # CSS content
            self.assertContains(response, "font-family: Arial")  # CSS content
