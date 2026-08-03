from __future__ import annotations

import json
import uuid
from typing import Any, Dict

from django.conf import settings
from django.contrib import messages
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from paiement.models import PaymentProvider, PaymentTransaction
from paiement.services import PaymentRegistry
from decimal import Decimal

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from formation.models import FormationRegistration


def indexpaiement(request: HttpRequest) -> HttpResponse:
    """
    Page principale de paiement avec la liste des fournisseurs actifs.
    """

    providers = PaymentProvider.objects.filter(
        is_active=True
    ).order_by("display_order", "name")


    reservation_id = request.GET.get("reservation_id")
    inscription_id = request.GET.get("inscription_id")
    domiciliation_id = request.GET.get("domiciliation_id")

    amount = Decimal("0")
    description = "Paiement Elite Buro"

    reservation = None
    inscription = None
    demande = None


    # =========================
    # PAIEMENT RESERVATION
    # =========================

    if reservation_id:
        try:
            from reservation.models import Reservation

            reservation = Reservation.objects.get(
                id=reservation_id,
                statut="awaiting_payment"
            )

            amount = reservation.montant_total
            description = reservation.reservation_number

        except Reservation.DoesNotExist:
            reservation_id = ""


    # =========================
    # PAIEMENT FORMATION
    # =========================

    if inscription_id:
        try:

            inscription = FormationRegistration.objects.select_related(
                "formation",
                "session"
            ).get(id=inscription_id)


            # récupérer le prix de la formation
            if inscription.session:
                amount = inscription.session.formation.prix

                description = (
                    f"Formation {inscription.session.formation.titre}"
                )

            elif inscription.formation:
                amount = inscription.formation.prix

                description = (
                    f"Formation {inscription.formation.titre}"
                )


        except FormationRegistration.DoesNotExist:
            inscription_id = ""


    # =========================
    # PAIEMENT DOMICILIATION
    # =========================

    if domiciliation_id:
        try:
            from domiciliation.models import DomiciliationRequest

            demande = DomiciliationRequest.objects.select_related(
                "formule", "entreprise"
            ).get(
                id=domiciliation_id,
                statut=DomiciliationRequest.Status.PAIEMENT_EN_ATTENTE,
            )

            amount = demande.formule.prix
            description = f"Domiciliation {demande.numero_demande}"

        except DomiciliationRequest.DoesNotExist:
            domiciliation_id = ""


    context = {

        "providers": providers,

        "reservation_id": reservation_id,
        "reservation": reservation,

        "inscription_id": inscription_id,
        "inscription": inscription,

        "domiciliation_id": domiciliation_id,
        "demande": demande,

        "amount": amount,
        "description": description,


        "CINETPAY_API_KEY": getattr(
            settings,
            "CINETPAY_API_KEY",
            ""
        ),

        "STRIPE_PUBLISHABLE_KEY": getattr(
            settings,
            "STRIPE_PUBLISHABLE_KEY",
            ""
        ),

        "PAYPAL_CLIENT_ID": getattr(
            settings,
            "PAYPAL_CLIENT_ID",
            ""
        ),

    }


    return render(
        request,
        "paiement/indexpaiement.html",
        context
    )


