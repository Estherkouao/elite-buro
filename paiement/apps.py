from django.apps import AppConfig


class PaiementConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = 'paiement'

    def ready(self):
        """Enregistre les services de paiement au démarrage."""
        from paiement.services import PaymentRegistry
        from paiement.services.cinetpay import CinetPayService
        from paiement.services.orange import OrangeMoneyService
        from paiement.services.wave import WaveService
        from paiement.services.stripe import StripeService
        from paiement.services.paypal import PayPalService

        PaymentRegistry.register("cinetpay", CinetPayService)
        PaymentRegistry.register("orange", OrangeMoneyService)
        PaymentRegistry.register("wave", WaveService)
        PaymentRegistry.register("stripe", StripeService)
        PaymentRegistry.register("paypal", PayPalService)
