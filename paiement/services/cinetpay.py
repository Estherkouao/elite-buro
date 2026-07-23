from __future__ import annotations

import json
from typing import Any, Dict, Optional

import requests

from paiement.services import BasePaymentService


class CinetPayService(BasePaymentService):
    """
    Service de paiement CinetPay.
    Documentation : https://docs.cinetpay.com/
    """

    provider_code = "cinetpay"

    def __init__(self, provider):
        super().__init__(provider)
        self.api_key = provider.api_key
        self.site_id = provider.merchant_id
        self.base_url = provider.get_endpoint() or "https://api-checkout.cinetpay.com"

    def process_payment(
        self,
        amount: float,
        currency: str = "XOF",
        phone_number: str = "",
        email: str = "",
        description: str = "",
        **kwargs,
    ) -> Dict[str, Any]:
        """Crée un paiement via l'API CinetPay."""
        transaction_id = kwargs.get(
            "transaction_id",
            f"CINETPAY-{__import__('uuid').uuid4().hex[:16].upper()}",
        )

        url = f"{self.base_url}/v2/payment"

        payload = {
            "apikey": self.api_key,
            "site_id": self.site_id,
            "transaction_id": transaction_id,
            "amount": int(amount),
            "currency": currency,
            "description": description,
            "notify_url": kwargs.get("notify_url", ""),
            "return_url": kwargs.get("return_url", ""),
            "channels": kwargs.get("channels", "ALL"),
        }

        # Ajouter les infos client si fournies
        if phone_number:
            payload["customer_phone"] = phone_number
        if email:
            payload["customer_email"] = email

        try:
            response = requests.post(url, json=payload, timeout=30)
            data = response.json()

            if data.get("code") == "00" or data.get("status") == "ACCEPTED":
                return {
                    "success": True,
                    "transaction_id": transaction_id,
                    "provider_data": data,
                    "payment_url": data.get("data", {}).get("payment_url", ""),
                }
            else:
                return {
                    "success": False,
                    "error_message": data.get("message", "Erreur CinetPay"),
                    "transaction_id": transaction_id,
                    "provider_data": data,
                }
        except requests.RequestException as e:
            return {
                "success": False,
                "error_message": f"Erreur réseau CinetPay: {str(e)}",
                "transaction_id": transaction_id,
            }

    def verify_payment(self, transaction_id: str) -> Dict[str, Any]:
        """Vérifie le statut d'un paiement CinetPay."""
        url = f"{self.base_url}/v2/payment/check"

        payload = {
            "apikey": self.api_key,
            "site_id": self.site_id,
            "transaction_id": transaction_id,
        }

        try:
            response = requests.post(url, json=payload, timeout=30)
            data = response.json()

            status = data.get("data", {}).get("status", "")
            is_successful = status in ["ACCEPTED", "SUCCESSFUL"]

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
        """Effectue un remboursement via CinetPay."""
        url = f"{self.base_url}/v2/payment/refund"

        payload = {
            "apikey": self.api_key,
            "site_id": self.site_id,
            "transaction_id": transaction_id,
        }

        if amount:
            payload["amount"] = int(amount)

        try:
            response = requests.post(url, json=payload, timeout=30)
            data = response.json()

            return {
                "success": data.get("code") == "00",
                "provider_data": data,
                "error_message": data.get("message", ""),
            }
        except requests.RequestException as e:
            return {
                "success": False,
                "error_message": str(e),
            }
