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
    DomiciliationLog,
    DomiciliationPlan,
    DomiciliationRequest,
    RedactionContrat,
    FermetureEntreprise,
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
    """
    Formulaire public d'inscription + demande de domiciliation.

    Crée automatiquement :
    - un compte utilisateur membre
    - une entreprise
    - une demande de domiciliation
    - envoie les identifiants par email
    - connecte automatiquement le membre
    """

    if request.method == "POST":

        # ==========================
        # Récupération des données
        # ==========================

        nom = request.POST.get("nom", "").strip()
        prenom = request.POST.get("prenom", "").strip()
        email = request.POST.get("email", "").strip()
        telephone = request.POST.get("telephone", "").strip()

        entreprise_nom = request.POST.get("entreprise", "").strip()
        activite = request.POST.get("activite", "").strip()

        formule_nom = request.POST.get("formule", "").strip()
        message_client = request.POST.get("message", "").strip()


        # ==========================
        # Validation
        # ==========================

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


        if email and User.objects.filter(email=email).exists():
            erreurs.append(
                "Cet email est déjà utilisé. Veuillez vous connecter."
            )


        if telephone and User.objects.filter(phone=telephone).exists():
            erreurs.append(
                "Ce numéro de téléphone est déjà utilisé."
            )


        # ==========================
        # Recherche formule
        # ==========================

        formule = None

        if formule_nom:

            try:

                formule = DomiciliationPlan.objects.get(
                    nom__iexact=formule_nom,
                    actif=True
                )

            except DomiciliationPlan.DoesNotExist:

                erreurs.append(
                    f"La formule '{formule_nom}' n'existe pas."
                )


        if erreurs:

            for erreur in erreurs:
                messages.error(request, erreur)


            plans = DomiciliationPlan.objects.filter(
                actif=True
            ).order_by(
                "ordre",
                "nom"
            )


            return render(
                request,
                "domiciliation/domiciliation.from.html",
                {
                    "plans": plans
                }
            )


        try:

            # ==========================
            # Création en base
            # ==========================

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


                # 3. Création demande


                numero = _generer_numero_demande()


                demande = DomiciliationRequest.objects.create(

                    utilisateur=user,

                    entreprise=company,

                    formule=formule,

                    numero_demande=numero,

                    type_demande="DOMICILIATION",

                    adresse_domiciliation=(
                        "Cocody Riviera Palmeraie, Abidjan"
                    ),

                    observations=message_client,

                    statut=(
                        DomiciliationRequest.Status.EN_ATTENTE
                    ),

                    date_creation=timezone.now(),

                )


                # 4. Création notification

                notification = NotificationService.notify(

                    user=user,

                    title=(
                        "Bienvenue chez EliteBuro "
                        "— Vos identifiants de connexion"
                    ),

                    message=(

                        f"Votre demande {numero} "
                        "a été enregistrée."

                    ),

                    notification_type=NotificationType.EMAIL,

                )


            # ==========================
            # Envoi email HTML
            # ==========================


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


            # ==========================
            # Connexion automatique
            # ==========================


            login(

                request,

                user,

                backend="django.contrib.auth.backends.ModelBackend"

            )


            # ==========================
            # Message succès
            # ==========================


            messages.success(

                request,

                "Votre demande de domiciliation "
                "a été enregistrée avec succès. "
                "Vos identifiants vous ont été envoyés "
                "par email."

            )


            return redirect(

                reverse(

                    "domiciliation:request_detail",

                    args=[str(demande.id)]

                )

            )


        except Exception as e:


            messages.error(

                request,

                f"Une erreur est survenue : {str(e)}"

            )


            plans = DomiciliationPlan.objects.filter(

                actif=True

            ).order_by(

                "ordre",

                "nom"

            )


            return render(

                request,

                "domiciliation/domiciliation.from.html",

                {

                    "plans": plans

                }

            )


    # ==========================
    # Affichage formulaire
    # ==========================

    plans = DomiciliationPlan.objects.filter(

        actif=True

    ).order_by(

        "ordre",

        "nom"

    )


    return render(

        request,

        "domiciliation/domiciliation.from.html",

        {

            "plans": plans

        }

    )


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
                    type_demande="EI",
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
        .prefetch_related("documents")
        .order_by("-date_creation")
    )
    document_types = DomiciliationDocument.Type.choices
    return render(
        request,
        "domiciliation/history.html",
        {
            "demandes": demandes,
            "document_types": document_types,
        },
    )


