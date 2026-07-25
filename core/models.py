from django.db import models
from django.conf import settings


class ContactMessage(models.Model):
    """Message envoyé depuis le formulaire de contact public."""

    nom = models.CharField(max_length=255)
    email = models.EmailField()
    telephone = models.CharField(max_length=50, blank=True, default="")
    sujet = models.CharField(max_length=255)
    message = models.TextField()
    lu = models.BooleanField(default=False, verbose_name="Lu")
    lu_le = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Message de contact"
        verbose_name_plural = "Messages de contact"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Message de {self.nom} - {self.sujet[:50]}"