@require_http_methods(["POST"])
def process_payment(request: HttpRequest) -> JsonResponse:
    """
    Traite un paiement via le provider sélectionné.
    Reçoit les données en JSON.
    Supporte reservation_id (coworking), inscription_id (formation) et
    domiciliation_id (domiciliation).
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "error": "Données JSON invalides"}, status=400
        )

    provider_code = data.get("provider_code", "")
    amount = float(data.get("amount", 0))
    currency = data.get("currency", "XOF")
    phone_number = data.get("phone_number", "")
    email = data.get("email", "")
    description = data.get("description", "Paiement Elite Buro")
    reservation_id = data.get("reservation_id", "")
    inscription_id = data.get("inscription_id", "")
    domiciliation_id = data.get("domiciliation_id", "")

    if not provider_code:
        return JsonResponse(
            {"success": False, "error": "Code fournisseur requis"}, status=400
        )

    if amount <= 0:
        return JsonResponse(
            {"success": False, "error": "Montant invalide"}, status=400
        )

    try:
        # Récupérer la réservation si fournie
        reservation = None
        if reservation_id:
            try:
                from reservation.models import Reservation
                reservation = Reservation.objects.get(id=reservation_id)
            except (Reservation.DoesNotExist, ValueError):
                pass

        result = PaymentRegistry.process_payment(
            provider_code=provider_code,
            amount=amount,
            currency=currency,
            phone_number=phone_number,
            email=email,
            description=description,
            reservation=reservation,
            return_url=request.build_absolute_uri(
                f"/paiement/success/?reservation_id={reservation_id}"
            ) if reservation_id else (
                request.build_absolute_uri(
                    f"/paiement/success/?inscription_id={inscription_id}"
                ) if inscription_id else (
                    request.build_absolute_uri(
                        f"/paiement/success/?domiciliation_id={domiciliation_id}"
                    ) if domiciliation_id else request.build_absolute_uri("/paiement/success/")
                )
            ),
            cancel_url=request.build_absolute_uri("/paiement/cancel/"),
            notify_url=request.build_absolute_uri("/paiement/notify/"),
        )

        return JsonResponse(result)
    except ValueError as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)
    except Exception as e:
        return JsonResponse(
            {"success": False, "error": f"Erreur serveur: {str(e)}"},
            status=500,
        )


@require_http_methods(["GET"])
def payment_success(request: HttpRequest) -> HttpResponse:
    """Page de succès du paiement.
    Supporte les réservations coworking, les inscriptions formation et
    les domiciliations.
    """
    transaction_id = request.GET.get("transaction_id", "")
    reservation_id = request.GET.get("reservation_id", "")
    inscription_id = request.GET.get("inscription_id", "")
    domiciliation_id = request.GET.get("domiciliation_id", "")
    transaction = None
    reservation = None
    inscription = None
    demande = None

    if transaction_id:
        try:
            transaction = PaymentTransaction.objects.get(
                transaction_id=transaction_id
            )
            if transaction.reservation:
                reservation = transaction.reservation
        except PaymentTransaction.DoesNotExist:
            pass

    if not reservation and reservation_id:
        from reservation.models import Reservation
        try:
            reservation = Reservation.objects.get(id=reservation_id)
        except (Reservation.DoesNotExist, ValueError):
            pass

    # ═══════════════════════════════════════════════
    #  TRAITEMENT PAIEMENT FORMATION
    # ═══════════════════════════════════════════════
    if inscription_id:
        try:
            from formation.models import (
                FormationRegistration,
                FormationPayment,
                FormationAccessCode,
            )
            from formation.services import (
                generate_access_code,
                notify_member_payment_success,
                notify_member_access_code,
            )
            from decimal import Decimal

            inscription = FormationRegistration.objects.select_related(
                "session__formation", "membre"
            ).get(id=inscription_id, membre=request.user)

            if inscription.statut == "confirmed":
                # Calculer le montant total de la formation
                montant_total = inscription.session.formation.prix if inscription.session else Decimal("0")

                # Enregistrer le paiement
                FormationPayment.objects.update_or_create(
                    inscription=inscription,
                    defaults={
                        "montant": montant_total,
                        "méthode": "card",
                        "statut": "paid",
                        "reference": transaction_id or f"PAY-{inscription.numero}",
                    },
                )

                # Vérifier si le montant total est atteint (via les paiements existants)
                from django.db.models import Sum
                total_paid = FormationPayment.objects.filter(
                    inscription=inscription, statut="paid"
                ).aggregate(total=Sum("montant"))["total"] or Decimal("0")

                if total_paid >= montant_total:
                    # Paiement complet — générer le code d'accès
                    code = generate_access_code(inscription)
                    FormationAccessCode.objects.update_or_create(
                        inscription=inscription,
                        defaults={
                            "code": code,
                            "actif": True,
                            "attribue_le": timezone.now(),
                        },
                    )

                    # Notifier le membre avec son code d'accès
                    notify_member_access_code(inscription, code)

                # Email de confirmation de paiement au membre
                notify_member_payment_success(
                    inscription, montant_total,
                    transaction_id or f"PAY-{inscription.numero}"
                )

                # Message de succès
                messages.success(
                    request,
                    "✅ Paiement effectué avec succès ! Votre code d'accès vous a été envoyé par email."
                )

                # Rediriger vers la page mes cours
                from django.shortcuts import redirect
                from django.urls import reverse
                return redirect(reverse("formation:my_courses"))

        except FormationRegistration.DoesNotExist:
            pass
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Erreur traitement paiement formation: {e}")

    # ═══════════════════════════════════════════════
    #  TRAITEMENT PAIEMENT RÉSERVATION COWORKING
    # ═══════════════════════════════════════════════
    if reservation and reservation.statut == "awaiting_payment":
        from reservation.services import (
            generate_calendar_update,
            export_reservation_invoice_pdf,
        )
        from reservation.models import (
            ReservationLog,
            ReservationStatus,
            ReservationReceipt,
            ReservationInvoice,
        )
        from django.core.mail import send_mail
        from django.conf import settings

        # 1. Marquer la réservation comme confirmée
        reservation.statut = ReservationStatus.CONFIRMED
        reservation.save(update_fields=["statut"])

        # 2. Bloquer la disponibilité de l'espace
        generate_calendar_update(reservation)

        # 3. Logger l'action
        ReservationLog.objects.create(
            reservation=reservation,
            action=ReservationLog.ActionType.PAYMENT,
            acteur=request.user if request.user.is_authenticated else None,
            detail="Paiement effectué avec succès. Réservation confirmée et espace bloqué.",
        )

        # 4. Mettre à jour la facture
        invoice = getattr(reservation, "invoice", None)
        if invoice:
            invoice.statut = ReservationInvoice.InvoiceStatus.PAID
            invoice.save(update_fields=["statut"])
            # Exporter le PDF de la facture
            export_reservation_invoice_pdf(reservation=reservation)

            # 5. Créer le reçu de paiement
            receipt, created = ReservationReceipt.objects.get_or_create(
                invoice=invoice,
                defaults={
                    "numero": f"RCPT-{reservation.reservation_number}",
                    "montant": reservation.montant_total,
                    "statut": ReservationReceipt.ReceiptStatus.PAID,
                },
            )
            if not created:
                receipt.statut = ReservationReceipt.ReceiptStatus.PAID
                receipt.save(update_fields=["statut"])

        # 6. Envoyer l'email de confirmation avec reçu
        subject_confirm = f"Confirmation de paiement - Réservation {reservation.reservation_number}"
        message_confirm = f"""
