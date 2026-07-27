"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.conf.urls.static import static
from django.urls import path, include
from django.conf import settings

from dashboard.urls import dashboard_trainer_urls
from reclamation.urls import member_urlpatterns

urlpatterns = [
    path('', include('core.urls')),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),

    path('blog/', include('blog.urls')),
    path('coworking/', include('coworking.urls')),
    # Les pages institutionnelles (core/) sont déjà incluses à la racine
    # via path('', include('core.urls')).
    path('dashboard/', include('dashboard.urls')),
    path('dashboard/trainer/', include((dashboard_trainer_urls, 'dashboard'), namespace='dashboard_trainer')),
    path('domiciliation/', include('domiciliation.urls')),
    path('formation/', include('formation.urls')),
    path('notification/', include('notification.urls')),
    path('paiement/', include('paiement.urls')),
    path('reservation/', include('reservation.urls')),
    path('reclamation/', include('reclamation.urls')),
    # URLs membres pour les réclamations (espace membre)
    path('reclamation/membre/', include((member_urlpatterns, 'reclamation'), namespace='reclamation')),
    path('accounts/', include('allauth.urls')),
    path('chatbot/', include('chatbot.urls')),
    path('conciergerie/', include('conciergerie.urls')),
]

if settings.DEBUG:

    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )


