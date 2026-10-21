from django import forms


class StyledFormMixin:
    """Barcha vidjetlarga dizayn tizimi klasslarini qo'shadi.

    ``wide_fields`` — modal formada ikki ustunni egallaydigan maydonlar (Textarea avtomatik keng).
    """

    wide_fields: tuple[str, ...] = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, (forms.CheckboxInput, forms.RadioSelect, forms.CheckboxSelectMultiple)):
                css = "checkbox"
            elif isinstance(widget, forms.ClearableFileInput):
                css = "file-input"
            elif isinstance(widget, forms.Textarea):
                css = "input textarea"
                widget.attrs.setdefault("rows", 3)
            elif isinstance(widget, forms.Select):
                css = "input select"
            else:
                css = "input"
            widget.attrs["class"] = f"{css} {widget.attrs.get('class', '')}".strip()
            if isinstance(widget, forms.Textarea) or name in self.wide_fields:
                field.wide = True
            if isinstance(widget, forms.CheckboxInput):
                field.is_checkbox = True


class StyledModelForm(StyledFormMixin, forms.ModelForm):
    pass


class DateInput(forms.DateInput):
    input_type = "date"

    def __init__(self, attrs=None):
        super().__init__(attrs, format="%Y-%m-%d")


class DateTimeInput(forms.DateTimeInput):
    input_type = "datetime-local"

    def __init__(self, attrs=None):
        super().__init__(attrs, format="%Y-%m-%dT%H:%M")


class MoneyInput(forms.TextInput):
    """1250000 → «1 250 000» (x-money direktivasi, serverga bo'shliqsiz ketadi)."""

    def __init__(self, attrs=None):
        base = {"inputmode": "numeric", "x-data": "", "x-money": "", "autocomplete": "off"}
        super().__init__({**base, **(attrs or {})})

    def value_from_datadict(self, data, files, name):
        # JS o'chiq bo'lsa ham «1 250 000» yoki «1 250 000,50» qabul qilinsin
        value = super().value_from_datadict(data, files, name)
        if isinstance(value, str):
            value = "".join(value.split()).replace(" ", "").replace(",", ".")
        return value

    def format_value(self, value):
        if value in (None, ""):
            return ""
        try:
            return f"{int(round(float(value))):,}".replace(",", " ")
        except (TypeError, ValueError):
            return value


def date_widgets(*names):
    return {n: DateInput() for n in names}
