import re

import pyotp
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase, override_settings

from .backup import BACKUP_DIR, is_valid_backup_filename, list_backups
from .crypto import decrypt_value, encrypt_value
from .models import APIKey, BackupCode, TOTPDevice


class CryptoTests(TestCase):
    def test_round_trip(self):
        token = encrypt_value("sekret-qiymat")
        self.assertEqual(decrypt_value(token), "sekret-qiymat")

    def test_ciphertext_differs_from_plaintext(self):
        token = encrypt_value("sekret-qiymat")
        self.assertNotIn("sekret-qiymat", token)

    def test_wrong_key_raises(self):
        from cryptography.fernet import Fernet, InvalidToken

        with override_settings(VAULT_FERNET_KEY=Fernet.generate_key()):
            token = encrypt_value("sekret-qiymat")

        with override_settings(VAULT_FERNET_KEY=Fernet.generate_key()):
            with self.assertRaises(InvalidToken):
                decrypt_value(token)


class APIKeyModelTests(TestCase):
    def test_set_get_value(self):
        key = APIKey(name="Telegram")
        key.set_value("shh-secret")
        key.save()
        key.refresh_from_db()
        self.assertEqual(key.get_value(), "shh-secret")

    def test_masked_value_hides_secret(self):
        key = APIKey(name="Telegram")
        key.set_value("shh-secret-123")
        self.assertNotIn("shh-secret-123", key.masked_value)
        self.assertTrue(key.masked_value.endswith("123"))


class APIKeyViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser("dev", "dev@example.com", "devpass12345")
        self.client.login(username="dev", password="devpass12345")

    def test_create_shows_plaintext_once_then_masks(self):
        r = self.client.post(
            "/panel/vault/api-keys/add/",
            {"name": "Telegram Bot", "notes": "", "value": "topsecretvalue"},
            follow=True,
        )
        self.assertContains(r, "topsecretvalue")  # flash message, shown once

        r2 = self.client.get("/panel/vault/api-keys/")
        self.assertNotContains(r2, "topsecretvalue")

    def test_edit_blank_value_keeps_existing_secret(self):
        key = APIKey(name="Telegram Bot")
        key.set_value("original-value")
        key.save()

        self.client.post(
            f"/panel/vault/api-keys/{key.pk}/edit/",
            {"name": "Telegram Bot", "notes": "updated", "value": ""},
        )
        key.refresh_from_db()
        self.assertEqual(key.get_value(), "original-value")
        self.assertEqual(key.notes, "updated")


class TwoFactorFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser("dev", "dev@example.com", "devpass12345")
        self.client.login(username="dev", password="devpass12345")

    def _enroll(self):
        self.client.get("/panel/vault/2fa/setup/")
        secret = self.client.session["pending_totp_secret"]
        code = pyotp.TOTP(secret).now()
        r = self.client.post("/panel/vault/2fa/setup/", {"code": code})
        self.assertRedirects(r, "/panel/vault/2fa/backup-codes/")
        return TOTPDevice.objects.get(user=self.user)

    def test_enrollment_creates_confirmed_device_and_backup_codes(self):
        device = self._enroll()
        self.assertTrue(device.confirmed)
        self.assertEqual(device.backup_codes.count(), 8)

    def test_wrong_setup_code_rejected(self):
        self.client.get("/panel/vault/2fa/setup/")
        r = self.client.post("/panel/vault/2fa/setup/", {"code": "000000"})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(TOTPDevice.objects.filter(user=self.user, confirmed=True).exists())

    def test_middleware_gates_panel_until_verified(self):
        device = self._enroll()
        session = self.client.session
        session["2fa_verified"] = False
        session.save()

        r = self.client.get("/panel/finance/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/panel/vault/2fa/verify/", r["Location"])

        code = pyotp.TOTP(device.get_secret()).now()
        r = self.client.post(
            "/panel/vault/2fa/verify/", {"code": code, "next": "/panel/finance/"}
        )
        self.assertRedirects(r, "/panel/finance/")

    def test_backup_code_is_single_use(self):
        device = self._enroll()
        session = self.client.session
        backup_codes_page = self.client.get("/panel/vault/2fa/backup-codes/")
        codes = re.findall(rb"[0-9A-F]{4}-[0-9A-F]{4}", backup_codes_page.content)
        raw_code = codes[0].decode()

        session["2fa_verified"] = False
        session.save()
        r = self.client.post(
            "/panel/vault/2fa/verify/", {"code": raw_code, "next": "/panel/finance/"}
        )
        self.assertRedirects(r, "/panel/finance/")
        self.assertEqual(
            BackupCode.objects.filter(device=device, used_at__isnull=False).count(), 1
        )

        session = self.client.session
        session["2fa_verified"] = False
        session.save()
        r = self.client.post(
            "/panel/vault/2fa/verify/", {"code": raw_code, "next": "/panel/finance/"}
        )
        self.assertEqual(r.status_code, 200)  # reused code rejected, stays on page

    def test_admin_reachable_without_2fa_verification(self):
        self._enroll()
        session = self.client.session
        session["2fa_verified"] = False
        session.save()
        r = self.client.get("/admin/")
        self.assertEqual(r.status_code, 200)

    def test_disable_requires_correct_password(self):
        self._enroll()
        r = self.client.post("/panel/vault/2fa/disable/", {"password": "wrong"})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(TOTPDevice.objects.filter(user=self.user).exists())

        r = self.client.post("/panel/vault/2fa/disable/", {"password": "devpass12345"})
        self.assertRedirects(r, "/panel/vault/")
        self.assertFalse(TOTPDevice.objects.filter(user=self.user).exists())


class BackupTests(TestCase):
    def setUp(self):
        User.objects.create_superuser("dev", "dev@example.com", "devpass12345")
        self.client.login(username="dev", password="devpass12345")
        self.addCleanup(self._cleanup_backups)

    def _cleanup_backups(self):
        for p in list_backups():
            p.unlink(missing_ok=True)

    def test_backup_db_command_creates_valid_file(self):
        call_command("backup_db")
        backups = list_backups()
        self.assertEqual(len(backups), 1)
        self.assertTrue(is_valid_backup_filename(backups[0].name))

    def test_download_rejects_invalid_filename(self):
        r = self.client.get("/panel/vault/backups/../../etc/passwd/download/")
        self.assertEqual(r.status_code, 404)

    def test_download_serves_valid_backup(self):
        call_command("backup_db")
        name = list_backups()[0].name
        r = self.client.get(f"/panel/vault/backups/{name}/download/")
        self.assertEqual(r.status_code, 200)

    def test_backup_not_reachable_under_static(self):
        call_command("backup_db")
        name = list_backups()[0].name
        r = self.client.get(f"/static/backups/{name}")
        self.assertEqual(r.status_code, 404)
