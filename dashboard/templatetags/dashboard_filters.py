from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    if dictionary:
        return dictionary.get(key, 0)
    return 0


@register.filter
def of_type(documents, type_value):
    """Filtre une liste/queryset de documents par type."""
    return [d for d in documents if getattr(d, "type", None) == type_value]


@register.filter
def filename(file_field):
    """Retourne le nom de base d'un fichier (FieldFile)."""
    name = getattr(file_field, "name", "") or ""
    return name.split("/")[-1]
