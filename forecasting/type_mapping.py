"""
Le modèle a été entraîné sur 4 types d'espace : HotDesk, MeetingRoom,
TrainingRoom, PrivateOffice. Ton site a 5 types possibles (ReservationType)
+ des catégories en texte libre (Category.nom / Category.slug) sur Workspace.

CE FICHIER EST LE PLUS IMPORTANT A VERIFIER / CORRIGER TOI-MEME.
Le matching par mots-clés ci-dessous est une estimation de secours.
Idéal : construis plutôt un mapping EXPLICITE {category_slug: space_type}
une fois que tu as la vraie liste de tes catégories en base.
"""

# Mapping direct depuis ReservationType (le plus fiable, car ce sont des valeurs fixes)
RESERVATION_TYPE_TO_MODEL_TYPE = {
    "private_office": "PrivateOffice",
    "hot_desk": "HotDesk",
    "meeting_room": "MeetingRoom",
    "training_room": "TrainingRoom",
    "conference_room": "MeetingRoom",  # <-- absent à l'entraînement, rapproché de MeetingRoom
}

# Mots-clés de secours si on doit deviner depuis Category.nom (texte libre)
CATEGORY_KEYWORDS = {
    "PrivateOffice": ["bureau", "privé", "office"],
    "HotDesk": ["hot desk", "hotdesk", "open space"],
    "MeetingRoom": ["réunion", "reunion", "conférence", "conference", "meeting"],
    "TrainingRoom": ["formation", "training"],
}

DEFAULT_TYPE = "HotDesk"


def guess_space_type_from_category(category_nom: str) -> str:
    nom = (category_nom or "").lower()
    for model_type, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in nom for kw in keywords):
            return model_type
    return DEFAULT_TYPE


def get_space_type_for_workspace(workspace) -> str:
    """
    Stratégie :
    1) Si des réservations existent déjà pour ce workspace, utiliser le
       type_reservation le plus fréquent (le plus fiable, car normalisé).
    2) Sinon, deviner depuis le nom de la catégorie (texte libre).
    """
    from reservation.models import Reservation  # import local pour éviter les imports circulaires

    most_common = (
        Reservation.objects.filter(espace=workspace)
        .values_list("type_reservation", flat=True)
        .first()
    )
    if most_common and most_common in RESERVATION_TYPE_TO_MODEL_TYPE:
        return RESERVATION_TYPE_TO_MODEL_TYPE[most_common]

    return guess_space_type_from_category(workspace.categorie.nom if workspace.categorie_id else "")
