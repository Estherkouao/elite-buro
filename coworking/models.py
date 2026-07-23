from django.conf import settings
from django.db import models
from django.utils.text import slugify


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class CoworkingSpace(TimeStampedModel):
    """Représente une agence ELITEBURO."""

    STATUS_ACTIVE = "active"
    STATUS_INACTIVE = "inactive"

    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Actif"),
        (STATUS_INACTIVE, "Inactif"),
    ]

    nom = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    description = models.TextField(blank=True, default="")

    adresse = models.CharField(max_length=255, blank=True, default="")
    ville = models.CharField(max_length=120, blank=True, default="")
    pays = models.CharField(max_length=120, blank=True, default="")

    telephone = models.CharField(max_length=60, blank=True, default="")
    email = models.EmailField(blank=True, default="")

    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)

    image_principale = models.ImageField(upload_to="coworking/spaces/images/")
    logo = models.ImageField(upload_to="coworking/spaces/logos/")
    horaires = models.TextField(blank=True, default="")

    statut = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)

    class Meta:
        verbose_name = "CoworkingSpace"
        verbose_name_plural = "CoworkingSpaces"

    def __str__(self) -> str:
        return self.nom

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nom)
        if self.slug:
            self.slug = slugify(self.slug)
        super().save(*args, **kwargs)


class Category(TimeStampedModel):
    """Catégorie d'espace (Bureau Privé, Hot Desk, etc.)."""

    nom = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    description = models.TextField(blank=True, default="")

    icone = models.CharField(max_length=120, blank=True, default="")
    image = models.ImageField(upload_to="coworking/categories/images/")

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def __str__(self) -> str:
        return self.nom

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nom)
        if self.slug:
            self.slug = slugify(self.slug)
        super().save(*args, **kwargs)


class Workspace(TimeStampedModel):
    """Espace réservé par le client."""

    espace = models.ForeignKey(CoworkingSpace, on_delete=models.CASCADE, related_name="workspaces")
    categorie = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="workspaces")

    nom = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220)
    description = models.TextField(blank=True, default="")

    capacite = models.PositiveIntegerField()
    superficie = models.DecimalField(max_digits=10, decimal_places=2)

    etage = models.CharField(max_length=50, blank=True, default="")
    numero = models.CharField(max_length=50, blank=True, default="")

    prix_heure = models.DecimalField(max_digits=12, decimal_places=2)
    prix_demi_journee = models.DecimalField(max_digits=12, decimal_places=2)
    prix_journee = models.DecimalField(max_digits=12, decimal_places=2)
    prix_semaine = models.DecimalField(max_digits=12, decimal_places=2)
    prix_mois = models.DecimalField(max_digits=12, decimal_places=2)

    caution = models.DecimalField(max_digits=12, decimal_places=2)

    disponible = models.BooleanField(default=True)
    vedette = models.BooleanField(default=False)

    image_principale = models.ImageField(upload_to="coworking/workspaces/images/")

    class Meta:
        verbose_name = "Workspace"
        verbose_name_plural = "Workspaces"
        unique_together = (
            "espace",
            "slug",
        )

    def __str__(self) -> str:
        return f"{self.nom} ({self.espace.nom})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nom)
        if self.slug:
            self.slug = slugify(self.slug)
        super().save(*args, **kwargs)


class WorkspaceImage(models.Model):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="coworking/workspaces/gallery/")

    class Meta:
        verbose_name = "WorkspaceImage"
        verbose_name_plural = "WorkspaceImages"

    def __str__(self) -> str:
        return f"Image de {self.workspace.nom}"


class Equipment(TimeStampedModel):
    """Liste des équipements."""

    nom = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)

    class Meta:
        verbose_name = "Equipment"
        verbose_name_plural = "Equipments"

    def __str__(self) -> str:
        return self.nom

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nom)
        if self.slug:
            self.slug = slugify(self.slug)
        super().save(*args, **kwargs)


class WorkspaceEquipment(TimeStampedModel):
    """Relation ManyToMany (via modèle) entre Workspace et Equipment."""

    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="equipment_links")
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name="workspace_links")

    class Meta:
        verbose_name = "WorkspaceEquipment"
        verbose_name_plural = "WorkspaceEquipments"
        unique_together = ("workspace", "equipment")

    def __str__(self) -> str:
        return f"{self.workspace.nom} - {self.equipment.nom}"


class WorkspaceAvailability(TimeStampedModel):
    """Disponibilités d’un espace."""

    espace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="availabilities")
    date = models.DateField()
    heure_debut = models.TimeField()
    heure_fin = models.TimeField()
    disponible = models.BooleanField(default=True)

    class Meta:
        verbose_name = "WorkspaceAvailability"
        verbose_name_plural = "WorkspaceAvailabilities"
        indexes = [
            models.Index(fields=["date"]),
        ]

    def __str__(self) -> str:
        return f"{self.espace.nom} - {self.date} ({self.heure_debut}-{self.heure_fin})"


class WorkspacePrice(TimeStampedModel):
    """Tarifs spéciaux (surcouches de prix)."""

    espace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="prices")

    # Optionnel : période / règle (non demandée explicitement)
    prix_heure = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    prix_demi_journee = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    prix_journee = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    prix_semaine = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    prix_mois = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    class Meta:
        verbose_name = "WorkspacePrice"
        verbose_name_plural = "WorkspacePrices"

    def __str__(self) -> str:
        return f"Prix spéciaux - {self.espace.nom}"


class WorkspaceReview(TimeStampedModel):
    utilisateur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="coworking_reviews")
    espace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="reviews")

    note = models.PositiveSmallIntegerField(help_text="Note de 1 à 5")
    commentaire = models.TextField(blank=True, default="")
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "WorkspaceReview"
        verbose_name_plural = "WorkspaceReviews"
        unique_together = ("utilisateur", "espace")

    def __str__(self) -> str:
        return f"Review ({self.note}/5) - {self.espace.nom}"


class FavoriteWorkspace(models.Model):
    utilisateur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorite_workspaces")
    espace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="favorites")

    class Meta:
        verbose_name = "FavoriteWorkspace"
        verbose_name_plural = "FavoriteWorkspaces"
        unique_together = ("utilisateur", "espace")

    def __str__(self) -> str:
        return f"Favori - {self.utilisateur} - {self.espace.nom}"

