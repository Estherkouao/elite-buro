from __future__ import annotations

from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models as db_models
from django.db.models import Prefetch, Sum
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.views import View

from .filters import FormationFilter
from .forms import (
    ContractForm,
    FormationSessionForm,
    FormationForm,
    QuoteForm,
    RegistrationForm,
    ReviewForm,
    TrainerForm,
)
from .models import (
    Formation,
    FormationCategory,
    FormationCertificate,
    FormationContract,
    FormationPayment,
    FormationQuote,
    FormationRegistration,
    FormationSession,
    Trainer,
)
from .permissions import FormationAccess, user_is_admin, user_is_manager, user_is_trainer
from .services import (
    create_or_update_contract,
    create_or_update_quote,
    create_registration,
    generate_certificate_for_registration,
    generate_quote_for_registration,
    maybe_reserve_room_automatically,
    process_payment_for_registration,
    sign_contract,
)




class FormationHomeView(View):
    """Page d'accueil publique du pôle Formation (landing page)."""

    template_name = "formation/formation_home.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        return render(request, self.template_name)


class CatalogueBaseMixin:
    template_name: str = "formation/catalogue.html"

    def get_queryset(self):
        return (
            Formation.objects.select_related("category")
            .filter(actif=True)
            .order_by("-updated_at")
        )


class CatalogueView(CatalogueBaseMixin, View):
    template_name = "formation/index.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        formations = self.get_queryset()[:12]
        categories = FormationCategory.objects.all().order_by("name")[:12]
        # la home utilise index.html, la route catalogue utilise catalogue.html
        return render(
            request,
            self.template_name,
            {"formations": formations, "categories": categories},
        )


class FormationDetailView(CatalogueBaseMixin, View):
    def get(self, request: HttpRequest, slug: str) -> HttpResponse:
        formation = get_object_or_404(self.get_queryset(), slug=slug)
        sessions = (
            FormationSession.objects.select_related("formation", "formateur")
            .filter(formation=formation)
            .order_by("date_debut", "heure_debut")
        )
        return render(
            request,
            "formation/detail.html",
            {"formation": formation, "sessions": sessions},
        )


class SessionsView(CatalogueBaseMixin, View):
    def get(self, request: HttpRequest) -> HttpResponse:
        sessions = (
            FormationSession.objects.select_related("formation", "formateur")
            .filter(formation__actif=True)
            .order_by("date_debut", "heure_debut")
        )
        # Template non créé dans ce sprint: repli sur catalogue
        return render(request, "formation/sessions.html", {"sessions": sessions})


class SearchView(CatalogueBaseMixin, View):
    def get(self, request: HttpRequest) -> HttpResponse:
        q = (request.GET.get("q") or "").strip()
        queryset = self.get_queryset()

        if q:
            queryset = queryset.filter(
                Q(titre__icontains=q)
                | Q(description_courte__icontains=q)
                | Q(description_complete__icontains=q)
                | Q(objectifs__icontains=q)
            )

        return render(request, "formation/catalogue.html", {"formations": queryset, "q": q})


class FiltersView(CatalogueBaseMixin, View):
    def get(self, request: HttpRequest) -> HttpResponse:
        base_qs = self.get_queryset()
        formation_filter = FormationFilter(request.GET or None, queryset=base_qs)
        return render(
            request,
            "formation/catalogue.html",
            {"filter": formation_filter, "formations": formation_filter.qs},
        )


@method_decorator(login_required, name="dispatch")
class SessionRegisterView(View):
    def get(self, request: HttpRequest, session_id: int) -> HttpResponse:
        session = get_object_or_404(FormationSession.objects.select_related("formation"), pk=session_id)
        form = RegistrationForm(initial={"session": session.pk})
        return render(request, "formation/register.html", {"session": session, "form": form})

    def post(self, request: HttpRequest, session_id: int) -> HttpResponse:
        session = get_object_or_404(FormationSession.objects.select_related("formation"), pk=session_id)
        from accounts.models import Company

        entreprise = Company.objects.filter(owner=request.user).first()
        if entreprise is None:
            messages.error(request, "Votre entreprise n'est pas configurée.")
            return redirect(reverse("formation:detail", kwargs={"slug": session.formation.slug}))

        form = RegistrationForm(request.POST)
        if not form.is_valid():
            return render(request, "formation/register.html", {"session": session, "form": form})

        registration = create_registration(
            session=session,
            member=request.user,
            entreprise=entreprise,
            commentaire=form.cleaned_data.get("commentaire") or "",
            preferred_date=form.cleaned_data.get("date"),
        )

        # workflow optionnel: si génération échoue, on garde l'inscription.
        try:
            quote = generate_quote_for_registration(registration)
            create_or_update_contract(quote)
            generate_certificate_for_registration(registration)

            maybe_reserve_room_automatically(session)
        except Exception:
            messages.warning(request, "Inscription enregistrée, mais génération devis/contrat/certificat en attente.")

        messages.success(request, "Inscription enregistrée.")
        return redirect(reverse("formation:my_courses"))


