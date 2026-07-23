from __future__ import annotations

import uuid
from typing import Any, Dict

import requests

from paiement.services import BasePaymentService


class MTNService(BasePaymentService):
    """
    Service de paiement MTN Mobile Money.
    """

    provider_code = "mtn"

    def __init__(self, provider):
        super().__init__(provider)

        self.api_key = provider.api_key
        self.subscription_key = provider.merchant_id

        self.base_url = (
            provider.get_endpoint()
            or "https://sandbox.momodeveloper.mtn.com"
        )


    def process_payment(
        self,
        amount: float,
        currency: str = "XOF",
        phone_number: str = "",
        email: str = "",
        description: str = "",
        **kwargs,
    ) -> Dict[str, Any]:

        transaction_id = str(uuid.uuid4())


        url = f"{self.base_url}/collection/v1_0/requesttopay"


        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "X-Reference-Id": transaction_id,
            "X-Target-Environment": "sandbox",
            "Ocp-Apim-Subscription-Key": self.subscription_key,
            "Content-Type": "application/json",
        }


        payload = {
            "amount": str(int(amount)),
            "currency": currency,
            "externalId": transaction_id,
            "payer": {
                "partyIdType": "MSISDN",
                "partyId": phone_number.replace("+225", "")
            },
            "payerMessage": description,
            "payeeNote": "Elite Buro paiement"
        }


        try:

            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=30
            )


            if response.status_code == 202:

                return {
                    "success": True,
                    "transaction_id": transaction_id,
                    "message": "Paiement MTN envoyé",
                }


            return {
                "success": False,
                "error_message": response.text
            }


        except requests.RequestException as e:

            return {
                "success": False,
                "error_message": str(e)
            }



    def verify_payment(
        self,
        transaction_id: str
    ) -> Dict[str, Any]:

        url = (
            f"{self.base_url}"
            f"/collection/v1_0/requesttopay/{transaction_id}"
        )


        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "X-Target-Environment": "sandbox",
            "Ocp-Apim-Subscription-Key": self.subscription_key,
        }


        response = requests.get(
            url,
            headers=headers,
            timeout=30
        )


        data = response.json()


        return {
            "success": data.get("status") == "SUCCESSFUL",
            "status": data.get("status"),
            "provider_data": data
        }