from __future__ import annotations

from django.db.models import Q

from .models import Formation, FormationSession, FormationCategory, Trainer


# NOTE: django-filter n'est pas installé dans cet environnement.
# On expose une classe de filtre compatible pour les vues,
# mais sans dépendance externe.
class FormationFilter:
    def __init__(self, data=None, queryset=None, **kwargs):
        self.data = data or {}
        self.qs = queryset or Formation.objects.all()

        self.qs = self._apply()

    @property
    def qs(self):
        return self._qs

    @qs.setter
    def qs(self, value):
        self._qs = value

    def _apply(self):
        qs = self.qs

        category_id = self.data.get("category")
        if category_id:
            qs = qs.filter(category_id=category_id)

        prix_min = self.data.get("prix_min")
        if prix_min not in (None, ""):
            qs = qs.filter(prix__gte=prix_min)

        prix_max = self.data.get("prix_max")
        if prix_max not in (None, ""):
            qs = qs.filter(prix__lte=prix_max)

        niveau = self.data.get("niveau")
        if niveau:
            qs = qs.filter(niveau=niveau)

        duree_min = self.data.get("duree_min")
        if duree_min not in (None, ""):
            qs = qs.filter(duree__gte=duree_min)

        duree_max = self.data.get("duree_max")
        if duree_max not in (None, ""):
            qs = qs.filter(duree__lte=duree_max)

        formateur_id = self.data.get("formateur")
        if formateur_id:
            sessions = FormationSession.objects.filter(formateur_id=formateur_id).values_list("formation_id", flat=True)
            qs = qs.filter(id__in=list(sessions))

        disponibilite = self.data.get("disponibilite")
        if str(disponibilite) == "True":
            qs_ids = FormationSession.objects.filter(places_restantes__gt=0).values_list("formation_id", flat=True)
            qs = qs.filter(id__in=list(qs_ids))

        return qs


