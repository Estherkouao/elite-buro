from __future__ import annotations

import io
import uuid

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from coworking.models import Workspace, WorkspaceAvailability

from notification.services import NotificationService
from notification.models import NotificationType

from .models import (
    Reservation,
    ReservationInvoice,
    ReservationLog,
    ReservationType,
    ReservationStatus,
)


# =====================================================
# RESULTAT CALCUL PRIX
# =====================================================

@dataclass(frozen=True)
class MoneyBreakdown:

    montant: Decimal
    remise: Decimal
    taxe: Decimal
    total: Decimal



# =====================================================
# CALCUL PRIX RESERVATION
# =====================================================

def calculate_amount_for_workspace(
    espace,
    type_reservation,
    date_debut,
    date_fin,
    heure_debut,
    heure_fin,
    nombre_personnes,
):

    base = Decimal("0")


    # réservation horaire

    if heure_debut and heure_fin and type_reservation in {

        ReservationType.HOT_DESK,
        ReservationType.PRIVATE_OFFICE,
        ReservationType.MEETING_ROOM,
        ReservationType.TRAINING_ROOM,
        ReservationType.CONFERENCE_ROOM,

    }:

        base = Decimal(espace.prix_heure)



    else:

        jours = (date_fin - date_debut).days + 1


        if jours == 1:

            base = Decimal(espace.prix_journee)


        elif jours <= 3:

            base = Decimal(espace.prix_demi_journee)


        elif jours <= 7:

            base = Decimal(espace.prix_semaine)


        else:

            base = Decimal(espace.prix_mois)



    remise = Decimal("0")

    taxe = Decimal("0")


    total = (
        base - remise + taxe
    ).quantize(
        Decimal("0.01")
    )


    return MoneyBreakdown(

        montant=base,

        remise=remise,

        taxe=taxe,

        total=total

    )



# =====================================================
# VERIFICATION DISPONIBILITE
# =====================================================


def check_availability_conflict(
    *,
    reservation,
    ignore_reservation_id=None
):

    conflits = Reservation.objects.filter(
        espace=reservation.espace,

        date_debut__lte=reservation.date_fin,

        date_fin__gte=reservation.date_debut,

        statut__in=[
            ReservationStatus.PENDING,
            ReservationStatus.CONFIRMED,
            ReservationStatus.IN_PROGRESS,
        ],
    )


    # Ignorer la réservation actuelle en modification
    if ignore_reservation_id:
        conflits = conflits.exclude(
            id=ignore_reservation_id
        )


    if conflits.exists():

        raise ValueError(
            "Cet espace est déjà réservé durant cette période."
        )



# =====================================================
# CREATION FACTURE
# =====================================================


def create_invoice_for_reservation(reservation):


    numero = (
        f"INV-{reservation.reservation_number}"
    )


    invoice = ReservationInvoice.objects.create(

        numero=numero,

        reservation=reservation,

        pdf=ContentFile(
            b"",
            name=f"{numero}.pdf"
        ),

        montant=reservation.montant_total,

        statut=ReservationInvoice.InvoiceStatus.DRAFT

    )


    return invoice




# =====================================================
# CALENDRIER
# =====================================================


def generate_calendar_update(reservation: Reservation) -> None:
    """
    Bloque les disponibilités après confirmation d'une réservation.
    """

    from datetime import time, timedelta


    # Réservation journée complète
    if reservation.heure_debut is None or reservation.heure_fin is None:


        current = reservation.date_debut


        while current <= reservation.date_fin:


            WorkspaceAvailability.objects.update_or_create(

                espace=reservation.espace,

                date=current,

                heure_debut=time(
                    0,0
                ),

                heure_fin=time(
                    23,59
                ),


                defaults={

                    "disponible": False

                }

            )


            current += timedelta(days=1)



    # Réservation horaire
    else:


        WorkspaceAvailability.objects.update_or_create(

            espace=reservation.espace,

            date=reservation.date_debut,

            heure_debut=reservation.heure_debut,

            heure_fin=reservation.heure_fin,


            defaults={

                "disponible": False

            }

        )




