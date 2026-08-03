from django.db import models

# Create your models here.
from django.db import models
from django.conf import settings


class ChatConversation(models.Model):

    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    session_key = models.CharField(
        max_length=100,
        blank=True
    )

    nom = models.CharField(
        max_length=150,
        blank=True
    )

    email = models.EmailField(
        blank=True
    )

    telephone = models.CharField(
        max_length=30,
        blank=True
    )

    date_creation = models.DateTimeField(
        auto_now_add=True
    )

    derniere_activite = models.DateTimeField(
        auto_now=True
    )

    est_terminee = models.BooleanField(
        default=False
    )

    class Meta:
        ordering = ["-date_creation"]

    def __str__(self):
        return f"Conversation #{self.id}"


class ChatMessage(models.Model):

    ROLE_CHOICES = [

        ("user", "Utilisateur"),

        ("assistant", "Assistant"),

    ]

    conversation = models.ForeignKey(
        ChatConversation,
        on_delete=models.CASCADE,
        related_name="messages"
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES
    )

    message = models.TextField()

    date_creation = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["date_creation"]

    def __str__(self):
        return self.role


class KnowledgeBase(models.Model):

    titre = models.CharField(
        max_length=200
    )

    mots_cles = models.TextField(
        help_text="bureau,coworking,hotdesk"
    )

    reponse = models.TextField()

    lien = models.CharField(
        max_length=250,
        blank=True
    )

    ordre = models.PositiveIntegerField(
        default=0
    )

    actif = models.BooleanField(
        default=True
    )

    class Meta:
        ordering = ["ordre"]

    def __str__(self):
        return self.titre

class QuickReply(models.Model):

    texte = models.CharField(
        max_length=100
    )

    ordre = models.PositiveIntegerField(
        default=0
    )

    actif = models.BooleanField(
        default=True
    )

    class Meta:
        ordering = ["ordre"]

    def __str__(self):
        return self.texte



class ChatLead(models.Model):

    conversation = models.OneToOneField(
        ChatConversation,
        on_delete=models.CASCADE
    )

    nom = models.CharField(
        max_length=150
    )

    email = models.EmailField()

    telephone = models.CharField(
        max_length=30
    )

    besoin = models.TextField()

    traite = models.BooleanField(
        default=False
    )

    date_creation = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.nom
