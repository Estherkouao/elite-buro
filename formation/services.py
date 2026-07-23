from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Count, F, Q
from django.utils import timezone

try:
    from reportlab.lib.pagesizes import A4  # type: ignore
    from reportlab.pdfgen import canvas  # type: ignore
except Exception:  # pragma: no cover
    A4 = None  # type: ignore
    canvas = None  # type: ignore

try:
    from docuseal import DocuSeal  # type: ignore
except Exception:  # pragma: no cover
    DocuSeal = None  # type: ignore


from .models import (
    Formation,
    FormationCertificate,
    FormationContract,
    FormationPayment,
    FormationQuote,
    FormationRegistration,
    FormationSession,
    Trainer,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class QuoteResult:
    quote: FormationQuote


def _generate_simple_pdf_bytes(title: str, lines: list[str]) -> bytes:
    buffer = []

    # reportlab exige un file-like object, mais on peut écrire sur un fichier temporaire.
    # Pour rester simple et sans dépendances externes supplémentaires, on génère sur bytes
    # via un fichier dans MEDIA_ROOT si possible.
    tmp_dir = Path(getattr(settings, "MEDIA_ROOT", Path.cwd() / "tmp")) / "formation" / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = tmp_dir / f"{timezone.now().timestamp()}_{abs(hash(title))}.pdf"

    c = canvas.Canvas(str(tmp_path), pagesize=A4)
    width, height = A4
    y = height - 60

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, title[:120])

    c.setFont("Helvetica", 11)
    y -= 30
    for line in lines[:80]:
        if y < 60:
            c.showPage()
            y = height - 60
            c.setFont("Helvetica", 11)
        c.drawString(50, y, str(line)[:180])
        y -= 16

    c.showPage()
    c.save()

    buffer = tmp_path.read_bytes()
    try:
        tmp_path.unlink(missing_ok=True)  # type: ignore[attr-defined]
    except Exception:
        logger.exception("Impossible de supprimer le PDF temporaire: %s", tmp_path)

    return buffer


def calculate_session_cost(session: FormationSession) -> Decimal:
    if not session or not session.formation:
        return Decimal("0")

    formation = session.formation

    # Règle de base: prix catalogue.
    # La logique d'ajustement (taxes/remises) pourra être enrichie ensuite.
    return formation.prix


def get_places_restantes(session: FormationSession) -> int:
    if not session:
        return 0

    confirmed_statuses = {"confirmed", "in_progress"}
    count_qs = (
        session.registrations.filter(statut__in=confirmed_statuses)
        .aggregate(c=Count("id"))
        .get("c", 0)
    )
    return max(0, int(session.nombre_maximum) - int(count_qs or 0))


def _generate_registration_number() -> str:
    # Production-ready: utiliser un séquence/numérotation robuste.
    # Ici: timestamp + aléatoire basée sur hash pour éviter collision quasi.
    return f"FR-{timezone.now().strftime('%Y%m%d%H%M%S')}-{abs(hash(timezone.now().isoformat())) % 100000:05d}"


@transaction.atomic
def create_registration(
    *,
    session: FormationSession | None = None,
    formation: Formation | None = None,
    member,
    entreprise,
    commentaire: str = "",
    preferred_date=None,
) -> FormationRegistration:
    if not member:
        raise ValueError("member est requis")
    if not entreprise:
        raise ValueError("entreprise est requise")

    # Verrouiller la session seulement si elle est fournie
    if session:
        session_locked = FormationSession.objects.select_for_update().select_related("formation").get(pk=session.pk)

        existing = FormationRegistration.objects.filter(
            session=session_locked,
            membre=member,
        ).exists()
        if existing:
            raise ValueError("Cet utilisateur est déjà inscrit à cette session.")

        remaining = get_places_restantes(session_locked)
        if remaining <= 0:
            raise ValueError("Plus de places restantes pour cette session.")
        
        # Dériver la formation depuis la session
        formation = session_locked.formation
    else:
        session_locked = None

    reg = FormationRegistration(
        session=session_locked,
        formation=formation,
        membre=member,
        entreprise=entreprise,
        numero=_generate_registration_number(),
        statut="pending",
        date=preferred_date or timezone.now(),
        commentaire=commentaire or "",
    )
    reg.save()
    return reg