# =====================================================
# CONFIRMATION ADMIN
# =====================================================


@transaction.atomic

def admin_confirm_reservation(
        actor_user,
        reservation
):


    check_availability_conflict(

        reservation=reservation,

        ignore_reservation_id=reservation.id

    )



    reservation.statut = (
        ReservationStatus.AWAITING_PAYMENT
    )


    reservation.save(
        update_fields=["statut"]
    )



    ReservationLog.objects.create(

        reservation=reservation,

        action=ReservationLog.ActionType.CONFIRMED,

        acteur=actor_user,

        detail="Réservation validée par administration. En attente de paiement du membre."

    )



    if not hasattr(reservation,"invoice"):

        create_invoice_for_reservation(
            reservation
        )



    # Envoyer un email au membre pour demander le paiement
    _send_payment_request_email(reservation)

    return reservation


def _send_payment_request_email(reservation):
    """Envoie un email HTML élégant au membre pour l'inviter à effectuer le paiement."""
    from django.conf import settings
    from django.urls import reverse
    from notification.services import send_html_email

    paiement_url = (
        f"{settings.SITE_URL}/paiement/"
        f"?reservation_id={reservation.id}"
        f"&amount={reservation.montant_total}"
        f"&description={reservation.reservation_number}"
    )

    subject = f"💳 Paiement requis - Réservation {reservation.reservation_number}"

    send_html_email(
        subject=subject,
        recipient_email=reservation.utilisateur.email,
        template_name="emails/reservation_payment_request.html",
        context={
            "reservation": reservation,
            "paiement_url": paiement_url,
        },
        fail_silently=True,
    )






# =====================================================
# ANNULATION
# =====================================================


@transaction.atomic

def admin_cancel_reservation(
        actor_user,
        reservation
):


    reservation.statut = (
        ReservationStatus.CANCELED
    )


    # Libère toute réservation qui a été annulée.
    # NOTE: Dans votre cas, la libération après paiement/expiration n’est pas encore implémentée,
    # mais l’annulation doit restaurer la disponibilité.
    try:
        from coworking.models import WorkspaceAvailability
        # On remet la plage à disponible (même principe que generate_calendar_update).
        if reservation.heure_debut is None or reservation.heure_fin is None:
            from datetime import time, timedelta
            current = reservation.date_debut
            while current <= reservation.date_fin:
                WorkspaceAvailability.objects.update_or_create(
                    espace=reservation.espace,
                    date=current,
                    heure_debut=time(0, 0),
                    heure_fin=time(23, 59),
                    defaults={"disponible": True},
                )
                current += timedelta(days=1)
        else:
            WorkspaceAvailability.objects.update_or_create(
                espace=reservation.espace,
                date=reservation.date_debut,
                heure_debut=reservation.heure_debut,
                heure_fin=reservation.heure_fin,
                defaults={"disponible": True},
            )
    except Exception:
        # Ne pas bloquer l’annulation si la libération échoue.
        pass



    reservation.save(
        update_fields=["statut"]
    )


    ReservationLog.objects.create(

        reservation=reservation,

        action=ReservationLog.ActionType.CANCELED,

        acteur=actor_user,

        detail="Réservation annulée."

    )


    return reservation




# =====================================================
# TERMINEE
# =====================================================


@transaction.atomic

def admin_finish_reservation(
        actor_user,
        reservation
):


    reservation.statut = (
        ReservationStatus.FINISHED
    )


    reservation.save(
        update_fields=["statut"]
    )


    ReservationLog.objects.create(

        reservation=reservation,

        action=ReservationLog.ActionType.UPDATED,

        acteur=actor_user,

        detail="Réservation terminée."

    )


    return reservation


# =====================================================
# EXPORT FACTURE PDF
# =====================================================
# EXPORT FACTURE PDF
# =====================================================

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
except Exception:
    A4 = None
    canvas = None


