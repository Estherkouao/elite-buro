from __future__ import annotations

import uuid
from typing import Any, Dict, Optional, Type

from django.utils import timezone

from paiement.models import PaymentProvider, PaymentTransaction


class BasePaymentService:
    """
    Classe de base pour tous les services de paiement.
    Chaque provider doit hériter de cette classe et implémenter
    les méthodes `process_payment`, `verify_payment` et `refund_payment`.
    """

    provider_code: str = ""

    def __init__(self, provider: PaymentProvider):
        self.provider = provider

    def process_payment(
        self,
        amount: float,
        currency: str = "XOF",
        phone_number: str = "",
        email: str = "",
        description: str = "",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Traite un paiement via le provider.
        Retourne un dictionnaire avec les clés :
            - success (bool)
            - transaction_id (str)
            - provider_data (dict)
            - error_message (str, optionnel)
        """
        raise NotImplementedError(
            "Chaque service doit implémenter process_payment"
        )

    def verify_payment(self, transaction_id: str) -> Dict[str, Any]:
        """
        Vérifie le statut d'une transaction existante.
        """
        raise NotImplementedError(
            "Chaque service doit implémenter verify_payment"
        )

    def refund_payment(
        self, transaction_id: str, amount: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Rembourse une transaction.
        """
        raise NotImplementedError(
            "Chaque service doit implémenter refund_payment"
        )

    def create_transaction(
        self,
        amount: float,
        transaction_id: str,
        reservation=None,
        phone_number: str = "",
        email: str = "",
        currency: str = "XOF",
        reference: str = "",
    ) -> PaymentTransaction:
        """Crée une transaction en base de données."""
        return PaymentTransaction.objects.create(
            reservation=reservation,
            provider=self.provider,
            transaction_id=transaction_id,
            reference=reference or f"TRX-{uuid.uuid4().hex[:12].upper()}",
            amount=amount,
            currency=currency,
            phone_number=phone_number,
            email=email,
            status="pending",
        )


class PaymentRegistry:
    """
    Registre des services de paiement.
    Permet d'obtenir le service correspondant à un provider.
    """

    _services: Dict[str, Type[BasePaymentService]] = {}

    @classmethod
    def register(cls, provider_code: str, service_class: Type[BasePaymentService]):
        """Enregistre un service pour un code provider donné."""
        cls._services[provider_code] = service_class

    @classmethod
    def get_service(cls, provider: PaymentProvider) -> BasePaymentService:
        """Retourne l'instance du service pour un provider donné."""
        service_class = cls._services.get(provider.code)
        if service_class is None:
            raise ValueError(
                f"Aucun service enregistré pour le provider '{provider.code}'. "
                f"Providers disponibles : {list(cls._services.keys())}"
            )
        return service_class(provider)

    @classmethod
    def get_available_providers(cls) -> Dict[str, Type[BasePaymentService]]:
        """Retourne tous les providers enregistrés."""
        return cls._services.copy()

    @classmethod
    def process_payment(
        cls,
        provider_code: str,
        amount: float,
        currency: str = "XOF",
        phone_number: str = "",
        email: str = "",
        description: str = "",
        reservation=None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Traite un paiement via le provider spécifié.
        Crée automatiquement la transaction en base.
        """
        try:
            provider = PaymentProvider.objects.get(
                code=provider_code, is_active=True
            )
        except PaymentProvider.DoesNotExist:
            return {
                "success": False,
                "error_message": f"Provider '{provider_code}' introuvable ou inactif.",
                "transaction_id": "",
            }

        service = cls.get_service(provider)
        transaction_id = f"{provider_code.upper()}-{uuid.uuid4().hex[:16].upper()}"

        # Créer la transaction en attente
        transaction = service.create_transaction(
            amount=amount,
            transaction_id=transaction_id,
            reservation=reservation,
            phone_number=phone_number,
            email=email,
            currency=currency,
        )

        try:
            result = service.process_payment(
                amount=amount,
                currency=currency,
                phone_number=phone_number,
                email=email,
                description=description,
                **kwargs,
            )

            if result.get("success"):
                transaction.mark_success()
                # Mettre à jour avec les données du provider si fournies
                if result.get("provider_data"):
                    transaction.provider_data = result["provider_data"]
                    transaction.save(update_fields=["provider_data"])
            else:
                transaction.mark_failed(
                    result.get("error_message", "Erreur inconnue")
                )

            return {
                "success": result.get("success", False),
                "transaction": transaction,
                "transaction_id": transaction_id,
                "provider_data": result.get("provider_data", {}),
                "error_message": result.get("error_message", ""),
            }

        except Exception as e:
            transaction.mark_failed(str(e))
            return {
                "success": False,
                "transaction": transaction,
                "transaction_id": transaction_id,
                "error_message": str(e),
            }

