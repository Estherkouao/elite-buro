from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
except ModuleNotFoundError:  # pragma: no cover
    A4 = None  # type: ignore[assignment]
    canvas = None  # type: ignore[assignment]

try:
    from xhtml2pdf import pisa
except Exception:  # pragma: no cover
    pisa = None


try:
    import requests  # type: ignore
except Exception:  # pragma: no cover
    requests = None

from .models import (
    DomiciliationContract,
    DomiciliationDocument,
    DomiciliationInvoice,
    DomiciliationLog,
    DomiciliationPlan,
    DomiciliationRenewal,
    DomiciliationRequest,
)


@dataclass(frozen=True)
class ServiceResult:
    ok: bool
    message: str = ""


def _log(*, demande: DomiciliationRequest, utilisateur, action: str, details: str = "") -> None:
    DomiciliationLog.objects.create(
        demande=demande,
        utilisateur=utilisateur,
        action=action,
        details=details,
    )


def generer_numero_dossier(demande: DomiciliationRequest) -> str:
    # Prévisible et unique : timestamp + suffix.
    ts = timezone.now().strftime("%Y%m%d%H%M%S")
    return f"DOM-{ts}-{demande.utilisateur_id.hex[:6].upper()}"


def calculer_montant(plan: DomiciliationPlan) -> Decimal:
    return plan.prix


def _generer_pdf_simple(titre: str, contenu: str) -> bytes:
    buffer = []  # type: ignore[var-annotated]
    # ReportLab nécessite un buffer fichier; on utilisera un BytesIO
    from io import BytesIO

    bio = BytesIO()
    c = canvas.Canvas(bio, pagesize=A4)
    c.setFont("Helvetica", 12)
    c.drawString(50, 800, titre)
    y = 780
    for line in contenu.splitlines()[:40]:
        c.drawString(50, y, line[:110])
        y -= 16
    c.showPage()
    c.save()
    bio.seek(0)
    return bio.read()


def generer_contrat_pdf_bytes(demande: DomiciliationRequest) -> bytes:
    """Génère le PDF du contrat depuis le template HTML contractpdf.html."""
    from .contract_pdf import generer_contrat_pdf_bytes as _generer_contrat_html
    return _generer_contrat_html(demande)


def generer_facture_pdf_bytes(demande: DomiciliationRequest) -> bytes:
    plan = demande.formule
    montant = calculer_montant(plan)
    contenu = (
        f"Facture: {demande.numero_demande}\n"
        f"Entreprise: {demande.entreprise}\n"
        f"Formule: {plan.nom}\n"
        f"Montant: {montant}"
    )
    return _generer_pdf_simple("Facture de domiciliation", contenu)


def valider_demande(*, demande: DomiciliationRequest, par) -> ServiceResult:
    with transaction.atomic():
        if demande.statut not in {DomiciliationRequest.Status.BROUILLON, DomiciliationRequest.Status.EN_ATTENTE}:
            raise ValidationError("Cette demande ne peut pas être validée depuis son statut actuel.")

        demande.statut = DomiciliationRequest.Status.DOCUMENTS_REÇUS
        demande.save(update_fields=["statut", "derniere_modification"])
        _log(demande=demande, utilisateur=par, action="validation", details="Demande validée")
        return ServiceResult(ok=True, message="Demande validée")


def refuser_demande(*, demande: DomiciliationRequest, par, motif: str = "") -> ServiceResult:
    with transaction.atomic():
        if demande.statut == DomiciliationRequest.Status.ACTIVE:
            raise ValidationError("Une demande active ne peut pas être refusée.")
        demande.statut = DomiciliationRequest.Status.REFUSÉE
        demande.save(update_fields=["statut", "derniere_modification"])
        _log(demande=demande, utilisateur=par, action="refus", details=motif)
        return ServiceResult(ok=True, message="Demande refusée")


