from django.urls import path

from . import views

app_name = "coworking"

urlpatterns = [
    path("", views.index, name="index"),
    path("workspaces/", views.workspace_list, name="workspace_list"),
    path(
        "workspaces/<slug:slug>/",
        views.workspace_detail,
        name="workspace_detail",
    ),
    path("categories/", views.category_list, name="category_list"),
    path("favorites/", views.favorites, name="favorites"),
    path("search/", views.search, name="search"),
]

