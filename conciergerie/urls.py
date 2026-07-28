from django.urls import path

from . import views

app_name = 'conciergerie'

urlpatterns = [
    path('', views.home, name='home'),
    path(
        "conciergerie/",
        views.conciergerie,
        name="conciergerie"
    ),
]
