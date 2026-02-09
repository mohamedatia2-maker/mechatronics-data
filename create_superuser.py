import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mechatronics_hub.settings')
django.setup()

from django.contrib.auth.models import User

username = "Mohamed Attia"
password = "AdminPassword2026!"
email = "mohamed.attia@mechatronics.com"

try:
    if not User.objects.filter(username=username).exists():
        User.objects.create_superuser(username, email, password)
        print(f"SUCCESS: Superuser '{username}' created.")
    else:
        u = User.objects.get(username=username)
        u.set_password(password)
        u.is_staff = True
        u.is_superuser = True
        u.save()
        print(f"SUCCESS: Superuser '{username}' updated.")
except Exception as e:
    print(f"ERROR: {e}")