def generate_quote_for_registration(registration: FormationRegistration) -> FormationQuote:
    if not registration:
        raise ValueError("registration requis")

    amount = calculate_session_cost(registration.session)

    lines = [
        "Devis Formation ELITEBURO",
        f"Numéro: {registration.numero}",
        f"Formation: {registration.session.formation.titre}",
        f"Session: {registration.session.date_debut} - {registration.session.date_fin}",
        f"Montant: {amount}",
    ]

    pdf_bytes = _generate_simple_pdf_bytes("Devis de formation", lines)

    quote = FormationQuote(
        inscription=registration,
        montant=amount,
        statut="draft",
        date=timezone.now(),
    )

    filename = f"formation/quotes/{registration.numero}_quote.pdf"
    quote.pdf.save(filename.split("/", 2)[-1], ContentFile(pdf_bytes), save=False)
    quote.save()

    return quote


def generate_contract_for_quote(quote: FormationQuote) -> FormationContract:
    if not quote:
        raise ValueError("quote requis")

    reg = quote.inscription
    session = reg.session
    formation = session.formation

    lines = [
        "Contrat de Formation ELITEBURO",
        f"Devis: {quote.numero if hasattr(quote, 'numero') else quote.id}",
        f"Inscription: {reg.numero}",
        f"Formation: {formation.titre}",
        f"Montant: {quote.montant}",
        "Signature électronique via DocuSeal (si configuré).",
    ]

    pdf_bytes = _generate_simple_pdf_bytes("Contrat de formation", lines)

    contract = FormationContract(
        devis=quote,
        signé=False,
        statut="draft",
        date=timezone.now(),
    )

    filename = f"formation/contracts/{reg.numero}_contract.pdf"
    contract.contrat_pdf.save(filename.split("/", 2)[-1], ContentFile(pdf_bytes), save=False)

    # Prépare un payload DocuSeal "best-effort".
    signature_payload: dict[str, Any] = {
        "provider": "docuseal",
        "status": "pending",
    }
    contract.signature_docuseal = json.dumps(signature_payload, ensure_ascii=False)

    contract.save()
    return contract


def sign_contract(contract: FormationContract) -> FormationContract:
    """Marque la signature comme effectuée.

    Note: sans webhook DocuSeal, on fait un passage en mode best-effort.
    En production, un endpoint webhook mettra à jour signature_docuseal et signé.
    """

    if not contract:
        raise ValueError("contract requis")

    contract.signé = True
    contract.statut = "signed" if hasattr(contract, "statut") else contract.statut
    contract.date = timezone.now()
    contract.save(update_fields=["signé", "statut", "date", "signature_docuseal"] if hasattr(contract, "signature_docuseal") else ["signé"])
    return contract


def generate_certificate_for_registration(registration: FormationRegistration) -> FormationCertificate:
    if not registration:
        raise ValueError("registration requis")

    formation = registration.session.formation
    session = registration.session

    lines = [
        "Attestation de Formation ELITEBURO",
        f"Inscription: {registration.numero}",
        f"Formation: {formation.titre}",
        f"Session: {session.date_debut} - {session.date_fin}",
        "Signée électroniquement (si configuré).",
    ]

    pdf_bytes = _generate_simple_pdf_bytes("Attestation", lines)

    cert = FormationCertificate(
        inscription=registration,
        date=timezone.now(),
    )

    filename = f"formation/certificates/{registration.numero}_certificate.pdf"
    cert.certificat_pdf.save(filename.split("/", 2)[-1], ContentFile(pdf_bytes), save=False)
    cert.save()

    return cert


def process_payment_for_registration(*, inscription: FormationRegistration, amount: Decimal, method: str, reference: str) -> FormationPayment:
    if not inscription:
        raise ValueError("inscription requis")

    payment, _ = FormationPayment.objects.update_or_create(
        inscription=inscription,
        defaults={
            "montant": amount,
            "méthode": method,
            "statut": "paid",
            "référence": reference,
        },
    )
    return payment


def create_or_update_quote(registration: FormationRegistration) -> FormationQuote:
    quote = getattr(registration, "quote", None)
    if quote:
        return quote
    return generate_quote_for_registration(registration)


def create_or_update_contract(quote: FormationQuote) -> FormationContract:
    contract = getattr(quote, "contract", None)
    if contract:
        return contract
    return generate_contract_for_quote(quote)


