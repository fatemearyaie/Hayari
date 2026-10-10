"""RED tests for observable defects in the supplied code.

@expectedFailure means the test describes DESIRED behavior but current code is known
not to satisfy it. Removing the decorator after a fix turns it into a normal
regression test. Do not interpret an expected failure as a passing feature.
"""

from unittest import expectedFailure
from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from Users.models.transactions_models import Transaction
from Users.models.users_models import CustomUser, OTP
from Users.serializers.users_serializers import OTPVerifySerializer
from Users.utils.google_auth import GoogleOIDC


class KnownOTPProblems(TestCase):
    @expectedFailure
    def test_unknown_otp_should_produce_validation_error_not_attribute_error(self):
        serializer = OTPVerifySerializer(data={"username": "09120000000", "otp": "123456"})
        # Current code accesses otp_instance.otp without checking for None.
        self.assertFalse(serializer.is_valid())
        self.assertIn("اخطار", serializer.errors)


class KnownGoogleProblems(TestCase):
    @expectedFailure
    @override_settings(
        GOOGLE_ISSUERS={"https://accounts.google.com"},
        GOOGLE_ALLOWED_CLIENT_IDS=["our-client"],
    )
    @patch("Users.utils.google_auth.google_id_token.verify_oauth2_token")
    def test_wrong_audience_without_azp_should_be_rejected(self, verify):
        verify.return_value = {
            "iss": "https://accounts.google.com",
            "email_verified": True,
            "aud": "untrusted-client",
            "exp": 9999999999,
        }
        # Current condition rejects wrong aud only when invalid azp is present.
        with self.assertRaisesRegex(ValueError, "Audience not allowed"):
            GoogleOIDC.verify_id_token("mock-token")


class KnownPaymentProblems(TestCase):
    @expectedFailure
    def test_insufficient_balance_should_not_mark_withdrawal_complete(self):
        user = CustomUser.objects.create_user(phone="09127770000")
        tx = Transaction.objects.create(
            user=user, amount=900,
            transaction_type=Transaction.TransactionType.Withdraw,
        )
        tx.transaction_status = Transaction.TransactionStatus.COMPLETE
        tx.save(update_fields=["transaction_status"])
        tx.refresh_from_db()
        # Current transaction pre_save signal leaves transaction COMPLETE.
        self.assertNotEqual(tx.transaction_status, Transaction.TransactionStatus.COMPLETE)

    @expectedFailure
    def test_invalid_amount_should_return_http_400(self):
        user = CustomUser.objects.create_user(phone="09127770001")
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post(
            "/api/v1/users/zarinpal/start/", {"amount": "0"}, format="json"
        )
        # Current view sends status 200 with an error object.
        self.assertEqual(response.status_code, 400)


class KnownJWTCachingProblems(TestCase):
    @expectedFailure
    @override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
    def test_disabled_user_should_not_be_accepted_from_stale_jwt_cache(self):
        from django.core.cache import cache
        from rest_framework.exceptions import AuthenticationFailed
        from Users.services.token_cache import CacheJWTAuthentication

        user = CustomUser.objects.create_user(phone="09127770002")
        cache.set(f"user:obj:{user.pk}", user)
        CustomUser.objects.filter(pk=user.pk).update(is_active=False)
        # The current implementation returns cached object without rechecking is_active.
        with self.assertRaises(AuthenticationFailed):
            CacheJWTAuthentication().get_user({"user_id": user.pk})


class KnownDonationProblems(TestCase):
    @expectedFailure
    @patch("Funds.services.donation.send_notification")
    @patch("Funds.services.donation.bump_version")
    @patch("Funds.signals.cache_signals.bump_version")
    @patch("Users.views.transactions_views.requests.post")
    def test_verified_donation_should_create_only_one_donor(
        self, provider_post, signal_bump, donation_bump, send_notification
    ):
        from Funds.models import Donor, FundRaising
        from Users.models.users_models import City, Country
        from rest_framework.test import APIClient

        user = CustomUser.objects.create_user(phone="09127770003")
        country = Country.objects.create(name="Country")
        city = City.objects.create(name="City", country=country)
        fundraising = FundRaising.objects.create(
            city=city, title="Cause", description="Help",
            total_amount=10000, each_don_xp=5,
        )
        tx = Transaction.objects.create(
            user=user, fundraising=fundraising, amount=100,
            transaction_type=Transaction.TransactionType.Withdraw,
        )
        provider_post.return_value.json.return_value = {"data": {"code": 100}}
        response = APIClient().get(
            "/api/v1/users/zarinpal/verify/",
            {"transaction_id": tx.pk, "Authority": "sample", "Status": "OK"},
        )
        self.assertEqual(response.status_code, 200)
        # Current view creates Donor, then donate_fundraising creates another Donor.
        self.assertEqual(Donor.objects.filter(user=user, fundraising=fundraising).count(), 1)