@login_required
@csrf_protect
def submit_request(request: HttpRequest, uuid: str) -> HttpResponse:
    """Soumet une demande en brouillon à l'admin (passe en « En attente »)."""
    demande = get_object_or_404(DomiciliationRequest, id=uuid)
    require_can_consulter_request(user=request.user, demande=demande)

    if request.method != "POST":
        return redirect("domiciliation:request_detail", uuid=demande.id)

    if demande.statut != DomiciliationRequest.Status.BROUILLON:
        messages.info(
            request,
            "Cette demande a déjà été soumise ou ne peut plus être soumise.",
        )
        return redirect("domiciliation:history_list")

    with transaction.atomic():
        demande.statut = DomiciliationRequest.Status.EN_ATTENTE
        demande.save(update_fields=["statut", "derniere_modification"])

        DomiciliationLog.objects.create(
            demande=demande,
            utilisateur=request.user,
            action="SOUMISSION",
            details="Demande soumise à l'administration par le membre.",
        )

        # Notifier les administrateurs / gestionnaires
        from accounts.models import User
        from notification.models import NotificationType

        admins = User.objects.filter(
            role__in=[User.Role.ADMIN, User.Role.MANAGER]
        )
        for admin in admins:
            NotificationService.notify(
                user=admin,
                title="📩 Nouvelle demande de domiciliation soumise",
                message=(
                    f"Le membre {demande.utilisateur.get_full_name()} "
                    f"a soumis la demande {demande.numero_demande} "
                    f"pour {demande.entreprise.company_name}."
                ),
                notification_type=NotificationType.SYSTEM,
                priority="HIGH",
            )

    messages.success(
        request,
        "✅ Votre demande a été soumise à l'administration. "
        "Vous pourrez suivre son évolution ici.",
    )
    return redirect("domiciliation:history_list")


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

    documents = demande.documents.all().order_by("created_at")
    contract = getattr(demande, "contrat", None)

    observations = demande.observations or ""
    entreprise_existante = ""
    delai_idu = ""
    ville = ""
    siege_social = ""

    if demande.type_demande == demande.TypeDemande.ENTREPRISE_INDIVIDUELLE:
        for line in observations.split("\n"):
            if line.startswith("Entreprise existante :"):
                entreprise_existante = line.split(":", 1)[1].strip() if ":" in line else ""
            elif line.startswith("Délai certificat IDU :"):
                delai_idu = line.split(":", 1)[1].strip() if ":" in line else ""
            elif line.startswith("Ville :"):
                ville = line.split(":", 1)[1].strip() if ":" in line else ""

    adresse_parts = [p.strip() for p in demande.adresse_domiciliation.split(",") if p.strip()]
    if not siege_social and adresse_parts:
        siege_social = adresse_parts[0]
    if not ville and len(adresse_parts) > 1:
        ville = adresse_parts[1]

    montant = demande.formule.prix if demande.formule else None
    facture = getattr(demande, "facture", None)
    statut_paiement = facture.statut if facture else "En attente"
    contrat_envoye = demande.statut in {
        DomiciliationRequest.Status.CONTRAT_ENVOYÉ,
        DomiciliationRequest.Status.SIGNATURE_EN_ATTENTE,
        DomiciliationRequest.Status.PAIEMENT_EN_ATTENTE,
        DomiciliationRequest.Status.ACTIVE,
    }
    is_admin = getattr(request.user, "role", None) in {
        getattr(User.Role, "ADMIN", "ADMIN"),
        getattr(User.Role, "MANAGER", "MANAGER"),
    }

    return render(
        request,
        "domiciliation/tracking.html",
        {
            "demande": demande,
            "documents": documents,
            "contract": contract,
            "entreprise_existante": entreprise_existante,
            "delai_idu": delai_idu,
            "ville": ville,
            "siege_social": siege_social,
            "montant": montant,
            "statut_paiement": statut_paiement,
            "contrat_envoye": contrat_envoye,
            "is_admin": is_admin,
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

    # Retour par défaut : page de détail de la demande
    next_url = request.POST.get("next") or request.GET.get("next") or reverse(
        "domiciliation:request_detail", args=[str(demande.id)]
    )

    if request.method == "POST":
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            doc_type = form.cleaned_data["type"]
            fichiers = form.cleaned_data["fichiers"]
            commentaire = form.cleaned_data.get("commentaire", "")
            # (Ré)-upload autorisé : on ne supprime pas les documents existants du même type,
            # on ajoute simplement les nouveaux fichiers pour ce type.
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
            messages.success(
                request,
                f"✅ {len(created)} document(s) « {doc_type} » téléversé(s) avec succès.",
            )
            return redirect(next_url)
        else:
            messages.error(request, "❌ Une erreur est survenue lors de l'upload du document.")

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

    if demande.statut not in {
        DomiciliationRequest.Status.CONTRAT_ENVOYÉ,
        DomiciliationRequest.Status.SIGNATURE_EN_ATTENTE,
        DomiciliationRequest.Status.PAIEMENT_EN_ATTENTE,
        DomiciliationRequest.Status.ACTIVE,
    }:
        messages.error(request, "Le contrat n'est pas encore disponible.")
        return redirect("domiciliation:request_detail", uuid=demande.id)

    contract = getattr(demande, "contrat", None)
    return render(request, "domiciliation/contract.html", {
        "demande": demande,
        "contract": contract,
        "peut_signer": demande.statut in {
            DomiciliationRequest.Status.CONTRAT_ENVOYÉ,
            DomiciliationRequest.Status.SIGNATURE_EN_ATTENTE,
        },
    })


@login_required
@csrf_protect
def sign_contract(request: HttpRequest, uuid: str) -> HttpResponse:
    demande = get_object_or_404(DomiciliationRequest, id=uuid)
    require_can_consulter_request(user=request.user, demande=demande)

    if request.method != "POST":
        return redirect("domiciliation:contract", uuid=demande.id)

    if demande.statut not in {
        DomiciliationRequest.Status.CONTRAT_ENVOYÉ,
        DomiciliationRequest.Status.SIGNATURE_EN_ATTENTE,
    }:
        messages.error(request, "Le contrat n'est pas encore disponible pour signature.")
        return redirect("domiciliation:request_detail", uuid=demande.id)

    contract = getattr(demande, "contrat", None)
    if not contract:
        messages.error(request, "Aucun contrat disponible pour cette demande.")
        return redirect("domiciliation:request_detail", uuid=demande.id)

    if contract.signé:
        messages.info(request, "Ce contrat est déjà signé.")
        return redirect("domiciliation:request_detail", uuid=demande.id)

    with transaction.atomic():
        contract.signé = True
        contract.date_signature = timezone.now()
        contract.signature_docuseal = f"DOCUSEAL-{demande.id.hex}-{contract.id}"
        contract.save(update_fields=["signé", "date_signature", "signature_docuseal"])

        demande.statut = DomiciliationRequest.Status.SIGNATURE_EN_ATTENTE
        demande.save(update_fields=["statut", "derniere_modification"])

        DomiciliationLog.objects.create(
            demande=demande,
            utilisateur=request.user,
            action="contrat_signé",
            details=f"Contrat {contract.numero} signé électroniquement.",
        )

    messages.success(request, "✅ Contrat signé avec succès.")
    return redirect("domiciliation:request_detail", uuid=demande.id)


@login_required
def contract_download(request: HttpRequest, uuid: str) -> HttpResponse:
    demande = get_object_or_404(DomiciliationRequest, id=uuid)
    require_can_consulter_request(user=request.user, demande=demande)

    if demande.statut not in {
        DomiciliationRequest.Status.CONTRAT_ENVOYÉ,
        DomiciliationRequest.Status.SIGNATURE_EN_ATTENTE,
        DomiciliationRequest.Status.PAIEMENT_EN_ATTENTE,
        DomiciliationRequest.Status.ACTIVE,
    }:
        raise Http404("Contrat non disponible.")

    contract = getattr(demande, "contrat", None)
    if not contract or not contract.fichier_pdf:
        raise Http404("Contrat introuvable.")

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

from django.views.generic import TemplateView


class CreationEntrepriseView(TemplateView):
    template_name = "domiciliation/creation_entreprise.html"    

@csrf_protect
def creation_sarl(request: HttpRequest) -> HttpResponse:
    """
    Formulaire public de création et domiciliation SARL.
    """

    if request.method == "POST":

        # ==========================
        # INFORMATIONS CLIENT
        # ==========================

        nom = request.POST.get("nom", "").strip()
        prenom = request.POST.get("prenom", "").strip()

        email = request.POST.get("email", "").strip()

        telephone = request.POST.get(
            "telephone",
            ""
        ).strip()



        # ==========================
        # INFORMATIONS SARL
        # ==========================

        entreprise_nom = request.POST.get(
            "entreprise",
            ""
        ).strip()

        


        activite = request.POST.get(
            "activite",
            ""
        ).strip()


        nombre_associes = request.POST.get(
            "nombre_associes",
            ""
        ).strip()


        capital_social = request.POST.get(
            "capital_social",
            ""
        ).strip()


        repartition_parts = request.POST.get(
            "repartition_parts",
            ""
        ).strip()


        gerant = request.POST.get(
            "gerant",
            ""
        ).strip()


        ville = request.POST.get(
            "ville",
            ""
        ).strip()


        siege = request.POST.get(
            "siege_social",
            ""
        ).strip()



        # Services

        statuts = request.POST.get(
            "statuts"
        )

        domiciliation = request.POST.get(
            "domiciliation"
        )

        accompagnement = request.POST.get(
            "accompagnement"
        )



        # ==========================
        # VALIDATION
        # ==========================

        erreurs = []


        if not nom:
            erreurs.append(
                "Le nom est obligatoire."
            )


        if not prenom:
            erreurs.append(
                "Le prénom est obligatoire."
            )


        if not email:
            erreurs.append(
                "L'email est obligatoire."
            )


        if not telephone:
            erreurs.append(
                "Le téléphone est obligatoire."
            )


        if not entreprise_nom:
            erreurs.append(
                "Le nom de la SARL est obligatoire."
            )


        if not activite:
            erreurs.append(
                "L'activité est obligatoire."
            )


        if not capital_social:
            erreurs.append(
                "Le capital social est obligatoire."
            )


        if not ville:
            erreurs.append(
                "La ville est obligatoire."
            )


        if not siege:
            erreurs.append(
                "L'adresse du siège est obligatoire."
            )



        # Vérification utilisateur existant

        if email and User.objects.filter(
            email=email
        ).exists():

            erreurs.append(
                "Cet email est déjà utilisé."
            )


        if telephone and User.objects.filter(
            phone=telephone
        ).exists():

            erreurs.append(
                "Ce numéro de téléphone est déjà utilisé."
            )



        if erreurs:

            for erreur in erreurs:

                messages.error(
                    request,
                    erreur
                )


            return render(
                request,
                "domiciliation/creation_sarl.html"
            )



        try:

            with transaction.atomic():



                # ==========================
                # CREATION CLIENT
                # ==========================


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



                # ==========================
                # CREATION ENTREPRISE
                # ==========================


                company = Company.objects.create(

                    owner=user,

                    company_name=entreprise_nom,

                    description=activite,

                )



                # ==========================
                # ADRESSE
                # ==========================


                adresse = (
                    f"{siege}, {ville}, Côte d'Ivoire"
                )



                # ==========================
                # OBSERVATIONS
                # ==========================


                observations = f"""
Type : SARL

Activité :
{activite}


Nombre associés :
{nombre_associes}


Capital social :
{capital_social} FCFA


Répartition des parts :
{repartition_parts}


Gérant :
{gerant}


Services demandés :

- Statuts SARL : {"Oui" if statuts else "Non"}

- Domiciliation : {"Oui" if domiciliation else "Non"}

- Accompagnement administratif :
{"Oui" if accompagnement else "Non"}


Ville :
{ville}

Adresse siège :
{siege}

"""



                # ==========================
                # DEMANDE
                # ==========================


                numero = _generer_numero_demande()



                demande = DomiciliationRequest.objects.create(

                    utilisateur=user,

                    entreprise=company,

                    formule=DomiciliationPlan.objects.filter(
                        actif=True
                    ).first(),

                    numero_demande=numero,

                    type_demande="SARL",

                    adresse_domiciliation=adresse,

                    observations=observations,

                    statut=(
                        DomiciliationRequest.Status.EN_ATTENTE
                    ),

                    date_creation=timezone.now(),

                )



                # ==========================
                # NOTIFICATION
                # ==========================


                notification = NotificationService.notify(

                    user=user,

                    title=(
                        "Bienvenue chez EliteBuro "
                        "— Création SARL"
                    ),


                    message=(

                        f"Votre demande SARL "
                        f"{numero} a été enregistrée."

                    ),


                    notification_type=(
                        NotificationType.EMAIL
                    ),

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

                            reverse(
                                "accounts:login"
                            )

                        ),

                    }

                )



                # ==========================
                # CONNEXION AUTO
                # ==========================


                from django.contrib.auth import login


                login(

                    request,

                    user,

                    backend=(
                        "django.contrib.auth.backends.ModelBackend"
                    )

                )



                messages.success(

                    request,

                    "Votre demande de création SARL a été enregistrée avec succès."

                )



                return redirect(

                    reverse(

                        "domiciliation:request_detail",

                        args=[
                            str(demande.id)
                        ]

                    )

                )



        except Exception as e:


            messages.error(
                request,
                str(e)
            )


            return render(

                request,

                "domiciliation/creation_sarl.html"

            )



    return render(

        request,

        "domiciliation/creation_sarl.html"

    )    

@csrf_protect
def creation_sarlu(request: HttpRequest) -> HttpResponse:
    """
    Création SARLU Côte d'Ivoire EliteBuro
    """

    if request.method == "POST":


        nom = request.POST.get("nom","").strip()

        prenom = request.POST.get("prenom","").strip()

        email = request.POST.get("email","").strip()

        telephone = request.POST.get("telephone","").strip()


        entreprise_nom = request.POST.get(
            "entreprise",
            ""
        ).strip()


        activite = request.POST.get(
            "activite",
            ""
        ).strip()



        capital_social = request.POST.get(
            "capital_social",
            ""
        )


        gerant = request.POST.get(
            "gerant",
            ""
        ).strip()



        ville = request.POST.get(
            "ville",
            ""
        ).strip()



        siege = request.POST.get(
            "siege_social",
            ""
        ).strip()



        mode_paiement = request.POST.get(
            "mode_paiement",
            ""
        )



        erreurs=[]



        if not nom:
            erreurs.append(
                "Le nom est obligatoire"
            )


        if not prenom:
            erreurs.append(
                "Le prénom est obligatoire"
            )


        if not email:
            erreurs.append(
                "L'email est obligatoire"
            )


        if not telephone:
            erreurs.append(
                "Le téléphone est obligatoire"
            )


        if not entreprise_nom:
            erreurs.append(
                "Le nom SARLU est obligatoire"
            )


        if not activite:
            erreurs.append(
                "L'activité est obligatoire"
            )



        if erreurs:

            for erreur in erreurs:
                messages.error(
                    request,
                    erreur
                )


            return render(
                request,
                "domiciliation/creation_sarlu.html"
            )



        try:


            with transaction.atomic():



                mot_de_passe = (
                    _generer_mot_de_passe()
                )



                user = User.objects.create_user(

                    email=email,

                    password=mot_de_passe,

                    first_name=prenom,

                    last_name=nom,

                    phone=telephone,

                    role=User.Role.MEMBER,

                    is_active=True,

                )





                company = Company.objects.create(

                    owner=user,

                    company_name=entreprise_nom,

                    description=activite,

                )





                adresse = (
                    siege
                    +
                    ", "
                    +
                    ville
                    +
                    ", Côte d'Ivoire"
                )





                numero = (
                    _generer_numero_demande()
                )





                observations = f"""

                Type :
                SARLU


                Associé unique :
                {prenom} {nom}


                Activité :
                {activite}


                Capital social :
                {capital_social} FCFA


                Gérant :
                {gerant}


                Mode paiement :
                {mode_paiement}

                """





                demande = DomiciliationRequest.objects.create(


                    utilisateur=user,


                    entreprise=company,


                    formule=
                    DomiciliationPlan.objects.filter(
                        actif=True
                    ).first(),



                    numero_demande=numero,


                    type_demande="SARLU",


                    adresse_domiciliation=adresse,


                    observations=observations,


                    statut=
                    DomiciliationRequest.Status.EN_ATTENTE,


                    date_creation=timezone.now()

                )





                notification = (
                    NotificationService.notify(

                        user=user,

                        title=
                        "Bienvenue chez EliteBuro",

                        message=
                        f"Votre demande SARLU {numero} est enregistrée.",

                        notification_type=
                        NotificationType.EMAIL

                    )
                )





                NotificationService.send_html_notification(

                    notification,

                    "emails/bienvenue_identifiants.html",

                    {

                    "prenom":prenom,

                    "nom":nom,

                    "numero":numero,

                    "email":email,

                    "mot_de_passe":mot_de_passe,

                    "login_url":
                    request.build_absolute_uri(
                        reverse(
                            "accounts:login"
                        )
                    )

                    }

                )





                login(
                    request,
                    user,
                    backend=
                    "django.contrib.auth.backends.ModelBackend"
                )





                messages.success(
                    request,
                    "Votre demande SARLU a été enregistrée."
                )




                return redirect(

                    reverse(

                        "domiciliation:request_detail",

                        args=[
                            str(demande.id)
                        ]

                    )

                )



        except Exception as e:


            messages.error(
                request,
                str(e)
            )



    return render(

        request,

        "domiciliation/creation_sarlu.html"

    )    


