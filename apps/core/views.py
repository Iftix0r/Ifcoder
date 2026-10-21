from django.conf import settings
from django.contrib.auth.decorators import login_not_required
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from .search import global_search


@login_not_required
@require_GET
def robots_txt(request):
    # Faqat ochiq landing sahifa indekslanadi — panel shaxsiy.
    lines = [
        "User-agent: *",
        "Allow: /$",
        "Disallow: /",
        "",
        f"Sitemap: {request.scheme}://{request.get_host()}/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


@login_not_required
@require_GET
def sitemap_xml(request):
    site = f"{request.scheme}://{request.get_host()}"
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"  <url><loc>{site}/</loc><changefreq>weekly</changefreq><priority>1.0</priority></url>\n"
        "</urlset>\n"
    )
    return HttpResponse(xml, content_type="application/xml")


@login_not_required
@require_GET
def google_site_verification(request):
    # Google Search Console «HTML-fayl» tasdiqlash usuli
    return HttpResponse("google-site-verification: googlecb3a790b25376a2f.html", content_type="text/html")


@login_not_required
@require_GET
def favicon(request):
    return FileResponse(open(settings.BASE_DIR / "static" / "img" / "favicon.ico", "rb"), content_type="image/x-icon")


@login_not_required
def healthz(request):
    return HttpResponse("ok", content_type="text/plain")


def search(request):
    return JsonResponse({"results": global_search(request.GET.get("q", ""))})


@login_not_required
def csrf_failure(request, reason=""):
    return render(request, "errors/csrf.html", {"continue_url": request.path}, status=403)
