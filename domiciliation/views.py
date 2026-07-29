from __future__ import annotations
import secrets
import string

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import FileResponse

from django.db.models import Prefetch
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect

from accounts.models import User, Company
from notification.models import NotificationType
from notification.services import NotificationService

from .forms import (
    DomiciliationPlanForm,
    DomiciliationRequestForm,
    DocumentUploadForm,
    RenewalForm,
)
from .models import (
    DomiciliationContract,
    DomiciliationDocument,
    DomiciliationPlan,
    DomiciliationRequest,
)
from .permissions import require_can_consulter_request, require_can_traiter_request
from .services import (
    activer_domiciliation,
    generer_contrat_pour_demande,
    generer_facture_pour_demande,
    renouveler_domiciliation,
    valider_demande,
)


def _generer_mot_de_passe(longueur: int = 12) -> str:
    """Génère un mot de passe aléatoire sécurisé."""
    alphabet = string.ascii_letters + string.digits + "@#$%"
    return ''.join(secrets.choice(alphabet) for _ in range(longueur))


def _generer_numero_demande() -> str:
    """Génère un numéro de demande unique."""
    ts = timezone.now().strftime("%Y%m%d%H%M%S")
    alea = secrets.token_hex(3).upper()
    return f"DOM-{ts}-{alea}"


@csrf_protect
def domiciliation_from(request: HttpRequest) -> HttpResponse:
    """Formulaire public d'inscription + demande de domiciliation en 7 étapes.

    Crée automatiquement un compte utilisateur, une entreprise et une demande.
    """
    if request.method == "POST":
        # Récupération des champs du formulaire
        nom = request.POST.get("nom", "").strip()
        prenom = request.POST.get("prenom", "").strip()
        email = request.POST.get("email", "").strip()
        telephone = request.POST.get("telephone", "").strip()
        entreprise_nom = request.POST.get("entreprise", "").strip()
        activite = request.POST.get("activite", "").strip()
        formule_nom = request.POST.get("formule", "").strip()
        message = request.POST.get("message", "").strip()

        # Validation basique
        erreurs = []
        if not nom:
            erreurs.append("Le nom est obligatoire.")
        if not prenom:
            erreurs.append("Le prénom est obligatoire.")
        if not email:
            erreurs.append("L'email est obligatoire.")
        if not telephone:
            erreurs.append("Le téléphone est obligatoire.")
        if not entreprise_nom:
            erreurs.append("Le nom de l'entreprise est obligatoire.")
        if not formule_nom:
            erreurs.append("La formule est obligatoire.")

        # Vérifier si l'email existe déjà
        if email and User.objects.filter(email=email).exists():
            erreurs.append("Cet email est déjà utilisé. Veuillez vous connecter.")

        # Récupérer la formule
        formule = None
        if formule_nom:
            try:
                formule = DomiciliationPlan.objects.get(nom__iexact=formule_nom, actif=True)
            except DomiciliationPlan.DoesNotExist:
                erreurs.append(f"La formule '{formule_nom}' n'existe pas.")

        if erreurs:
            for err in erreurs:
                messages.error(request, err)
            plans = DomiciliationPlan.objects.filter(actif=True).order_by("ordre", "nom")
            return render(request, "domiciliation/domiciliation.from.html", {"plans": plans})

        try:
            with transaction.atomic():
                # 1. Créer l'utilisateur
                mot_de_passe = _generer_mot_de_passe()
                user = User.objects.create_user(
                    email=email,
                    password=mot_de_passe,
                    first_name=prenom,
                    last_name=nom,
                    phone=telephone,
                    role=User.Role.MEMBER,
                    is_active=True,
                )

                # 2. Créer l'entreprise
                company = Company.objects.create(
                    owner=user,
                    company_name=entreprise_nom,
                    description=activite,
                )

                # 3. Créer la demande de domiciliation
                numero = _generer_numero_demande()
                demande = DomiciliationRequest.objects.create(
                    utilisateur=user,
                    entreprise=company,
                    formule=formule,
                    numero_demande=numero,
                    adresse_domiciliation="Cocody Riviera Palmeraie, Abidjan",
                    observations=message,
                    statut=DomiciliationRequest.Status.EN_ATTENTE,
                    date_creation=timezone.now(),
                )

