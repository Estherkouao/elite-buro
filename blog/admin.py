from django.contrib import admin

from .models import BlogArticle, BlogCategory


@admin.register(BlogCategory)
class BlogCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "created_at", "updated_at")
    search_fields = ("name", "slug")
    list_filter = ("created_at", "updated_at")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(BlogArticle)
class BlogArticleAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "slug",
        "category",
        "is_published",
        "created_at",
        "updated_at",
    )
    search_fields = ("title", "slug", "excerpt")
    list_filter = ("is_published", "created_at", "updated_at", "category")
    prepopulated_fields = {"slug": ("title",)}

