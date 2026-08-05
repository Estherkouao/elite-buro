from django.shortcuts import render

from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
import json
import os

from anthropic import Anthropic

from .models import (
    ChatConversation,
    ChatMessage,
    KnowledgeBase,
    QuickReply,
)

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

SYSTEM_PROMPT = """Tu es l'Assistant Elite Buro, l'assistant virtuel officiel du centre d'affaires
Elite Buro situé à Riviera Palmeraie, Cocody, Abidjan.

Ton rôle : répondre aux questions des visiteurs sur les services d'Elite Buro, de façon
chaleureuse, professionnelle et concise (3-5 phrases maximum sauf si on te demande des détails).
Utilise des emojis avec modération.

=== SERVICES ET INFOS OFFICIELLES ===

BUREAUX PRIVATIFS
- 11 bureaux privatifs disponibles, 12 à 40 m², 2 à 10 personnes
- Disponibilités en temps réel sur le site
- À partir de 15 000 FCFA/jour

HOT DESKS
- 12 hot desks disponibles
- Réservation à la demi-journée ou à la journée
- Idéal freelances/entrepreneurs
- À partir de 5 000 FCFA/jour

SALLES DE RÉUNION
- Salle Ivoire (12 pers.), Salle Savane (20 pers.), Salle Élite (30 pers.)
- Équipées : vidéoprojecteur, tableau blanc, système audio
- Tarifs demi-journée : 45 000 à 90 000 FCFA

DOMICILIATION D'ENTREPRISE
- Adresse à Riviera Palmeraie, autorisée par le CEPICI
- Souscription 100% en ligne, signature électronique, dossier validé en 48h
- Plusieurs formules disponibles
- À partir de 25 000 FCFA/mois

ELITE BURO ACADEMY (formation)
- Salles de formation modulables et équipées
- 120+ formateurs partenaires, 2 400+ stagiaires formés
- Devis automatique en 60 secondes

RÉSERVATION (étapes)
1. Consulter les disponibilités en temps réel sur le site
2. Sélectionner l'espace et la date
3. Compléter ses informations
4. Payer
5. Confirmation instantanée

MOYENS DE PAIEMENT
Orange Money, Wave, MTN MoMo, Visa/Mastercard, PayPal, virement bancaire.
Paiements sécurisés par CinetPay, confirmation SMS + Email + WhatsApp.

CONTACT
📍 Riviera Palmeraie, Cocody, Abidjan
📞 +225 07 XX XX XX XX
📧 contact@eliteburo.com
🕐 Lun–Ven : 7h–20h | Sam : 8h–17h

AVIS CLIENTS
Note moyenne de 4.9/5 ⭐

=== RÈGLES ===
- Si on te demande un tarif exact, une disponibilité précise ou une réservation, invite la
  personne à consulter le site en temps réel ou à contacter Elite Buro — ne garantis jamais
  une disponibilité que tu ne peux pas vérifier.
- Si la question sort du cadre d'Elite Buro (météo, actualité, autre entreprise...),
  réponds poliment que tu es dédié aux services Elite Buro et recentre la conversation.
- Ne jamais inventer d'informations qui ne figurent pas ci-dessus (numéro de téléphone,
  prix exact, etc.) : utilise les placeholders tels quels si besoin.
"""


def rechercher_reponse(question):
    question = question.lower()
    connaissances = KnowledgeBase.objects.filter(actif=True).order_by("ordre")
    for connaissance in connaissances:
        mots = [mot.strip().lower() for mot in connaissance.mots_cles.split(",")]
        for mot in mots:
            if mot in question:
                return connaissance
    return None


@csrf_exempt
@require_POST
def chatbot_api(request):
    data = json.loads(request.body)
    message = data.get("message", "").strip()
    history = data.get("history", [])
    conversation_id = data.get("conversation_id")

    if not message:
        return JsonResponse({"error": "Message vide"}, status=400)

    if conversation_id:
        conversation = ChatConversation.objects.get(id=conversation_id)
    else:
        conversation = ChatConversation.objects.create(
            session_key=request.session.session_key or ""
        )

    ChatMessage.objects.create(conversation=conversation, role="user", message=message)

    reponse = None

    if client.api_key:
        try:
            messages = history + [{"role": "user", "content": message}]
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=500,
                system=SYSTEM_PROMPT,
                messages=messages,
            )
            reponse = "".join(block.text for block in response.content if block.type == "text")
        except Exception:
            reponse = None

    if not reponse:
        connaissance = rechercher_reponse(message)
        reponse = connaissance.reponse if connaissance else (
            "Je n'ai pas trouvé de réponse précise."
            " Souhaitez-vous être mis en relation avec un conseiller EliteBuro ?"
        )

    ChatMessage.objects.create(conversation=conversation, role="assistant", message=reponse)

    suggestions = list(
        QuickReply.objects.filter(actif=True).values_list("texte", flat=True)
    )

    return JsonResponse({
        "conversation_id": conversation.id,
        "response": reponse,
        "suggestions": suggestions,
    })