@csrf_protect
def creation_sas(request: HttpRequest) -> HttpResponse:
    """
    Création SAS Côte d'Ivoire EliteBuro
    """

    if request.method == "POST":

        nom = request.POST.get("nom","").strip()
        prenom = request.POST.get("prenom","").strip()
        email = request.POST.get("email","").strip()
        telephone = request.POST.get("telephone","").strip()


        entreprise_nom = request.POST.get(
            "entreprise",
            ""
        ).strip()


        activite = request.POST.get(
            "activite",
            ""
        ).strip()


        nombre_actionnaires = request.POST.get(
            "nombre_actionnaires",
            ""
        )


        capital_social = request.POST.get(
            "capital_social",
            ""
        )


        repartition_actions = request.POST.get(
            "repartition_actions",
            ""
        )


        president = request.POST.get(
            "president",
            ""
        ).strip()


        ville = request.POST.get(
            "ville",
            ""
        ).strip()


        siege = request.POST.get(
            "siege_social",
            ""
        ).strip()


        mode_paiement = request.POST.get(
            "mode_paiement",
            ""
        )



        erreurs=[]



        if not nom:
            erreurs.append(
                "Le nom est obligatoire."
            )


        if not prenom:
            erreurs.append(
                "Le prénom est obligatoire."
            )


        if not email:
            erreurs.append(
                "L'email est obligatoire."
            )


        if not telephone:
            erreurs.append(
                "Le téléphone est obligatoire."
            )


        if not entreprise_nom:
            erreurs.append(
                "Le nom SAS est obligatoire."
            )


        if erreurs:

            for erreur in erreurs:
                messages.error(
                    request,
                    erreur
                )


            return render(
                request,
                "domiciliation/creation_sas.html"
            )



        try:

            with transaction.atomic():


                mot_de_passe = (
                    _generer_mot_de_passe()
                )



                user = User.objects.create_user(

                    email=email,

                    password=mot_de_passe,

                    first_name=prenom,

                    last_name=nom,

                    phone=telephone,

                    role=User.Role.MEMBER,

                    is_active=True

                )




                company = Company.objects.create(

                    owner=user,

                    company_name=entreprise_nom,

                    description=activite

                )




                numero = (
                    _generer_numero_demande()
                )



                adresse = (
                    siege
                    +
                    ", "
                    +
                    ville
                    +
                    ", Côte d'Ivoire"
                )




                observations=f"""
                    Type : SAS

                    Activité :
                    {activite}

                    Nombre actionnaires :
                    {nombre_actionnaires}

                    Capital social :
                    {capital_social} FCFA

                    Répartition actions :
                    {repartition_actions}

                    Président :
                    {president}

                    Paiement :
                    {mode_paiement}

                    """



                demande = DomiciliationRequest.objects.create(

                    utilisateur=user,

                    entreprise=company,

                    formule=
                    DomiciliationPlan.objects.filter(
                        actif=True
                    ).first(),

                    numero_demande=numero,

                    type_demande="SAS",

                    adresse_domiciliation=adresse,

                    observations=observations,

                    statut=
                    DomiciliationRequest.Status.EN_ATTENTE,

                    date_creation=timezone.now()

                )




                notification = NotificationService.notify( 

                    user=user,

                    title="Bienvenue chez EliteBuro",

                    message=
                    f"Votre demande SAS {numero} est enregistrée.",

                    notification_type=
                    NotificationType.EMAIL
                )



                NotificationService.send_html_notification(

                    notification,

                    "emails/bienvenue_identifiants.html",

                    {

                    "prenom":prenom,

                    "nom":nom,

                    "numero":numero,

                    "email":email,

                    "mot_de_passe":mot_de_passe,

                    "login_url":
                    request.build_absolute_uri(
                        reverse(
                            "accounts:login"
                        )
                    )

                    }

                )



                login(
                    request,
                    user,
                    backend=
                    "django.contrib.auth.backends.ModelBackend"
                )



                messages.success(
                    request,
                    "Votre demande SAS a été enregistrée."
                )


                return redirect(

                    reverse(
                        "domiciliation:request_detail",
                        args=[
                            str(demande.id)
                        ]
                    )

                )


        except Exception as e:

            messages.error(
                request,
                str(e)
            )



    return render(
        request,
        "domiciliation/creation_sas.html"
    )


@csrf_protect
def creation_sasu(request: HttpRequest) -> HttpResponse:
    """
    Création SASU Côte d'Ivoire EliteBuro
    """

    if request.method == "POST":

        nom = request.POST.get("nom", "").strip()
        prenom = request.POST.get("prenom", "").strip()
        email = request.POST.get("email", "").strip()
        telephone = request.POST.get("telephone", "").strip()

        entreprise_nom = request.POST.get(
            "entreprise",
            ""
        ).strip()

        activite = request.POST.get(
            "activite",
            ""
        ).strip()

        capital_social = request.POST.get(
            "capital_social",
            ""
        )

        apport = request.POST.get(
            "apport_associe",
            ""
        )

        president = request.POST.get(
            "president",
            ""
        ).strip()

        ville = request.POST.get(
            "ville",
            ""
        ).strip()

        siege = request.POST.get(
            "siege_social",
            ""
        ).strip()


        mode_paiement = request.POST.get(
            "mode_paiement",
            ""
        )



        erreurs = []



        if not nom:
            erreurs.append(
                "Le nom est obligatoire."
            )


        if not prenom:
            erreurs.append(
                "Le prénom est obligatoire."
            )


        if not email:
            erreurs.append(
                "L'email est obligatoire."
            )


        if not telephone:
            erreurs.append(
                "Le téléphone est obligatoire."
            )


        if not entreprise_nom:
            erreurs.append(
                "Le nom de la SASU est obligatoire."
            )



        if erreurs:

            for erreur in erreurs:
                messages.error(
                    request,
                    erreur
                )


            return render(
                request,
                "domiciliation/creation_sasu.html"
            )




        try:

            with transaction.atomic():


                mot_de_passe = (
                    _generer_mot_de_passe()
                )



                user = User.objects.create_user(

                    email=email,

                    password=mot_de_passe,

                    first_name=prenom,

                    last_name=nom,

                    phone=telephone,

                    role=User.Role.MEMBER,

                    is_active=True

                )




                company = Company.objects.create(

                    owner=user,

                    company_name=entreprise_nom,

                    description=activite

                )




                numero = (
                    _generer_numero_demande()
                )




                adresse = (
                    siege
                    +
                    ", "
                    +
                    ville
                    +
                    ", Côte d'Ivoire"
                )




                observations = f"""

Type : SASU

Activité :
{activite}


Associé unique :
{prenom} {nom}


Capital social :
{capital_social} FCFA


Apport associé unique :
{apport}


Président :
{president}


Mode paiement :
{mode_paiement}


"""




                demande = DomiciliationRequest.objects.create(

                    utilisateur=user,

                    entreprise=company,

                    formule=
                    DomiciliationPlan.objects.filter(
                        actif=True
                    ).first(),

                    numero_demande=numero,

                    adresse_domiciliation=adresse,

                    observations=observations,

                    statut=
                    DomiciliationRequest.Status.EN_ATTENTE,

                    date_creation=timezone.now()

                )





                notification = NotificationService.notify(

                    user=user,

                    title=
                    "Bienvenue chez EliteBuro",

                    message=
                    f"Votre demande SASU {numero} est enregistrée.",

                    notification_type=
                    NotificationType.EMAIL

                )





                NotificationService.send_html_notification(

                    notification,

                    "emails/bienvenue_identifiants.html",

                    {

                    "prenom":prenom,

                    "nom":nom,

                    "numero":numero,

                    "email":email,

                    "mot_de_passe":mot_de_passe,

                    "login_url":
                    request.build_absolute_uri(
                        reverse(
                            "accounts:login"
                        )
                    )

                    }

                )





                login(
                    request,
                    user,
                    backend=
                    "django.contrib.auth.backends.ModelBackend"
                )





                messages.success(
                    request,
                    "Votre demande SASU a été enregistrée."
                )





                return redirect(

                    reverse(
                        "domiciliation:request_detail",
                        args=[
                            str(demande.id)
                        ]
                    )

                )



        except Exception as e:

            messages.error(
                request,
                str(e)
            )





    return render(
        request,
        "domiciliation/creation_sasu.html"
    )


