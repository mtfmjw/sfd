import logging
from typing import Any

from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView

logger = logging.getLogger(__name__)


class IndexView(LoginRequiredMixin, TemplateView):
    """
    Main application homepage view for authenticated users.

    This view renders the main landing page of the SFD application and serves
    as the primary entry point for authenticated users. It requires user
    authentication and provides basic context information for the homepage template.

    The view integrates with Django's authentication system to ensure only
    logged-in users can access the application's main interface.

    Attributes:
        template_name (str): Path to the homepage template file

    Mixins:
        LoginRequiredMixin: Ensures only authenticated users can access this view.
                           Redirects unauthenticated users to the login page.

    Template Context:
        title (str): Page title displayed in the browser and page header

    URL Mapping:
        Typically mapped to the root URL pattern ('/') in the application's
        URL configuration.

    Security:
        - Requires user authentication
        - Logs access attempts for audit purposes
        - Integrates with Django's session management

    Example:
        URL: http://example.com/
        Template: sfd/index.html
        Access: Requires valid Django user session
    """

    template_name = "sfd/index.html"

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        """
        Add application-specific context data to the template.

        Extends the base template context with homepage-specific information
        and logs the access for audit and monitoring purposes.

        Args:
            **kwargs: Additional keyword arguments passed to the parent method

        Returns:
            dict: Template context dictionary containing:
                - All parent context data
                - title: Application title for display in browser and templates

        Side Effects:
            Logs an INFO-level message recording the homepage access,
            which includes user and IP information via the RequestLoggingFilter.
        """
        logger.info("IndexView accessed - rendering home page")
        context = super().get_context_data(**kwargs)
        context["title"] = _("SFD - Django Application")
        return context
