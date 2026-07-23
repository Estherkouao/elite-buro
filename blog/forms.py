from django import forms

from .models import BlogArticle, BlogCategory


class BlogCategoryForm(forms.ModelForm):
    class Meta:
        model = BlogCategory
        fields = ["name", "slug", "description"]

        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "slug": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }


class BlogArticleForm(forms.ModelForm):
    class Meta:
        model = BlogArticle
        fields = [
            "category",
            "title",
            "image",
            "excerpt",
            "content",
            "is_published",
        ]
        widgets = {
            "category": forms.Select(attrs={"class": "form-control"}),
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "excerpt": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "content": forms.Textarea(attrs={"class": "form-control", "rows": 10}),
            "is_published": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