def maybe_reserve_room_automatically(session: FormationSession) -> bool:
    """Réservation automatique best-effort.

    L'app reservation est présente mais ses modèles/API exacts ne sont pas forcément alignés.
    Pour rester production-safe, on ne crée aucune réservation si le mapping n'est pas certain.
    """

    # On renvoie False si non géré.
    logger.info("Réservation automatique best-effort non activée pour session %s", session.pk)
    return False


def notify_user(*, user, kind: str, message: str) -> None:
    """Envoi de notifications.

    - `notification` app est actuellement un stub; on fait donc un fallback vers logging.
    - Les pages seront aussi compatibles via `django.contrib.messages` (côté vues).
    """

    logger.info("Notification [%s] user=%s: %s", kind, getattr(user, "id", None), message)


def build_quote_preview_amount(session: FormationSession) -> Decimal:
    return calculate_session_cost(session)


# ═══════════════════════════════════════════════════════════════
#  NOTIFICATIONS EMAIL — Workflow Inscription Formation
# ═══════════════════════════════════════════════════════════════

from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from notification.services import NotificationService
from notification.models import NotificationType


def notify_admin_new_registration(registration: FormationRegistration) -> None:
    """Envoyer un email à l'admin quand un membre s'inscrit."""
    subject = f"[EliteBuro] Nouvelle inscription - {registration.numero}"
    message = (
        f"Bonjour,\n\n"
        f"Une nouvelle inscription vient d'être effectuée :\n\n"
        f"  Inscription : {registration.numero}\n"
        f"  Formation : {registration.session.formation.titre}\n"
        f"  Session : {registration.session.date_debut} au {registration.session.date_fin}\n"
        f"  Membre : {registration.membre.full_name}\n"
        f"  Email : {registration.membre.email}\n"
        f"  Téléphone : {registration.membre.phone}\n\n"
        f"Connectez-vous au dashboard pour valider ou refuser :\n"
        f"{settings.SITE_URL}/dashboard/formations/inscriptions/\n\n"
        f"Cordialement,\nL'équipe EliteBuro"
    )
    # Envoyer à tous les admins
    from django.contrib.auth import get_user_model
    User = get_user_model()
    admins = User.objects.filter(role=User.Role.ADMIN, is_active=True)
    for admin in admins:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[admin.email],
            fail_silently=True,
        )


def notify_trainer_new_registration(registration: FormationRegistration) -> None:
    """Envoyer un email au formateur de la session."""
    trainer = registration.session.formateur
    if not trainer or not trainer.user or not trainer.user.email:
        return

    subject = f"[EliteBuro] Nouvel inscrit à votre formation - {registration.numero}"
    message = (
        f"Bonjour {trainer.user.full_name},\n\n"
        f"Un nouveau membre s'est inscrit à votre formation :\n\n"
        f"  Inscription : {registration.numero}\n"
        f"  Formation : {registration.session.formation.titre}\n"
        f"  Session : {registration.session.date_debut} au {registration.session.date_fin}\n"
        f"  Membre : {registration.membre.full_name}\n"
        f"  Email : {registration.membre.email}\n"
        f"  Téléphone : {registration.membre.phone}\n\n"
        f"L'inscription est en attente de validation par l'administration.\n\n"
        f"Cordialement,\nL'équipe EliteBuro"
    )
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[trainer.user.email],
        fail_silently=True,
    )


def notify_member_registration_confirmed(registration: FormationRegistration) -> None:
    """Envoyer un email au membre pour l'informer que son inscription est approuvée
    et l'inviter à payer."""
    subject = f"[EliteBuro] Inscription approuvée - {registration.numero}"
    payment_url = f"{settings.SITE_URL}/formation/paiement/{registration.id}/"
    message = (
        f"Bonjour {registration.membre.full_name},\n\n"
        f"Votre inscription à la formation '{registration.session.formation.titre}' "
        f"(session du {registration.session.date_debut} au {registration.session.date_fin}) "
        f"a été approuvée !\n\n"
        f"Pour finaliser votre inscription et accéder aux cours, veuillez effectuer le paiement "
        f"via le lien ci-dessous :\n\n"
        f"  {payment_url}\n\n"
        f"Montant à payer : {registration.session.formation.prix} FCFA\n\n"
        f"Une fois le paiement effectué, vous recevrez votre code d'accès aux cours "
        f"et votre facture par email.\n\n"
        f"Cordialement,\nL'équipe EliteBuro"
    )
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[registration.membre.email],
            fail_silently=False,
        )
        logger.info(
            "Email de confirmation envoyé avec succès à %s pour l'inscription %s",
            registration.membre.email,
            registration.numero,
        )
    except Exception as e:
        logger.error(
            "ÉCHEC envoi email de confirmation à %s pour inscription %s: %s",
            registration.membre.email,
            registration.numero,
            e,
        )