# 4. Envoyer l'email de bienvenue avec les identifiants
                NotificationService.notify(
                    user=user,
                    title="Bienvenue chez EliteBuro — Vos identifiants de connexion",
                    message=(
                        f"Bonjour {prenom} {nom},\n\n"
                        f"Merci d'avoir souscrit à la domiciliation d'entreprise EliteBuro.\n\n"
                        f"Votre demande a été enregistrée sous le numéro : {numero}\n\n"
                        f"Voici vos identifiants pour accéder à votre espace membre :\n"
                        f"   📧 Email : {email}\n"
                        f"   🔑 Mot de passe : {mot_de_passe}\n\n"
                        f"Lien de connexion : {request.build_absolute_uri(reverse('accounts:login'))}\n\n"
                        f"Nous vous recommandons de changer votre mot de passe après votre première connexion.\n\n"
                        f"L'équipe EliteBuro"
                    ),
                    notification_type=NotificationType.EMAIL,
                )

                # 5. Connecter automatiquement l'utilisateur
                login(request, user)

                # 5. Message de bienvenue avec identifiants
                messages.success(
                    request,
                    f"✅ Votre demande de domiciliation a été enregistrée !\n"
                    f"Vos identifiants :\n"
                    f"   Email : {email}\n"
                    f"   Mot de passe : {mot_de_passe}\n"
                    f"Veuillez conserver ces informations."
                )

                return redirect(reverse("domiciliation:request_detail", args=[str(demande.id)]))

        except Exception as e:
            messages.error(request, f"Une erreur est survenue : {str(e)}")
            plans = DomiciliationPlan.objects.filter(actif=True).order_by("ordre", "nom")
            return render(request, "domiciliation/domiciliation.from.html", {"plans": plans})

    # GET : afficher le formulaire
    plans = DomiciliationPlan.objects.filter(actif=True).order_by("ordre", "nom")
    return render(request, "domiciliation/domiciliation.from.html", {"plans": plans})


