"""
Example usage of encrypted fields for sensitive personal information.

This module demonstrates how to use the encrypted fields and permission system
to protect sensitive data in the sfd application.
"""

from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, render
from django.views.generic import DetailView

from sfd.models import Person
from sfd.utils.permissions import can_view_personal_info, get_masked_person_name, get_masked_phone


# Example 1: Function-based view with permission checking
@login_required
def person_detail_view(request, person_id):
    """
    Display person details with encryption-aware permission checking.

    - Users with 'view_personal_info' permission see full data (decrypted)
    - Other users see masked data
    """
    person = get_object_or_404(Person, pk=person_id)

    # Check if user has permission to view personal info
    has_permission = can_view_personal_info(request.user)

    if has_permission:
        # User has permission - show decrypted data
        context = {
            "person": person,
            "full_name": f"{person.family_name} {person.name}",
            "phone": person.phone_number,
            "email": person.email,
            "address": person.address_detail,
            "birthday": person.birthday,
            "has_permission": True,
        }
    else:
        # User lacks permission - show masked data
        context = {
            "person": person,
            "full_name": get_masked_person_name(person, request.user),
            "phone": get_masked_phone(person.phone_number, request.user) if person.phone_number else "N/A",
            "email": "***@***.***",
            "address": "***",
            "birthday": "****-**-**",
            "has_permission": False,
        }

    return render(request, "person_detail.html", context)


# Example 2: Class-based view with permission decorator
class PersonDetailView(DetailView):
    """
    Class-based view for person details.
    Only users with 'view_personal_info' permission can access.
    """

    model = Person
    template_name = "person_detail.html"

    def dispatch(self, request, *args, **kwargs):
        """Check permission before processing request."""
        if not can_view_personal_info(request.user):
            raise PermissionDenied("You don't have permission to view personal information")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["has_permission"] = True
        return context


# Example 3: List view with selective field display
@login_required
def person_list_view(request):
    """
    Display list of people with appropriate masking based on permissions.
    """
    people = Person.objects.all()
    has_permission = can_view_personal_info(request.user)

    # Prepare data for display
    people_data = []
    for person in people:
        if has_permission:
            people_data.append(
                {
                    "id": person.id,
                    "name": f"{person.family_name} {person.name}",
                    "phone": person.phone_number or "N/A",
                    "email": person.email or "N/A",
                }
            )
        else:
            people_data.append(
                {
                    "id": person.id,
                    "name": get_masked_person_name(person, request.user),
                    "phone": "***-****-****",
                    "email": "***@***.***",
                }
            )

    context = {
        "people_data": people_data,
        "has_permission": has_permission,
    }

    return render(request, "person_list.html", context)


# Example 4: API endpoint with permission checking
from django.http import JsonResponse


@login_required
def person_api(request, person_id):
    """
    API endpoint that returns person data in JSON format.
    Data is masked if user lacks permission.
    """
    person = get_object_or_404(Person, pk=person_id)
    has_permission = can_view_personal_info(request.user)

    if has_permission:
        data = {
            "id": person.id,
            "family_name": person.family_name,
            "name": person.name,
            "family_name_kana": person.family_name_kana,
            "name_kana": person.name_kana,
            "email": person.email,
            "phone_number": person.phone_number,
            "mobile_number": person.mobile_number,
            "birthday": person.birthday.isoformat() if person.birthday else None,
            "address_detail": person.address_detail,
        }
    else:
        data = {
            "id": person.id,
            "family_name": person.family_name[:1] + "***",
            "name": person.name[:1] + "***",
            "family_name_kana": "***",
            "name_kana": "***",
            "email": "***@***.***",
            "phone_number": "***-****-****",
            "mobile_number": "***-****-****",
            "birthday": "****-**-**",
            "address_detail": "***",
        }

    return JsonResponse(
        {
            "person": data,
            "has_permission": has_permission,
        }
    )


# Example 5: Creating and updating encrypted data
@permission_required("sfd.change_personal_info", raise_exception=True)
def create_person_view(request):
    """
    Create a new person with encrypted sensitive data.
    Only users with 'change_personal_info' permission can create.
    """
    if request.method == "POST":
        # Data is automatically encrypted when saved
        person = Person.objects.create(
            family_name=request.POST.get("family_name"),
            family_name_kana=request.POST.get("family_name_kana"),
            name=request.POST.get("name"),
            name_kana=request.POST.get("name_kana"),
            email=request.POST.get("email"),
            phone_number=request.POST.get("phone_number"),
            mobile_number=request.POST.get("mobile_number"),
            address_detail=request.POST.get("address_detail"),
        )

        # Data is encrypted in the database but available as plaintext here
        print(f"Created person: {person.family_name} {person.name}")
        print(f"Email: {person.email}")  # Automatically decrypted

        return JsonResponse(
            {
                "success": True,
                "person_id": person.id,
            }
        )

    return render(request, "person_form.html")


# Example 6: Searching encrypted fields (Note: limitations)
@login_required
@permission_required("sfd.view_personal_info", raise_exception=True)
def search_people_view(request):
    """
    Search people by name.

    IMPORTANT: Because data is encrypted, we cannot search in the database.
    We must load all records and filter in Python.
    """
    query = request.GET.get("q", "")

    if not query:
        people = []
    else:
        # Load all people (encrypted data is decrypted automatically)
        all_people = Person.objects.all()

        # Filter in Python (case-insensitive)
        people = [
            person
            for person in all_people
            if query.lower() in person.family_name.lower()
            or query.lower() in person.name.lower()
            or (person.family_name_kana and query.lower() in person.family_name_kana.lower())
            or (person.name_kana and query.lower() in person.name_kana.lower())
        ]

    return render(
        request,
        "person_search_results.html",
        {
            "people": people,
            "query": query,
        },
    )


# Example 7: Batch processing with permission checking
@login_required
def export_people_csv(request):
    """
    Export people to CSV with appropriate data masking.
    """
    import csv

    from django.http import HttpResponse

    has_permission = can_view_personal_info(request.user)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="people.csv"'

    writer = csv.writer(response)
    writer.writerow(["ID", "Name", "Phone", "Email"])

    people = Person.objects.all()

    for person in people:
        if has_permission:
            writer.writerow(
                [
                    person.id,
                    f"{person.family_name} {person.name}",
                    person.phone_number or "",
                    person.email or "",
                ]
            )
        else:
            writer.writerow(
                [
                    person.id,
                    get_masked_person_name(person, request.user),
                    "***-****-****",
                    "***@***.***",
                ]
            )

    return response