Bonjour {reservation.utilisateur.get_full_name() or reservation.utilisateur.email},

Nous vous confirmons que votre paiement de {reservation.montant_total} FCFA a bien été effectué avec succès.

Votre réservation {reservation.reservation_number} est maintenant CONFIRMÉE.

Détails :
- Espace : {reservation.espace.nom}
- Période : {reservation.date_debut} au {reservation.date_fin}
- Montant total : {reservation.montant_total} FCFA

Le bureau vous appartient désormais à partir de la date de début de votre réservation !

Vous trouverez ci-joint votre reçu de paiement et votre facture.

Cordialement,
L'équipe EliteBuro
"""
        send_mail(
            subject=subject_confirm,
            message=message_confirm,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[reservation.utilisateur.email],
            fail_silently=True,
        )

    # ═══════════════════════════════════════════════
    #  TRAITEMENT PAIEMENT DOMICILIATION
    # ═══════════════════════════════════════════════
    if domiciliation_id:
        try:
            from domiciliation.models import (
                DomiciliationRequest,
                DomiciliationLog,
            )
            from domiciliation.services import activer_domiciliation

            demande = DomiciliationRequest.objects.select_related(
                "formule", "entreprise", "utilisateur"
            ).get(
                id=domiciliation_id,
                statut=DomiciliationRequest.Status.PAIEMENT_EN_ATTENTE,
            )

            # Marquer la facture comme payée si elle existe
            facture = getattr(demande, "facture", None)
            if facture:
                facture.statut = DomiciliationInvoice.Status.PAYÉE
                facture.save(update_fields=["statut"])

            # Activer la domiciliation
            activer_domiciliation(
                demande=demande,
                par=request.user if request.user.is_authenticated else demande.utilisateur,
            )

            # Notification email de confirmation
            from notification.services import NotificationService
            from notification.models import NotificationType

            NotificationService.notify(
                user=demande.utilisateur,
                title="✅ Paiement confirmé - Domiciliation activée",
                message=(
                    f"Bonjour {demande.utilisateur.get_full_name()},\n\n"
                    f"Votre paiement de {demande.formule.prix} FCFA pour la domiciliation "
                    f"{demande.numero_demande} a bien été reçu.\n\n"
                    f"Votre domiciliation est désormais active jusqu'au "
                    f"{demande.date_fin.strftime('%d/%m/%Y')}.\n\n"
                    f"Merci de votre confiance.\nL'équipe EliteBuro"
                ),
                notification_type=NotificationType.EMAIL,
            )

            messages.success(
                request,
                "✅ Paiement effectué avec succès ! Votre domiciliation est active."
            )

            from django.shortcuts import redirect
            from django.urls import reverse
            return redirect(
                reverse("domiciliation:request_detail", args=[str(demande.id)])
            )

        except DomiciliationRequest.DoesNotExist:
            pass
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Erreur traitement paiement domiciliation: {e}")

    return render(
        request,
        "paiement/indexpaiement.html",
        {
            "success": True,
            "transaction": transaction,
            "reservation": reservation,
            "inscription": inscription,
            "demande": demande,
            "providers": PaymentProvider.objects.filter(is_active=True),
        },
    )


@require_http_methods(["GET"])
def payment_cancel(request: HttpRequest) -> HttpResponse:
    """Page d'annulation du paiement."""
    return render(
        request,
        "paiement/indexpaiement.html",
        {
            "cancelled": True,
            "providers": PaymentProvider.objects.filter(is_active=True),
        },
    )


