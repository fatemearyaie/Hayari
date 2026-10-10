"""HTTP endpoints for OTP, Google auth, user profile, city list and splash."""

from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from Users.models.banner_models import LoginEntry
from Users.models.users_models import CustomUser, OTP


class APIBase(TestCase):
    def setUp(self):
        self.client = APIClient()


class OTPAPItests(APIBase):
    @patch("Users.views.users_views.send_otp_sms.delay")
    @patch("Users.views.users_views.send_otp_email.delay")
    def test_auth_requests_sms_for_phone(self, email_delay, sms_delay):
        response = self.client.post(
            "/api/v1/users/auth/", {"username": " 0912-345 6789 "}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        otp = OTP.objects.get()
        self.assertEqual(otp.phone, "09123456789")
        sms_delay.assert_called_once_with("09123456789", otp.otp)
        email_delay.assert_not_called()

    @patch("Users.views.users_views.send_otp_sms.delay")
    @patch("Users.views.users_views.send_otp_email.delay")
    def test_auth_requests_email_for_email_address(self, email_delay, sms_delay):
        response = self.client.post("/api/v1/users/auth/", {"username": "  Me@Example.COM  "}, format="json")
        self.assertEqual(response.status_code, 200)
        otp = OTP.objects.get()
        self.assertEqual(otp.email, "me@example.com")
        email_delay.assert_called_once_with("me@example.com", otp.otp)
        sms_delay.assert_not_called()

    @patch("Users.views.users_views.send_otp_sms.delay")
    @patch("Users.views.users_views.send_otp_email.delay")
    def test_auth_rejects_missing_username_without_creating_otp(self, email_delay, sms_delay):
        response = self.client.post("/api/v1/users/auth/", {}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(OTP.objects.exists())
        sms_delay.assert_not_called()
        email_delay.assert_not_called()

    def test_verify_otp_creates_user_and_returns_tokens(self):
        otp = OTP.objects.create(phone="09122221111", otp="123456")
        response = self.client.post("/api/v1/users/auth/register/",{"username": otp.phone, "otp": "123456"}, format="json",)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["username"], otp.phone)
        self.assertTrue(response.data["created"])
        self.assertIn("access_token", response.data)
        self.assertIn("refresh_token", response.data)
        otp.refresh_from_db()
        self.assertTrue(otp.is_used)

    def test_verify_rejects_wrong_code(self):
        otp = OTP.objects.create(phone="09122221112", otp="123456")
        response = self.client.post("/api/v1/users/auth/register/",{"username": otp.phone, "otp": "000000"}, format="json",)
        self.assertEqual(response.status_code, 400)
        otp.refresh_from_db()
        self.assertFalse(otp.is_used)


class ProfileAPItests(APIBase):
    def setUp(self):
        super().setUp()
        self.user = CustomUser.objects.create_user(phone="09123330000", name="Old name")

    def test_profile_requires_authentication(self):
        response = self.client.get("/api/v1/users/profile/")
        self.assertIn(response.status_code, (401, 403))

    def test_profile_get_returns_current_user(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/v1/users/profile/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["phone"], self.user.phone)
        self.assertEqual(response.data["name"], "Old name")

    def test_profile_patch_updates_name_but_not_balance(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch("/api/v1/users/profile/", {"name": "Updated", "balance": 99999}, format="json")
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.name, "Updated")
        self.assertEqual(self.user.balance, 0)

    def test_splash_requires_authentication(self):
        response = self.client.get("/api/v1/users/splash/")
        self.assertIn(response.status_code, (401, 403))
        self.assertEqual(LoginEntry.objects.count(), 0)

    def test_splash_creates_login_entry(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/v1/users/splash/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(LoginEntry.objects.filter(user=self.user).count(), 1)


class CityAndGoogleAPItests(APIBase):
    @patch("Users.views.users_views.get_cached_cities", return_value=[{"id": 1, "name": "City"}])
    def test_cities_uses_cache_service(self, get_cities):
        response = self.client.get("/api/v1/users/cities/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [{"id": 1, "name": "City"}])
        get_cities.assert_called_once_with()

    def test_google_rejects_request_without_token_or_code(self):
        response = self.client.post("/api/v1/users/auth/google/", {}, format="json")
        self.assertEqual(response.status_code, 400)

    @patch("Users.views.users_views.GoogleOIDC.verify_id_token")
    def test_google_creates_user_when_email_is_new(self, verify_token):
        verify_token.return_value = {"sub": "sub-1", "email": "new@example.com"}
        response = self.client.post("/api/v1/users/auth/google/", {"id_token": "fake-token"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["is_new"])
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertTrue(CustomUser.objects.filter(email="new@example.com").exists())
        verify_token.assert_called_once_with("fake-token")

    @patch("Users.views.users_views.GoogleOIDC.verify_id_token")
    def test_google_reuses_existing_account_and_reactivates_it(self, verify_token):
        user = CustomUser.objects.create_user(email="existing@example.com", is_active=False)
        verify_token.return_value = {"sub": "sub-2", "email": user.email}
        response = self.client.post("/api/v1/users/auth/google/", {"id_token": "fake-token"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["is_new"])
        self.assertEqual(CustomUser.objects.count(), 1)
        user.refresh_from_db()
        self.assertTrue(user.is_active)

    @patch("Users.views.users_views.GoogleOIDC.exchange_code_for_tokens")
    @patch("Users.views.users_views.GoogleOIDC.verify_id_token")
    def test_google_supports_auth_code_exchange(self, verify_token, exchange):
        exchange.return_value = {"id_token": "exchanged-token"}
        verify_token.return_value = {"sub": "sub-3", "email": "code@example.com"}
        response = self.client.post("/api/v1/users/auth/google/", {"code": "some-code", "code_verifier": "pkce","redirect_uri": "https://example.com/callback",}, format="json")
        self.assertEqual(response.status_code, 200)
        exchange.assert_called_once_with(code="some-code", code_verifier="pkce",redirect_uri="https://example.com/callback",)
        verify_token.assert_called_once_with("exchanged-token")
