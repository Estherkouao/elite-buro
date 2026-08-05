"""Génération du contrat de domiciliation au format PDF (reportlab platypus).

Génère un contrat professionnel identique au modèle de référence :
en-tête ELITEBURO, titre, référence, identification des parties,
nature de la prestation, informations sur l'entreprise, articles 1 à 13,
déclaration du client et signatures.
"""
from __future__ import annotations

from datetime import date
from io import BytesIO
from pathlib import Path

from django.conf import settings

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)

ORANGE = colors.HexColor("#FF8000")
ORANGE_DARK = colors.HexColor("#E66A00")
ORANGE_LIGHT = colors.HexColor("#FFF3E6")
GREY = colors.HexColor("#555555")
GREY_LIGHT = colors.HexColor("#F4F4F4")
TEXT = colors.HexColor("#222222")

ELITEBURO_INFOS = {
    "adresse": "Cocody Riviera Palmeraie, Abidjan, Côte d'Ivoire",
    "telephone": "+225 01 41 13 67 17",
    "email": "info@eliteburo.com",
    "rccm": "CI-ABJ-2019-B-12345",
    "cc": "1234567890",
}


def _libelle_type_demande(demande) -> str:
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
    adresse = demande.adresse_domiciliation or ""
    parts = [p.strip() for p in adresse.split(",") if p.strip()]
    siege = parts[0] if parts else ""
    ville = parts[1] if len(parts) > 1 else ""
    return ville, siege


def _logo_path() -> str:
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


def _styles():
    ss = getSampleStyleSheet()
    s = {}

    s["title"] = ParagraphStyle(
        "ebTitle", parent=ss["Title"], fontName="Helvetica-Bold",
        fontSize=22, leading=26, textColor=ORANGE, alignment=TA_CENTER,
        spaceAfter=2,
    )
    s["subtitle"] = ParagraphStyle(
        "ebSubtitle", parent=ss["Normal"], fontName="Helvetica",
        fontSize=9, leading=12, textColor=GREY, alignment=TA_CENTER,
    )
    s["contract_title"] = ParagraphStyle(
        "ebContractTitle", parent=ss["Normal"], fontName="Helvetica-Bold",
        fontSize=14, leading=18, textColor=ORANGE, alignment=TA_CENTER,
        spaceBefore=6, spaceAfter=10,
    )
    s["section_title"] = ParagraphStyle(
        "ebSectionTitle", parent=ss["Normal"], fontName="Helvetica-Bold",
        fontSize=12, leading=16, textColor=TEXT, spaceBefore=10, spaceAfter=4,
    )
    s["body"] = ParagraphStyle(
        "ebBody", parent=ss["Normal"], fontName="Helvetica",
        fontSize=10, leading=14, textColor=TEXT, alignment=TA_JUSTIFY, spaceAfter=3,
    )
    s["body_ind"] = ParagraphStyle(
        "ebBodyInd", parent=s["body"], leftIndent=14, spaceAfter=2,
    )
    s["article_title"] = ParagraphStyle(
        "ebArticle", parent=ss["Normal"], fontName="Helvetica-Bold",
        fontSize=11, leading=15, textColor=ORANGE_DARK, spaceBefore=12, spaceAfter=4,
    )
    s["cell_text"] = ParagraphStyle(
        "ebCell", parent=ss["Normal"], fontName="Helvetica",
        fontSize=9.5, leading=13, textColor=TEXT,
    )
    s["cell_label"] = ParagraphStyle(
        "ebCellLabel", parent=s["cell_text"], fontName="Helvetica-Bold",
    )
    s["sign"] = ParagraphStyle(
        "ebSign", parent=ss["Normal"], fontName="Helvetica",
        fontSize=9.5, leading=13, textColor=TEXT, alignment=TA_CENTER,
    )
    s["sign_title"] = ParagraphStyle(
        "ebSignTitle", parent=s["sign"], fontName="Helvetica-Bold",
        fontSize=11, leading=15, textColor=ORANGE_DARK,
    )
    s["footer"] = ParagraphStyle(
        "ebFooter", parent=ss["Normal"], fontName="Helvetica",
        fontSize=7, leading=10, textColor=GREY, alignment=TA_CENTER,
    )
    return s


