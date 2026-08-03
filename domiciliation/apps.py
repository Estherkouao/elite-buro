from django.apps import AppConfig


class DomiciliationConfig(AppConfig):
    name = 'domiciliation'

    def ready(self) -> None:
        # Enregistre les signaux (auto-génération du contrat à la création d'une demande)
        from . import signals  # noqa: F401
