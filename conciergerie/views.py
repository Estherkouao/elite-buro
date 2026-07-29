from django.shortcuts import render


def home(request):
    """Page d'accueil de la conciergerie."""
    return render(request, 'conciergerie/conciergeriehome.html')

from django.shortcuts import render, redirect
from .forms import DemandeConciergerieForm
from django.contrib import messages


def conciergerie(request):

    if request.method == "POST":

        form = DemandeConciergerieForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():

            demande = form.save()


            messages.success(
                request,
                "Votre demande a été envoyée avec succès."
            )


            return redirect(
                "conciergerie:conciergerie"
            )


    else:

        form = DemandeConciergerieForm()


    return render(
        request,
        "conciergerie/demandeconciergerie.html",
        {
            "form":form
        }
    )