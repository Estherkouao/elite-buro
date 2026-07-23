from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Optional

import requests

from paiement.services import BasePaymentService


class OrangeMoneyService(BasePaymentService):
    """
    Service de paiement Orange Money (Côte d'Ivoire).
    Utilise l'API Orange Money Merchant.
    Documentation : https://developer.orange.com/apis/orange-money-web
    """

    provider_code = "orange"

    def __init__(self, provider):
        super().__init__(provider)
        self.client_id = provider.api_key
        self.client_secret = provider.api_secret
        self.merchant_id = provider.merchant_id
        self.base_url = provider.get_endpoint() or "https://api.orange.com"

    def _get_access_token(self) -> Optional[str]:
        """Obtient un token d'accès OAuth2 pour l'API Orange."""
        url = f"{self.base_url}/oauth/v2/token"
        headers = {
            "Authorization": f"Basic {self._encode_credentials()}",
            "Accept": "application/json",
        }
        data = {
            "grant_type": "client_credentials",
        }

        try:
            response = requests.post(url, headers=headers, data=data, timeout=30)
            if response.status_code == 200:
                return response.json().get("access_token")
            return None
        except requests.RequestException:
            return None

    def _encode_credentials(self) -> str:
        """Encode les credentials en Base64."""
        credentials = f"{self.client_id}:{self.client_secret}"
        import base64
        return base64.b64encode(credentials.encode()).decode()

    def process_payment(
        self,
        amount: float,
        currency: str = "XOF",
        phone_number: str = "",
        email: str = "",
        description: str = "",
        **kwargs,
    ) -> Dict[str, Any]:
        """Initie un paiement Orange Money."""
        token = self._get_access_token()
        if not token:
            return {
                "success": False,
                "error_message": "Impossible d'obtenir le token d'accès Orange",
            }

        # Générer une référence unique
        import uuid
        order_id = kwargs.get(
            "order_id",
            f"ORANGE-{uuid.uuid4().hex[:16].upper()}",
        )

        url = f"{self.base_url}/orange-money-webpay/v1/webpayment"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        payload = {
            "merchant": {
                "merchantId": self.merchant_id or "",
            },
            "order": {
                "orderId": order_id,
                "amount": str(int(amount)),
                "currency": currency,
                "description": description or "Paiement Elite Buro",
            },
            "customer": {},
            "notifyUrl": kwargs.get("notify_url", ""),
            "returnUrl": kwargs.get("return_url", ""),
        }

        if phone_number:
            payload["customer"]["phoneNumber"] = phone_number
        if email:
            payload["customer"]["email"] = email

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            data = response.json()

            if response.status_code == 201 or response.status_code == 200:
                return {
                    "success": True,
                    "transaction_id": order_id,
                    "provider_data": data,
                    "payment_url": data.get("payment_url", ""),
                    "redirect_url": data.get("redirect_url", ""),
                }
            else:
                return {
                    "success": False,
                    "error_message": data.get("message", "Erreur Orange Money"),
                    "transaction_id": order_id,
                    "provider_data": data,
                }
        except requests.RequestException as e:
            return {
                "success": False,
                "error_message": f"Erreur réseau Orange: {str(e)}",
                "transaction_id": order_id,
            }

    def verify_payment(self, transaction_id: str) -> Dict[str, Any]:
        """Vérifie le statut d'un paiement Orange Money."""
        token = self._get_access_token()
        if not token:
            return {
                "success": False,
                "status": "ERROR",
                "error_message": "Impossible d'obtenir le token d'accès",
            }

        url = f"{self.base_url}/orange-money-webpay/v1/transactionstatus"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        payload = {
            "orderId": transaction_id,
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            data = response.json()

            status = data.get("status", "")
            is_successful = status in ["SUCCESS", "SUCCESSFUL", "00"]

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
        """Effectue un remboursement Orange Money."""
        token = self._get_access_token()
        if not token:
            return {
                "success": False,
                "error_message": "Impossible d'obtenir le token d'accès",
            }

        url = f"{self.base_url}/orange-money-webpay/v1/refund"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        payload = {
            "orderId": transaction_id,
            "amount": str(int(amount)) if amount else "",
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

