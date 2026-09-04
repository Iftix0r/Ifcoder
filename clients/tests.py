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


from unittest.mock import patch
from projects.models import Project
from debts.models import Debt
from tasks.models import Task
from .telegram_reports import generate_project_report, generate_debt_report, generate_summary_report, send_report_to_client


class TelegramReportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="admin2", password="pass12345")
        self.client.force_login(self.user)
        self.client_obj = Client.objects.create(
            name="Test Client",
            telegram="testclient_tg",
            telegram_id="12345678"
        )
        self.project = Project.objects.create(
            name="Test Project",
            client=self.client_obj,
            status="in_progress"
        )
        self.task = Task.objects.create(
            title="Design DB Schema",
            project=self.project,
            client=self.client_obj,
            status="done"
        )
        self.debt = Debt.objects.create(
            counterparty="Test Client",
            client=self.client_obj,
            amount=500000,
            paid_amount=200000,
            currency="uzs",
            direction="they_owe",
            reason="Loyiha to'lovi"
        )

    def test_report_generators(self):
        p_report = generate_project_report(self.client_obj)
        self.assertIn("Test Project", p_report)
        self.assertIn("Design DB Schema", p_report)

        d_report = generate_debt_report(self.client_obj)
        self.assertIn("500,000", d_report)

        s_report = generate_summary_report(self.client_obj)
        self.assertIn("Test Project", s_report)
        self.assertIn("500,000", s_report)

    @patch("clients.telegram_reports.send_userbot_message")
    def test_send_report_api(self, mock_send_msg):
        mock_send_msg.returnValue = {"status": "ok", "message_id": 100, "chat_id": 12345678}

        url = reverse("clients:send_report_api", args=[self.client_obj.pk])
        response = self.client.post(
            url,
            data={"report_type": "projects"},
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertIn(json_data.get("status"), ["ok", "warning"])