def export_reservation_invoice_pdf(reservation, user=None):
    """
    Génération simple du fichier PDF de facture.
    """

    invoice = getattr(
        reservation,
        "invoice",
        None
    )

    if invoice is None:
        invoice = create_invoice_for_reservation(reservation)

    # Generate proper PDF using reportlab
    from django.conf import settings
    from django.core.files.base import ContentFile
    from pathlib import Path
    from django.utils import timezone
    import tempfile

    if canvas is None or A4 is None:
        # Fallback to text content if reportlab not available
        content = f"""
EliteBuro
----------------------------

Facture : {invoice.numero}

Réservation :
{reservation.reservation_number}

Client :
{reservation.utilisateur}

Espace :
{reservation.espace}

Date début :
{reservation.date_debut}

Date fin :
{reservation.date_fin}


Montant total :
{reservation.montant_total} FCFA

----------------------------
Merci pour votre confiance.
""".encode()
    else:
        # Create proper PDF
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp_path = Path(tmp.name)

        c = canvas.Canvas(str(tmp_path), pagesize=A4)
        width, height = A4
        y = height - 60

        # Header
        c.setFont("Helvetica-Bold", 18)
        c.setFillColorRGB(1, 0.5, 0)  # Orange
        c.drawString(50, y, "EliteBuro")
        y -= 25

        c.setFont("Helvetica", 10)
        c.setFillColorRGB(0.3, 0.3, 0.3)
        c.drawString(50, y, "Créateur de liens et de business")
        y -= 15
        c.drawString(50, y, "Riviera Palmeraie · Cocody · Abidjan")
        y -= 30

        # Line
        c.setStrokeColorRGB(0.8, 0.8, 0.8)
        c.line(50, y, width - 50, y)
        y -= 30

        # Invoice info
        c.setFont("Helvetica-Bold", 14)
        c.setFillColorRGB(0, 0, 0)
        c.drawString(50, y, f"Facture : {invoice.numero}")
        y -= 30

        # Details
        c.setFont("Helvetica", 11)
        details = [
            ("Réservation :", str(reservation.reservation_number)),
            ("Client :", str(reservation.utilisateur)),
            ("Espace :", str(reservation.espace)),
            ("Date début :", str(reservation.date_debut)),
            ("Date fin :", str(reservation.date_fin)),
        ]

        for label, value in details:
            c.setFont("Helvetica-Bold", 11)
            c.drawString(50, y, label)
            c.setFont("Helvetica", 11)
            c.drawString(180, y, value)
            y -= 22

        y -= 10
        c.setStrokeColorRGB(0.8, 0.8, 0.8)
        c.line(50, y, width - 50, y)
        y -= 25

        # Total
        c.setFont("Helvetica-Bold", 14)
        c.setFillColorRGB(1, 0.5, 0)
        c.drawString(50, y, f"Montant total : {reservation.montant_total} FCFA")
        y -= 40

        # Footer
        c.setFont("Helvetica-Oblique", 10)
        c.setFillColorRGB(0.5, 0.5, 0.5)
        c.drawString(50, y, "Merci pour votre confiance.")
        y -= 20
        c.drawString(50, y, f"Document généré le {timezone.now().strftime('%d/%m/%Y à %H:%M')}")

        c.showPage()
        c.save()

        content = tmp_path.read_bytes()
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass

    filename = f"{invoice.numero}.pdf"

    invoice.pdf.save(
        filename,
        ContentFile(content),
        save=True
    )

    invoice.statut = (
        ReservationInvoice.InvoiceStatus.ISSUED
    )

    invoice.save(
        update_fields=[
            "statut",
            "pdf"
        ]
    )

    ReservationLog.objects.create(
        reservation=reservation,
        action=ReservationLog.ActionType.EXPORTED,
        acteur=user,
        detail=f"Export facture {filename}"
    )

    return filename
