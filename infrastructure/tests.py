import datetime

from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import Domain, SSLCertificate


class DomainExpiryTests(TestCase):
    def test_expired_domain(self):
        d = Domain.objects.create(
            name="old.uz", expiration_date=datetime.date.today() - datetime.timedelta(days=1)
        )
        self.assertTrue(d.is_expired)
        self.assertFalse(d.is_expiring_soon)

    def test_expiring_soon_domain(self):
        d = Domain.objects.create(
            name="soon.uz", expiration_date=datetime.date.today() + datetime.timedelta(days=10)
        )
        self.assertFalse(d.is_expired)
        self.assertTrue(d.is_expiring_soon)

    def test_far_future_domain_not_flagged(self):
        d = Domain.objects.create(
            name="safe.uz", expiration_date=datetime.date.today() + datetime.timedelta(days=200)
        )
        self.assertFalse(d.is_expired)
        self.assertFalse(d.is_expiring_soon)

    def test_expiring_soon_queryset(self):
        Domain.objects.create(
            name="soon.uz", expiration_date=datetime.date.today() + datetime.timedelta(days=10)
        )
        Domain.objects.create(
            name="safe.uz", expiration_date=datetime.date.today() + datetime.timedelta(days=200)
        )
        names = list(Domain.objects.expiring_soon().values_list("name", flat=True))
        self.assertEqual(names, ["soon.uz"])


class SSLCertificateValidationTests(TestCase):
    def test_requires_domain_or_name(self):
        cert = SSLCertificate(expiration_date=datetime.date.today())
        with self.assertRaises(ValidationError):
            cert.full_clean()

    def test_valid_with_name_only(self):
        cert = SSLCertificate(name="Freeform cert", expiration_date=datetime.date.today())
        cert.full_clean()  # should not raise

    def test_valid_with_domain_only(self):
        domain = Domain.objects.create(
            name="withcert.uz", expiration_date=datetime.date.today() + datetime.timedelta(days=30)
        )
        cert = SSLCertificate(domain=domain, expiration_date=datetime.date.today())
        cert.full_clean()  # should not raise
