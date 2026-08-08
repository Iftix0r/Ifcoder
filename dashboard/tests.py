from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase


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
        self.assertContains(r, "Juda ko'p")

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
