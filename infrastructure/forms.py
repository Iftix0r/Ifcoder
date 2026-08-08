from django import forms

from .models import Domain, Server, SSLCertificate


class DomainForm(forms.ModelForm):
    class Meta:
        model = Domain
        fields = ["name", "registrar", "expiration_date", "auto_renew", "notes"]
        widgets = {
            "expiration_date": forms.DateInput(attrs={"type": "date"}),
        }


class ServerForm(forms.ModelForm):
    class Meta:
        model = Server
        fields = ["name", "ip_address", "provider", "specs", "ssh_port"]


class SSLCertificateForm(forms.ModelForm):
    class Meta:
        model = SSLCertificate
        fields = ["domain", "name", "issuer", "expiration_date", "notes"]
        widgets = {
            "expiration_date": forms.DateInput(attrs={"type": "date"}),
        }
