import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sfd_prj.settings")
django.setup()

from django.db import connection

# Check current schema
with connection.cursor() as cursor:
    cursor.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='sfd_person' AND column_name='birthday'")
    result = cursor.fetchone()

print(f"Current birthday column: {result}")

if result:
    column_name, data_type = result
    print(f"Column: {column_name}, Type: {data_type}")

    # If it's still DATE, convert it to VARCHAR
    if data_type.startswith("date"):
        print("\nAltering column from DATE to VARCHAR(180)...")
        with connection.cursor() as cursor:
            cursor.execute("ALTER TABLE sfd_person ALTER COLUMN birthday SET DATA TYPE VARCHAR(180)")
        print("✓ Column successfully altered to VARCHAR(180)")

        # Verify the change
        with connection.cursor() as cursor:
            cursor.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='sfd_person' AND column_name='birthday'")
            new_result = cursor.fetchone()
        print(f"New birthday column: {new_result}")
    else:
        print(f"\n✓ Column is already {data_type}, no conversion needed")
else:
    print("ERROR: birthday column not found")
