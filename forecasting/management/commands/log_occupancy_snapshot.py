"""
A lancer toutes les 15 minutes (cron ou Celery beat) :
    */15 * * * * cd /path/to/project && python manage.py log_occupancy_snapshot

Construit une "photo" de l'occupation actuelle de chaque Workspace a partir
des Reservation en cours (statut confirmed/in_progress, date du jour, et
si heure_debut/heure_fin sont renseignees : dans la plage horaire).
"""
from django.core.management.base import BaseCommand
from django.db.models import Q, Sum
from django.utils import timezone

from coworking.models import Workspace
from reservation.models import Reservation, ReservationStatus
from forecasting.models import OccupancySnapshot
from forecasting.type_mapping import get_space_type_for_workspace

# Verite terrain : occupation reelle et garantie (utilisee pour l'entrainement du modele).
# "pending" est deliberement exclu : une resa en attente peut etre refusee ou expirer,
# ce qui introduirait du bruit dans l'historique d'occupation.
ACTIVE_STATUSES = [ReservationStatus.CONFIRMED, ReservationStatus.IN_PROGRESS]

# Signal de demande (non utilise dans occupancy_rate) : garde pour une future
# analyse "demande vs capacite reelle", distincte de l'occupation physique.
DEMAND_STATUSES = [ReservationStatus.PENDING, ReservationStatus.AWAITING_PAYMENT]


def get_current_occupancy_count(workspace: Workspace, now) -> int:
    today = now.date()
    current_time = now.time()

    qs = Reservation.objects.filter(
        espace=workspace,
        statut__in=ACTIVE_STATUSES,
        date_debut__lte=today,
        date_fin__gte=today,
    ).filter(
        Q(heure_debut__isnull=True, heure_fin__isnull=True)
        | Q(heure_debut__lte=current_time, heure_fin__gte=current_time)
    )
    total = qs.aggregate(total=Sum("nombre_participants"))["total"]
    return total or 0


def get_current_demand_count(workspace: Workspace, now) -> int:
    """Non utilise pour l'instant, dispo pour une future feature 'pression de demande'."""
    today = now.date()
    qs = Reservation.objects.filter(
        espace=workspace,
        statut__in=DEMAND_STATUSES,
        date_debut__lte=today,
        date_fin__gte=today,
    )
    total = qs.aggregate(total=Sum("nombre_participants"))["total"]
    return total or 0


class Command(BaseCommand):
    help = "Enregistre un instantane de l'occupation de chaque Workspace"

    def handle(self, *args, **options):
        now = timezone.localtime()
        created = 0

        for workspace in Workspace.objects.filter(disponible=True):
            count = get_current_occupancy_count(workspace, now)
            capacity = workspace.capacite or 1
            rate = round(min(count / capacity, 1.0), 4)
            space_type = get_space_type_for_workspace(workspace)

            OccupancySnapshot.objects.create(
                workspace=workspace,
                space_type=space_type,
                capacity=capacity,
                timestamp=now,
                occupancy_count=count,
                occupancy_rate=rate,
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(f"{created} snapshots enregistres a {now:%Y-%m-%d %H:%M}"))
