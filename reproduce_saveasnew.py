import os
import sys

import django
from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory

sys.path.append("/workspaces/sfd")
sfd_prj_path = "/workspaces/sfd"
if sfd_prj_path not in sys.path:
    sys.path.append(sfd_prj_path)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sfd_prj.settings")
django.setup()

from django.contrib.auth.models import Permission, User
from django.utils import timezone

from sfd.models.municipality import Municipality
from sfd.models.person import Person
from sfd.models.postcode import Postcode
from sfd.views.person import PersonAdmin

# Setup data
try:
    user = User.objects.get(username="admin")
except User.DoesNotExist:
    user = User.objects.create_superuser("admin", "admin@example.com", "password")

# Create Permissions
from django.contrib.contenttypes.models import ContentType

ct = ContentType.objects.get_for_model(Person)
perm = Permission.objects.filter(content_type=ct, codename="view_personal_info").first()
# if perm:
#     user.user_permissions.add(perm)


mun = Municipality.objects.filter(municipality_code="999999").first()
if mun:
    Postcode.objects.filter(municipality=mun).delete()
    mun.delete()

mun = Municipality.objects.create(
    municipality_code="999999",
    prefecture_name="TestPref",
    prefecture_name_kana="TestPref",
    valid_from=timezone.now().date(),
    created_by="test",
    updated_by="test",
)
post = Postcode.objects.create(postcode="9999999", municipality=mun, created_by="test", updated_by="test")

# Admin instance
site = AdminSite()
person_admin = PersonAdmin(Person, site)

# Simulate Save as New POST request
factory = RequestFactory()
data = {
    "family_name": "Original",
    "name": "Person",
    "family_name_kana": "Original",
    "name_kana": "Person",
    "postcode_search": "999-9999",
    "valid_from": str(timezone.now().date()),  # Will be overwritten by logic
    "_saveasnew": "on",  # triggering Save as New logic
    "gender": "Male",
}

request = factory.post("/admin/sfd/person/add/", data)
request.user = user

# Initialize admin attributes typically set in changeform_view
person_admin._is_delete_action = False
person_admin._is_undelete_action = False
person_admin.inlines = []  # inlines might be checked too

# Get the form class
# Note: we are simulating 'add_view' so obj is None
ModelForm = person_admin.get_form(request, obj=None)
form = ModelForm(data=data, files={})

if form.is_valid():
    print("Form is VALID")
    # Simulate save
    instance = form.save(commit=False)
    # save_model usually handles created_by/updated_by
    person_admin.save_model(request, instance, form, False)
    instance.save()
    form.save_m2m()

    print(f"Saved Person ID: {instance.pk}")
    print(f"Postcode: {instance.postcode}")
    print(f"Municipality: {instance.municipality}")

    if instance.postcode is None:
        print("FAILURE: Postcode is None")
    else:
        print("SUCCESS: Postcode found")

else:
    print("Form is INVALID")
    print(form.errors)
    # Check if postcode_search logic in PersonAdminForm.clean failed
    if "postcode_search" in form.cleaned_data:
        print(f"Cleaned postcode_search: {form.cleaned_data['postcode_search']}")

# Cleanup
try:
    if "instance" in locals() and instance.pk:
        instance.delete()
except:
    pass
post.delete()
mun.delete()
