"""Génération du contrat de domiciliation au format PDF depuis le template HTML.

Ce module rend le template `domiciliation/contractpdf.html` grâce à xhtml2pdf
(ou reportlab en secours) puis renvoie les octets du PDF.
"""
from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.template.loader import render_to_string

try:
    from xhtml2pdf import pisa
except Exception:  # pragma: no cover
    pisa = None

# Informations ELITEBURO (prestataire) affichées sur le contrat
ELITEBURO_INFOS = {
    "adresse": "Cocody Riviera Palmeraie, Abidjan, Côte d'Ivoire",
    "telephone": "+225 27 22 00 00 00",
    "email": "contact@eliteburo.com",
    "rccm": "CI-ABJ-2019-B-12345",
    "cc": "1234567890",
}


def _libelle_type_demande(demande) -> str:
    """Retourne un libellé clair pour le type de demande."""
    codes = {
        "DOMICILIATION": "Domiciliation commerciale",
        "EI": "Création d'entreprise individuelle et domiciliation",
        "SARL": "Création de SARL et domiciliation",
        "SARLU": "Création de SARLU et domiciliation",
        "SAS": "Création de SAS et domiciliation",
        "SASU": "Création de SASU et domiciliation",
        "ONG": "Création d'ONG et domiciliation",
        "STARTUP": "Création de Startup et domiciliation",
        "SCI": "Création de SCI et domiciliation",
        "ASSOCIATION": "Création d'association et domiciliation",
        "FONDATION": "Création de fondation et domiciliation",
        "SCOOP": "Création de SCOOP et domiciliation",
    }
    return codes.get(demande.type_demande, demande.type_demande)


def _forme_juridique(demande) -> str:
    codes = {
        "DOMICILIATION": "Domiciliation simple",
        "EI": "Entreprise Individuelle (EI)",
        "SARL": "Société à Responsabilité Limitée (SARL)",
        "SARLU": "SARL Unipersonnelle (SARLU)",
        "SAS": "Société par Actions Simplifiée (SAS)",
        "SASU": "SAS Unipersonnelle (SASU)",
        "ONG": "Organisation Non Gouvernementale (ONG)",
        "STARTUP": "Startup",
        "SCI": "Société Civile Immobilière (SCI)",
        "ASSOCIATION": "Association",
        "FONDATION": "Fondation",
        "SCOOP": "Société Coopérative Simplifiée (SCOOP)",
    }
    return codes.get(demande.type_demande, demande.type_demande)


def _extraire_ville_siege(demande):
    """Extrait ville et siège depuis adresse_domiciliation ou observations."""
    adresse = demande.adresse_domiciliation or ""
    parts = [p.strip() for p in adresse.split(",") if p.strip()]
    siege = parts[0] if parts else ""
    ville = parts[1] if len(parts) > 1 else ""
    return ville, siege


def _logo_path() -> str:
    """Retourne le chemin absolu du logo ELITEBURO si présent."""
    candidates = [
        settings.BASE_DIR / "media" / "ELITE BURO LOG1.png",
        settings.BASE_DIR / "media" / "ELITE BURO LOG1.jpg",
        settings.BASE_DIR / "media" / "logo.png",
        settings.BASE_DIR / "media" / "logo1.png",
    ]
    for c in candidates:
        if Path(c).exists():
            return str(c)
    return ""


def _contexte_contrat(demande) -> dict:
    """Construit le contexte Django pour le template du contrat."""
    ville, siege = _extraire_ville_siege(demande)
    return {
        "demande": demande,
        "entreprise": ELITEBURO_INFOS,
        "type_demande_label": _libelle_type_demande(demande),
        "forme_juridique": _forme_juridique(demande),
        "ville": ville,
        "siege_social": siege,
        "logo": _logo_path(),
    }


def generer_contrat_pdf_from_template(demande) -> bytes:
    """Génère le PDF du contrat à partir du template HTML contractpdf.html."""
    if pisa is None:
        return generer_contrat_pdf_bytes_simple(demande)

    from io import BytesIO

    html = render_to_string(
        "domiciliation/contractpdf.html",
        _contexte_contrat(demande),
    )
    result = BytesIO()
    pdf = pisa.pisaDocument(src=html, dest=result, encoding="utf-8")
    if not pdf.err:
        return result.getvalue()
    return generer_contrat_pdf_bytes_simple(demande)


def generer_contrat_pdf_bytes_simple(demande) -> bytes:
    """Fallback : génère un PDF texte simple si le template ne peut pas être rendu.

    Utilise reportlab (déjà importé dans services.py).
    """
    from .services import _generer_pdf_simple

    plan = demande.formule
    contenu = (
        "Demande: {0}\n"
        "Client: {1}\n"
        "Entreprise: {2}\n"
        "Formule: {3} ({4} mois)\n"
        "Adresse: {5}\n"
        "Type: {6}".format(
            demande.numero_demande,
            demande.utilisateur.get_full_name(),
            demande.entreprise.company_name,
            plan.nom,
            plan.durée,
            demande.adresse_domiciliation,
            _libelle_type_demande(demande),
        )
    )
    return _generer_pdf_simple("Contrat de domiciliation", contenu)


def generer_contrat_pdf_bytes(demande) -> bytes:
    """Génère le PDF du contrat à partir du template HTML contractpdf.html."""
    return generer_contrat_pdf_from_template(demande)