@csrf_exempt
@require_http_methods(["POST"])
def payment_notify(request: HttpRequest) -> JsonResponse:
    """
    Endpoint de notification (webhook) pour les providers.
    Chaque provider envoie une notification POST avec le statut de la transaction.
    """
    provider_code = request.GET.get("provider", "")

    try:
        data = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        data = request.POST.dict()

    # Logique de traitement du webhook selon le provider
    transaction_id = data.get("transaction_id", "") or data.get("id", "")

    if transaction_id:
        try:
            transaction = PaymentTransaction.objects.get(
                transaction_id=transaction_id
            )
            # Vérifier le statut auprès du provider
            if provider_code:
                try:
                    provider = PaymentProvider.objects.get(code=provider_code)
                    service = PaymentRegistry.get_service(provider)
                    verification = service.verify_payment(transaction_id)
                    if verification.get("success"):
                        transaction.mark_success()
                    else:
                        transaction.mark_failed(
                            verification.get("error_message", "Échec vérification")
                        )
                except Exception:
                    pass

            return JsonResponse({"success": True})
        except PaymentTransaction.DoesNotExist:
            return JsonResponse(
                {"success": False, "error": "Transaction introuvable"}, status=404
            )

    return JsonResponse({"success": True})


@require_http_methods(["GET"])
def provider_config(request: HttpRequest, provider_code: str) -> JsonResponse:
    """
    Retourne la configuration publique d'un provider (sans les clés secrètes).
    Utile pour Stripe (publishable_key) ou PayPal (client_id).
    """
    try:
        provider = get_object_or_404(
            PaymentProvider, code=provider_code, is_active=True
        )

        config = {
            "code": provider.code,
            "name": provider.name,
            "description": provider.description,
            "sandbox_mode": provider.sandbox_mode,
            "config": provider.config_json,
        }

        # Ajouter les clés publiques spécifiques
        if provider.code == "stripe":
            config["publishable_key"] = provider.api_key
        elif provider.code == "paypal":
            config["client_id"] = provider.api_key

        return JsonResponse({"success": True, "config": config})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)
