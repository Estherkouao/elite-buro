from __future__ import annotations

import base64
import json
import uuid
from typing import Any, Dict, Optional

import requests

from paiement.services import BasePaymentService


class PayPalService(BasePaymentService):
    """
    Service de paiement PayPal.
    Utilise l'API PayPal Orders v2.
    Documentation : https://developer.paypal.com/docs/api/orders/v2/
    """

    provider_code = "paypal"

    def __init__(self, provider):
        super().__init__(provider)
        self.client_id = provider.api_key
        self.client_secret = provider.api_secret
        self.base_url = provider.get_endpoint() or "https://api-m.paypal.com"

        if provider.sandbox_mode:
            self.base_url = provider.sandbox_endpoint or "https://api-m.sandbox.paypal.com"

    def _get_access_token(self) -> Optional[str]:
        """Obtient un token d'accès OAuth2 pour l'API PayPal."""
        url = f"{self.base_url}/v1/oauth2/token"
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()

        headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Accept": "application/json",
        }
        data = {"grant_type": "client_credentials"}

        try:
            response = requests.post(url, headers=headers, data=data, timeout=30)
            if response.status_code == 200:
                return response.json().get("access_token")
            return None
        except requests.RequestException:
            return None

    def process_payment(
        self,
        amount: float,
        currency: str = "XOF",
        phone_number: str = "",
        email: str = "",
        description: str = "",
        **kwargs,
    ) -> Dict[str, Any]:
        """Crée une commande PayPal."""
        token = self._get_access_token()
        if not token:
            return {
                "success": False,
                "error_message": "Impossible d'obtenir le token d'accès PayPal",
            }

        transaction_id = kwargs.get(
            "transaction_id",
            f"PAYPAL-{uuid.uuid4().hex[:16].upper()}",
        )

        url = f"{self.base_url}/v2/checkout/orders"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        # Convertir le montant (XOF n'est pas supporté par PayPal, utiliser EUR ou USD)
        paypal_currency = "EUR"
        converted_amount = self._convert_currency(amount, currency, paypal_currency)

        payload = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "reference_id": transaction_id,
                    "description": description or "Paiement Elite Buro",
                    "amount": {
                        "currency_code": paypal_currency,
                        "value": str(converted_amount),
                    },
                }
            ],
            "payment_source": {
                "paypal": {
                    "experience_context": {
                        "payment_method_preference": "IMMEDIATE_PAYMENT_REQUIRED",
                        "landing_page": "LOGIN",
                        "user_action": "PAY_NOW",
                        "return_url": kwargs.get("return_url", ""),
                        "cancel_url": kwargs.get("cancel_url", ""),
                    }
                }
            },
        }

        if email:
            payload["payer"] = {"email_address": email}

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            data = response.json()

            if response.status_code in [200, 201]:
                # Trouver l'URL d'approbation
                approval_url = ""
                for link in data.get("links", []):
                    if link.get("rel") == "payer-action":
                        approval_url = link.get("href", "")
                        break

                return {
                    "success": True,
                    "transaction_id": transaction_id,
                    "provider_data": data,
                    "payment_url": approval_url,
                    "approval_url": approval_url,
                    "order_id": data.get("id", ""),
                }
            else:
                return {
                    "success": False,
                    "error_message": data.get("message", "Erreur PayPal"),
                    "transaction_id": transaction_id,
                    "provider_data": data,
                }
        except requests.RequestException as e:
            return {
                "success": False,
                "error_message": f"Erreur réseau PayPal: {str(e)}",
                "transaction_id": transaction_id,
            }

    def verify_payment(self, transaction_id: str) -> Dict[str, Any]:
        """Vérifie le statut d'une commande PayPal."""
        token = self._get_access_token()
        if not token:
            return {
                "success": False,
                "status": "ERROR",
                "error_message": "Impossible d'obtenir le token d'accès",
            }

        url = f"{self.base_url}/v2/checkout/orders/{transaction_id}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

        try:
            response = requests.get(url, headers=headers, timeout=30)
            data = response.json()

            status = data.get("status", "")
            is_successful = status in ["COMPLETED", "APPROVED"]

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
        """Effectue un remboursement via PayPal."""
        token = self._get_access_token()
        if not token:
            return {
                "success": False,
                "error_message": "Impossible d'obtenir le token d'accès",
            }

        url = f"{self.base_url}/v2/payments/captures/{transaction_id}/refund"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        payload = {}
        if amount:
            # Convertir le montant
            converted_amount = self._convert_currency(amount, "XOF", "EUR")
            payload["amount"] = {
                "value": str(converted_amount),
                "currency_code": "EUR",
            }

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

    def _convert_currency(
        self, amount: float, from_currency: str, to_currency: str
    ) -> float:
        """
        Convertit un montant d'une devise à une autre.
        Simplifié : taux de conversion fixe pour XOF -> EUR.
        En production, utilisez une API de taux de change.
        """
        if from_currency == to_currency:
            return amount

        # Taux de conversion approximatif
        conversion_rates = {
            ("XOF", "EUR"): 0.0015,  # 1 XOF ≈ 0.0015 EUR
            ("EUR", "XOF"): 655.96,
        }

        rate = conversion_rates.get((from_currency, to_currency), 1)
        return round(amount * rate, 2)

