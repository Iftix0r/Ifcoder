from django.contrib.auth.models import User
from django.test import Client as HttpClient, TestCase
from django.urls import reverse

from clients.models import Client
from tickets.models import Ticket, TicketReply


class TicketModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testclient", password="password123")
        self.client_obj = Client.objects.create(name="Test Client", user=self.user)
        self.ticket = Ticket.objects.create(
            title="Vebsayt yuklanishida muammo",
            body="Bosh sahifa judayam sekin yuklanmoqda.",
            client=self.client_obj,
            created_by=self.user,
            priority=Ticket.Priority.HIGH,
        )

    def test_ticket_creation_and_str(self):
        self.assertEqual(str(self.ticket), f"#{self.ticket.pk} — Vebsayt yuklanishida muammo")
        self.assertEqual(self.ticket.status, Ticket.Status.OPEN)
        self.assertTrue(self.ticket.is_open)
        self.assertEqual(self.ticket.reply_count, 0)

    def test_ticket_reply(self):
        reply = TicketReply.objects.create(
            ticket=self.ticket,
            author=self.user,
            body="Qo'shimcha skrinshot biriktirildi.",
        )
        self.assertEqual(self.ticket.reply_count, 1)
        self.assertEqual(self.ticket.last_reply, reply)
        self.assertEqual(str(reply), f"Reply #{reply.pk} — Tiket #{self.ticket.pk}")


class PortalTicketViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="clientuser", password="password123")
        self.client_profile = Client.objects.create(name="Client Org", user=self.user)
        self.http_client = HttpClient()

    def test_portal_new_ticket_flow(self):
        self.http_client.login(username="clientuser", password="password123")

        # GET new ticket page
        res = self.http_client.get(reverse("tickets:portal_new"))
        self.assertEqual(res.status_code, 200)

        # POST new ticket
        res = self.http_client.post(reverse("tickets:portal_new"), {
            "title": "SSL sertifikat muddati tugadi",
            "body": "Saytda HTTPS xatoligi chiqmoqda.",
            "priority": "urgent",
        }, follow=True)

        self.assertEqual(res.status_code, 200)
        self.assertEqual(Ticket.objects.count(), 1)
        ticket = Ticket.objects.first()
        self.assertEqual(ticket.title, "SSL sertifikat muddati tugadi")
        self.assertEqual(ticket.client, self.client_profile)
        self.assertEqual(ticket.priority, "urgent")

    def test_portal_list_and_detail_views(self):
        self.http_client.login(username="clientuser", password="password123")
        ticket = Ticket.objects.create(
            title="Domen sozlari",
            body="Domen DNS yozuvlari noto'g'ri.",
            client=self.client_profile,
            created_by=self.user,
        )

        # List view
        res = self.http_client.get(reverse("tickets:portal_list"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Domen sozlari")

        # Detail view
        res = self.http_client.get(reverse("tickets:portal_detail", kwargs={"pk": ticket.pk}))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Domen DNS yozuvlari")

        # Post reply
        res = self.http_client.post(reverse("tickets:portal_detail", kwargs={"pk": ticket.pk}), {
            "body": "Xatolik skrinshotini telegramga yubordim.",
        }, follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(ticket.replies.count(), 1)


class AdminTicketViewsTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username="adminuser", password="adminpassword")
        self.client_user = User.objects.create_user(username="client1", password="password123")
        self.client_profile = Client.objects.create(name="Mijoz LLC", user=self.client_user)
        self.ticket = Ticket.objects.create(
            title="Server javob bermayapti",
            body="API endpoints 504 Gateway Timeout qaytarmoqda.",
            client=self.client_profile,
            created_by=self.client_user,
        )
        self.http_client = HttpClient()

    def test_admin_list_and_detail(self):
        self.http_client.login(username="adminuser", password="adminpassword")

        # Admin list
        res = self.http_client.get(reverse("tickets:admin_list"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Server javob bermayapti")

        # Admin detail
        res = self.http_client.get(reverse("tickets:admin_detail", kwargs={"pk": self.ticket.pk}))
        self.assertEqual(res.status_code, 200)

    def test_admin_reply_and_status_changes(self):
        self.http_client.login(username="adminuser", password="adminpassword")

        # Admin replies
        res = self.http_client.post(reverse("tickets:admin_detail", kwargs={"pk": self.ticket.pk}), {
            "action": "reply",
            "body": "Server qayta yuklandi va muammo hal etildi.",
        }, follow=True)

        self.assertEqual(res.status_code, 200)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.ANSWERED)
        self.assertEqual(self.ticket.replies.count(), 1)
        self.assertTrue(self.ticket.replies.first().is_staff)

        # Admin changes status
        self.http_client.post(reverse("tickets:admin_detail", kwargs={"pk": self.ticket.pk}), {
            "action": "change_status",
            "status": "in_progress",
        })
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.IN_PROGRESS)

        # Admin closes ticket
        self.http_client.post(reverse("tickets:admin_detail", kwargs={"pk": self.ticket.pk}), {
            "action": "close",
        })
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.CLOSED)
        self.assertFalse(self.ticket.is_open)
