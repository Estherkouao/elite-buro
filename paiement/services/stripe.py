from __future__ import annotations

import json
import uuid
from typing import Any, Dict, Optional

import requests

from paiement.services import BasePaymentService


class StripeService(BasePaymentService):
    """
    Service de paiement Stripe.
    Utilise l'API Stripe Payment Intents.
    Documentation : https://stripe.com/docs/api
    """

    provider_code = "stripe"

    def __init__(self, provider):
        super().__init__(provider)
        self.api_key = provider.api_key
        self.api_secret = provider.api_secret
        self.base_url = provider.get_endpoint() or "https://api.stripe.com/v1"

    def _get_headers(self) -> Dict[str, str]:
        """Retourne les headers d'authentification pour Stripe."""
        return {
            "Authorization": f"Bearer {self.api_secret}",
            "Content-Type": "application/x-www-form-urlencoded",
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
        """Crée un Payment Intent Stripe."""
        transaction_id = kwargs.get(
            "transaction_id",
            f"STRIPE-{uuid.uuid4().hex[:16].upper()}",
        )

        # Stripe utilise les centimes (plus petite unité)
        # Pour XOF qui n'a pas de centime, on utilise le montant directement
        amount_in_cents = int(amount * 100)

        url = f"{self.base_url}/payment_intents"
        headers = self._get_headers()

        data = {
            "amount": amount_in_cents,
            "currency": currency.lower(),
            "description": description or "Paiement Elite Buro",
            "metadata[transaction_id]": transaction_id,
            "metadata[provider]": "stripe",
        }

        if email:
            data["receipt_email"] = email

        # Ajouter les infos de carte si fournies (pour payment_method)
        payment_method_id = kwargs.get("payment_method_id", "")
        if payment_method_id:
            data["payment_method"] = payment_method_id
            data["confirm"] = "true"
            data["return_url"] = kwargs.get("return_url", "")

        try:
            response = requests.post(url, data=data, headers=headers, timeout=30)
            result = response.json()

            if response.status_code in [200, 201] and result.get("status") not in [
                "requires_payment_method",
                "requires_confirmation",
            ]:
                return {
                    "success": True,
                    "transaction_id": transaction_id,
                    "provider_data": result,
                    "payment_url": "",
                    "client_secret": result.get("client_secret", ""),
                }
            elif result.get("status") == "requires_payment_method":
                # Paiement nécessite une action côté client
                return {
                    "success": True,
                    "transaction_id": transaction_id,
                    "provider_data": result,
                    "client_secret": result.get("client_secret", ""),
                    "requires_action": True,
                }
            else:
                return {
                    "success": False,
                    "error_message": result.get(
                        "error", {}
                    ).get("message", "Erreur Stripe"),
                    "transaction_id": transaction_id,
                    "provider_data": result,
                }
        except requests.RequestException as e:
            return {
                "success": False,
                "error_message": f"Erreur réseau Stripe: {str(e)}",
                "transaction_id": transaction_id,
            }

    def verify_payment(self, transaction_id: str) -> Dict[str, Any]:
        """Vérifie le statut d'un Payment Intent Stripe."""
        url = f"{self.base_url}/payment_intents/{transaction_id}"
        headers = self._get_headers()

        try:
            response = requests.get(url, headers=headers, timeout=30)
            data = response.json()

            status = data.get("status", "")
            is_successful = status in ["succeeded", "processing"]

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
        """Effectue un remboursement via Stripe."""
        url = f"{self.base_url}/refunds"
        headers = self._get_headers()

        data = {
            "payment_intent": transaction_id,
        }
        if amount:
            data["amount"] = int(amount * 100)

        try:
            response = requests.post(url, data=data, headers=headers, timeout=30)
            result = response.json()

            return {
                "success": response.status_code in [200, 201],
                "provider_data": result,
                "error_message": result.get("error", {}).get("message", ""),
            }
        except requests.RequestException as e:
            return {
                "success": False,
                "error_message": str(e),
            }