@csrf_protect
def creation_ong(request: HttpRequest) -> HttpResponse:
    """
    Création ONG Côte d'Ivoire EliteBuro
    """

    if request.method == "POST":


        nom = request.POST.get(
            "nom",
            ""
        ).strip()


        prenom = request.POST.get(
            "prenom",
            ""
        ).strip()


        email = request.POST.get(
            "email",
            ""
        ).strip()


        telephone = request.POST.get(
            "telephone",
            ""
        ).strip()



        ong_nom = request.POST.get(
            "ong_nom",
            ""
        ).strip()



        domaine = request.POST.get(
            "domaine",
            ""
        ).strip()



        mission = request.POST.get(
            "mission",
            ""
        ).strip()



        fondateurs = request.POST.get(
            "fondateurs",
            ""
        ).strip()



        president = request.POST.get(
            "president",
            ""
        ).strip()



        ville = request.POST.get(
            "ville",
            ""
        ).strip()



        siege = request.POST.get(
            "siege_social",
            ""
        ).strip()



        mode_paiement = request.POST.get(
            "mode_paiement",
            ""
        )



        erreurs = []



        if not nom:
            erreurs.append(
                "Le nom est obligatoire."
            )


        if not prenom:
            erreurs.append(
                "Le prénom est obligatoire."
            )


        if not email:
            erreurs.append(
                "L'email est obligatoire."
            )


        if not telephone:
            erreurs.append(
                "Le téléphone est obligatoire."
            )


        if not ong_nom:
            erreurs.append(
                "Le nom de l'ONG est obligatoire."
            )



        if erreurs:

            for erreur in erreurs:

                messages.error(
                    request,
                    erreur
                )


            return render(
                request,
                "domiciliation/creation_ong.html"
            )






        try:

            with transaction.atomic():



                mot_de_passe = (
                    _generer_mot_de_passe()
                )




                user = User.objects.create_user(

                    email=email,

                    password=mot_de_passe,

                    first_name=prenom,

                    last_name=nom,

                    phone=telephone,

                    role=User.Role.MEMBER,

                    is_active=True

                )






                company = Company.objects.create(

                    owner=user,

                    company_name=ong_nom,

                    description=mission

                )






                numero = (
                    _generer_numero_demande()
                )






                adresse = (

                    siege
                    +
                    ", "
                    +
                    ville
                    +
                    ", Côte d'Ivoire"

                )






                observations = f"""

Type : ONG


Domaine :
{domaine}


Mission :
{mission}



Membres fondateurs :
{fondateurs}



Président :
{president}



Mode paiement :
{mode_paiement}

"""







                demande = DomiciliationRequest.objects.create(

                    utilisateur=user,

                    entreprise=company,

                    formule=
                    DomiciliationPlan.objects.filter(
                        actif=True
                    ).first(),


                    numero_demande=numero,


                    adresse_domiciliation=adresse,


                    observations=observations,


                    statut=
                    DomiciliationRequest.Status.EN_ATTENTE,


                    date_creation=timezone.now()

                )








                notification = NotificationService.notify(

                    user=user,

                    title=
                    "Bienvenue chez EliteBuro",


                    message=
                    f"Votre demande ONG {numero} est enregistrée.",


                    notification_type=
                    NotificationType.EMAIL

                )








                NotificationService.send_html_notification(

                    notification,

                    "emails/bienvenue_identifiants.html",

                    {

                    "prenom":prenom,

                    "nom":nom,

                    "numero":numero,

                    "email":email,

                    "mot_de_passe":mot_de_passe,

                    "login_url":
                    request.build_absolute_uri(
                        reverse(
                            "accounts:login"
                        )
                    )

                    }

                )







                login(

                    request,

                    user,

                    backend=
                    "django.contrib.auth.backends.ModelBackend"

                )







                messages.success(

                    request,

                    "Votre demande de création ONG a été enregistrée."

                )








                return redirect(

                    reverse(

                        "domiciliation:request_detail",

                        args=[
                            str(demande.id)
                        ]

                    )

                )





        except Exception as e:


            messages.error(
                request,
                str(e)
            )




    return render(

        request,

        "domiciliation/creation_ong.html"

    )





@csrf_protect
def creation_startup(request: HttpRequest) -> HttpResponse:
    """
    Formulaire public de création Startup Côte d'Ivoire.
    """

    if request.method == "POST":


        # ==========================
        # INFORMATIONS RESPONSABLE
        # ==========================

        nom = request.POST.get("nom", "").strip()
        prenom = request.POST.get("prenom", "").strip()

        email = request.POST.get("email", "").strip()

        telephone = request.POST.get("telephone", "").strip()



        # ==========================
        # INFORMATIONS STARTUP
        # ==========================

        startup_nom = request.POST.get(
            "startup_nom",
            ""
        ).strip()


        domaine = request.POST.get(
            "domaine",
            ""
        ).strip()


        description = request.POST.get(
            "description_projet",
            ""
        ).strip()



        type_startup = request.POST.get(
            "type_startup",
            ""
        ).strip()



        stade = request.POST.get(
            "stade_projet",
            ""
        ).strip()



        nombre_fondateurs = request.POST.get(
            "nombre_fondateurs",
            ""
        ).strip()



        fondateurs = request.POST.get(
            "fondateurs",
            ""
        ).strip()



        structure = request.POST.get(
            "structure_juridique",
            ""
        ).strip()



        # ==========================
        # ADRESSE
        # ==========================

        ville = request.POST.get(
            "ville",
            ""
        ).strip()



        siege = request.POST.get(
            "siege_social",
            ""
        ).strip()



        # ==========================
        # SERVICES
        # ==========================

        creation_entreprise = (
            "Oui"
            if request.POST.get("creation_entreprise")
            else "Non"
        )


        domiciliation = (
            "Oui"
            if request.POST.get("domiciliation")
            else "Non"
        )


        accompagnement = (
            "Oui"
            if request.POST.get("accompagnement")
            else "Non"
        )



        mode_paiement = request.POST.get(
            "mode_paiement",
            ""
        )



        # ==========================
        # VALIDATION
        # ==========================


        erreurs = []


        if not nom:
            erreurs.append(
                "Le nom est obligatoire."
            )


        if not prenom:
            erreurs.append(
                "Le prénom est obligatoire."
            )


        if not email:
            erreurs.append(
                "L'email est obligatoire."
            )


        if not telephone:
            erreurs.append(
                "Le téléphone est obligatoire."
            )


        if not startup_nom:
            erreurs.append(
                "Le nom de la startup est obligatoire."
            )


        if not domaine:
            erreurs.append(
                "Le domaine est obligatoire."
            )


        if not ville:
            erreurs.append(
                "La ville est obligatoire."
            )


        if not siege:
            erreurs.append(
                "L'adresse du siège est obligatoire."
            )



        if email and User.objects.filter(
            email=email
        ).exists():

            erreurs.append(
                "Cet email est déjà utilisé."
            )



        if telephone and User.objects.filter(
            phone=telephone
        ).exists():

            erreurs.append(
                "Ce numéro est déjà utilisé."
            )



        if erreurs:

            for erreur in erreurs:

                messages.error(
                    request,
                    erreur
                )


            return render(
                request,
                "domiciliation/creation_startup.html"
            )





        try:


            with transaction.atomic():



                # ==========================
                # CREATION UTILISATEUR
                # ==========================


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





                # ==========================
                # CREATION ENTREPRISE
                # ==========================


                company = Company.objects.create(

                    owner=user,

                    company_name=startup_nom,

                    description=description,

                )





                # ==========================
                # DEMANDE DOMICILIATION
                # ==========================


                numero = _generer_numero_demande()



                adresse = (
                    f"{siege}, "
                    f"{ville}, "
                    "Côte d'Ivoire"
                )





                observations = f"""

Type : Startup


Domaine :
{domaine}


Type Startup :
{type_startup}


Stade du projet :
{stade}


Nombre fondateurs :
{nombre_fondateurs}


Fondateurs :
{fondateurs}


Structure juridique souhaitée :
{structure}


Services :

Création entreprise :
{creation_entreprise}


Domiciliation :
{domiciliation}


Accompagnement :
{accompagnement}


Mode paiement :
{mode_paiement}


Description projet :

{description}

"""





                demande = DomiciliationRequest.objects.create(


                    utilisateur=user,


                    entreprise=company,


                    formule=DomiciliationPlan.objects.filter(
                        actif=True
                    ).first(),


                    numero_demande=numero,


                    adresse_domiciliation=adresse,


                    observations=observations,


                    statut=DomiciliationRequest.Status.EN_ATTENTE,


                    date_creation=timezone.now(),


                )







                # ==========================
                # NOTIFICATION EMAIL
                # ==========================


                notification = NotificationService.notify(

                    user=user,

                    title=(
                        "Bienvenue chez EliteBuro "
                        "— Création Startup"
                    ),


                    message=(

                        f"Votre demande Startup "
                        f"{numero} a été enregistrée."

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

                            reverse(
                                "accounts:login"
                            )

                        ),

                    }

                )






                # ==========================
                # CONNEXION AUTOMATIQUE
                # ==========================


                login(

                    request,

                    user,

                    backend=
                    "django.contrib.auth.backends.ModelBackend"

                )





                messages.success(

                    request,

                    "Votre demande Startup a été enregistrée avec succès."

                )





                return redirect(

                    reverse(

                        "domiciliation:request_detail",

                        args=[
                            str(demande.id)
                        ],

                    )

                )




        except Exception as e:


            messages.error(
                request,
                str(e)
            )


            return render(
                request,
                "domiciliation/creation_startup.html"
            )




    return render(
        request,
        "domiciliation/creation_startup.html"
    )    