def _header_footer(canvas, doc):
    canvas.saveState()

    canvas.setStrokeColor(ORANGE)
    canvas.setLineWidth(2.5)
    canvas.line(18 * mm, A4[1] - 12 * mm, A4[0] - 18 * mm, A4[1] - 12 * mm)

    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(GREY)
    canvas.drawCentredString(
        A4[0] / 2.0, 14 * mm,
        "ELITEBURO — Cabinet de Création d'Entreprise • Domiciliation • Assistance Administrative",
    )
    canvas.drawCentredString(
        A4[0] / 2.0, 9 * mm,
        f"{ELITEBURO_INFOS['adresse']} | Tél : {ELITEBURO_INFOS['telephone']} | {ELITEBURO_INFOS['email']}",
    )
    canvas.drawRightString(A4[0] - 18 * mm, 14 * mm, f"Page {canvas.getPageNumber()}")

    canvas.restoreState()


def _checkbox_table(rows, styles) -> Table:
    S = styles
    data = []
    for label, checked in rows:
        mark = "X" if checked else ""
        data.append([
            Paragraph(label, S["cell_text"]),
            Paragraph(mark, ParagraphStyle(
                "ebCheck", parent=S["cell_text"], alignment=TA_CENTER, fontName="Helvetica-Bold",
                textColor=ORANGE if checked else GREY,
            )),
        ])
    t = Table(data, colWidths=[150 * mm, 18 * mm])
    t.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#DDDDDD")),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#DDDDDD")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
    ]))
    return t


def _partie_table(demande, styles):
    S = styles
    ville, siege = _extraire_ville_siege(demande)
    client_name = f"{demande.utilisateur.first_name} {demande.utilisateur.last_name}"

    prestataire_data = [
        [Paragraph("Prestataire", S["cell_label"])],
        [Paragraph(f"<b>ELITEBURO</b>", S["cell_text"])],
        [Paragraph(f"Adresse : {ELITEBURO_INFOS['adresse']}", S["cell_text"])],
        [Paragraph(f"Téléphone : {ELITEBURO_INFOS['telephone']}", S["cell_text"])],
        [Paragraph(f"Email : {ELITEBURO_INFOS['email']}", S["cell_text"])],
        [Paragraph(f"RCCM : {ELITEBURO_INFOS['rccm']}", S["cell_text"])],
        [Paragraph(f"CC : {ELITEBURO_INFOS['cc']}", S["cell_text"])],
    ]

    client_data = [
        [Paragraph("Le Client", S["cell_label"])],
        [Paragraph(f"<b>{client_name}</b>", S["cell_text"])],
        [Paragraph(f"Téléphone : {demande.utilisateur.phone or '—'}", S["cell_text"])],
        [Paragraph(f"Email : {demande.utilisateur.email or '—'}", S["cell_text"])],
        [Paragraph(f"Adresse : {demande.adresse_domiciliation or '—'}", S["cell_text"])],
        [Paragraph(f"Ville : {ville or '—'}", S["cell_text"])],
    ]

    t = Table([[prestataire_data, client_data]], colWidths=[85 * mm, 85 * mm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#FAFAFA")),
        ("BACKGROUND", (1, 0), (1, -1), colors.white),
    ]))
    return t


