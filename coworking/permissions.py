from django.contrib.auth.models import Group


class PermissionRoles:
    """Rôles métiers génériques pour coworking."""

    ADMIN = "coworking_admin"
    MANAGER = "coworking_manager"
    MEMBER = "coworking_member"
    INVITED = "coworking_invited"

    @staticmethod
    def sync_groups():
        """Crée (si nécessaire) les groupes Django.

        Note: cette méthode est optionnelle et peut être appelée via une commande de maintenance.
        """

        Group.objects.get_or_create(name=PermissionRoles.ADMIN)
        Group.objects.get_or_create(name=PermissionRoles.MANAGER)
        Group.objects.get_or_create(name=PermissionRoles.MEMBER)
        Group.objects.get_or_create(name=PermissionRoles.INVITED)