@csrf_protect
def creation_sci(request: HttpRequest) -> HttpResponse:
    """
    Formulaire public de création SCI Côte d'Ivoire.
    """

    if request.method == "POST":

        nom = request.POST.get("nom", "").strip()
        prenom = request.POST.get("prenom", "").strip()
        email = request.POST.get("email", "").strip()
        telephone = request.POST.get("telephone", "").strip()


        entreprise_nom = request.POST.get("entreprise", "").strip()

        objet_sci = request.POST.get(
            "objet_sci",
            ""
        ).strip()


        type_sci = request.POST.get(
            "type_sci",
            ""
        ).strip()


        nombre_associes = request.POST.get(
            "nombre_associes",
            ""
        ).strip()


        associes = request.POST.get(
            "associes",
            ""
        ).strip()


        capital_social = request.POST.get(
            "capital_social",
            ""
        ).strip()


        repartition_parts = request.POST.get(
            "repartition_parts",
            ""
        ).strip()


        gerant = request.POST.get(
            "gerant",
            ""
        ).strip()


        ville = request.POST.get(
            "ville",
            ""
        ).strip()


        siege = request.POST.get(
            "siege_social",
            ""
        ).strip()


        mode_paiement = request.POST.get(
            "mode_paiement",
            ""
        ).strip()



        erreurs = []


        if not nom:
            erreurs.append(
                "Le nom est obligatoire."
            )


        if not prenom:
            erreurs.append(
                "Le prénom est obligatoire."
            )


        if not email:
            erreurs.append(
                "L'email est obligatoire."
            )


        if not telephone:
            erreurs.append(
                "Le téléphone est obligatoire."
            )


        if not entreprise_nom:
            erreurs.append(
                "Le nom de la SCI est obligatoire."
            )


        if not ville:
            erreurs.append(
                "La ville est obligatoire."
            )



        if not siege:
            erreurs.append(
                "L'adresse du siège est obligatoire."
            )



        if email and User.objects.filter(
            email=email
        ).exists():

            erreurs.append(
                "Cet email existe déjà."
            )



        if telephone and User.objects.filter(
            phone=telephone
        ).exists():

            erreurs.append(
                "Ce téléphone existe déjà."
            )



        if erreurs:

            for erreur in erreurs:

                messages.error(
                    request,
                    erreur
                )


            return render(
                request,
                "domiciliation/creation_sci.html"
            )





        try:

            with transaction.atomic():


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





                company = Company.objects.create(

                    owner=user,

                    company_name=entreprise_nom,

                    description=(
                        "SCI - "
                        + objet_sci
                    )

                )






                adresse = (
                    siege
                    + ", "
                    + ville
                    + ", Côte d'Ivoire"
                )






                observations = f"""
Type : SCI

Objet :
{objet_sci}

Type SCI :
{type_sci}

Nombre associés :
{nombre_associes}

Associés :
{associes}

Capital social :
{capital_social}

Répartition :
{repartition_parts}

Gérant :
{gerant}

Mode paiement :
{mode_paiement}
"""







                numero = _generer_numero_demande()





                demande = DomiciliationRequest.objects.create(

                    utilisateur=user,

                    entreprise=company,

                    formule=
                    DomiciliationPlan.objects.filter(
                        actif=True
                    ).first(),


                    numero_demande=numero,


                    adresse_domiciliation=adresse,


                    observations=observations,


                    statut=
                    DomiciliationRequest.Status.EN_ATTENTE,


                    date_creation=timezone.now()

                )







                notification = NotificationService.notify(

                    user=user,

                    title=
                    "Bienvenue chez EliteBuro - Création SCI",


                    message=
                    f"Votre demande SCI {numero} a été enregistrée.",


                    notification_type=
                    NotificationType.EMAIL

                )






                NotificationService.send_html_notification(

                    notification,

                    "emails/bienvenue_identifiants.html",


                    {

                    "prenom":prenom,

                    "nom":nom,

                    "numero":numero,

                    "email":email,

                    "mot_de_passe":mot_de_passe,


                    "login_url":
                    request.build_absolute_uri(

                        reverse(
                            "accounts:login"
                        )

                    )

                    }

                )






                login(
                    request,
                    user,
                    backend=
                    "django.contrib.auth.backends.ModelBackend"
                )





                messages.success(

                    request,

                    "Votre demande SCI a été enregistrée."

                )





                return redirect(

                    reverse(

                        "domiciliation:request_detail",

                        args=[
                            str(demande.id)
                        ]

                    )

                )





        except Exception as e:


            messages.error(
                request,
                str(e)
            )



            return render(

                request,

                "domiciliation/creation_sci.html"

            )





    return render(

        request,

        "domiciliation/creation_sci.html"

    )

@csrf_protect
def creation_association(request: HttpRequest) -> HttpResponse:
    """
    Formulaire public de création d'une association en Côte d'Ivoire.
    """

    if request.method == "POST":

        # ==========================
        # INFORMATIONS RESPONSABLE
        # ==========================

        prenom = request.POST.get("prenom", "").strip()
        nom = request.POST.get("nom", "").strip()
        email = request.POST.get("email", "").strip()
        telephone = request.POST.get("telephone", "").strip()


        # ==========================
        # ASSOCIATION
        # ==========================

        association_nom = request.POST.get(
            "association",
            ""
        ).strip()


        objet = request.POST.get(
            "objet_association",
            ""
        ).strip()


        domaine = request.POST.get(
            "domaine",
            ""
        ).strip()



        # ==========================
        # RESPONSABLE ASSOCIATION
        # ==========================

        president = request.POST.get(
            "president",
            ""
        ).strip()



        membres = request.POST.get(
            "membres_fondateurs",
            ""
        ).strip()



        bureau = request.POST.get(
            "bureau",
            ""
        ).strip()



        # ==========================
        # ADRESSE
        # ==========================

        ville = request.POST.get(
            "ville",
            ""
        ).strip()


        siege = request.POST.get(
            "siege_social",
            ""
        ).strip()



        # ==========================
        # SERVICES
        # ==========================

        statuts = request.POST.get(
            "statuts"
        )

        depot = request.POST.get(
            "depot_dossier"
        )

        suivi = request.POST.get(
            "suivi"
        )



        mode_paiement = request.POST.get(
            "mode_paiement",
            ""
        )



        # ==========================
        # VALIDATION
        # ==========================

        erreurs = []


        if not nom:
            erreurs.append(
                "Le nom est obligatoire."
            )


        if not prenom:
            erreurs.append(
                "Le prénom est obligatoire."
            )


        if not email:
            erreurs.append(
                "L'email est obligatoire."
            )


        if not telephone:
            erreurs.append(
                "Le téléphone est obligatoire."
            )


        if not association_nom:
            erreurs.append(
                "Le nom de l'association est obligatoire."
            )


        if not objet:
            erreurs.append(
                "L'objet de l'association est obligatoire."
            )


        if not ville:
            erreurs.append(
                "La ville est obligatoire."
            )


        if not siege:
            erreurs.append(
                "L'adresse du siège est obligatoire."
            )



        if email and User.objects.filter(
            email=email
        ).exists():

            erreurs.append(
                "Cet email existe déjà."
            )



        if telephone and User.objects.filter(
            phone=telephone
        ).exists():

            erreurs.append(
                "Ce numéro existe déjà."
            )



        if erreurs:

            for erreur in erreurs:
                messages.error(
                    request,
                    erreur
                )


            return render(
                request,
                "domiciliation/creation_association.html"
            )




        try:

            with transaction.atomic():



                # ==========================
                # CREATION UTILISATEUR
                # ==========================


                mot_de_passe = (
                    _generer_mot_de_passe()
                )



                user = User.objects.create_user(

                    email=email,

                    password=mot_de_passe,

                    first_name=prenom,

                    last_name=nom,

                    phone=telephone,

                    role=User.Role.MEMBER,

                    is_active=True

                )





                # ==========================
                # CREATION STRUCTURE
                # ==========================


                company = Company.objects.create(

                    owner=user,

                    company_name=association_nom,

                    description=objet

                )





                # ==========================
                # ADRESSE
                # ==========================


                adresse = (
                    f"{siege}, "
                    f"{ville}, "
                    "Côte d'Ivoire"
                )





                # ==========================
                # OBSERVATIONS
                # ==========================


                observations = (

                    "Type : Association\n"

                    f"Domaine : {domaine}\n"

                    f"Objet : {objet}\n"

                    f"Président : {president}\n"

                    f"Membres fondateurs : {membres}\n"

                    f"Bureau : {bureau}\n"

                    f"Services : "
                    f"Statuts={bool(statuts)}, "
                    f"Dépôt={bool(depot)}, "
                    f"Suivi={bool(suivi)}\n"

                    f"Mode paiement : {mode_paiement}"

                )





                # ==========================
                # DEMANDE
                # ==========================


                numero = (
                    _generer_numero_demande()
                )



                demande = DomiciliationRequest.objects.create(

                    utilisateur=user,

                    entreprise=company,

                    formule=
                    DomiciliationPlan.objects.filter(
                        actif=True
                    ).first(),


                    numero_demande=numero,


                    adresse_domiciliation=adresse,


                    observations=observations,


                    statut=
                    DomiciliationRequest.Status.EN_ATTENTE,


                    date_creation=timezone.now()

                )






                # ==========================
                # NOTIFICATION EMAIL
                # ==========================


                notification = (
                    NotificationService.notify(

                        user=user,

                        title=
                        "Bienvenue chez EliteBuro",

                        message=(

                            f"Votre demande "
                            f"{numero} "
                            "a été enregistrée."

                        ),

                        notification_type=
                        NotificationType.EMAIL

                    )
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


                        "login_url":
                        request.build_absolute_uri(

                            reverse(
                                "accounts:login"
                            )

                        ),

                    }

                )





                # ==========================
                # CONNEXION AUTO
                # ==========================


                from django.contrib.auth import login


                login(

                    request,

                    user,

                    backend=
                    "django.contrib.auth.backends.ModelBackend"

                )





                messages.success(

                    request,

                    "Votre demande d'association a été enregistrée."

                )





                return redirect(

                    reverse(

                        "domiciliation:request_detail",

                        args=[
                            str(demande.id)
                        ]

                    )

                )



        except Exception as e:


            messages.error(
                request,
                str(e)
            )


            return render(

                request,

                "domiciliation/creation_association.html"

            )




    return render(

        request,

        "domiciliation/creation_association.html"

    )

