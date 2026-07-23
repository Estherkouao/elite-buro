from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    """Profil premium du membre."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    photo = models.ImageField(upload_to="profiles/%Y/%m/%d", blank=True, null=True)

    telephone = models.CharField(max_length=30, blank=True)
    entreprise = models.CharField(max_length=255, blank=True)
    fonction = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"Profil de {self.user}"


class Workspace(models.Model):
    """Référence d’espace réservable côté membre.

    Remarque: Le projet a déjà des modèles de coworking.
    Ici on suit la demande de l’utilisateur pour la section membre.
    """

    nom = models.CharField(max_length=255)
    categorie = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="workspaces/%Y/%m/%d", blank=True, null=True)
    prix = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.nom


class Reservation(models.Model):
    utilisateur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reservations")
    espace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="reservations")

    date = models.DateField()
    heure_debut = models.TimeField()
    heure_fin = models.TimeField()

    prix = models.PositiveIntegerField(default=0)

    STATUS_PENDING = "pending"
    STATUS_CONFIRMED = "confirmed"
    STATUS_CANCELED = "canceled"

    statut = models.CharField(
        max_length=20,
        choices=[
            (STATUS_PENDING, "En attente"),
            (STATUS_CONFIRMED, "Confirmée"),
            (STATUS_CANCELED, "Annulée"),
        ],
        default=STATUS_PENDING,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reservation #{self.id} - {self.utilisateur}"


class Payment(models.Model):
    utilisateur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payments")
    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE, related_name="payments")

    montant = models.PositiveIntegerField(default=0)

    METHOD_MOMO = "momo"
    METHOD_CARD = "card"

    methode = models.CharField(max_length=30, blank=True, choices=[(METHOD_MOMO, "Mobile Money"), (METHOD_CARD, "Carte"),])

    STATUS_PAID = "paid"
    STATUS_PENDING = "pending"

    statut = models.CharField(
        max_length=20,
        choices=[
            (STATUS_PAID, "Payé"),
            (STATUS_PENDING, "En attente"),
        ],
        default=STATUS_PENDING,
    )

    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment #{self.id}"


class Favorite(models.Model):
    utilisateur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites")
    espace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="favorites")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("utilisateur", "espace")

    def __str__(self):
        return f"Favori de {self.utilisateur} - {self.espace}"


class Notification(models.Model):
    utilisateur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="dashboard_notifications")

    titre = models.CharField(max_length=255)
    message = models.TextField()

    lu = models.BooleanField(default=False)
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.titre} ({self.utilisateur})"


class Testimonial(models.Model):
    """Avis client soumis depuis le dashboard membre, modéré par l'admin."""

    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="testimonials",
    )

    note = models.PositiveSmallIntegerField(
        help_text="Note de 1 à 5",
        default=5,
    )

    commentaire = models.TextField(blank=True, default="")

    approuvé = models.BooleanField(default=False)

    approuvé_le = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Avis client"
        verbose_name_plural = "Avis clients"
        ordering = ["-approuvé_le", "-created_at"]

    def __str__(self):
        return f"Avis de {self.utilisateur.full_name} ({self.note}/5)"

