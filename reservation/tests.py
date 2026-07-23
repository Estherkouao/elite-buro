from decimal import Decimal
from datetime import date

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase

from accounts.models import User
from coworking.models import Category, CoworkingSpace, Workspace

from .filters import ReservationFilter
from .forms import ReservationForm
from .models import Reservation, ReservationType, ReservationStatus




class ReservationFormTests(TestCase):
    def test_form_accepts_request_kwarg(self):
        request = RequestFactory().get("/reservation/reservations/create/")

        form = ReservationForm(request=request)

        self.assertIn("espace", form.fields)


class ReservationFilterTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="member@example.com",
            password="password123",
            first_name="Jane",
            last_name="Doe",
            phone="+2250700000000",
        )
        self.workspace = self._create_workspace()

        Reservation.objects.create(
            reservation_number="RES-001",
            utilisateur=self.user,
            entreprise=None,
            espace=self.workspace,
            type_reservation=ReservationType.HOT_DESK,
            date_debut=date(2026, 7, 10),
            date_fin=date(2026, 7, 10),
            heure_debut=None,
            heure_fin=None,
            nombre_participants=1,
            duree_minutes=0,
            prix_unitaire=Decimal("100.00"),
            remise=Decimal("0.00"),
            taxes=Decimal("0.00"),
            montant_total=Decimal("100.00"),
            commentaire="",
            statut=ReservationStatus.PENDING,
        )
        Reservation.objects.create(
            reservation_number="RES-002",
            utilisateur=self.user,
            entreprise=None,
            espace=self.workspace,
            type_reservation=ReservationType.PRIVATE_OFFICE,
            date_debut=date(2026, 7, 11),
            date_fin=date(2026, 7, 12),
            heure_debut=None,
            heure_fin=None,
            nombre_participants=1,
            duree_minutes=0,
            prix_unitaire=Decimal("250.00"),
            remise=Decimal("0.00"),
            taxes=Decimal("0.00"),
            montant_total=Decimal("250.00"),
            commentaire="",
            statut=ReservationStatus.CONFIRMED,
        )


    def _create_workspace(self):
        espace = CoworkingSpace.objects.create(
            nom="Espace Test",
            slug="espace-test",
            image_principale=SimpleUploadedFile("space.jpg", b"x", content_type="image/jpeg"),
            logo=SimpleUploadedFile("logo.jpg", b"x", content_type="image/jpeg"),
        )
        categorie = Category.objects.create(
            nom="Catégorie Test",
            slug="categorie-test",
            image=SimpleUploadedFile("category.jpg", b"x", content_type="image/jpeg"),
        )
        return Workspace.objects.create(
            espace=espace,
            categorie=categorie,
            nom="Bureau Test",
            slug="bureau-test",
            capacite=4,
            superficie=20,
            etage="1",
            numero="A1",
            prix_heure=Decimal("10.00"),
            prix_demi_journee=Decimal("50.00"),
            prix_journee=Decimal("100.00"),
            prix_semaine=Decimal("500.00"),
            prix_mois=Decimal("1500.00"),
            caution=Decimal("100.00"),
            image_principale=SimpleUploadedFile("workspace.jpg", b"x", content_type="image/jpeg"),
        )

    def test_filter_exposes_form_and_applies_status_filter(self):
        reservation_filter = ReservationFilter(
{"statut": ReservationStatus.CONFIRMED},
            Reservation.objects.all(),
        )

        self.assertTrue(hasattr(reservation_filter, "form"))
        self.assertIn("statut", reservation_filter.form.fields)
        self.assertEqual(reservation_filter.qs.count(), 1)
        self.assertEqual(reservation_filter.qs.first().reservation_number, "RES-002")