def notify_trainer_registration_confirmed(registration: FormationRegistration) -> None:
    """Envoyer un email au formateur pour l'informer qu'une inscription a été validée
    avec la liste complète des inscrits à sa session."""
    trainer = registration.session.formateur
    if not trainer or not trainer.user or not trainer.user.email:
        return

    # Récupérer la liste de tous les inscrits (confirmés) à cette session
    all_regs = FormationRegistration.objects.filter(
        session=registration.session,
        statut=FormationRegistration.Statut.CONFIRMED,
    ).select_related("membre", "entreprise")

    students_list = ""
    for i, r in enumerate(all_regs, 1):
        company_name = r.entreprise.company_name if r.entreprise else "N/A"
        students_list += (
            f"  {i}. {r.membre.full_name} — {r.membre.email}"
            f" — {company_name}\n"
        )

    trainer_url = f"{settings.SITE_URL}/dashboard/trainer/students/"
    subject = f"[EliteBuro] Inscription validée - {registration.numero}"
    message = (
        f"Bonjour {trainer.user.full_name},\n\n"
        f"Une inscription à votre formation a été validée par l'administration :\n\n"
        f"  Inscription : {registration.numero}\n"
        f"  Formation : {registration.session.formation.titre}\n"
        f"  Session : {registration.session.date_debut} au {registration.session.date_fin}\n"
        f"  Membre : {registration.membre.full_name}\n"
        f"  Email : {registration.membre.email}\n"
        f"  Téléphone : {registration.membre.phone}\n\n"
        f"--- Liste complète des inscrits à cette session ---\n\n"
        f"{students_list}\n"
        f"Consultez la liste complète sur votre dashboard :\n"
        f"{trainer_url}\n\n"
        f"Cordialement,\nL'équipe EliteBuro"
    )
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[trainer.user.email],
        fail_silently=True,
    )


def notify_member_payment_success(registration: FormationRegistration, montant: Decimal, reference: str) -> None:
    """Envoyer un email au membre après paiement réussi avec sa facture."""
    subject = f"[EliteBuro] Paiement confirmé - {registration.numero}"
    message = (
        f"Bonjour {registration.membre.full_name},\n\n"
        f"Nous vous confirmons la réception de votre paiement de {montant} FCFA "
        f"pour la formation '{registration.session.formation.titre}'.\n\n"
        f"  Référence : {reference}\n"
        f"  Montant : {montant} FCFA\n"
        f"  Formation : {registration.session.formation.titre}\n"
        f"  Session : {registration.session.date_debut} au {registration.session.date_fin}\n\n"
        f"Vous trouverez ci-joint votre facture acquittée.\n\n"
        f"Votre code d'accès aux cours vous sera communiqué par le formateur "
        f"dans les plus brefs délais.\n\n"
        f"Cordialement,\nL'équipe EliteBuro"
    )
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[registration.membre.email],
        fail_silently=True,
    )


def notify_member_access_code(registration: FormationRegistration, code: str) -> None:
    """Envoyer au membre son code d'accès aux cours."""
    subject = f"[EliteBuro] Votre code d'accès aux cours - {registration.numero}"
    message = (
        f"Bonjour {registration.membre.full_name},\n\n"
        f"Votre code d'accès aux cours de '{registration.session.formation.titre}' "
        f"est maintenant disponible :\n\n"
        f"  Code d'accès : {code}\n\n"
        f"Rendez-vous sur votre espace membre pour accéder aux cours :\n"
        f"{settings.SITE_URL}/formation/mes-cours/\n\n"
        f"Ce code est personnel et non transférable.\n\n"
        f"Cordialement,\nL'équipe EliteBuro"
    )
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[registration.membre.email],
        fail_silently=True,
    )


def generate_access_code(registration: FormationRegistration) -> str:
    """Générer un code d'accès unique pour le membre."""
    import hashlib
    import uuid
    raw = f"{registration.id}-{registration.numero}-{uuid.uuid4()}"
    code = hashlib.sha256(raw.encode()).hexdigest()[:12].upper()
    return f"EB-{code}"

