import datetime
import json
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import override_settings
from django.core.cache import cache
from django.test import TestCase

from clients.models import Client
from finance.models import Invoice
from projects.models import Project
from tasks.models import Task
from dashboard.views import _ask_openai


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

    def test_dashboard_task_can_be_completed_quickly(self):
        task = Task.objects.create(
            title="Dashboarddan bajarish",
            due_date=datetime.date.today()
        )

        response = self.client.get("/panel/")
        self.assertContains(response, "Dashboarddan bajarish")

        status_response = self.client.post(
            f"/panel/tasks/{task.pk}/set-status/", {"status": Task.Status.DONE}
        )

        self.assertEqual(status_response.status_code, 200)
        task.refresh_from_db()
        self.assertEqual(task.status, Task.Status.DONE)

    def test_reports_page_loads(self):
        response = self.client.get("/panel/reports/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sof Natija")

    def test_global_search_finds_client(self):
        Client.objects.create(name="Acme Studio", email="hello@acme.test")

        response = self.client.get("/panel/search/?q=acme")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Acme Studio")
        self.assertContains(response, "Mijoz")

    @override_settings(OPENAI_API_KEY="")
    def test_ai_assistant_explains_missing_api_key(self):
        response = self.client.post("/panel/ai/", {"question": "Bugungi rejam qanday?"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "OPENAI_API_KEY sozlanmagan")

    @override_settings(OPENAI_API_KEY="test-key")
    @patch("dashboard.views.urllib.request.urlopen")
    def test_ai_prompt_contains_actionable_crm_context(self, mock_urlopen):
        Project.objects.create(name="Yangi sayt")
        Task.objects.create(title="Landing page tayyorlash", priority=Task.Priority.HIGH)

        response = mock_urlopen.return_value.__enter__.return_value
        response.read.return_value = json.dumps(
            {"output_text": "Avval landing page ustida ishlang."}
        ).encode()

        answer = _ask_openai("Bugun nima qilay?")

        payload = json.loads(mock_urlopen.call_args.args[0].data)
        self.assertEqual(answer, "Avval landing page ustida ishlang.")
        self.assertIn("Landing page tayyorlash", payload["input"][0]["content"])
        self.assertIn("Yangi sayt", payload["input"][0]["content"])


class ErrorPageTests(TestCase):
    @override_settings(DEBUG=False)
    def test_custom_404_page_rendered_when_debug_false(self):
        response = self.client.get("/non-existent-page-url/")
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "Sahifa topilmadi", status_code=404)
        self.assertContains(response, "404", status_code=404)