@csrf_protect
def domiciliation_individuelle(request: HttpRequest) -> HttpResponse:
    """
    Formulaire public de création et domiciliation d'entreprise individuelle.
    """

    if request.method == "POST":
        # Récupération des champs
        nom = request.POST.get("nom", "").strip()
        prenom = request.POST.get("prenom", "").strip()
        email = request.POST.get("email", "").strip()
        telephone = request.POST.get("telephone", "").strip()

        entreprise_nom = request.POST.get("entreprise", "").strip()
        activite = request.POST.get("activite", "").strip()
        deja_entreprise = request.POST.get("entreprise_existante", "").strip()
        certificat_delai = request.POST.get("delai_idu", "").strip()
        ville = request.POST.get("ville", "").strip()
        siege = request.POST.get("siege_social", "").strip()

        # Validation
        erreurs = []

        if not nom:
            erreurs.append("Le nom est obligatoire.")

        if not prenom:
            erreurs.append("Le prénom est obligatoire.")

        if not email:
            erreurs.append("L'email est obligatoire.")

        if not telephone:
            erreurs.append("Le téléphone est obligatoire.")

        if not entreprise_nom:
            erreurs.append("Le nom de l'entreprise est obligatoire.")

        if not ville:
            erreurs.append("La ville est obligatoire.")

        if not siege:
            erreurs.append("Le siège social est obligatoire.")

        if email and User.objects.filter(email=email).exists():
            erreurs.append("Cet email est déjà utilisé.")

        if telephone and User.objects.filter(phone=telephone).exists():
            erreurs.append("Ce numéro de téléphone est déjà utilisé.")

        if erreurs:
            for err in erreurs:
                messages.error(request, err)

            return render(
                request,
                "domiciliation/domiciliation_individuelle.html",
            )

        try:
            with transaction.atomic():

                # 1. Création utilisateur
                mot_de_passe = _generer_mot_de_passe()

                user = User.objects.create_user(
                    email=email,
                    password=mot_de_passe,
                    first_name=prenom,
                    last_name=nom,
                    phone=telephone,
                    role=User.Role.MEMBER,
                    is_active=True,
                )

                # 2. Création entreprise
                company = Company.objects.create(
                    owner=user,
                    company_name=entreprise_nom,
                    description=activite,
                )

                # 3. Adresse
                adresse = f"{siege}, {ville}, Côte d'Ivoire"

                # 4. Observations
                observations = (
                    f"Type : Entreprise Individuelle\n"
                    f"Activité : {activite}\n"
                    f"Entreprise existante : {deja_entreprise}\n"
                    f"Délai certificat IDU : {certificat_delai}\n"
                    f"Ville : {ville}"
                )

                # 5. Création demande
                numero = _generer_numero_demande()

                demande = DomiciliationRequest.objects.create(
                    utilisateur=user,
                    entreprise=company,
                    formule=DomiciliationPlan.objects.filter(actif=True).first(),
                    numero_demande=numero,
                    adresse_domiciliation=adresse,
                    observations=observations,
                    statut=DomiciliationRequest.Status.EN_ATTENTE,
                    date_creation=timezone.now(),
                )

                # 6. Notification
                notification = NotificationService.notify(
                    user=user,
                    title="Bienvenue chez EliteBuro — Vos identifiants de connexion",
                    message=(
                        f"Votre demande {numero} a été enregistrée."
                    ),
                    notification_type=NotificationType.EMAIL,
                )


                NotificationService.send_html_notification(
                    notification,
                    "emails/bienvenue_identifiants.html",
                    {
                        "prenom": prenom,
                        "nom": nom,
                        "numero": numero,
                        "email": email,
                        "mot_de_passe": mot_de_passe,
                        "login_url": request.build_absolute_uri(
                            reverse("accounts:login")
                        ),
                    }
                )

                # 7. Connexion automatique
                from django.contrib.auth import login

                login(
                    request,
                    user,
                    backend="django.contrib.auth.backends.ModelBackend"
                )

                # 8. Message
                messages.success(
                    request,
                    "Votre demande a été enregistrée avec succès. "
                    "Vos identifiants vous ont été envoyés par email."
                )

                return redirect(
                    reverse(
                        "domiciliation:request_detail",
                        args=[str(demande.id)],
                    )
                )

        except Exception as e:
            messages.error(request, str(e))

            return render(
                request,
                "domiciliation/domiciliation_individuelle.html",
            )

    return render(
        request,
        "domiciliation/domiciliation_individuelle.html",
    )


def index(request: HttpRequest) -> HttpResponse:
    plans = DomiciliationPlan.objects.filter(actif=True).order_by("ordre", "nom")
    return render(request, "domiciliation/index.html", {"plans": plans})


def plans(request: HttpRequest) -> HttpResponse:
    plans_qs = DomiciliationPlan.objects.filter(actif=True).order_by("ordre", "nom")
    return render(request, "domiciliation/plans.html", {"plans": plans_qs})


def plan_detail(request: HttpRequest, slug: str) -> HttpResponse:
    plan = get_object_or_404(DomiciliationPlan, slug=slug, actif=True)
    return render(request, "domiciliation/detail.html", {"plan": plan})


@login_required
def history_list(request: HttpRequest) -> HttpResponse:
    demandes = (
        DomiciliationRequest.objects.filter(utilisateur=request.user)
        .select_related("entreprise", "formule")
        .order_by("-date_creation")
    )
    return render(request, "domiciliation/history.html", {"demandes": demandes})


