from django.shortcuts import redirect
from django.urls import reverse

from apps.core.roles import is_student

ALLOWED_PREFIXES = ("/portal/", "/static/")


class StudentGateMiddleware:
    """O'quvchini panelga kiritmaydi.

    Ruxsat ro'yxati ishlatiladi: panelga kelajakda qo'shiladigan har qanday sahifa o'quvchiga avtomatik yopiq.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if user.is_authenticated and not request.path.startswith(ALLOWED_PREFIXES) and is_student(user):
            return redirect(reverse("portal_home"))
        return self.get_response(request)
