from django.contrib import admin
from django.contrib.admin import AdminSite
from django.contrib.auth.models import Group, User
from django.contrib.auth.views import LoginView
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from sfd.models.csv_log import CsvLog
from sfd.models.holiday import Holiday
from sfd.models.municipality import Municipality
from sfd.models.person import Person
from sfd.models.postcode import Postcode
from sfd.views.common.csv_log import CsvLogAdmin
from sfd.views.group import SfdGroupAdmin
from sfd.views.holiday import HolidayAdmin
from sfd.views.municipality import MunicipalityAdmin
from sfd.views.person import PersonAdmin
from sfd.views.postcode import PostcodeAdmin
from sfd.views.user import SfdUserAdmin


class SfdAdminSite(AdminSite):
    """Custom admin site that allows any authenticated user to access with ordered app list.

    This custom Django admin site extends the default AdminSite to provide
    a more permissive authentication model and custom organization of the
    admin interface. It allows any authenticated user to access the admin
    without requiring staff permissions, and provides custom ordering for
    applications and models in the admin index.


    Attributes:
        site_header (str): The header text displayed in the admin interface
        site_title (str): The title text used in browser tabs and page titles
        index_title (str): The title displayed on the admin index page

    Features:
        - Allows access for any authenticated user (not just staff)
        - Custom model ordering within applications
        - Japanese localization support through gettext_lazy
    """

    site_header = _("sfd")
    site_title = _("sfd Admin")
    index_title = _("sfd Administration")

    login_template = "registration/login.html"

    def has_permission(self, request):
        """Allow any authenticated user to access the admin.

        This method overrides Django's default admin permission checking
        which normally requires users to have is_staff=True. Instead, this
        implementation allows any authenticated user to access the admin
        interface, making it more accessible for business users.

        Args:
            request (HttpRequest): The HTTP request object containing user information

        Returns:
            bool: True if the user is authenticated, False otherwise

        Note:
            This is less secure than the default Django admin behavior and should
            only be used in trusted environments where all authenticated users
            should have admin access.
        """
        return request.user.is_authenticated

    def login(self, request, extra_context=None):
        """
        Overrides the default admin login view to allow any active user.
        """
        # If the user is already authenticated, redirect them to the admin index.
        if request.user.is_authenticated:
            return HttpResponseRedirect(reverse_lazy("admin:index"))

        # If they are not authenticated, display the login form.
        # We are essentially using the standard LoginView, but within our custom admin site.
        return LoginView.as_view(
            template_name=self.login_template,
            extra_context={
                **self.each_context(request),
                **(extra_context or {}),
            },
        )(request)


# Create custom admin site instance
admin_site = SfdAdminSite(name="sfdadmin")

# Set the default admin site to our custom one
admin.site = admin_site
admin.sites.site = admin_site

# Customize the default admin site as well (fallback)
admin.site.site_header = "sfd"
admin.site.site_title = "sfd Admin"
admin.site.index_title = "sfd Administration"

# Register default Django models with our custom admin site
admin_site.register(Group, SfdGroupAdmin)
admin_site.register(User, SfdUserAdmin)

admin_site.register(Holiday, HolidayAdmin)
admin_site.register(Municipality, MunicipalityAdmin)
admin_site.register(Postcode, PostcodeAdmin)
admin_site.register(Person, PersonAdmin)
admin_site.register(CsvLog, CsvLogAdmin)