def _build_story(demande, styles):
    S = styles
    story = []

    logo_path = _logo_path()
    if logo_path:
        try:
            img = Image(logo_path, width=50 * mm, height=25 * mm)
            img.hAlign = "CENTER"
            story.append(img)
        except Exception:
            pass

    story.append(Paragraph("ELITEBURO", S["title"]))
    story.append(Paragraph(
        "Cabinet de Création d'Entreprise • Domiciliation • Assistance Administrative",
        S["subtitle"],
    ))
    story.append(Spacer(1, 3 * mm))
    story.append(HRFlowable(width="100%", thickness=2.5, color=ORANGE, spaceAfter=5 * mm))

    story.append(Paragraph(
        "CONTRAT DE PRESTATION DE SERVICES<br/>"
        "CRÉATION D'ENTREPRISE ET / OU DOMICILIATION COMMERCIALE",
        S["contract_title"],
    ))

    story.append(Paragraph(
        f"Référence : <b>{demande.numero_demande}</b> &nbsp;&nbsp;|&nbsp;&nbsp; "
        f"Date : {date.today().strftime('%d/%m/%Y')}",
        S["body"],
    ))
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("IDENTIFICATION DES PARTIES", S["section_title"]))
    story.append(_partie_table(demande, styles))
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("NATURE DE LA PRESTATION", S["section_title"]))
    story.append(Paragraph(f"Le présent contrat concerne la prestation suivante : {_libelle_type_demande(demande)}", S["body"]))
    story.append(_checkbox_table([
        ("Prestation", False),
        ("Cocher", False),
        ("Domiciliation commerciale", demande.type_demande == "DOMICILIATION"),
        ("Création d'entreprise individuelle", demande.type_demande == "EI"),
        ("Création de société", demande.type_demande in {"SARL", "SARLU", "SAS", "SASU"}),
        ("Création ONG / Association / Fondation", demande.type_demande in {"ONG", "ASSOCIATION", "FONDATION"}),
        (f"Autre : {_libelle_type_demande(demande)}", False),
    ], S))

    if demande.type_demande != "DOMICILIATION":
        story.append(_checkbox_table([
            ("Création + Domiciliation", True),
        ], S))

    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("INFORMATIONS SUR L'ENTREPRISE", S["section_title"]))
    entreprise = demande.entreprise
    ville, siege = _extraire_ville_siege(demande)
    story.append(_checkbox_table([
        (f"Nom de l'entreprise {entreprise.company_name or '—'}", True),
        (f"Forme juridique {_forme_juridique(demande)}", True),
        (f"Activité {entreprise.description or '—'}", True),
        (f"Ville {ville or '—'}", True),
        (f"Adresse du siège {siege or '—'}", True),
    ], S))
    story.append(Spacer(1, 4 * mm))

    articles = [
        (
            "ARTICLE 1 — OBJET DU CONTRAT",
            [
                "Le présent contrat a pour objet de définir les conditions dans lesquelles ELITEBURO accompagne le Client dans ses démarches administratives relatives à la création, à la domiciliation ou à la régularisation de son entreprise.",
                "Selon la prestation choisie, ELITEBURO assure la constitution du dossier, le suivi administratif, l'accompagnement auprès des administrations compétentes ainsi que la remise des documents officiels obtenus. Les prestations réalisées sont exclusivement celles commandées par le Client et mentionnées dans le présent contrat.",
            ]
        ),
        (
            "ARTICLE 2 — PRESTATIONS FOURNIES PAR ELITEBURO",
            [
                "Selon la nature de la demande formulée par le Client, ELITEBURO s'engage à réaliser les prestations nécessaires à la bonne exécution de sa mission. Les prestations peuvent comprendre notamment :",
                "✓ Analyse et vérification du dossier du Client ;",
                "✓ Constitution des pièces administratives ;",
                "✓ Assistance dans la préparation des documents ;",
                "✓ Dépôt du dossier auprès des administrations compétentes ;",
                "✓ Suivi administratif jusqu'à l'obtention des documents ;",
                "✓ Information régulière du Client sur l'avancement de son dossier ;",
                "✓ Mise à disposition des documents dans l'espace client EliteBuro ;",
                "✓ Assistance administrative après la création lorsque cela est prévu dans l'offre souscrite.",
                "Lorsque la prestation comprend une domiciliation commerciale, ELITEBURO met également à disposition une adresse de domiciliation conformément aux dispositions légales en vigueur.",
            ]
        ),
        (
            "ARTICLE 3 — DOCUMENTS REMIS AU CLIENT",
            [
                "Selon la prestation choisie et après validation des administrations compétentes, le Client recevra tout ou partie des documents suivants :",
                "✔ Certificat d'Immatriculation (IDU)",
                "✔ RCCM",
                "✔ Déclaration Fiscale d'Existence (DFE)",
                "✔ Numéro de Compte Contribuable",
                "✔ Attestation d'existence",
                "✔ Statuts de la société (si applicable)",
                "✔ Contrat de domiciliation",
                "✔ Attestation de domiciliation",
                "✔ Facture",
                "✔ Reçu de paiement",
                "✔ Accès à l'espace client EliteBuro",
                "✔ Autres documents administratifs",
                "La liste des documents effectivement remis dépend de la nature de la prestation commandée par le Client.",
            ]
        ),
        (
            "ARTICLE 4 — OBLIGATIONS D'ELITEBURO",
            [
                "ELITEBURO s'engage à :",
                "• Mettre en œuvre tous les moyens nécessaires pour assurer le traitement du dossier.",
                "• Respecter les délais administratifs dans la mesure où ceux-ci dépendent des administrations publiques.",
                "• Informer régulièrement le Client de l'évolution de sa demande.",
                "• Préserver la confidentialité des informations communiquées.",
                "• Remettre au Client les documents obtenus dès leur disponibilité.",
                "• Fournir une assistance professionnelle durant toute la durée de la mission.",
                "ELITEBURO est tenue à une obligation de moyens et non de résultat. Les délais administratifs restent exclusivement de la responsabilité des administrations concernées.",
            ]
        ),
        (
            "ARTICLE 5 — OBLIGATIONS DU CLIENT",
            [
                "Le Client s'engage à :",
                "• Fournir des informations exactes et sincères.",
                "• Transmettre l'ensemble des pièces demandées.",
                "• Respecter les délais de transmission des documents.",
                "• Informer ELITEBURO de toute modification concernant son dossier.",
                "• Respecter les lois et règlements de la République de Côte d'Ivoire.",
                "• Régler les frais prévus selon les modalités convenues.",
                "Le Client demeure seul responsable de l'authenticité des informations et des documents transmis. Toute fausse déclaration ou tout document falsifié pourra entraîner la suspension immédiate de la prestation sans remboursement des sommes déjà engagées.",
            ]
        ),
        (
            "ARTICLE 6 — DURÉE DU CONTRAT",
            [
                "Le présent contrat prend effet à compter de sa signature par les deux parties.",
                "Pour une prestation de création d'entreprise, le contrat prend fin à la remise de l'ensemble des documents administratifs prévus dans la commande.",
                "Pour une prestation de domiciliation commerciale, le contrat est conclu pour une durée de douze (12) mois, sauf disposition particulière mentionnée dans le devis ou la commande.",
                "À son échéance, le contrat pourra être renouvelé d'un commun accord entre les parties selon les conditions tarifaires en vigueur.",
            ]
        ),
        (
            "ARTICLE 7 — CONDITIONS FINANCIÈRES",
            [
                "Le Client s'engage à régler le montant correspondant à la prestation choisie conformément au devis, au bon de commande ou à la facture émis par ELITEBURO.",
                "Le règlement peut être effectué par :",
                "• Paiement en ligne depuis l'espace client.",
                "• Mobile Money.",
                "• Virement bancaire.",
                "• Espèces ou carte bancaire dans les bureaux d'ELITEBURO.",
                "En cas de retard de paiement, ELITEBURO se réserve le droit de suspendre le traitement du dossier jusqu'à régularisation complète.",
            ]
        ),
        (
            "ARTICLE 8 — CONFIDENTIALITÉ",
            [
                "Toutes les informations, données et documents transmis par le Client sont strictement confidentiels.",
                "ELITEBURO s'engage à ne communiquer aucune information à un tiers sans l'accord préalable du Client, sauf lorsque cette communication est exigée par une autorité administrative ou judiciaire compétente.",
            ]
        ),
        (
            "ARTICLE 9 — RESPONSABILITÉ",
            [
                "ELITEBURO est tenue à une obligation de moyens.",
                "Sa responsabilité ne pourra être engagée en cas de :",
                "• Retard imputable à une administration publique.",
                "• Informations inexactes communiquées par le Client.",
                "• Documents incomplets ou falsifiés.",
                "• Cas de force majeure.",
                "Le Client demeure seul responsable des déclarations effectuées auprès des administrations.",
            ]
        ),
        (
            "ARTICLE 10 — RÉSILIATION",
            [
                "Le présent contrat peut être résilié par l'une ou l'autre des parties en cas de manquement grave aux obligations contractuelles.",
                "Toute prestation déjà exécutée reste due.",
                "En cas de domiciliation commerciale, le Client devra accomplir toutes les formalités nécessaires au transfert de son siège social avant la fin du contrat.",
            ]
        ),
        (
            "ARTICLE 11 — FORCE MAJEURE",
            [
                "Aucune des parties ne pourra être tenue responsable d'un retard ou d'une inexécution résultant d'un événement indépendant de sa volonté, notamment :",
                "• Catastrophe naturelle.",
                "• Incendie.",
                "• Pandémie.",
                "• Grève.",
                "• Décision administrative.",
                "• Panne informatique majeure.",
                "L'exécution du contrat sera suspendue pendant toute la durée de l'événement.",
            ]
        ),
        (
            "ARTICLE 12 — PROTECTION DES DONNÉES",
            [
                "Les données personnelles du Client sont collectées uniquement pour l'exécution des prestations confiées à ELITEBURO.",
                "Elles sont conservées de manière sécurisée et ne sont utilisées qu'à des fins administratives et contractuelles.",
            ]
        ),
        (
            "ARTICLE 13 — DROIT APPLICABLE ET LITIGES",
            [
                "Le présent contrat est soumis au droit de la République de Côte d'Ivoire.",
                "Les parties privilégient un règlement amiable de tout différend. À défaut d'accord amiable, les juridictions compétentes d'Abidjan seront seules compétentes.",
            ]
        ),
    ]

    for title, paragraphs in articles:
        story.append(Paragraph(title, S["article_title"]))
        for p in paragraphs:
            story.append(Paragraph(p, S["body"]))

    story.append(Spacer(1, 5 * mm))
    story.append(Paragraph("DÉCLARATION DU CLIENT", S["section_title"]))
    story.append(Paragraph(
        "Le Client déclare avoir pris connaissance de l'ensemble des clauses du présent contrat. Il reconnaît "
        "avoir reçu toutes les informations nécessaires concernant les prestations commandées et accepte sans "
        "réserve les présentes conditions contractuelles.",
        S["body"],
    ))

    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph("SIGNATURES", S["section_title"]))
    story.append(Paragraph(
        f"Fait à : <b>Abidjan</b>",
        S["body"],
    ))
    story.append(Paragraph(
        f"Le : <b>{date.today().strftime('%d/%m/%Y')}</b>",
        S["body"],
    ))
    story.append(Spacer(1, 8 * mm))

    client_name = f"{demande.utilisateur.first_name} {demande.utilisateur.last_name}"
    sign_left = [
        Paragraph("ELITEBURO", S["sign_title"]),
        Spacer(1, 4 * mm),
        Paragraph("Nom du représentant", S["sign"]),
        Spacer(1, 20 * mm),
        Paragraph("__________________", S["sign"]),
        Spacer(1, 4 * mm),
        Paragraph("Signature et cachet", S["sign"]),
    ]
    sign_right = [
        Paragraph("LE CLIENT", S["sign_title"]),
        Spacer(1, 4 * mm),
        Paragraph(f"<b>{client_name}</b>", S["sign"]),
        Spacer(1, 20 * mm),
        Paragraph("__________________", S["sign"]),
        Spacer(1, 4 * mm),
        Paragraph("Signature précédée de la mention « Lu et approuvé »", S["sign"]),
    ]
    sign_table = Table(
        [[sign_left, sign_right]],
        colWidths=[85 * mm, 85 * mm],
        style=TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]),
    )
    story.append(sign_table)

    return story


def generer_contrat_pdf_from_template(demande) -> bytes:
    buf = BytesIO()

    doc = BaseDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=20 * mm,
        title=f"Contrat {demande.numero_demande}",
        author="ELITEBURO",
    )

    frame = Frame(
        doc.leftMargin,
        doc.bottomMargin,
        doc.width,
        doc.height,
        id="normal",
    )

    doc.addPageTemplates([PageTemplate(id="page", frames=[frame], onPage=_header_footer)])

    styles = _styles()
    story = _build_story(demande, styles)
    doc.build(story)

    buf.seek(0)
    return buf.read()


def _contexte_contrat(demande) -> dict:
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


def generer_contrat_pdf_bytes_simple(demande) -> bytes:
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
    try:
        return generer_contrat_pdf_from_template(demande)
    except Exception:
        return generer_contrat_pdf_bytes_simple(demande)
