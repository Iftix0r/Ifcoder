from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.static import serve

from apps.core import views as core

admin.site.site_header = "Ifcoder — ma'lumotlar bazasi"
admin.site.site_title = "Ifcoder"

urlpatterns = [
    path("robots.txt", core.robots_txt),
    path("sitemap.xml", core.sitemap_xml),
    path("googlecb3a790b25376a2f.html", core.google_site_verification),
    path("favicon.ico", core.favicon),
    path("healthz/", core.healthz),
    path("search/", core.search, name="search"),
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
    path("", include("apps.dashboard.urls")),
    path("", include("apps.planner.urls")),
    path("", include("apps.crm.urls")),
    path("", include("apps.projects.urls")),
    path("", include("apps.finance.urls")),
    path("", include("apps.growth.urls")),
    path("", include("apps.notes.urls")),
    path("", include("apps.resources.urls")),
    path("", include("apps.vault.urls")),
    path("", include("apps.landing.urls")),
]

if settings.DEBUG:
    urlpatterns += [path("media/<path:path>", serve, {"document_root": settings.MEDIA_ROOT})]
