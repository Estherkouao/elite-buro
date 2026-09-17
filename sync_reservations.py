import os
import sys
import django
import psycopg

# Django
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from reservation.models import Reservation


# Connexion TimescaleDB
conn = psycopg.connect(
    host="127.0.0.1",
    port=5433,
    dbname="eliteburo",
    user="eliteburo",
    password="eliteburo",
)

cursor = conn.cursor()

reservations = (
    Reservation.objects
    .select_related("espace", "espace__categorie")
    .all()
)

total = 0

for r in reservations:

    # Date + heure de début
    start_time = r.date_debut

    if r.heure_debut:
        start_time = f"{r.date_debut} {r.heure_debut}"
    else:
        start_time = f"{r.date_debut} 00:00:00"

    # Date + heure de fin
    end_time = r.date_fin

    if r.heure_fin:
        end_time = f"{r.date_fin} {r.heure_fin}"
    else:
        end_time = f"{r.date_fin} 23:59:59"

    space_name = r.espace.nom
    space_type = r.espace.categorie.nom
    capacity = r.espace.capacite

    cursor.execute(
        """
        INSERT INTO django_reservations (
            reservation_id,
            reservation_number,
            space_name,
            space_type,
            capacity,
            start_time,
            end_time,
            participants,
            status
        )
        VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s
        )
        ON CONFLICT (reservation_id)
        DO UPDATE SET
            reservation_number = EXCLUDED.reservation_number,
            space_name = EXCLUDED.space_name,
            space_type = EXCLUDED.space_type,
            capacity = EXCLUDED.capacity,
            start_time = EXCLUDED.start_time,
            end_time = EXCLUDED.end_time,
            participants = EXCLUDED.participants,
            status = EXCLUDED.status
        """,
        (
            str(r.id),
            r.reservation_number,
            space_name,
            space_type,
            capacity,
            start_time,
            end_time,
            r.nombre_participants,
            r.statut,
        ),
    )

    total += 1


conn.commit()
cursor.close()
conn.close()

print(f"Synchronisation terminée : {total} réservations")