@csrf_protect
def creation_fondation(request: HttpRequest) -> HttpResponse:
    """
    Formulaire public de création d'une fondation en Côte d'Ivoire.
    """

    if request.method == "POST":

        # ==========================
        # RESPONSABLE
        # ==========================

        prenom = request.POST.get(
            "prenom",
            ""
        ).strip()

        nom = request.POST.get(
            "nom",
            ""
        ).strip()

        email = request.POST.get(
            "email",
            ""
        ).strip()

        telephone = request.POST.get(
            "telephone",
            ""
        ).strip()



        # ==========================
        # FONDATION
        # ==========================

        fondation_nom = request.POST.get(
            "fondation",
            ""
        ).strip()


        type_fondation = request.POST.get(
            "type_fondation",
            ""
        ).strip()


        domaine = request.POST.get(
            "domaine",
            ""
        ).strip()


        mission = request.POST.get(
            "mission",
            ""
        ).strip()



        ressources = request.POST.get(
            "ressources",
            ""
        ).strip()



        conseil = request.POST.get(
            "conseil_administration",
            ""
        ).strip()



        # ==========================
        # ADRESSE
        # ==========================


        ville = request.POST.get(
            "ville",
            ""
        ).strip()


        siege = request.POST.get(
            "siege_social",
            ""
        ).strip()



        # ==========================
        # SERVICES
        # ==========================


        statuts = request.POST.get(
            "statuts"
        )


        declaration = request.POST.get(
            "declaration"
        )


        suivi = request.POST.get(
            "suivi"
        )


        mode_paiement = request.POST.get(
            "mode_paiement",
            ""
        )



        # ==========================
        # VALIDATION
        # ==========================


        erreurs = []



        if not prenom:
            erreurs.append(
                "Le prénom est obligatoire."
            )


        if not nom:
            erreurs.append(
                "Le nom est obligatoire."
            )


        if not email:
            erreurs.append(
                "L'email est obligatoire."
            )


        if not telephone:
            erreurs.append(
                "Le téléphone est obligatoire."
            )


        if not fondation_nom:
            erreurs.append(
                "Le nom de la fondation est obligatoire."
            )


        if not mission:
            erreurs.append(
                "La mission de la fondation est obligatoire."
            )


        if not ville:
            erreurs.append(
                "La ville est obligatoire."
            )


        if not siege:
            erreurs.append(
                "Le siège social est obligatoire."
            )



        if email and User.objects.filter(
            email=email
        ).exists():

            erreurs.append(
                "Cet email existe déjà."
            )



        if telephone and User.objects.filter(
            phone=telephone
        ).exists():

            erreurs.append(
                "Ce numéro de téléphone existe déjà."
            )




        if erreurs:

            for erreur in erreurs:

                messages.error(
                    request,
                    erreur
                )


            return render(
                request,
                "domiciliation/creation_fondation.html"
            )






        try:

            with transaction.atomic():



                # ==========================
                # CREATION UTILISATEUR
                # ==========================


                mot_de_passe = (
                    _generer_mot_de_passe()
                )



                user = User.objects.create_user(

                    email=email,

                    password=mot_de_passe,

                    first_name=prenom,

                    last_name=nom,

                    phone=telephone,

                    role=User.Role.MEMBER,

                    is_active=True

                )





                # ==========================
                # CREATION STRUCTURE
                # ==========================


                company = Company.objects.create(

                    owner=user,

                    company_name=fondation_nom,

                    description=mission

                )







                # ==========================
                # ADRESSE
                # ==========================


                adresse = (

                    f"{siege}, "
                    f"{ville}, "
                    "Côte d'Ivoire"

                )







                # ==========================
                # OBSERVATIONS
                # ==========================


                observations = (

                    "Type : Fondation\n"

                    f"Type fondation : {type_fondation}\n"

                    f"Domaine : {domaine}\n"

                    f"Mission : {mission}\n"

                    f"Ressources initiales : {ressources}\n"

                    f"Conseil administration : {conseil}\n"

                    f"Services : "
                    f"Statuts={bool(statuts)}, "
                    f"Déclaration={bool(declaration)}, "
                    f"Suivi={bool(suivi)}\n"

                    f"Mode paiement : {mode_paiement}"

                )







                # ==========================
                # CREATION DEMANDE
                # ==========================


                numero = (
                    _generer_numero_demande()
                )



                demande = DomiciliationRequest.objects.create(

                    utilisateur=user,

                    entreprise=company,

                    formule=
                    DomiciliationPlan.objects.filter(
                        actif=True
                    ).first(),


                    numero_demande=numero,


                    adresse_domiciliation=adresse,


                    observations=observations,


                    statut=
                    DomiciliationRequest.Status.EN_ATTENTE,


                    date_creation=timezone.now()

                )







                # ==========================
                # NOTIFICATION EMAIL
                # ==========================


                notification = NotificationService.notify(

                    user=user,

                    title=
                    "Bienvenue chez EliteBuro — Fondation",


                    message=(

                        f"Votre demande "
                        f"{numero} "
                        "a été enregistrée."

                    ),


                    notification_type=
                    NotificationType.EMAIL

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


                        "login_url":
                        request.build_absolute_uri(

                            reverse(
                                "accounts:login"
                            )

                        ),

                    }

                )







                # ==========================
                # CONNEXION AUTOMATIQUE
                # ==========================


                from django.contrib.auth import login


                login(

                    request,

                    user,

                    backend=
                    "django.contrib.auth.backends.ModelBackend"

                )







                messages.success(

                    request,

                    "Votre demande de création de fondation a été enregistrée avec succès."

                )







                return redirect(

                    reverse(

                        "domiciliation:request_detail",

                        args=[
                            str(demande.id)
                        ]

                    )

                )






        except Exception as e:


            messages.error(
                request,
                str(e)
            )


            return render(

                request,

                "domiciliation/creation_fondation.html"

            )





    return render(

        request,

        "domiciliation/creation_fondation.html"

    )   


@csrf_protect
def creation_scoop(request: HttpRequest) -> HttpResponse:
    """
    Formulaire public de création d'une Société Coopérative Simplifiée (SCOOP).
    """

    if request.method == "POST":


        # ==========================
        # RESPONSABLE
        # ==========================

        prenom = request.POST.get(
            "prenom",
            ""
        ).strip()


        nom = request.POST.get(
            "nom",
            ""
        ).strip()


        email = request.POST.get(
            "email",
            ""
        ).strip()


        telephone = request.POST.get(
            "telephone",
            ""
        ).strip()



        # ==========================
        # SCOOP
        # ==========================

        scoop_nom = request.POST.get(
            "scoop",
            ""
        ).strip()


        type_scoop = request.POST.get(
            "type_scoop",
            ""
        ).strip()


        domaine = request.POST.get(
            "domaine",
            ""
        ).strip()


        objet = request.POST.get(
            "objet",
            ""
        ).strip()



        nombre_membres = request.POST.get(
            "nombre_membres",
            ""
        ).strip()



        membres = request.POST.get(
            "membres_fondateurs",
            ""
        ).strip()



        president = request.POST.get(
            "president",
            ""
        ).strip()



        capital = request.POST.get(
            "capital_social",
            ""
        ).strip()



        ville = request.POST.get(
            "ville",
            ""
        ).strip()



        siege = request.POST.get(
            "siege_social",
            ""
        ).strip()



        mode_paiement = request.POST.get(
            "mode_paiement",
            ""
        ).strip()



        # ==========================
        # VALIDATION
        # ==========================

        erreurs = []


        champs_obligatoires = {

            "Nom": nom,

            "Prénom": prenom,

            "Email": email,

            "Téléphone": telephone,

            "Nom SCOOP": scoop_nom,

            "Objet": objet,

            "Ville": ville,

            "Siège social": siege,

        }


        for label, valeur in champs_obligatoires.items():

            if not valeur:

                erreurs.append(
                    f"{label} obligatoire."
                )



        if email and User.objects.filter(
            email=email
        ).exists():

            erreurs.append(
                "Cet email est déjà utilisé."
            )



        if telephone and User.objects.filter(
            phone=telephone
        ).exists():

            erreurs.append(
                "Ce téléphone est déjà utilisé."
            )




        if erreurs:

            for erreur in erreurs:

                messages.error(
                    request,
                    erreur
                )


            return render(
                request,
                "domiciliation/creation_scoop.html"
            )





        try:

            with transaction.atomic():



                # ==========================
                # CREATION USER
                # ==========================


                mot_de_passe = _generer_mot_de_passe()



                user = User.objects.create_user(

                    email=email,

                    password=mot_de_passe,

                    first_name=prenom,

                    last_name=nom,

                    phone=telephone,

                    role=User.Role.MEMBER,

                    is_active=True

                )




                # ==========================
                # CREATION ENTREPRISE
                # ==========================


                company = Company.objects.create(

                    owner=user,

                    company_name=scoop_nom,

                    description=objet

                )





                adresse = (

                    f"{siege}, "
                    f"{ville}, "
                    "Côte d'Ivoire"

                )





                observations = (

                    "Type : SCOOP\n"

                    f"Forme : {type_scoop}\n"

                    f"Domaine : {domaine}\n"

                    f"Objet : {objet}\n"

                    f"Nombre membres : {nombre_membres}\n"

                    f"Membres fondateurs : {membres}\n"

                    f"Président : {president}\n"

                    f"Capital : {capital} FCFA\n"

                    f"Paiement : {mode_paiement}"

                )






                numero = _generer_numero_demande()





                demande = DomiciliationRequest.objects.create(

                    utilisateur=user,

                    entreprise=company,

                    formule=
                    DomiciliationPlan.objects.filter(
                        actif=True
                    ).first(),

                    numero_demande=numero,

                    adresse_domiciliation=adresse,

                    observations=observations,

                    statut=
                    DomiciliationRequest.Status.EN_ATTENTE,

                    date_creation=timezone.now()

                )





                # ==========================
                # EMAIL IDENTIFIANTS
                # ==========================


                notification = NotificationService.notify(

                    user=user,

                    title=
                    "Bienvenue chez EliteBuro — Création SCOOP",

                    message=
                    f"Votre demande {numero} a été enregistrée.",

                    notification_type=
                    NotificationType.EMAIL

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

                        "login_url":
                        request.build_absolute_uri(
                            reverse(
                                "accounts:login"
                            )
                        )

                    }

                )





                from django.contrib.auth import login



                login(

                    request,

                    user,

                    backend=
                    "django.contrib.auth.backends.ModelBackend"

                )





                messages.success(

                    request,

                    "Votre demande de création SCOOP a été enregistrée."

                )





                return redirect(

                    reverse(

                        "domiciliation:request_detail",

                        args=[
                            str(demande.id)
                        ]

                    )

                )





        except Exception as e:


            messages.error(
                request,
                str(e)
            )


            return render(
                request,
                "domiciliation/creation_scoop.html"
            )



    return render(

        request,

        "domiciliation/creation_scoop.html"

    )


