from .models import KnowledgeBase


class ChatbotEngine:

    @staticmethod
    def search(question):

        question = question.lower()

        connaissances = KnowledgeBase.objects.filter(
            actif=True
        ).order_by("ordre")

        meilleur_score = 0
        meilleure_reponse = None

        for fiche in connaissances:

            score = 0

            mots = fiche.mots_cles.lower().split(",")

            for mot in mots:

                mot = mot.strip()

                if mot and mot in question:
                    score += 1

            if score > meilleur_score:
                meilleur_score = score
                meilleure_reponse = fiche

        return meilleure_reponse