from django import forms
from django.core.validators import RegexValidator

from apps.core.forms import StyledFormMixin

from .models import BlockedIP, TrustedIP


class TrustedForm(StyledFormMixin, forms.ModelForm):
    ip = forms.CharField(
        label="IP yoki boshi",
        max_length=45,
        validators=[RegexValidator(r"^[0-9a-fA-F:.]{3,45}$", "Masalan: 84.54.72.42 yoki 84.54.")],
    )

    class Meta:
        model = TrustedIP
        fields = ["ip", "note"]


class BlockForm(StyledFormMixin, forms.ModelForm):
    ip = forms.GenericIPAddressField(label="IP manzil")
    hours = forms.TypedChoiceField(
        label="Muddat",
        choices=[(1, "1 soat"), (24, "24 soat"), (168, "7 kun"), (720, "30 kun")],
        coerce=int,
        initial=24,
    )

    class Meta:
        model = BlockedIP
        fields = ["ip", "reason"]
        labels = {"reason": "Sabab"}
