from django.db import models

# Create your models here.

from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.validators import RegexValidator
from django.conf import settings
import uuid


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        
        if not email:
            raise ValueError("L'adresse email est obligatoire.")

        email = self.normalize_email(email)

        user = self.model(email=email, **extra_fields)

        user.set_password(password)

        user.save(using=self._db)

        return user

    def create_superuser(self, email, password=None, **extra_fields):

        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("role", User.Role.ADMIN)

        return self.create_user(email, password, **extra_fields)



class User(AbstractUser):

    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Administrateur"
        MANAGER = "MANAGER", "Gestionnaire"
        MEMBER = "MEMBER", "Membre"
        TRAINER = "TRAINER", "Formateur"

    username = None

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    email = models.EmailField(
        unique=True
    )

    first_name = models.CharField(
        max_length=150
    )

    last_name = models.CharField(
        max_length=150
    )

    phone_validator = RegexValidator(
        regex=r'^\+?[0-9]{8,15}$',
        message="Numéro de téléphone invalide."
    )

    phone = models.CharField(
        max_length=20,
        validators=[phone_validator],
        unique=True
    )

    avatar = models.ImageField(
        upload_to="users/avatar/",
        blank=True,
        null=True
    )

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER
    )

    company_name = models.CharField(
        max_length=255,
        blank=True
    )

    job_title = models.CharField(
        max_length=255,
        blank=True
    )

    birth_date = models.DateField(
        blank=True,
        null=True
    )

    gender = models.CharField(
        max_length=20,
        blank=True
    )

    website = models.URLField(
        blank=True
    )

    bio = models.TextField(
        blank=True
    )

    language = models.CharField(
        max_length=10,
        default="fr"
    )

    timezone = models.CharField(
        max_length=100,
        default="Africa/Abidjan"
    )

    is_email_verified = models.BooleanField(
        default=False
    )

    is_phone_verified = models.BooleanField(
        default=False
    )

    receive_email_notification = models.BooleanField(
        default=True
    )

    receive_sms_notification = models.BooleanField(
        default=True
    )

    receive_whatsapp_notification = models.BooleanField(
        default=True
    )

    last_activity = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    USERNAME_FIELD = "email"

    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_manager(self):
        return self.role == self.Role.MANAGER

    @property
    def is_member(self):
        return self.role == self.Role.MEMBER

    @property
    def is_trainer(self):
        return self.role == self.Role.TRAINER





class Company(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="companies"
    )

    company_name = models.CharField(
        max_length=255
    )

    legal_form = models.CharField(
        max_length=100,
        blank=True
    )

    registration_number = models.CharField(
        max_length=100,
        blank=True
    )

    tax_number = models.CharField(
        max_length=100,
        blank=True
    )

    phone = models.CharField(
        max_length=20,
        blank=True
    )

    email = models.EmailField(
        blank=True
    )

    website = models.URLField(
        blank=True
    )

    description = models.TextField(
        blank=True
    )

    logo = models.ImageField(
        upload_to="companies/logo/",
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["company_name"]

    def __str__(self):
        return self.company_name




class Address(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="address"
    )

    country = models.CharField(
        max_length=100,
        default="Côte d'Ivoire"
    )

    city = models.CharField(
        max_length=100
    )

    district = models.CharField(
        max_length=100,
        blank=True
    )

    postal_code = models.CharField(
        max_length=20,
        blank=True
    )

    address = models.TextField()

    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        blank=True,
        null=True
    )

    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        blank=True,
        null=True
    )

    def __str__(self):
        return f"{self.address} - {self.city}"



class Profile(models.Model):

    class Gender(models.TextChoices):
        MALE = "M", "Homme"
        FEMALE = "F", "Femme"
        OTHER = "O", "Autre"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile"
    )

    gender = models.CharField(
        max_length=1,
        choices=Gender.choices,
        blank=True
    )

    nationality = models.CharField(
        max_length=100,
        blank=True
    )

    profession = models.CharField(
        max_length=255,
        blank=True
    )

    biography = models.TextField(
        blank=True
    )

    linkedin = models.URLField(
        blank=True
    )

    facebook = models.URLField(
        blank=True
    )

    instagram = models.URLField(
        blank=True
    )

    twitter = models.URLField(
        blank=True
    )

    emergency_contact_name = models.CharField(
        max_length=255,
        blank=True
    )

    emergency_contact_phone = models.CharField(
        max_length=20,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.full_name


            
class UserPreference(models.Model):

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="preferences"
    )

    dark_mode = models.BooleanField(default=False)

    language = models.CharField(
        max_length=10,
        default="fr"
    )

    timezone = models.CharField(
        max_length=100,
        default="Africa/Abidjan"
    )

    email_notification = models.BooleanField(default=True)

    sms_notification = models.BooleanField(default=True)

    whatsapp_notification = models.BooleanField(default=True)

    newsletter = models.BooleanField(default=True)

    def __str__(self):
        return self.user.full_name




class EmailVerification(models.Model):

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    token = models.UUIDField(
        default=uuid.uuid4,
        editable=False
    )

    verified = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    expires_at = models.DateTimeField()

    def is_expired(self):
        return timezone.now() > self.expires_at




class PhoneVerification(models.Model):

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    otp = models.CharField(
        max_length=6
    )

    verified = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    expires_at = models.DateTimeField()

    def is_expired(self):
        return timezone.now() > self.expires_at                            