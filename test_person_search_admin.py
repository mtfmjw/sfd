"""Test person search functionality."""

import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sfd_prj.settings")
django.setup()

from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory

from sfd.models.person import Person
from sfd.views.person import PersonAdmin

# Setup
admin = PersonAdmin(Person, AdminSite())
factory = RequestFactory()
request = factory.get("/admin/")
queryset = Person.objects.all()

# Test search
print("Testing PersonAdmin search functionality...")
print()

test_cases = [
    "大西",
    "昇",
    "タナカ",
    "田中",
]

for search_term in test_cases:
    results, use_distinct = admin.get_search_results(request, queryset, search_term)
    print(f'Search for "{search_term}": {results.count()} results')
    for r in results[:3]:  # Show first 3
        print(f"  - {r.family_name} {r.name}")
    if results.count() > 3:
        print(f"  ... and {results.count() - 3} more")
    print()
