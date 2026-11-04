from django import forms
from django.core.validators import RegexValidator

from apps.core.forms import StyledFormMixin

from .models import TrustedIP


class TrustedForm(StyledFormMixin, forms.ModelForm):
    ip = forms.CharField(
        label="IP yoki boshi",
        max_length=45,
        validators=[RegexValidator(r"^[0-9a-fA-F:.]{3,45}$", "Masalan: 84.54.72.42 yoki 84.54.")],
    )

    class Meta:
        model = TrustedIP
        fields = ["ip", "note"]
