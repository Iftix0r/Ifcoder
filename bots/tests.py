from unittest.mock import patch
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Bot
from .handler import process_telegram_update
from .telegram import get_telegram_config, send_telegram_message, send_telegram_document


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


class TelegramBotHandlerTests(TestCase):
    def test_get_telegram_config(self):
        token, chat_id = get_telegram_config()
        self.assertIsInstance(token, str)
        self.assertIsInstance(chat_id, str)

    @patch("bots.handler.send_telegram_message")
    def test_process_telegram_update_start(self, mock_send):
        update = {
            "message": {
                "chat": {"id": 123456789},
                "from": {"first_name": "TestAdmin"},
                "text": "/start",
            }
        }
        process_telegram_update(update)
        mock_send.assert_called_once()
        self.assertIn("Ifcoder CRM Telegram Boti", mock_send.call_args[0][0])

    @patch("bots.handler.send_telegram_message")
    def test_process_telegram_update_status(self, mock_send):
        update = {
            "message": {
                "chat": {"id": 123456789},
                "text": "/status",
            }
        }
        process_telegram_update(update)
        mock_send.assert_called_once()
        self.assertIn("Ifcoder CRM Tizim Holati", mock_send.call_args[0][0])

    @patch("bots.handler.send_telegram_document")
    @patch("bots.handler.send_telegram_message")
    def test_process_telegram_update_backup(self, mock_send_msg, mock_send_doc):
        mock_send_doc.return_value = True
        update = {
            "message": {
                "chat": {"id": 123456789},
                "text": "/backup",
            }
        }
        process_telegram_update(update)
        mock_send_msg.assert_called_once()
        mock_send_doc.assert_called_once()

    @patch("bots.handler.send_telegram_message")
    def test_process_telegram_update_tasks(self, mock_send):
        update = {
            "message": {
                "chat": {"id": 123456789},
                "text": "/tasks",
            }
        }
        process_telegram_update(update)
        mock_send.assert_called_once()

    def test_telegram_webhook_post(self):
        url = reverse("bots:telegram_webhook")
        payload = {
            "message": {
                "chat": {"id": 123456789},
                "text": "/help",
            }
        }
        response = self.client.post(url, data=payload, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
