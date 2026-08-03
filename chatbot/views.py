from django.shortcuts import render

# Create your views here.
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
import json

from .models import (
    ChatConversation,
    ChatMessage,
    KnowledgeBase,
    QuickReply,
)

def rechercher_reponse(question):

    question = question.lower()

    connaissances = KnowledgeBase.objects.filter(
        actif=True
    ).order_by("ordre")

    for connaissance in connaissances:

        mots = [
            mot.strip().lower()
            for mot in connaissance.mots_cles.split(",")
        ]

        for mot in mots:

            if mot in question:

                return connaissance

    return None


@csrf_exempt
@require_POST
def chatbot_api(request):

    data = json.loads(request.body)

    message = data.get("message", "").strip()

    conversation_id = data.get("conversation_id")

    if conversation_id:

        conversation = ChatConversation.objects.get(
            id=conversation_id
        )

    else:

        conversation = ChatConversation.objects.create(
            session_key=request.session.session_key or ""
        )

    ChatMessage.objects.create(
        conversation=conversation,
        role="user",
        message=message
    )

    connaissance = rechercher_reponse(message)

    if connaissance:

        reponse = connaissance.reponse

    else:

        reponse = (
            "Je n'ai pas trouvé de réponse précise."
            " Souhaitez-vous être mis en relation avec un conseiller EliteBuro ?"
        )

    ChatMessage.objects.create(
        conversation=conversation,
        role="assistant",
        message=reponse
    )

    suggestions = list(
        QuickReply.objects.filter(
            actif=True
        ).values_list(
            "texte",
            flat=True
        )
    )

    return JsonResponse({

        "conversation_id": conversation.id,

        "response": reponse,

        "suggestions": suggestions,

    })    