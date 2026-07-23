from django.db import migrations
from django.contrib.auth.hashers import make_password


def create_superuser(apps, schema_editor):
    User = apps.get_model("accounts", "User")

    if not User.objects.filter(email="admin@eliteburo.com").exists():
        User.objects.create(
            email="admin@eliteburo.com",
            password=make_password("Admin@12345"),
            first_name="Super",
            last_name="Admin",
            phone="+2250101010101",
            role="ADMIN",
            is_staff=True,
            is_superuser=True,
            is_active=True,
        )


def delete_superuser(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.filter(email="admin@eliteburo.com").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_superuser, delete_superuser),
    ]