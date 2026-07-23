from __future__ import annotations

import uuid
from typing import Any, Dict

import requests

from paiement.services import BasePaymentService


class VisaService(BasePaymentService):
    """
    Service de paiement Visa / Carte bancaire.
    """

    provider_code = "visa"


    def __init__(self, provider):
        super().__init__(provider)

        self.api_key = provider.api_key
        self.merchant_id = provider.merchant_id

        self.base_url = (
            provider.get_endpoint()
            or "https://sandbox.payment-gateway.com"
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


        transaction_id = (
            "VISA-"
            + uuid.uuid4().hex[:16].upper()
        )


        url = f"{self.base_url}/payments"


        headers = {

            "Authorization":
                f"Bearer {self.api_key}",

            "Content-Type":
                "application/json"

        }


        payload = {

            "merchant_id":
                self.merchant_id,

            "transaction_id":
                transaction_id,

            "amount":
                int(amount),

            "currency":
                currency,


            "customer": {

                "email":
                    email

            },


            "description":
                description,


            "return_url":
                kwargs.get(
                    "return_url",
                    ""
                ),


            "notify_url":
                kwargs.get(
                    "notify_url",
                    ""
                )

        }



        try:

            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=30
            )


            data = response.json()


            if response.status_code in [200,201]:

                return {

                    "success": True,

                    "transaction_id":
                        transaction_id,

                    "payment_url":
                        data.get(
                            "payment_url",
                            ""
                        ),

                    "provider_data":
                        data

                }



            return {

                "success": False,

                "error_message":
                    data.get(
                        "message",
                        "Erreur paiement Visa"
                    ),

                "provider_data":
                    data

            }


        except requests.RequestException as e:

            return {

                "success": False,

                "error_message":
                    str(e)

            }



    def verify_payment(
        self,
        transaction_id: str
    ) -> Dict[str, Any]:


        url = (
            f"{self.base_url}"
            f"/payments/{transaction_id}"
        )


        headers = {

            "Authorization":
                f"Bearer {self.api_key}"

        }


        response = requests.get(
            url,
            headers=headers,
            timeout=30
        )


        data = response.json()


        status = data.get(
            "status",
            ""
        )


        return {

            "success":
                status in [
                    "SUCCESS",
                    "COMPLETED",
                    "PAID"
                ],

            "status":
                status,

            "provider_data":
                data

        }