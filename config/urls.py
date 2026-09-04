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
    # Bu shaxsiy CRM/boshqaruv paneli — qidiruv tizimlari indekslamasligi kerak.
    return HttpResponse("User-agent: *\nDisallow: /\n", content_type="text/plain")


from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from django.urls import re_path

from bots.views import telegram_webhook

urlpatterns = [
    path('robots.txt', robots_txt, name='robots_txt'),
    path('bots/telegram/webhook/', telegram_webhook, name='telegram_webhook_root'),
    path('admin/', admin.site.urls),
    path('accounts/login/', ThrottledLoginView.as_view(), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
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

