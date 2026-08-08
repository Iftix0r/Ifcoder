from django.contrib import admin

from .models import Domain, Server, SSLCertificate


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ("name", "registrar", "expiration_date", "auto_renew")
    search_fields = ("name", "registrar")


@admin.register(Server)
class ServerAdmin(admin.ModelAdmin):
    list_display = ("name", "ip_address", "provider", "ssh_port")
    search_fields = ("name", "ip_address", "provider")


@admin.register(SSLCertificate)
class SSLCertificateAdmin(admin.ModelAdmin):
    list_display = ("__str__", "domain", "issuer", "expiration_date")
    search_fields = ("name", "domain__name", "issuer")