@login_required
def gestion_entreprise(request):
    entreprises = request.user.companies.all()

    return render(
        request,
        "domiciliation/gestion_entreprise/gestion_entreprise.html",
        {
            "entreprises": entreprises,
        }
    )




from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from .models import ChangementGerant


@login_required
@login_required
@csrf_protect
def changement_gerant(request):
    """
    Affiche et traite le formulaire de demande
    de changement de gérant.
    """

    if request.method == "POST":
        entreprise_id = request.POST.get("entreprise_id")

        ancien_nom = request.POST.get("ancien_nom")
        ancien_prenoms = request.POST.get("ancien_prenoms")
        ancien_email = request.POST.get("ancien_email")
        ancien_telephone = request.POST.get("ancien_telephone")

        nouveau_nom = request.POST.get("nouveau_nom")
        nouveau_prenoms = request.POST.get("nouveau_prenoms")
        nouveau_email = request.POST.get("nouveau_email")
        nouveau_telephone = request.POST.get("nouveau_telephone")

        motif = request.POST.get("motif")

        erreurs = []

        if not entreprise_id:
            erreurs.append("Veuillez sélectionner une entreprise.")

        if not ancien_nom:
            erreurs.append("Le nom de l'ancien gérant est obligatoire.")

        if not ancien_prenoms:
            erreurs.append("Les prénoms de l'ancien gérant sont obligatoires.")

        if not nouveau_nom:
            erreurs.append("Le nom du nouveau gérant est obligatoire.")

        if not nouveau_prenoms:
            erreurs.append("Les prénoms du nouveau gérant sont obligatoires.")

        if not nouveau_email:
            erreurs.append("L'email du nouveau gérant est obligatoire.")

        if not nouveau_telephone:
            erreurs.append("Le téléphone du nouveau gérant est obligatoire.")

        if not motif:
            erreurs.append("Le motif du changement est obligatoire.")

        if erreurs:
            for erreur in erreurs:
                messages.error(request, erreur)

            entreprises = request.user.companies.all()
            context = {
                "entreprises": entreprises,
            }
            return render(
                request,
                "domiciliation/gestion_entreprise/changement_gerant.html",
                context
            )

        demande = ChangementGerant.objects.create(
            entreprise_id=entreprise_id,
            ancien_nom=ancien_nom,
            ancien_prenoms=ancien_prenoms,
            ancien_email=ancien_email,
            ancien_telephone=ancien_telephone,
            nouveau_nom=nouveau_nom,
            nouveau_prenoms=nouveau_prenoms,
            nouveau_email=nouveau_email,
            nouveau_telephone=nouveau_telephone,
            motif=motif,
            demandeur=request.user,
            statut="EN_ATTENTE",
        )

        messages.success(
            request,
            "Votre demande de changement de gérant a été enregistrée avec succès."
        )

        return redirect(
            "gestion_entreprise:detail_changement_gerant",
            pk=demande.pk
        )

    # Récupérer les entreprises du client

    entreprises = request.user.companies.all()

    context = {
        "entreprises": entreprises,
    }

    return render(
        request,
        "domiciliation/gestion_entreprise/changement_gerant.html",
        context
    )


@login_required
def detail_changement_gerant(request, pk):
    """
    Affiche le détail d'une demande de changement de gérant.
    """

    demande = ChangementGerant.objects.get(
        pk=pk,
        demandeur=request.user
    )

    return render(
        request,
        "domiciliation/gestion_entreprise/detail_changement_gerant.html",
        {
            "demande": demande
        }
    )


@login_required
def mes_changements_gerant(request):
    """
    Liste les demandes de changement de gérant
    du client connecté.
    """

    demandes = ChangementGerant.objects.filter(
        demandeur=request.user
    ).order_by("-date_creation")

    return render(
        request,
        "domiciliation/gestion_entreprise/mes_changements_gerant.html",
        {
            "demandes": demandes
        }
    )



from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect

from .models import CessionPartsSociales

@login_required
def cession_parts_sociales(request):

    entreprises = request.user.companies.all()

    if request.method == "POST":

        entreprise_id = request.POST.get("entreprise_id")

        entreprise = get_object_or_404(
            entreprises,
            id=entreprise_id
        )

        demande = CessionPartsSociales.objects.create(

            demandeur=request.user,

            entreprise=entreprise,

            # Cédant
            cedant_nom=request.POST.get("cedant_nom"),
            cedant_prenoms=request.POST.get("cedant_prenoms"),
            cedant_email=request.POST.get("cedant_email"),
            cedant_telephone=request.POST.get("cedant_telephone"),

            # Cessionnaire
            cessionnaire_nom=request.POST.get("cessionnaire_nom"),
            cessionnaire_prenoms=request.POST.get("cessionnaire_prenoms"),
            cessionnaire_email=request.POST.get("cessionnaire_email"),
            cessionnaire_telephone=request.POST.get(
                "cessionnaire_telephone"
            ),
            cessionnaire_nationalite=request.POST.get(
                "cessionnaire_nationalite"
            ),
            cessionnaire_adresse=request.POST.get(
                "cessionnaire_adresse"
            ),

            # Parts
            nombre_parts=request.POST.get("nombre_parts"),
            valeur_nominale=request.POST.get("valeur_nominale"),
            prix_cession=request.POST.get("prix_cession"),
            date_cession=request.POST.get("date_cession") or None,

            # Informations
            motif=request.POST.get("motif"),
            observations=request.POST.get("observations"),

            # Documents
            piece_identite_cedant=request.FILES.get(
                "piece_identite_cedant"
            ),
            piece_identite_cessionnaire=request.FILES.get(
                "piece_identite_cessionnaire"
            ),
            acte_cession=request.FILES.get(
                "acte_cession"
            ),
            proces_verbal=request.FILES.get(
                "proces_verbal"
            ),
            statuts=request.FILES.get(
                "statuts"
            ),
            autres_documents=request.FILES.get(
                "autres_documents"
            ),

            statut=CessionPartsSociales.Statut.EN_ATTENTE,
        )

        messages.success(
            request,
            "Votre demande de cession de parts sociales "
            "a été enregistrée avec succès."
        )

        return redirect(
            "domiciliation:detail_cession_parts",
            pk=demande.pk
        )

    return render(
        request,
        "domiciliation/gestion_entreprise/cession_parts_sociales.html",
        {
            "entreprises": entreprises,
        }
    )

@login_required
def detail_cession_parts(request, pk):

    demande = get_object_or_404(
        CessionPartsSociales,
        pk=pk,
        demandeur=request.user
    )

    return render(
        request,
        "domiciliation/detail_cession_parts.html",
        {
            "demande": demande
        }
    )
@login_required
def mes_cessions_parts(request):

    demandes = CessionPartsSociales.objects.filter(
        demandeur=request.user
    ).select_related(
        "entreprise"
    ).order_by("-date_creation")

    return render(
        request,
        "domiciliation/mes_cessions_parts.html",
        {
            "demandes": demandes
        }
    )


@login_required
def modification_activite(request):

    entreprises = request.user.companies.all()

    if request.method == "POST":

        entreprise_id = request.POST.get("entreprise_id")

        entreprise = get_object_or_404(
            entreprises,
            id=entreprise_id
        )

        demande = ModificationActivite.objects.create(

            demandeur=request.user,

            entreprise=entreprise,

            activite_actuelle=request.POST.get(
                "activite_actuelle"
            ),

            nouvelle_activite=request.POST.get(
                "nouvelle_activite"
            ),

            motif=request.POST.get("motif"),

            observations=request.POST.get(
                "observations"
            ),

            statuts=request.FILES.get("statuts"),

            proces_verbal=request.FILES.get(
                "proces_verbal"
            ),

            justificatif=request.FILES.get(
                "justificatif"
            ),

            autres_documents=request.FILES.get(
                "autres_documents"
            ),

            statut=ModificationActivite.Statut.EN_ATTENTE
        )

        messages.success(
            request,
            "Votre demande de modification d'activité "
            "a été enregistrée avec succès."
        )

        return redirect(
            "domiciliation:detail_modification_activite",
            pk=demande.pk
        )

    return render(
        request,
        "domiciliation/gestion_entreprise/modification_activite.html",
        {
            "entreprises": entreprises
        }
    )

@login_required
def detail_modification_activite(request, pk):

    demande = get_object_or_404(
        ModificationActivite,
        pk=pk,
        demandeur=request.user
    )

    return render(
        request,
        "domiciliation/detail_modification_activite.html",
        {
            "demande": demande
        }
    )

@login_required
def mes_modifications_activite(request):

    demandes = ModificationActivite.objects.filter(
        demandeur=request.user
    ).select_related(
        "entreprise"
    ).order_by("-date_creation")

    return render(
        request,
        "domiciliation/mes_modifications_activite.html",
        {
            "demandes": demandes
        }
    )    


@login_required
def changement_nom_entreprise(request):

    entreprises = request.user.companies.all()

    if request.method == "POST":

        entreprise_id = request.POST.get("entreprise_id")

        entreprise = get_object_or_404(
            entreprises,
            id=entreprise_id
        )

        demande = ChangementNomEntreprise.objects.create(

            demandeur=request.user,

            entreprise=entreprise,

            ancien_nom=request.POST.get(
                "ancien_nom"
            ),

            nouveau_nom=request.POST.get(
                "nouveau_nom"
            ),

            motif=request.POST.get(
                "motif"
            ),

            observations=request.POST.get(
                "observations"
            ),

            statuts=request.FILES.get(
                "statuts"
            ),

            proces_verbal=request.FILES.get(
                "proces_verbal"
            ),

            justificatif=request.FILES.get(
                "justificatif"
            ),

            autres_documents=request.FILES.get(
                "autres_documents"
            ),

            statut=ChangementNomEntreprise.Statut.EN_ATTENTE
        )

        messages.success(
            request,
            "Votre demande de changement de dénomination "
            "a été enregistrée avec succès."
        )

        return redirect(
            "domiciliation:detail_changement_nom",
            pk=demande.pk
        )

    return render(
        request,
        "domiciliation/gestion_entreprise/changement_nom.html",
        {
            "entreprises": entreprises
        }
    )

