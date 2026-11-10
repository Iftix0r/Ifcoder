from django.http import HttpResponse

from apps.core.roles import is_student

from . import services


class SecurityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        ip = services.client_ip(request)
        blocked = services.active_block(ip)
        if blocked:
            return HttpResponse("So'rov xavfsizlik tizimi tomonidan bloklandi.", status=403)
        dangerous = services.dangerous_request_reason(request)
        if dangerous:
            services.block_ip(ip, dangerous)
            return HttpResponse("So'rov bloklandi.", status=403)
        if services.TRAP.search(request.path):
            services.note_trap(request)
            if services.active_block(ip):
                return HttpResponse("So'rov bloklandi.", status=403)
        if services.request_rate_exceeded(request):
            response = HttpResponse("Juda ko'p so'rov. Birozdan keyin qayta urinib ko'ring.", status=429)
            response["Retry-After"] = str(services.RATE_WINDOW)
            return response
        response = self.get_response(request)
        if request.user.is_authenticated and not is_student(request.user):
            services.touch_session(request)
        csp = (
            "default-src 'self'; img-src 'self' data: blob:; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; connect-src 'self'; "
            "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )
        response.setdefault("Content-Security-Policy", csp)
        response.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=(), usb=()")
        response.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        return response
