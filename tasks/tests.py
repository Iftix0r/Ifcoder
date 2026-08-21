import datetime

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Task


class TaskOverdueTests(TestCase):
    def _make_task(self, due_date, status):
        return Task.objects.create(title="Test vazifa", due_date=due_date, status=status)

    def test_past_due_open_is_overdue(self):
        past = datetime.date.today() - datetime.timedelta(days=1)
        task = self._make_task(past, Task.Status.TODO)
        self.assertTrue(task.is_overdue)

    def test_past_due_done_is_not_overdue(self):
        past = datetime.date.today() - datetime.timedelta(days=1)
        task = self._make_task(past, Task.Status.DONE)
        self.assertFalse(task.is_overdue)

    def test_future_due_is_not_overdue(self):
        future = datetime.date.today() + datetime.timedelta(days=1)
        task = self._make_task(future, Task.Status.TODO)
        self.assertFalse(task.is_overdue)

    def test_no_due_date_is_not_overdue(self):
        task = Task.objects.create(title="Muddatsiz")
        self.assertFalse(task.is_overdue)


class TaskViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="admin", password="pass12345")
        self.client.force_login(self.user)

    def test_list_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("tasks:list"))
        self.assertEqual(response.status_code, 302)

    def test_create_task(self):
        response = self.client.post(
            reverse("tasks:add"),
            {"title": "Yangi vazifa", "status": Task.Status.TODO, "priority": Task.Priority.MEDIUM},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Task.objects.filter(title="Yangi vazifa").exists())

    def test_csv_export(self):
        Task.objects.create(title="Eksport vazifasi")
        response = self.client.get(reverse("tasks:list"), {"export": "csv"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("Eksport vazifasi", response.content.decode())

    def test_list_filters_by_priority_and_due_date(self):
        past = datetime.date.today() - datetime.timedelta(days=1)
        future = datetime.date.today() + datetime.timedelta(days=2)
        Task.objects.create(title="Shoshilinch", priority=Task.Priority.HIGH, due_date=past)
        Task.objects.create(title="Keyinroq", priority=Task.Priority.LOW, due_date=future)

        response = self.client.get(
            reverse("tasks:list"), {"priority": "high", "due": "overdue"}
        )

        self.assertContains(response, "Shoshilinch")
        self.assertNotContains(response, "Keyinroq")

    def test_add_time_entry(self):
        task = Task.objects.create(title="Vaqt yoziladigan vazifa")
        response = self.client.post(
            reverse("tasks:add_time", args=[task.pk]),
            {"date": datetime.date.today(), "hours": "2.5", "note": "API"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(task.time_entries.filter(hours="2.50", user=self.user).exists())

    def test_delete_removes_object(self):
        obj = Task.objects.create(title="O'chiriladigan vazifa")
        response = self.client.post(reverse("tasks:delete", args=[obj.pk]))
        self.assertRedirects(response, reverse("tasks:list"), fetch_redirect_response=False)
        self.assertFalse(Task.objects.filter(pk=obj.pk).exists())
