"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.http import HttpResponse
from django.urls import include, path
from django.views.generic import RedirectView

from dashboard.views import ThrottledLoginView
from portal.views import landing_view


def robots_txt(request):
    # Faqat ochiq landing sahifa (/) qidiruv tizimlariga ko'rinadi — CRM/boshqaruv
    # paneli, mijoz kabineti va API kabi shaxsiy bo'limlar indekslanmasligi kerak.
    lines = [
        "User-agent: *",
        "Allow: /$",
        "Disallow: /panel/",
        "Disallow: /admin/",
        "Disallow: /portal/",
        "Disallow: /accounts/",
        "Disallow: /api/",
        "Disallow: /tickets/",
        "Disallow: /bots/",
        "Disallow: /media/",
        "",
        f"Sitemap: {request.scheme}://{request.get_host()}/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


def google_site_verification(request):
    # Google Search Console'ning "HTML-fayl" tasdiqlash usuli uchun — fayl mazmuni
    # Google konsolida ko'rsatilgan matn bilan bir xil bo'lishi shart.
    return HttpResponse(
        "google-site-verification: googlecb3a790b25376a2f.html",
        content_type="text/html",
    )


def sitemap_xml(request):
    site_url = f"{request.scheme}://{request.get_host()}"
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"  <url><loc>{site_url}/</loc><changefreq>weekly</changefreq><priority>1.0</priority></url>\n"
        "</urlset>\n"
    )
    return HttpResponse(xml, content_type="application/xml")


from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from django.urls import re_path

from bots.views import telegram_webhook

urlpatterns = [
    path('robots.txt', robots_txt, name='robots_txt'),
    path('sitemap.xml', sitemap_xml, name='sitemap_xml'),
    path('googlecb3a790b25376a2f.html', google_site_verification, name='google_site_verification'),
    path('bots/telegram/webhook/', telegram_webhook, name='telegram_webhook_root'),
    path('admin/', admin.site.urls),
    path('accounts/login/', ThrottledLoginView.as_view(), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('api/', include('mobileapi.urls')),
    path('portal/', include('portal.urls')),
    path('panel/clients/', include('clients.urls')),
    path('panel/projects/', include('projects.urls')),
    path('panel/bots/', include('bots.urls')),
    path('panel/finance/', include('finance.urls')),
    path('panel/infrastructure/', include('infrastructure.urls')),
    path('panel/content/', include('content.urls')),
    path('panel/vault/', include('vault.urls')),
    path('panel/tasks/', include('tasks.urls')),
    path('panel/debts/', include('debts.urls')),
    path('panel/goals/', include('goals.urls')),
    path('tickets/', include('tickets.urls')),
    path('panel/audit/', include('auditlog.urls')),
    path('panel/learning/', include('learning.urls')),
    path('panel/', include('dashboard.urls')),
    path('', landing_view, name='landing'),
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]