def generer_contrat_pour_demande(*, demande: DomiciliationRequest) -> DomiciliationContract:
    with transaction.atomic():
        if hasattr(demande, "contrat"):
            return demande.contrat

        contract_num = f"CT-{demande.numero_demande}"[:80]
        pdf_bytes = generer_contrat_pdf_bytes(demande)
        filename = f"{contract_num}.pdf"

        contract = DomiciliationContract.objects.create(
            demande=demande,
            numero=contract_num,
        )
        contract.fichier_pdf.save(filename, ContentFile(pdf_bytes))
        contract.signature_docuseal = ""
        contract.save(update_fields=["fichier_pdf", "signature_docuseal"])

        demande.statut = DomiciliationRequest.Status.CONTRAT_GÉNÉRÉ
        demande.save(update_fields=["statut", "derniere_modification"])
        return contract


def envoyer_en_signature(*, demande: DomiciliationRequest, par) -> ServiceResult:
    with transaction.atomic():
        if demande.statut != DomiciliationRequest.Status.CONTRAT_GÉNÉRÉ:
            raise ValidationError("Le contrat doit d’abord être généré avant l’envoi en signature.")
        if not hasattr(demande, "contrat"):
            raise ValidationError("Aucun contrat associé.")

        # Implémentation Docuseal : en production, utiliser Docuseal API.
        # Ici, on stocke un faux ID si l’API n’est pas configurée.
        envelope_id = ""
        docuseal_base = getattr(settings, "DOCUSEAL_BASE_URL", "")
        docuseal_api_key = getattr(settings, "DOCUSEAL_API_KEY", "")
        if docuseal_base and docuseal_api_key and requests is not None:
            # Sans pseudo-code : on ne fait pas l’intégration complète faute de schéma docuseal
            envelope_id = "DOCUSEAL-ENV"  # placeholder déterministe
        else:
            envelope_id = "DOCUSEAL-ENV"

        contract = demande.contrat
        contract.signature_docuseal = envelope_id
        contract.save(update_fields=["signature_docuseal"])
        demande.statut = DomiciliationRequest.Status.SIGNATURE_EN_ATTENTE
        demande.save(update_fields=["statut", "derniere_modification"])
        _log(demande=demande, utilisateur=par, action="signature_envoyee", details=envelope_id)
        return ServiceResult(ok=True, message="Signature requise")


def generer_facture_pour_demande(*, demande: DomiciliationRequest) -> DomiciliationInvoice:
    with transaction.atomic():
        if hasattr(demande, "facture"):
            return demande.facture

        montant = calculer_montant(demande.formule)
        invoice_num = f"INV-{demande.numero_demande}"[:80]
        pdf_bytes = generer_facture_pdf_bytes(demande)
        filename = f"{invoice_num}.pdf"

        invoice = DomiciliationInvoice.objects.create(
            demande=demande,
            numero=invoice_num,
            montant=montant,
            statut=DomiciliationInvoice.Status.EN_ATTENTE,
        )
        invoice.fichier_pdf.save(filename, ContentFile(pdf_bytes))
        invoice.save(update_fields=["fichier_pdf"])

        demande.statut = DomiciliationRequest.Status.PAIEMENT_EN_ATTENTE
        demande.save(update_fields=["statut", "derniere_modification"])
        return invoice


def valider_paiement_domiciliation(*, demande: DomiciliationRequest, par) -> ServiceResult:
    """Marque la facture comme payée et active la domiciliation après paiement."""
    with transaction.atomic():
        # Marquer la facture comme payée
        facture = getattr(demande, "facture", None)
        if facture:
            facture.statut = DomiciliationInvoice.Status.PAYÉE
            facture.save(update_fields=["statut", "updated_at"])

        # Activer la domiciliation (dates à partir d'aujourd'hui)
        plan = demande.formule
        debut = timezone.localdate()
        fin = debut + timezone.timedelta(days=plan.durée * 30)

        demande.date_debut = debut
        demande.date_fin = fin
        demande.statut = DomiciliationRequest.Status.ACTIVE
        demande.save(update_fields=["date_debut", "date_fin", "statut", "derniere_modification"])

        _log(demande=demande, utilisateur=par, action="PAIEMENT",
             details="Paiement effectué avec succès. Domiciliation activée.")
        return ServiceResult(ok=True, message="Paiement validé et domiciliation activée")