@method_decorator(login_required, name="dispatch")
class MyCoursesView(View):
    def get(self, request: HttpRequest) -> HttpResponse:
        registrations = (
            FormationRegistration.objects.select_related("session__formation", "session__formateur", "formation")
            .filter(membre=request.user)
            .order_by("-date")
        )
        # Annoter chaque registration avec son paiement et code d'accès
        for reg in registrations:
            try:
                reg.payment = FormationPayment.objects.filter(inscription=reg).first()
            except Exception:
                reg.payment = None
            try:
                from .models import FormationAccessCode
                reg.access_code = FormationAccessCode.objects.filter(inscription=reg).first()
            except Exception:
                reg.access_code = None
        formations = (
            Formation.objects.select_related("category")
            .filter(actif=True)
            .order_by("-updated_at")
        )
        return render(request, "formation/my_courses.html", {
            "registrations": registrations,
            "formations": formations,
        })


@method_decorator(login_required, name="dispatch")
class MyCertificatesView(View):
    def get(self, request: HttpRequest) -> HttpResponse:
        certificates = (
            FormationCertificate.objects.select_related("inscription__session__formation")
            .filter(inscription__membre=request.user)
            .order_by("-date")
        )
        return render(request, "formation/my_certificates.html", {"certificates": certificates})


@method_decorator(login_required, name="dispatch")
class MyQuotesView(View):
    def get(self, request: HttpRequest) -> HttpResponse:
        quotes = (
            FormationQuote.objects.select_related("inscription__session__formation")
            .filter(inscription__membre=request.user)
            .order_by("-date")
        )
        return render(request, "formation/my_quotes.html", {"quotes": quotes})


@method_decorator(login_required, name="dispatch")
class MyContractsView(View):
    def get(self, request: HttpRequest) -> HttpResponse:
        contracts = (
            FormationContract.objects.select_related("devis__inscription__session__formation")
            .filter(devis__inscription__membre=request.user)
            .order_by("-date")
        )
        return render(request, "formation/contracts.html", {"contracts": contracts})


@method_decorator(login_required, name="dispatch")
class PaymentView(View):
    def get(self, request: HttpRequest) -> HttpResponse:
        payments = (
            FormationPayment.objects.select_related("inscription__session__formation")
            .filter(inscription__membre=request.user)
            .order_by("-id")
        )
        return render(request, "formation/payment.html", {"payments": payments})


@method_decorator(login_required, name="dispatch")
class ReviewCreateView(View):
    def get(self, request: HttpRequest) -> HttpResponse:
        form = ReviewForm(initial={"membre": request.user.pk})
        return render(request, "formation/review.html", {"form": form})

    def post(self, request: HttpRequest) -> HttpResponse:
        form = ReviewForm(request.POST)
        if not form.is_valid():
            return render(request, "formation/review.html", {"form": form})

        review = form.save(commit=False)
        review.membre = request.user
        review.save()
        messages.success(request, "Merci pour votre avis.")
        return redirect(reverse("formation:catalogue"))


class TrainerListView(View):
    def get(self, request: HttpRequest) -> HttpResponse:
        trainers = Trainer.objects.all().order_by("annees_experience")
        return render(request, "formation/trainer.html", {"trainers": trainers})


class TrainerDetailView(View):
    def get(self, request: HttpRequest, trainer_id: int) -> HttpResponse:
        trainer = get_object_or_404(Trainer, pk=trainer_id)
        formations = Formation.objects.filter(sessions__formateur=trainer).distinct()
        return render(request, "formation/trainer.html", {"trainer": trainer, "formations": formations})


class QuotePreviewView(View):
    def get(self, request: HttpRequest, quote_id: int) -> HttpResponse:
        quote = get_object_or_404(FormationQuote, pk=quote_id)
        if not quote.pdf:
            quote = generate_quote_for_registration(quote.inscription)
        if not quote.pdf:
            raise Http404()
        return redirect(quote.pdf.url)


