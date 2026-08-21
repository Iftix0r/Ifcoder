import datetime

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase

from clients.models import Client
from finance.models import Invoice
from tasks.models import Task


class LoginThrottleTests(TestCase):
    def setUp(self):
        User.objects.create_user("dev", "dev@example.com", "correctpass123")
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_correct_password_logs_in(self):
        r = self.client.post(
            "/accounts/login/", {"username": "dev", "password": "correctpass123"}
        )
        self.assertRedirects(r, "/panel/")

    def test_locked_out_after_too_many_failures(self):
        for _ in range(5):
            self.client.post("/accounts/login/", {"username": "dev", "password": "wrong"})

        r = self.client.post(
            "/accounts/login/", {"username": "dev", "password": "correctpass123"}
        )
        self.assertEqual(r.status_code, 200)  # blocked, even with the right password
        self.assertContains(r, "Juda ko")

    def test_successful_login_resets_counter(self):
        for _ in range(3):
            self.client.post("/accounts/login/", {"username": "dev", "password": "wrong"})
        self.client.post("/accounts/login/", {"username": "dev", "password": "correctpass123"})
        self.client.get("/accounts/logout/")

        for _ in range(3):
            self.client.post("/accounts/login/", {"username": "dev", "password": "wrong"})
        r = self.client.post(
            "/accounts/login/", {"username": "dev", "password": "correctpass123"}
        )
        self.assertRedirects(r, "/panel/")


class AlertsAndReportsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="admin", password="pass12345")
        self.client.force_login(self.user)

    def test_alerts_page_lists_overdue_invoice_and_task(self):
        client_obj = Client.objects.create(name="Test Mijoz")
        past = datetime.date.today() - datetime.timedelta(days=3)
        Invoice.objects.create(
            number="INV-OVERDUE",
            client=client_obj,
            amount=1000,
            issued_date=past,
            due_date=past,
            status=Invoice.Status.SENT,
        )
        Task.objects.create(title="Kechikkan vazifa", due_date=past, status=Task.Status.TODO)

        response = self.client.get("/panel/alerts/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "INV-OVERDUE")
        self.assertContains(response, "Kechikkan vazifa")

    def test_alerts_page_empty_when_nothing_overdue(self):
        response = self.client.get("/panel/alerts/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hozircha e'tibor talab qiladigan holatlar yo'q.")

    def test_reports_page_loads(self):
        response = self.client.get("/panel/reports/")
        self.assertEqual(response.status_code, 200)

    def test_global_search_finds_client(self):
        Client.objects.create(name="Acme Studio", email="hello@acme.test")

        response = self.client.get("/panel/search/?q=acme")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Acme Studio")
        self.assertContains(response, "Mijoz")
