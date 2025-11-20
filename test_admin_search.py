#!/usr/bin/env python3
"""
Test script to demonstrate how admin search works with encrypted fields.
This script shows what exact values need to be searched.
"""

import os

import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sfd_prj.settings")
django.setup()

from sfd.common.encrypted import generate_search_hash
from sfd.models.person import Person

print("=" * 70)
print("ADMIN SEARCH TEST - Encrypted Fields")
print("=" * 70)
print()

# Get a sample person
persons = Person.objects.all()[:5]

if not persons:
    print("❌ No persons found in database. Please add some test data first.")
    exit(1)

print(f"Found {Person.objects.count()} total persons in database")
print()
print("IMPORTANT: Encrypted field search only supports EXACT matches!")
print("=" * 70)
print()

for person in persons:
    print(f"\n{'=' * 70}")
    print(f"Person ID: {person.id}")
    print(f"{'=' * 70}")

    # Show the decrypted values and what to search for
    fields_to_test = [
        ("family_name", "Family Name"),
        ("name", "Name"),
        ("family_name_kana", "Family Name (Kana)"),
        ("name_kana", "Name (Kana)"),
        ("family_name_romaji", "Family Name (Romaji)"),
        ("name_romaji", "Name (Romaji)"),
        ("email", "Email"),
    ]

    print("\n📋 To search for this person in admin, type EXACTLY one of these:")
    print("-" * 70)

    for field_name, field_label in fields_to_test:
        value = getattr(person, field_name, None)
        hash_field = f"{field_name}_hash"
        hash_value = getattr(person, hash_field, None)

        if value:
            print(f"\n  {field_label}:")
            print(f"    Search term: '{value}'")
            print(f"    Hash stored: {hash_value[:16]}...")

            # Test the search
            test_hash = generate_search_hash(value)
            matches = Person.objects.filter(**{hash_field: test_hash}).count()
            print(f"    ✅ Found {matches} match(es)" if matches > 0 else "    ❌ No matches")

print("\n" + "=" * 70)
print("\n🔍 SEARCH TIPS:")
print("-" * 70)
print("1. You must type the EXACT value (case-sensitive)")
print("2. Partial searches will NOT work (e.g., 'John' won't find 'Johnson')")
print("3. You can search by any of these fields:")
print("   - Family Name (姓)")
print("   - Name (名)")
print("   - Family Name Kana (姓カナ)")
print("   - Name Kana (名カナ)")
print("   - Family Name Romaji")
print("   - Name Romaji")
print("   - Email")
print("\n4. Example searches that will work:")
print("   - Search '太郎' to find people with name '太郎'")
print("   - Search '田中' to find people with family_name '田中'")
print("   - Search 'タロウ' to find people with name_kana 'タロウ'")
print("=" * 70)