# ═══════════════════════════════════════════════════════════════
#  INSCRIPTION FORMATION — Page publique/membre connecté
# ═══════════════════════════════════════════════════════════════

from .forms import InscriptionFormationForm
from .services import (
    create_registration,
    generate_quote_for_registration,
    create_or_update_quote,
    create_or_update_contract,
    generate_certificate_for_registration,
    notify_admin_new_registration,
    notify_trainer_new_registration,
    notify_member_registration_confirmed,
    notify_member_payment_success,
    notify_member_access_code,
    generate_access_code,
)
from accounts.models import Company
from paiement.services import PaymentRegistry
from paiement.models import PaymentProvider, PaymentTransaction
from decimal import Decimal


@method_decorator(login_required, name="dispatch")
class InscriptionFormationView(View):
    """Page d'inscription multi-étapes à une formation (connecté à la BDD)."""

    template_name = "formation/inscription_formation.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        formations = Formation.objects.filter(actif=True).select_related("category")

        # Pré-remplir les infos de l'utilisateur connecté
        user = request.user
        initial_data = {
            "prenom": user.first_name,
            "nom": user.last_name,
            "email": user.email,
            "telephone": user.phone,
        }

        # Pré-sélectionner la formation passée en paramètre GET (ex: depuis la page détail)
        formation_id = request.GET.get("formation")
        if formation_id:
            try:
                formation_obj = Formation.objects.get(pk=formation_id, actif=True)
                initial_data["formation"] = formation_obj
            except (Formation.DoesNotExist, ValueError, TypeError):
                pass

        form = InscriptionFormationForm(request.GET, initial=initial_data)
        form.fields["formation"].queryset = formations

        if formation_id:
            try:
                form.fields["session"].queryset = FormationSession.objects.filter(
                    formation_id=int(formation_id), statut__in=["published", "open"]
                ).order_by("date_debut")
            except (ValueError, TypeError):
                pass

        return render(request, self.template_name, {
            "form": form,
            "formations": formations,
        })

    def post(self, request: HttpRequest) -> HttpResponse:
        form = InscriptionFormationForm(request.POST)
        formations = Formation.objects.filter(actif=True)
        form.fields["formation"].queryset = formations

        formation_id = request.POST.get("formation")
        if formation_id:
            try:
                form.fields["session"].queryset = FormationSession.objects.filter(
                    formation_id=int(formation_id), statut__in=["published", "open"]
                ).order_by("date_debut")
            except (ValueError, TypeError):
                pass

        if not form.is_valid():
            return render(request, self.template_name, {
                "form": form,
                "formations": formations,
                "error": True,
            })

        cd = form.cleaned_data

        try:
            # 1. Trouver ou créer l'entreprise du membre
            entreprise = Company.objects.filter(owner=request.user).first()
            if not entreprise:
                # Créer une entreprise par défaut si l'utilisateur n'en a pas
                entreprise = Company.objects.create(
                    owner=request.user,
                    company_name=cd.get("organisation") or f"Entreprise {request.user.last_name}",
                    phone=cd.get("telephone", request.user.phone),
                    email=cd.get("email", request.user.email),
                )

            # 2. Créer l'inscription
            session = cd.get("session")
            registration = create_registration(
                session=session,
                formation=cd.get("formation") if not session else None,
                member=request.user,
                entreprise=entreprise,
                commentaire=cd.get("objectifs", "") or "",
            )

            # 3. Si une session est sélectionnée, générer devis + contrat
            if session:
                try:
                    quote = generate_quote_for_registration(registration)
                    create_or_update_contract(quote)
                    generate_certificate_for_registration(registration)
                except Exception:
                    pass

            # 4. Notifier admin + formateur par email
            try:
                notify_admin_new_registration(registration)
                if session:
                    notify_trainer_new_registration(registration)
            except Exception:
                pass

            messages.success(
                request,
                f"Votre inscription {registration.numero} a été enregistrée avec succès. "
                f"Vous recevrez un email dès qu'elle sera approuvée."
            )
            return redirect(reverse("formation:my_courses"))

        except ValueError as e:
            messages.error(request, str(e))
            return render(request, self.template_name, {
                "form": form,
                "formations": formations,
            })
        except Exception as e:
            messages.error(request, f"Erreur lors de l'inscription: {str(e)}")
            return render(request, self.template_name, {
                "form": form,
                "formations": formations,
            })


