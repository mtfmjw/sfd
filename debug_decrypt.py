import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sfd_prj.settings")
import django

django.setup()
from django.db import connection

from sfd.models import Person

p = Person.objects.first()
print("Person found:", bool(p))
if not p:
    print("No Person in DB")
    exit(0)

print("Model attribute family_name:", p.family_name)
print("Model attribute email:", p.email)
print("Model attribute phone_number:", p.phone_number)
print("Model attribute mobile_number:", p.mobile_number)

with connection.cursor() as c:
    c.execute("SELECT family_name, email, phone_number, mobile_number FROM sfd_person WHERE id=%s", [p.id])
    row = c.fetchone()
    print("\nRaw DB values:")
    print("family_name_raw:", row[0])
    print("email_raw:", row[1])
    print("phone_raw:", row[2])
    print("mobile_raw:", row[3])
