from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Client


class ClientDeleteExportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="admin", password="pass12345")
        self.client.force_login(self.user)
        self.obj = Client.objects.create(name="O'chiriladigan mijoz")

    def test_csv_export(self):
        response = self.client.get(reverse("clients:list"), {"export": "csv"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("O'chiriladigan mijoz", response.content.decode())

    def test_delete_removes_object(self):
        response = self.client.post(reverse("clients:delete", args=[self.obj.pk]))
        self.assertRedirects(response, reverse("clients:list"), fetch_redirect_response=False)
        self.assertFalse(Client.objects.filter(pk=self.obj.pk).exists())
