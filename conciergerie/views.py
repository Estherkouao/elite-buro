from django.shortcuts import render


def home(request):
    """Page d'accueil de la conciergerie."""
    return render(request, 'conciergerie/conciergeriehome.html')