@method_decorator(login_required, name="dispatch")
class LoadSessionsView(View):
    """AJAX: retourne les sessions d'une formation au format JSON."""

    def get(self, request: HttpRequest) -> JsonResponse:
        formation_id = request.GET.get("formation_id")
        if not formation_id:
            return JsonResponse({"sessions": []})

        try:
            sessions = FormationSession.objects.filter(
                formation_id=int(formation_id),
                statut__in=["published", "open"],
            ).order_by("date_debut").values("id", "date_debut", "date_fin", "nombre_maximum", "places_restantes")

            session_list = []
            for s in sessions:
                session_list.append({
                    "id": s["id"],
                    "label": f"{s['date_debut']} au {s['date_fin']} "
                             f"({s['places_restantes']}/{s['nombre_maximum']} places)",
                })

            return JsonResponse({"sessions": session_list})
        except (ValueError, TypeError):
            return JsonResponse({"sessions": []})


@method_decorator(login_required, name="dispatch")
class FormationPaymentView(View):
    """Page de paiement pour une inscription formation."""

    template_name = "formation/payment.html"

    def get(self, request: HttpRequest, inscription_id: int) -> HttpResponse:
        registration = get_object_or_404(
            FormationRegistration,
            id=inscription_id,
            membre=request.user,
        )

        if registration.statut != "confirmed":
            messages.warning(request, "Votre inscription doit être approuvée avant de pouvoir payer.")
            return redirect(reverse("formation:my_courses"))

        # Vérifier si déjà payé
        existing_payment = FormationPayment.objects.filter(inscription=registration, statut="paid").first()
        if existing_payment:
            messages.info(request, "Cette inscription est déjà payée.")
            return redirect(reverse("formation:my_courses"))

        providers = PaymentProvider.objects.filter(is_active=True).order_by("display_order")
        montant_total = registration.session.formation.prix
        montant_partiel_50 = montant_total * Decimal("0.5")
        montant_partiel_30 = montant_total * Decimal("0.3")
        montant_partiel_70 = montant_total * Decimal("0.7")

        return render(request, self.template_name, {
            "registration": registration,
            "providers": providers,
            "montant_total": montant_total,
            "montant_partiel_50": montant_partiel_50,
            "montant_partiel_30": montant_partiel_30,
            "montant_partiel_70": montant_partiel_70,
        })


@method_decorator(login_required, name="dispatch")
class FormationPaymentProcessView(View):
    """Traiter le paiement pour une inscription."""

    def post(self, request: HttpRequest, inscription_id: int) -> JsonResponse:
        import json

        registration = get_object_or_404(
            FormationRegistration,
            id=inscription_id,
            membre=request.user,
            statut="confirmed",
        )

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Données invalides"}, status=400)

        provider_code = data.get("provider_code")
        type_paiement = data.get("type_paiement", "total")  # total, partiel_50, partiel_30
        phone_number = data.get("phone_number", "")
        montant_total = registration.session.formation.prix

        if type_paiement == "partiel_50":
            montant = montant_total * Decimal("0.5")
        elif type_paiement == "partiel_30":
            montant = montant_total * Decimal("0.3")
        else:
            montant = montant_total

        try:
            result = PaymentRegistry.process_payment(
                provider_code=provider_code,
                amount=float(montant),
                currency="XOF",
                phone_number=phone_number,
                email=request.user.email,
                description=f"Formation: {registration.session.formation.titre} - {registration.numero}",
            )

            if result.get("success"):
                # Enregistrer le paiement
                reference = result.get("transaction_id", "")
                payment = process_payment_for_registration(
                    inscription=registration,
                    amount=montant,
                    method=provider_code,
                    reference=reference,
                )

                # Vérifier si le montant total est atteint
                total_paid = FormationPayment.objects.filter(
                    inscription=registration, statut="paid"
                ).aggregate(total=Sum("montant"))["total"] or Decimal("0")

                if total_paid >= montant_total:
                    # Paiement complet — générer le code d'accès
                    code = generate_access_code(registration)
                    from .models import FormationAccessCode
                    FormationAccessCode.objects.create(
                        inscription=registration,
                        code=code,
                        actif=True,
                        attribue_le=timezone.now(),
                    )

                    # Notifier le membre
                    notify_member_access_code(registration, code)

                # Email de confirmation
                notify_member_payment_success(registration, montant, reference)

                return JsonResponse({
                    "success": True,
                    "message": "Paiement effectué avec succès !",
                    "reference": reference,
                })
            else:
                return JsonResponse({
                    "success": False,
                    "error": result.get("error_message", "Échec du paiement"),
                })

        except Exception as e:
            return JsonResponse({
                "success": False,
                "error": f"Erreur: {str(e)}",
            }, status=500)
