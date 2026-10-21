from django import forms

from apps.core.forms import DateInput, MoneyInput, StyledFormMixin, StyledModelForm

from .models import Activity, Contact, Deal


class ContactForm(StyledModelForm):
    wide_fields = ("tags",)

    class Meta:
        model = Contact
        fields = [
            "name",
            "kind",
            "company",
            "position",
            "phone",
            "telegram",
            "email",
            "website",
            "status",
            "source",
            "next_contact",
            "tags",
            "notes",
        ]
        widgets = {"next_contact": DateInput()}


class DealForm(StyledModelForm):
    wide_fields = ("title",)

    class Meta:
        model = Deal
        fields = ["title", "contact", "value", "currency", "stage", "expected_close", "project", "note"]
        widgets = {"expected_close": DateInput(), "value": MoneyInput()}


class ActivityForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Activity
        fields = ["kind", "text"]
        widgets = {
            "text": forms.Textarea(
                attrs={"rows": 2, "placeholder": "Nima bo'ldi? Masalan: narx kelishildi, ertaga TZ yuboradi"}
            )
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["kind"].choices = [c for c in Activity.Kind.choices if c[0] != Activity.Kind.STAGE]