@login_required
def detail_changement_nom(request, pk):

    demande = get_object_or_404(
        ChangementNomEntreprise,
        pk=pk,
        demandeur=request.user
    )

    return render(
        request,
        "domiciliation/detail_changement_nom.html",
        {
            "demande": demande
        }
    )

@login_required
def mes_changements_nom(request):

    demandes = ChangementNomEntreprise.objects.filter(
        demandeur=request.user
    ).select_related(
        "entreprise"
    ).order_by("-date_creation")

    return render(
        request,
        "domiciliation/mes_changements_nom.html",
        {
            "demandes": demandes
        }
    )        



@login_required
def depot_marque(request):

    entreprises = request.user.companies.all()

    if request.method == "POST":

        entreprise_id = request.POST.get(
            "entreprise_id"
        )

        entreprise = get_object_or_404(
            entreprises,
            id=entreprise_id
        )

        demande = DepotMarque.objects.create(

            demandeur=request.user,

            entreprise=entreprise,

            # Marque
            nom_marque=request.POST.get(
                "nom_marque"
            ),

            type_marque=request.POST.get(
                "type_marque"
            ),

            description_marque=request.POST.get(
                "description_marque"
            ),

            slogan=request.POST.get(
                "slogan"
            ),

            # Titulaire
            titulaire_nom=request.POST.get(
                "titulaire_nom"
            ),

            titulaire_prenoms=request.POST.get(
                "titulaire_prenoms"
            ),

            titulaire_adresse=request.POST.get(
                "titulaire_adresse"
            ),

            titulaire_email=request.POST.get(
                "titulaire_email"
            ),

            titulaire_telephone=request.POST.get(
                "titulaire_telephone"
            ),

            # Classes
            classes_nice=request.POST.get(
                "classes_nice"
            ),

            produits_services=request.POST.get(
                "produits_services"
            ),

            # Informations
            pays_protection=request.POST.get(
                "pays_protection"
            ),

            marque_deja_utilisee=(
                request.POST.get("marque_deja_utilisee")
                == "oui"
            ),

            date_premiere_utilisation=(
                request.POST.get(
                    "date_premiere_utilisation"
                ) or None
            ),

            motif=request.POST.get(
                "motif"
            ),

            observations=request.POST.get(
                "observations"
            ),

            # Documents
            logo_marque=request.FILES.get(
                "logo_marque"
            ),

            piece_identite=request.FILES.get(
                "piece_identite"
            ),

            justificatif_entreprise=request.FILES.get(
                "justificatif_entreprise"
            ),

            document_marque=request.FILES.get(
                "document_marque"
            ),

            autres_documents=request.FILES.get(
                "autres_documents"
            ),

            statut=DepotMarque.Statut.EN_ATTENTE
        )

        messages.success(
            request,
            "Votre demande de dépôt de marque "
            "a été enregistrée avec succès."
        )

        return redirect(
            "domiciliation:detail_depot_marque",
            pk=demande.pk
        )

    return render(
        request,
        "domiciliation/gestion_entreprise/depot_marque.html",
        {
            "entreprises": entreprises
        }
    )

@login_required
def detail_depot_marque(request, pk):

    demande = get_object_or_404(
        DepotMarque,
        pk=pk,
        demandeur=request.user
    )

    return render(
        request,
        "domiciliation/detail_depot_marque.html",
        {
            "demande": demande
        }
    )

@login_required
def mes_depots_marque(request):

    demandes = DepotMarque.objects.filter(
        demandeur=request.user
    ).select_related(
        "entreprise"
    ).order_by(
        "-date_creation"
    )

    return render(
        request,
        "domiciliation/mes_depots_marque.html",
        {
            "demandes": demandes
        }
    )


@login_required
def redaction_contrat(request):

    entreprises = request.user.companies.all()

    if request.method == "POST":

        entreprise = get_object_or_404(
            entreprises,
            id=request.POST.get("entreprise_id")
        )

        contrat = RedactionContrat.objects.create(

            demandeur=request.user,

            entreprise=entreprise,

            type_contrat=request.POST.get(
                "type_contrat"
            ),

            objet=request.POST.get(
                "objet"
            ),

            description=request.POST.get(
                "description"
            ),

            partie_1_nom=request.POST.get(
                "partie_1_nom"
            ),

            partie_1_type=request.POST.get(
                "partie_1_type"
            ),

            partie_1_adresse=request.POST.get(
                "partie_1_adresse"
            ),

            partie_1_telephone=request.POST.get(
                "partie_1_telephone"
            ),

            partie_1_email=request.POST.get(
                "partie_1_email"
            ),

            partie_2_nom=request.POST.get(
                "partie_2_nom"
            ),

            partie_2_type=request.POST.get(
                "partie_2_type"
            ),

            partie_2_adresse=request.POST.get(
                "partie_2_adresse"
            ),

            partie_2_telephone=request.POST.get(
                "partie_2_telephone"
            ),

            partie_2_email=request.POST.get(
                "partie_2_email"
            ),

            montant=request.POST.get(
                "montant"
            ) or None,

            date_debut=request.POST.get(
                "date_debut"
            ) or None,

            date_fin=request.POST.get(
                "date_fin"
            ) or None,

            duree=request.POST.get(
                "duree"
            ),

            conditions_particulieres=request.POST.get(
                "conditions_particulieres"
            ),

            clauses_souhaitees=request.POST.get(
                "clauses_souhaitees"
            ),

            documents_fournis=request.FILES.get(
                "documents_fournis"
            ),

            statut=RedactionContrat.Statut.EN_ATTENTE
        )

        messages.success(
            request,
            "Votre demande de rédaction de contrat "
            "a été enregistrée."
        )

        return redirect(
            "domiciliation:detail_redaction_contrat",
            pk=contrat.pk
        )

    return render(
        request,
        "domiciliation/gestion_entreprise/redaction_contrat.html",
        {
            "entreprises": entreprises,
            "types_contrat": RedactionContrat.TypeContrat.choices
        }
    )


@login_required
def detail_redaction_contrat(request, pk):

    contrat = get_object_or_404(
        RedactionContrat,
        pk=pk,
        demandeur=request.user
    )

    return render(
        request,
        "domiciliation/detail_redaction_contrat.html",
        {
            "contrat": contrat
        }
    )

@login_required
def mes_redactions_contrats(request):

    contrats = RedactionContrat.objects.filter(
        demandeur=request.user
    ).select_related(
        "entreprise"
    ).order_by(
        "-date_creation"
    )

    return render(
        request,
        "domiciliation/mes_redactions_contrats.html",
        {
            "contrats": contrats
        }
    )    



@login_required
def fermeture_entreprise(request):

    entreprises = request.user.companies.all()

    if request.method == "POST":

        entreprise = get_object_or_404(
            entreprises,
            id=request.POST.get("entreprise_id")
        )

        demande = FermetureEntreprise.objects.create(

            demandeur=request.user,

            entreprise=entreprise,

            motif=request.POST.get(
                "motif"
            ),

            motif_detail=request.POST.get(
                "motif_detail"
            ),

            date_cessation=request.POST.get(
                "date_cessation"
            ) or None,

            activite_arretee=(
                request.POST.get(
                    "activite_arretee"
                ) == "oui"
            ),

            dettes_en_cours=(
                request.POST.get(
                    "dettes_en_cours"
                ) == "oui"
            ),

            dettes_details=request.POST.get(
                "dettes_details"
            ),

            employes=(
                request.POST.get(
                    "employes"
                ) == "oui"
            ),

            nombre_employes=request.POST.get(
                "nombre_employes"
            ) or 0,

            litiges_en_cours=(
                request.POST.get(
                    "litiges_en_cours"
                ) == "oui"
            ),

            litiges_details=request.POST.get(
                "litiges_details"
            ),

            liquidateur_nom=request.POST.get(
                "liquidateur_nom"
            ),

            liquidateur_telephone=request.POST.get(
                "liquidateur_telephone"
            ),

            liquidateur_email=request.POST.get(
                "liquidateur_email"
            ),

            liquidateur_adresse=request.POST.get(
                "liquidateur_adresse"
            ),

            piece_identite=request.FILES.get(
                "piece_identite"
            ),

            document_entreprise=request.FILES.get(
                "document_entreprise"
            ),

            decision_fermeture=request.FILES.get(
                "decision_fermeture"
            ),

            autres_documents=request.FILES.get(
                "autres_documents"
            ),

            statut=FermetureEntreprise.Statut.EN_ATTENTE
        )

        messages.success(
            request,
            "Votre demande de fermeture d'entreprise "
            "a été enregistrée avec succès."
        )

        return redirect(
            "domiciliation:detail_fermeture_entreprise",
            pk=demande.pk
        )

    return render(
        request,
        "domiciliation/gestion_entreprise/fermeture_entreprise.html",
        {
            "entreprises": entreprises,
            "motifs": FermetureEntreprise.Motif.choices,
        }
    )


@login_required
def detail_fermeture_entreprise(request, pk):

    demande = get_object_or_404(
        FermetureEntreprise,
        pk=pk,
        demandeur=request.user
    )

    return render(
        request,
        "domiciliation/detail_fermeture_entreprise.html",
        {
            "demande": demande
        }
    )

@login_required
def mes_fermetures_entreprise(request):

    demandes = FermetureEntreprise.objects.filter(
        demandeur=request.user
    ).select_related(
        "entreprise"
    ).order_by(
        "-date_creation"
    )

    return render(
        request,
        "domiciliation/mes_fermetures_entreprise.html",
        {
            "demandes": demandes
        }
    )    

