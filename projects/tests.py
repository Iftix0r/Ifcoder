from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from finance.models import Expense, Income
from tasks.models import Task, TimeEntry

from .models import Project


class ProjectDeleteExportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="admin", password="pass12345")
        self.client.force_login(self.user)
        self.obj = Project.objects.create(name="O'chiriladigan loyiha")

    def test_csv_export(self):
        response = self.client.get(reverse("projects:list"), {"export": "csv"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("O'chiriladigan loyiha", response.content.decode())

    def test_delete_removes_object(self):
        response = self.client.post(reverse("projects:delete", args=[self.obj.pk]))
        self.assertRedirects(response, reverse("projects:list"), fetch_redirect_response=False)
        self.assertFalse(Project.objects.filter(pk=self.obj.pk).exists())

    def test_detail_shows_progress_and_profitability(self):
        project = Project.objects.create(
            name="Hisobot loyihasi", hourly_rate="10", contract_value="1000"
        )
        task = Task.objects.create(project=project, title="Bajarilgan", status=Task.Status.DONE)
        TimeEntry.objects.create(task=task, user=self.user, hours="5")
        Income.objects.create(amount="1000", project=project)
        Expense.objects.create(amount="100", project=project)

        response = self.client.get(reverse("projects:detail", args=[project.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["project"].progress_percent, 100)
        self.assertEqual(response.context["project"].profit, 850)
        self.assertContains(response, "Hisobot loyihasi")
