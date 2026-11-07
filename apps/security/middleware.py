from apps.core.roles import is_student

from . import services


class SecurityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if services.TRAP.search(request.path):
            services.note_trap(request)
        response = self.get_response(request)
        if request.user.is_authenticated and not is_student(request.user):
            services.touch_session(request)
        return response
