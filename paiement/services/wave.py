from __future__ import annotations

import json
import uuid
from typing import Any, Dict, Optional

import requests

from paiement.services import BasePaymentService


class WaveService(BasePaymentService):
    """
    Service de paiement Wave (Côte d'Ivoire, Sénégal, etc.).
    Utilise l'API Wave Money Merchant.
    Documentation : https://docs.wave.com/
    """

    provider_code = "wave"

    def __init__(self, provider):
        super().__init__(provider)
        self.api_key = provider.api_key
        self.api_secret = provider.api_secret
        self.base_url = provider.get_endpoint() or "https://api.wave.com/v1"

    def _get_headers(self) -> Dict[str, str]:
        """Retourne les headers d'authentification pour l'API Wave."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def process_payment(
        self,
        amount: float,
        currency: str = "XOF",
        phone_number: str = "",
        email: str = "",
        description: str = "",
        **kwargs,
    ) -> Dict[str, Any]:
        """Initie un paiement via Wave."""
        transaction_id = kwargs.get(
            "transaction_id",
            f"WAVE-{uuid.uuid4().hex[:16].upper()}",
        )

        url = f"{self.base_url}/checkout/sessions"
        headers = self._get_headers()

        # Convertir en centimes pour Wave (qui utilise la plus petite unité)
        amount_in_smallest_unit = int(amount)

        payload = {
            "amount": amount_in_smallest_unit,
            "currency": currency,
            "reference": transaction_id,
            "description": description or "Paiement Elite Buro",
            "success_url": kwargs.get("return_url", ""),
            "cancel_url": kwargs.get("cancel_url", ""),
            "metadata": {
                "transaction_id": transaction_id,
            },
        }

        if phone_number:
            payload["phone"] = phone_number
        if email:
            payload["email"] = email

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            data = response.json()

            if response.status_code in [200, 201]:
                return {
                    "success": True,
                    "transaction_id": transaction_id,
                    "provider_data": data,
                    "payment_url": data.get("payment_url", ""),
                    "checkout_url": data.get("checkout_url", ""),
                }
            else:
                return {
                    "success": False,
                    "error_message": data.get("message", "Erreur Wave"),
                    "transaction_id": transaction_id,
                    "provider_data": data,
                }
        except requests.RequestException as e:
            return {
                "success": False,
                "error_message": f"Erreur réseau Wave: {str(e)}",
                "transaction_id": transaction_id,
            }

    def verify_payment(self, transaction_id: str) -> Dict[str, Any]:
        """Vérifie le statut d'un paiement Wave."""
        url = f"{self.base_url}/checkout/sessions/{transaction_id}"
        headers = self._get_headers()

        try:
            response = requests.get(url, headers=headers, timeout=30)
            data = response.json()

            status = data.get("status", "")
            is_successful = status in ["COMPLETED", "SUCCEEDED", "success"]

            return {
                "success": is_successful,
                "status": status,
                "provider_data": data,
            }
        except requests.RequestException as e:
            return {
                "success": False,
                "status": "ERROR",
                "error_message": str(e),
            }

    def refund_payment(
        self, transaction_id: str, amount: Optional[float] = None
    ) -> Dict[str, Any]:
        """Effectue un remboursement via Wave."""
        url = f"{self.base_url}/checkout/sessions/{transaction_id}/refund"
        headers = self._get_headers()

        payload = {}
        if amount:
            payload["amount"] = int(amount)

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            data = response.json()

            return {
                "success": response.status_code in [200, 201],
                "provider_data": data,
                "error_message": data.get("message", ""),
            }
        except requests.RequestException as e:
            return {
                "success": False,
                "error_message": str(e),
            }

