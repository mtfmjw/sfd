"""Script to regenerate hash fields for all Person records."""

import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sfd_prj.settings")
django.setup()

from sfd.common.encrypted import generate_search_hash
from sfd.models.person import Person

print("Regenerating hash fields for all Person records...")
print()

persons = Person.objects.all()
total = persons.count()
print(f"Total persons: {total}")
print()

updated = 0
for i, person in enumerate(persons, 1):
    # Generate hashes for all searchable fields
    person.family_name_hash = generate_search_hash(person.family_name)
    person.family_name_kana_hash = generate_search_hash(person.family_name_kana)
    person.family_name_romaji_hash = generate_search_hash(person.family_name_romaji)
    person.name_hash = generate_search_hash(person.name)
    person.name_kana_hash = generate_search_hash(person.name_kana)
    person.name_romaji_hash = generate_search_hash(person.name_romaji)
    person.email_hash = generate_search_hash(person.email)
    person.phone_number_hash = generate_search_hash(person.phone_number)
    person.mobile_number_hash = generate_search_hash(person.mobile_number)

    # Save without triggering save() method again
    Person.objects.filter(pk=person.pk).update(
        family_name_hash=person.family_name_hash,
        family_name_kana_hash=person.family_name_kana_hash,
        family_name_romaji_hash=person.family_name_romaji_hash,
        name_hash=person.name_hash,
        name_kana_hash=person.name_kana_hash,
        name_romaji_hash=person.name_romaji_hash,
        email_hash=person.email_hash,
        phone_number_hash=person.phone_number_hash,
        mobile_number_hash=person.mobile_number_hash,
    )

    updated += 1
    if i % 100 == 0:
        print(f"Processed {i}/{total} persons...")

print()
print(f"Successfully updated {updated} persons!")
print()

# Test the search
print("Testing search for '大西'...")
from django.db.models import Q

search_term = "大西"
search_hash = generate_search_hash(search_term)

search_query = Q(family_name_hash=search_hash) | Q(name_hash=search_hash) | Q(family_name_kana_hash=search_hash) | Q(name_kana_hash=search_hash)

results = Person.objects.filter(search_query)
print(f"Found {results.count()} results:")
for result in results:
    print(f"  - {result.family_name} {result.name}")