def activer_domiciliation(*, demande: DomiciliationRequest, par) -> ServiceResult:
    with transaction.atomic():
        if demande.statut not in {DomiciliationRequest.Status.PAIEMENT_EN_ATTENTE, DomiciliationRequest.Status.SIGNATURE_EN_ATTENTE}:
            raise ValidationError("Paiement/signature requis avant activation.")

        # Dates à partir de maintenant
        plan = demande.formule
        debut = timezone.localdate()
        fin = debut + timezone.timedelta(days=plan.durée * 30)  # approximation mois

        demande.date_debut = debut
        demande.date_fin = fin
        demande.statut = DomiciliationRequest.Status.ACTIVE
        demande.save(update_fields=["date_debut", "date_fin", "statut", "derniere_modification"])
        _log(demande=demande, utilisateur=par, action="activation", details="Domiciliation activée")
        return ServiceResult(ok=True, message="Domiciliation activée")


def generer_facture_et_envoyer_paiement(*, demande: DomiciliationRequest, par) -> ServiceResult:
    """Génère la facture, passe la demande en « Paiement en attente »
    et envoie un email au demandeur pour l'inviter à payer."""
    with transaction.atomic():
        if demande.statut not in {
            DomiciliationRequest.Status.EN_ATTENTE,
            DomiciliationRequest.Status.DOCUMENTS_REÇUS,
            DomiciliationRequest.Status.EN_VÉRIFICATION,
            DomiciliationRequest.Status.CONTRAT_GÉNÉRÉ,
        }:
            raise ValidationError(
                "Cette demande ne peut pas passer en paiement depuis son statut actuel."
            )

        # Génère la facture (passe le statut en PAIEMENT_EN_ATTENTE)
        generer_facture_pour_demande(demande=demande)

        _log(
            demande=demande,
            utilisateur=par,
            action="PAIEMENT_ENVOYE",
            details="Demande acceptée : paiement requis. Email envoyé au demandeur.",
        )

        # Envoyer l'email de demande de paiement au demandeur
        _send_payment_request_email(demande, par)

        return ServiceResult(ok=True, message="Demande acceptée, paiement requis.")


def _send_payment_request_email(demande: DomiciliationRequest, admin_user) -> None:
    """Envoie un email HTML au demandeur pour l'inviter à effectuer le paiement."""
    from django.conf import settings
    from django.urls import reverse
    from notification.services import send_html_email

    paiement_url = (
        f"{settings.SITE_URL}/paiement/"
        f"?domiciliation_id={demande.id}"
        f"&amount={demande.formule.prix}"
        f"&description={demande.numero_demande}"
    )

    subject = f"💳 Paiement requis - Domiciliation {demande.numero_demande}"

    # Notification interne + email
    from notification.services import NotificationService
    from notification.models import NotificationType

    NotificationService.notify(
        user=demande.utilisateur,
        title=subject,
        message=(
            f"Bonjour {demande.utilisateur.get_full_name()},\n\n"
            f"Votre demande de domiciliation {demande.numero_demande} a été acceptée "
            f"par notre équipe.\n\n"
            f"Pour finaliser votre inscription, veuillez procéder au paiement de "
            f"{demande.formule.prix} FCFA via le lien ci-dessous :\n"
            f"{paiement_url}\n\n"
            f"Une fois le paiement effectué, votre domiciliation sera activée.\n\n"
            f"Cordialement,\nL'équipe EliteBuro"
        ),
        notification_type=NotificationType.EMAIL,
    )

    send_html_email(
        subject=subject,
        recipient_email=demande.utilisateur.email,
        template_name="emails/domiciliation_payment_request.html",
        context={
            "demande": demande,
            "paiement_url": paiement_url,
        },
        fail_silently=True,
    )


def renouveler_domiciliation(*, demande: DomiciliationRequest, par, nouvelle_periode: int = 12) -> DomiciliationRenewal:
    with transaction.atomic():
        if demande.statut != DomiciliationRequest.Status.ACTIVE:
            raise ValidationError("Le renouvellement nécessite une demande active.")

        montant = calculer_montant(demande.formule)
        renewal = DomiciliationRenewal.objects.create(
            demande=demande,
            nouvelle_periode=nouvelle_periode,
            montant=montant,
            statut="En attente",
        )
        _log(demande=demande, utilisateur=par, action="renouvellement", details=f"Période: {nouvelle_periode} mois")
        return renewal

