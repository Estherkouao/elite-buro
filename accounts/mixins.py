from django.core.exceptions import PermissionDenied
from django.contrib.auth.mixins import LoginRequiredMixin


class AdminRequiredMixin(LoginRequiredMixin):

    def dispatch(self, request, *args, **kwargs):

        if request.user.role != request.user.Role.ADMIN:
            raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)


class ManagerRequiredMixin(LoginRequiredMixin):

    def dispatch(self, request, *args, **kwargs):

        if request.user.role not in [
            request.user.Role.ADMIN,
            request.user.Role.MANAGER,
        ]:
            raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)


class TrainerRequiredMixin(LoginRequiredMixin):

    def dispatch(self, request, *args, **kwargs):

        if request.user.role != request.user.Role.TRAINER:
            raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)


class MemberRequiredMixin(LoginRequiredMixin):

    def dispatch(self, request, *args, **kwargs):

        if request.user.role != request.user.Role.MEMBER:
            raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)