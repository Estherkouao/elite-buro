from django.urls import path

from . import views

app_name = "blog"

urlpatterns = [
    # Pages publiques
    path("", views.blog_list, name="list"),
    path("article/<slug:slug>/", views.blog_detail, name="detail"),

    # Categories (admin)
    path("categories/", views.categories_list, name="categories_list"),
    path("categories/create/", views.category_create, name="category_create"),
    path(
        "categories/<int:category_id>/edit/",
        views.category_edit,
        name="category_edit",
    ),
    path(
        "categories/<int:category_id>/delete/",
        views.category_delete,
        name="category_delete",
    ),

    # Articles (admin)
    path("articles/", views.articles_list, name="articles_list"),
    path("articles/create/", views.article_create, name="article_create"),
    path(
        "articles/<int:article_id>/edit/",
        views.article_edit,
        name="article_edit",
    ),
    path(
        "articles/<int:article_id>/delete/",
        views.article_delete,
        name="article_delete",
    ),


    path(
        "articles/<int:id>/",
        views.article_detail_admin,
        name="article_detail"
    ),
]

