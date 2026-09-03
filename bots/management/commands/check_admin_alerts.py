import html
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

from infrastructure.models import Domain, SSLCertificate
from debts.models import Debt
from tickets.models import Ticket
from bots.telegram import send_telegram_message


class Command(BaseCommand):
    help = "Tizimdagi muhim muammolar (SSL, Domen, Qarzlar, Tiketlar) haqida Telegram adminga jamlangan xabar yuboradi."

    def handle(self, *args, **options):
        today = timezone.localdate()
        alerts = []

        # 1. SSL Sertifikatlar
        expiring_ssl = SSLCertificate.objects.expiring_soon(days=30)
        expired_ssl = SSLCertificate.objects.expired()

        if expired_ssl.exists():
            for ssl_item in expired_ssl:
                alerts.append(f"❌ <b>SSL Muddati tugagan:</b> {html.escape(str(ssl_item))} ({ssl_item.expiration_date})")
        if expiring_ssl.exists():
            for ssl_item in expiring_ssl:
                days_left = (ssl_item.expiration_date - today).days
                alerts.append(f"⚠️ <b>SSL Tugamoqda ({days_left} kun qoldi):</b> {html.escape(str(ssl_item))} ({ssl_item.expiration_date})")

        # 2. Domenlar
        expiring_domains = Domain.objects.expiring_soon(days=30)
        expired_domains = Domain.objects.expired()

        if expired_domains.exists():
            for dom in expired_domains:
                alerts.append(f"❌ <b>Domen Muddati tugagan:</b> {html.escape(dom.name)} ({dom.expiration_date})")
        if expiring_domains.exists():
            for dom in expiring_domains:
                days_left = (dom.expiration_date - today).days
                alerts.append(f"⚠️ <b>Domen Tugamoqda ({days_left} kun qoldi):</b> {html.escape(dom.name)} ({dom.expiration_date})")

        # 3. Qarzlar va to'lovlar
        unpaid_debts = Debt.objects.filter(
            status__in=[Debt.Status.PENDING, Debt.Status.PARTIAL, Debt.Status.OVERDUE]
        )
        for debt in unpaid_debts:
            if debt.is_overdue:
                alerts.append(
                    f"💸 <b>MUDDATI O'TGAN QARZ:</b> {html.escape(debt.counterparty)} — "
                    f"{debt.remaining_amount:,.2f} {debt.get_currency_display()} (Muddat: {debt.due_date})"
                )
            elif debt.due_date and (debt.due_date - today).days <= 7:
                days_left = (debt.due_date - today).days
                alerts.append(
                    f"⏰ <b>To'lov muddati yaqinlashdi ({days_left} kun qoldi):</b> {html.escape(debt.counterparty)} — "
                    f"{debt.remaining_amount:,.2f} {debt.get_currency_display()}"
                )

        # 4. Tiketlar
        urgent_tickets = Ticket.objects.filter(
            status__in=[Ticket.Status.OPEN, Ticket.Status.IN_PROGRESS],
            priority=Ticket.Priority.URGENT,
        )
        if urgent_tickets.exists():
            alerts.append(f"🚨 <b>Shoshilinch Ochiq Tiketlar:</b> {urgent_tickets.count()} ta shoshilinch tiket mavjud!")

        if not alerts:
            self.stdout.write(self.style.SUCCESS("Barcha infratuzilma va moliya ko'rsatkichlari joyida. Ogohlantirish yo'q."))
            return

        msg = f"🔔 <b>Ifcoder CRM Daily Admin Notification</b>\n<i>Sana: {today.strftime('%d.%m.%Y')}</i>\n\n"
        msg += "\n".join(alerts)

        success = send_telegram_message(msg)
        if success:
            self.stdout.write(self.style.SUCCESS("Telegram adminga ogohlantirishlar yuborildi."))
        else:
            self.stdout.write(self.style.WARNING("Ogohlantirish yaratildi, lekin Telegram'ga yuborib bo'lmadi (Token/Chat ID sozlanmagan bo'lishi mumkin)."))