@login_required
@csrf_protect
def new_request(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = DomiciliationRequestForm(request.POST, user=request.user)
        if form.is_valid():
            req: DomiciliationRequest = form.save(commit=False)
            req.utilisateur = request.user
            req.numero_demande = _generer_numero_demande()
            req.statut = DomiciliationRequest.Status.BROUILLON
            req.date_creation = timezone.now()
            req.save()
            messages.success(request, "Votre demande de domiciliation a été créée avec succès.")
            return redirect(reverse("domiciliation:request_detail", args=[str(req.id)]))
    else:
        form = DomiciliationRequestForm(user=request.user)
    plans = DomiciliationPlan.objects.filter(actif=True).order_by("ordre", "nom")
    return render(request, "domiciliation/request.html", {"form": form, "plans": plans})


@login_required
@csrf_protect
def request_detail(request: HttpRequest, uuid: str) -> HttpResponse:
    demande = get_object_or_404(
        DomiciliationRequest.objects.select_related("entreprise", "formule", "utilisateur"),
        id=uuid,
    )
    require_can_consulter_request(user=request.user, demande=demande)

    # Prefetch documents/contract
    documents = demande.documents.all().order_by("created_at")
    contract = getattr(demande, "contrat", None)
    return render(
        request,
        "domiciliation/tracking.html",
        {
            "demande": demande,
            "documents": documents,
            "contract": contract,
        },
    )


@login_required
@csrf_protect
def request_edit(request: HttpRequest, uuid: str) -> HttpResponse:
    demande = get_object_or_404(DomiciliationRequest, id=uuid)
    require_can_consulter_request(user=request.user, demande=demande)

    if request.method == "POST":
        form = DomiciliationRequestForm(request.POST, instance=demande)
        if form.is_valid():
            form.save()
            return redirect(reverse("domiciliation:request_detail", args=[str(demande.id)]))
    else:
        form = DomiciliationRequestForm(instance=demande)
    return render(request, "domiciliation/edit.html", {"form": form, "demande": demande})


@login_required
@csrf_protect
def upload_documents(request: HttpRequest, uuid: str) -> HttpResponse:
    demande = get_object_or_404(DomiciliationRequest, id=uuid)
    require_can_consulter_request(user=request.user, demande=demande)

    if request.method == "POST":
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            doc_type = form.cleaned_data["type"]
            fichiers = form.cleaned_data["fichiers"]
            commentaire = form.cleaned_data.get("commentaire", "")
            created = []
            for f in fichiers:
                doc = DomiciliationDocument.objects.create(
                    demande=demande,
                    type=doc_type,
                    commentaire=commentaire,
                    validé=False,
                )
                # assign file
                doc.fichier.save(f.name, f, save=True)
                created.append(doc)
            return redirect(reverse("domiciliation:request_detail", args=[str(demande.id)]))
    else:
        form = DocumentUploadForm()

    return render(
        request,
        "domiciliation/documents.html",
        {"demande": demande, "form": form, "documents": demande.documents.all().order_by("created_at")},
    )


@login_required
@csrf_protect
def contract_view(request: HttpRequest, uuid: str) -> HttpResponse:
    demande = get_object_or_404(DomiciliationRequest, id=uuid)
    require_can_consulter_request(user=request.user, demande=demande)

    contract = getattr(demande, "contrat", None)
    return render(request, "domiciliation/contract.html", {"demande": demande, "contract": contract})


@login_required
def contract_download(request: HttpRequest, uuid: str) -> HttpResponse:
    demande = get_object_or_404(DomiciliationRequest, id=uuid)
    # “Tout le monde peut” => même règle que la consultation du dossier
    require_can_consulter_request(user=request.user, demande=demande)

    contract = getattr(demande, "contrat", None)
    if not contract or not contract.fichier_pdf:
        raise Http404("Contrat introuvable.")

    # FileResponse gère stream + headers.
    response = FileResponse(contract.fichier_pdf.open("rb"), content_type="application/pdf")
    response["Content-Disposition"] = f"attachment; filename=\"{contract.numero}.pdf\""
    return response



@login_required
@csrf_protect
def history(request: HttpRequest, uuid: str) -> HttpResponse:
    demande = get_object_or_404(DomiciliationRequest, id=uuid)
    require_can_consulter_request(user=request.user, demande=demande)
    return render(
        request,
        "domiciliation/request_logs.html",
        {"demande": demande, "logs": demande.logs.all().order_by("created_at").select_related("utilisateur")},
    )


@login_required
@csrf_protect
def renew(request: HttpRequest, uuid: str) -> HttpResponse:
    demande = get_object_or_404(DomiciliationRequest, id=uuid)
    require_can_consulter_request(user=request.user, demande=demande)


    if request.method == "POST":
        form = RenewalForm(request.POST)
        if form.is_valid():
            renewal: DomiciliationRenewal = renouveler_domiciliation(demande=demande, par=request.user)
            return redirect(reverse("domiciliation:request_detail", args=[str(demande.id)]))
    else:
        form = RenewalForm()

    return render(request, "domiciliation/renew.html", {"demande": demande, "form": form})

