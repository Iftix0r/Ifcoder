from django.contrib.auth.models import User
from django.test import TestCase
from clients.models import Client
from projects.models import Project


class PortalTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_superuser("adminuser", "admin@test.com", "pass12345")
        self.client_user = User.objects.create_user("clientuser", "client@test.com", "pass12345")
        self.client_profile = Client.objects.create(
            user=self.client_user,
            name="Test Client Corp",
            phone="+998901234567",
        )
        self.project = Project.objects.create(
            name="Test Website",
            client=self.client_profile,
        )

    def test_landing_page_renders(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ifcoder")
        self.assertContains(response, "Xizmatlarimiz")

    def test_landing_page_contact_form_creates_client(self):
        response = self.client.post("/", {
            "name": "Yangi Mijoz MCHJ",
            "phone": "+998998887766",
            "telegram": "@newclient",
            "notes": "Sayt kerak"
        })
        self.assertRedirects(response, "/")
        self.assertTrue(Client.objects.filter(name="Yangi Mijoz MCHJ").exists())

    def test_client_registration(self):
        response = self.client.post("/portal/register/", {
            "name": "Samarqand IT Center",
            "username": "samarqand_it",
            "email": "sam@test.com",
            "phone": "+998661234567",
            "telegram": "@sam_it",
            "password": "secretpassword123",
            "password_confirm": "secretpassword123",
        })
        self.assertRedirects(response, "/portal/")
        self.assertTrue(User.objects.filter(username="samarqand_it").exists())
        self.assertTrue(Client.objects.filter(name="Samarqand IT Center").exists())

    def test_client_portal_access(self):
        self.client.force_login(self.client_user)
        response = self.client.get("/portal/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Client Corp")
        self.assertContains(response, "Test Website")

    def test_smart_login_redirects_staff_to_panel(self):
        response = self.client.post("/portal/login/", {
            "username": "adminuser",
            "password": "pass12345"
        })
        self.assertRedirects(response, "/panel/")

    def test_smart_login_redirects_client_to_portal(self):
        response = self.client.post("/portal/login/", {
            "username": "clientuser",
            "password": "pass12345"
        })
        self.assertRedirects(response, "/portal/")

    def test_client_portal_project_detail(self):
        self.client.force_login(self.client_user)
        response = self.client.get(f"/portal/projects/{self.project.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Website")
        self.assertContains(response, "Loyiha Vazifalari")
