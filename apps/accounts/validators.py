"""Django'ning o'zbekcha tarjimasida parol xabarlari yo'q: ular inglizcha chiqardi."""

from django.contrib.auth import password_validation as base


class MinimumLengthValidator(base.MinimumLengthValidator):
    def get_error_message(self):
        return f"Parol juda qisqa: kamida {self.min_length} ta belgi bo'lsin."

    def get_help_text(self):
        return f"Kamida {self.min_length} ta belgi."


class CommonPasswordValidator(base.CommonPasswordValidator):
    def get_error_message(self):
        return "Bu parol juda oddiy, uni oson topishadi. Boshqasini tanlang."

    def get_help_text(self):
        return "Oddiy parol bo'lmasin."
