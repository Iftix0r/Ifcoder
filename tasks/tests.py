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
