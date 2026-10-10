"""Celery task bodies and Google integration with real network blocked by mocks."""

from unittest.mock import Mock, patch

import requests
from django.test import TestCase, override_settings

from Users.models.users_models import CustomUser
from Users.tasks import reset_monthly_scores, send_otp_email, send_otp_sms
from Users.utils.google_auth import GoogleOIDC


class NotificationTaskTests(TestCase):
    @patch("Users.tasks.EmailMultiAlternatives")
    @patch("Users.tasks.render_to_string", return_value="<b>Code: 123456</b>")
    def test_email_task_sends_html_and_text(self, render_template, mail_class):
        send_otp_email.run("otp@example.com", "123456")
        render_template.assert_called_once_with("otp_email.html", {"otp_code": "123456"})
        mail_class.assert_called_once()
        args = mail_class.call_args.args
        self.assertIn("123456", args[1])
        self.assertEqual(args[3], ["otp@example.com"])
        mail_class.return_value.attach_alternative.assert_called_once_with(
            "<b>Code: 123456</b>", "text/html"
        )
        mail_class.return_value.send.assert_called_once_with()

    @patch("Users.tasks.requests.post")
    def test_sms_task_posts_pattern_with_timeout(self, post):
        post.return_value.json.return_value = {"meta": {"status": True}}
        actual = send_otp_sms.run("09123456789", "654321")
        kwargs = post.call_args.kwargs
        self.assertEqual(kwargs["timeout"], 15)
        self.assertEqual(kwargs["json"]["recipients"], ["09123456789"])
        self.assertEqual(kwargs["json"]["params"], {"code": "654321"})
        post.return_value.raise_for_status.assert_called_once_with()
        self.assertTrue(actual["meta"]["status"])

    @patch("Users.tasks.requests.post")
    def test_sms_provider_negative_status_raises_error(self, post):
        post.return_value.json.return_value = {"meta": {"status": False}}
        with self.assertRaises(RuntimeError):
            send_otp_sms.run("09123456789", "123456")

    def test_sms_task_has_expected_retry_configuration(self):
        # This checks task configuration only, not actual broker/worker retries.
        self.assertEqual(send_otp_sms.max_retries, 6)
        self.assertIn(requests.Timeout, send_otp_sms.autoretry_for)

    def test_monthly_score_reset_preserves_total_score(self):
        first = CustomUser.objects.create_user(phone="09125551111")
        second = CustomUser.objects.create_user(phone="09125551112")
        CustomUser.objects.filter(pk=first.pk).update(total_score=50, month_score=20)
        CustomUser.objects.filter(pk=second.pk).update(total_score=70, month_score=10)
        self.assertEqual(reset_monthly_scores.run(), {"status": "ok"})
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual((first.total_score, first.month_score), (50, 0))
        self.assertEqual((second.total_score, second.month_score), (70, 0))


@override_settings(
    GOOGLE_ISSUERS={"https://accounts.google.com"},
    GOOGLE_ALLOWED_CLIENT_IDS=["allowed-client"],
    GOOGLE_WEB_CLIENT_ID="allowed-client",
    GOOGLE_WEB_CLIENT_SECRET="not-a-real-secret",
    GOOGLE_TOKEN_ENDPOINT="https://oauth2.googleapis.com/token",
)
class GoogleOIDCTests(TestCase):
    def claims(self, **overrides):
        data = {
            "iss": "https://accounts.google.com",
            "email_verified": True,
            "aud": "allowed-client",
            "exp": 9999999999,
            "sub": "google-subject",
            "email": "user@example.com",
        }
        data.update(overrides)
        return data

    @patch("Users.utils.google_auth.google_id_token.verify_oauth2_token")
    def test_valid_claims_are_returned(self, google_verify):
        google_verify.return_value = self.claims()
        self.assertEqual(GoogleOIDC.verify_id_token("mock-token")["sub"], "google-subject")

    @patch("Users.utils.google_auth.google_id_token.verify_oauth2_token")
    def test_unverified_email_is_rejected(self, google_verify):
        google_verify.return_value = self.claims(email_verified=False)
        with self.assertRaisesRegex(ValueError, "Email not verified"):
            GoogleOIDC.verify_id_token("mock-token")

    @patch("Users.utils.google_auth.google_id_token.verify_oauth2_token")
    def test_wrong_issuer_is_rejected(self, google_verify):
        google_verify.return_value = self.claims(iss="https://bad.example")
        with self.assertRaisesRegex(ValueError, "Invalid issuer"):
            GoogleOIDC.verify_id_token("mock-token")

    @patch("Users.utils.google_auth.google_id_token.verify_oauth2_token")
    def test_expired_token_is_rejected(self, google_verify):
        google_verify.return_value = self.claims(exp=1)
        with self.assertRaisesRegex(ValueError, "Token expired"):
            GoogleOIDC.verify_id_token("mock-token")

    @patch("Users.utils.google_auth.requests.post")
    def test_code_exchange_uses_pkce_and_checks_http_status(self, post):
        post.return_value.json.return_value = {"id_token": "token"}
        result = GoogleOIDC.exchange_code_for_tokens("code", "verifier", "https://example.com/cb")
        self.assertEqual(result, {"id_token": "token"})
        self.assertEqual(post.call_args.kwargs["timeout"], 10)
        self.assertEqual(post.call_args.kwargs["data"]["code_verifier"], "verifier")
        post.return_value.raise_for_status.assert_called_once_with()
