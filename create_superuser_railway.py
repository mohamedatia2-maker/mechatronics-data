import os
import django

# Setup Django Environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mechatronics_hub.settings')
django.setup()

from django.contrib.auth.models import User

# Configuration
USERNAME = "Mohamed Attia"
PASSWORD = "AdminPassword2026!"
EMAIL = "mohamed.attia@mechatronics.com"

def create_admin():
    try:
        if not User.objects.filter(username=USERNAME).exists():
            print(f"Creating superuser: {USERNAME}")
            User.objects.create_superuser(USERNAME, EMAIL, PASSWORD)
            print("Superuser created successfully.")
        else:
            print(f"Superuser '{USERNAME}' already exists. Skipping creation.")
            
            # Optional: Ensure it's staff/superuser if it exists but permissions were lost
            u = User.objects.get(username=USERNAME)
            if not u.is_staff or not u.is_superuser:
                u.is_staff = True
                u.is_superuser = True
                u.save()
                print(f"Permissions updated for '{USERNAME}'.")

    except Exception as e:
        print(f"Error creating superuser: {e}")

if __name__ == "__main__":
    create_admin()
