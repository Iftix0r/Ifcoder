from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Bot


class BotDeleteExportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="admin", password="pass12345")
        self.client.force_login(self.user)
        self.obj = Bot.objects.create(name="O'chiriladigan bot")

    def test_csv_export(self):
        response = self.client.get(reverse("bots:list"), {"export": "csv"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("O'chiriladigan bot", response.content.decode())

    def test_delete_removes_object(self):
        response = self.client.post(reverse("bots:delete", args=[self.obj.pk]))
        self.assertRedirects(response, reverse("bots:list"), fetch_redirect_response=False)
        self.assertFalse(Bot.objects.filter(pk=self.obj.pk).exists())
