import logging

from django.contrib.admin.helpers import AdminForm
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView
from django.views.generic.edit import ModelFormMixin

logger = logging.getLogger(__name__)


class BaseSearchView(ModelFormMixin, ListView):  # type: ignore
    """Base class for search views in the SFD application."""

    model = None  # type: ignore
    form_class = None
    template_name = "sfd/search.html"
    paginate_by = 10
    on_each_side = 2
    on_ends = 2
    is_popup = True

    list_display = ()
    fieldsets = []

    def get_search_result_columns(self) -> dict[str, str]:
        if self.list_display:
            # Build column headers, skipping 'select' for model field lookup
            headers = {}
            for f in self.list_display:  # type: ignore
                if f == "select":
                    headers[f] = _("Select")
                else:
                    headers[f] = self.model._meta.get_field(f).verbose_name
            return headers
        return {}

    def get_query(self, form):
        """This method should be implemented to return a Q object based on cleaned_data"""
        # Get field names from list_display, excluding special fields like 'select'
        field_names = [f for f in self.list_display if f != "select"]
        criteria = {key: value for key, value in form.cleaned_data.items() if key in field_names and value}
        if any(v for v in criteria.values()):
            return Q(**criteria)
        return Q()

    def get_queryset(self):
        queryset = super().get_queryset()
        form = self.form_class(self.request.GET)  # type: ignore
        if form.is_valid():
            q = self.get_query(form)
            if q:
                queryset = queryset.filter(q)
            else:
                # Return empty queryset if no valid search criteria
                return queryset.none()

        # Ensure queryset is ordered to avoid pagination warnings
        if not queryset.ordered:
            # Try to use model's default ordering first
            if hasattr(self.model, "_meta") and self.model._meta.ordering:
                queryset = queryset.order_by(*self.model._meta.ordering)
            # Fallback to common date fields, then pk
            elif hasattr(self.model, "date"):
                queryset = queryset.order_by("date")
            elif hasattr(self.model, "created_at"):
                queryset = queryset.order_by("created_at")
            else:
                queryset = queryset.order_by("pk")

        return queryset

    def get_form_kwargs(self):
        # Get the default kwargs
        kwargs = super().get_form_kwargs()
        # Update with GET data, or None if no search has been made
        kwargs["data"] = self.request.GET or None
        return kwargs

    def get_context_data(self, **kwargs):
        if not hasattr(self, "object"):
            self.object = None
        context = super().get_context_data(**kwargs)

        context["search_url"] = self.request.path
        context["page_link_url"] = self.request.get_full_path()
        context["search_form"] = self.form_class(self.request.GET or None)  # type: ignore
        context["is_popup"] = self.is_popup
        context["headers"] = self.get_search_result_columns().values()
        context["list_display"] = self.list_display

        adminform = AdminForm(
            form=self.get_form(),
            fieldsets=self.fieldsets,
            prepopulated_fields={},
            readonly_fields=(),
            model_admin=None,  # outside admin
        )
        context["adminform"] = adminform

        # Only add elided_page_range if pagination is enabled and page_obj exists
        if context.get("page_obj"):
            page_obj = context["page_obj"]
            context["elided_page_range"] = list(
                page_obj.paginator.get_elided_page_range(number=page_obj.number, on_each_side=self.on_each_side, on_ends=self.on_ends)
            )

        return context
