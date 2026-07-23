from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from .forms import BlogArticleForm, BlogCategoryForm
from .models import BlogArticle, BlogCategory


def blog_list(request):
    """Page publique listant les articles publiés."""
    articles = BlogArticle.objects.filter(is_published=True).select_related("category").order_by("-created_at")
    featured = articles.first()
    categories = BlogCategory.objects.all()
    return render(request, "core/blog.html", {
        "articles": articles,
        "featured": featured,
        "categories": categories,
    })


def blog_detail(request, slug: str):
    """Page publique de détail d'un article."""
    article = get_object_or_404(BlogArticle, slug=slug, is_published=True)
    recent_articles = BlogArticle.objects.filter(is_published=True).exclude(id=article.id).order_by("-created_at")[:3]
    return render(request, "blog/detail.html", {
        "article": article,
        "recent_articles": recent_articles,
    })


def staff_required(user):
    return user.is_authenticated and user.is_staff


@user_passes_test(staff_required)
def categories_list(request):
    categories = BlogCategory.objects.all().order_by("name")
    return render(request, "blog/categories_list.html", {"categories": categories})


@user_passes_test(staff_required)
def category_create(request):
    if request.method == "POST":
        form = BlogCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Catégorie créée avec succès.")
            return redirect("blog:categories_list")
        messages.error(request, "Erreur lors de la création de la catégorie.")
    else:
        form = BlogCategoryForm()

    return render(request, "blog/category_form.html", {"form": form, "mode": "create"})


@user_passes_test(staff_required)
def category_edit(request, category_id: int):
    target_category = get_object_or_404(BlogCategory, id=category_id)

    if request.method == "POST":
        form = BlogCategoryForm(request.POST, instance=target_category)
        if form.is_valid():
            form.save()
            messages.success(request, "Catégorie modifiée avec succès.")
            return redirect("blog:categories_list")
        messages.error(request, "Erreur lors de la modification de la catégorie.")
    else:
        form = BlogCategoryForm(instance=target_category)

    return render(
        request,
        "blog/category_form.html",
        {"form": form, "mode": "edit", "target_category": target_category},
    )


@user_passes_test(staff_required)
def category_delete(request, category_id: int):
    target_category = get_object_or_404(BlogCategory, id=category_id)

    if request.method == "POST":
        target_category.delete()
        messages.success(request, "Catégorie supprimée.")
        return redirect("blog:categories_list")

    return render(
        request,
        "blog/category_confirm_delete.html",
        {"target_category": target_category},
    )


@user_passes_test(staff_required)
def articles_list(request):
    articles = BlogArticle.objects.select_related("category").all().order_by("-created_at")
    return render(request, "blog/articles_list.html", {"articles": articles})


@user_passes_test(staff_required)
def article_create(request):
    if request.method == "POST":
        form = BlogArticleForm(request.POST, request.FILES)

        if form.is_valid():
            form.save()
            messages.success(request, "Article créé avec succès.")
            return redirect("blog:articles_list")
        messages.error(request, "Erreur lors de la création de l'article.")
    else:
        form = BlogArticleForm()

    return render(request, "blog/article_form.html", {"form": form, "mode": "create"})


@user_passes_test(staff_required)
def article_edit(request, article_id: int):
    target_article = get_object_or_404(BlogArticle, id=article_id)

    if request.method == "POST":
        form = BlogArticleForm(request.POST, request.FILES, instance=target_article)

        if form.is_valid():
            form.save()
            messages.success(request, "Article modifié avec succès.")
            return redirect("blog:articles_list")
        messages.error(request, "Erreur lors de la modification de l'article.")
    else:
        form = BlogArticleForm(instance=target_article)

    return render(
        request,
        "blog/article_form.html",
        {"form": form, "mode": "edit", "target_article": target_article},
    )


@user_passes_test(staff_required)
def article_delete(request, article_id: int):
    target_article = get_object_or_404(BlogArticle, id=article_id)

    if request.method == "POST":
        target_article.delete()
        messages.success(request, "Article supprimé.")
        return redirect("blog:articles_list")

    return render(
        request,
        "blog/article_confirm_delete.html",
        {"target_article": target_article},
    )

from django.shortcuts import render, get_object_or_404
from blog.models import BlogArticle


def article_detail_admin(request, id):

    article = get_object_or_404(
        BlogArticle,
        id=id
    )

    return render(
        request,
        "blog/article_detail.html",
        {
            "article": article
        }
    )  

