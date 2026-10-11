from decimal import Decimal, InvalidOperation
from unittest.mock import Mock, patch

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import Http404
from django.test import Client, TestCase, override_settings
from rest_framework_simplejwt.tokens import AccessToken

from Funds.models import Donor, FundImage, FundRaising
from Funds.serializers.funds_serializers import (
    DonateSerializer,
    FundRaisingDetailSerializer,
    FundRaisingSerializer,
)
from Funds.services.donation import donate_fundraising
from Funds.services.list_cache import bump_version, cached_list
from Users.models import City, Country, CustomUser, Transaction, XPTracker
from Users.models.users_models import City as UserCity


def create_user(email, balance=Decimal("0")):
    return CustomUser.objects.create_user(email=email, balance=balance)


def create_city(name="Tehran"):
    country = Country.objects.create(name=f"Country {name}")
    return City.objects.create(name=name, country=country, is_available=True)


def auth_headers(user):
    token = AccessToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


def image_file(name="fund.png"):
    return SimpleUploadedFile(name, b"fund-image", content_type="image/png")


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "funds-tests",
        }
    }
)
class FundsModelAndServiceTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = create_user("donor@example.com", balance=Decimal("1000"))
        self.other_user = create_user("other-donor@example.com")
        self.city = create_city()
        self.fundraising = FundRaising.objects.create(
            city=self.city,
            title="Community project",
            description="A project description",
            total_amount=10000,
            each_don_xp=7,
            website="https://example.com",
        )
        self.media_dir = __import__("tempfile").TemporaryDirectory()
        self.media_override = override_settings(MEDIA_ROOT=self.media_dir.name)
        self.media_override.enable()
        self.addCleanup(self.media_override.disable)
        self.addCleanup(self.media_dir.cleanup)

    def test_donor_place_starts_at_one_and_increments_per_fundraising(self):
        first = Donor.objects.create(user=self.user, fundraising=self.fundraising, amount=100, xp=7)
        second = Donor.objects.create(user=self.other_user, fundraising=self.fundraising, amount=200, xp=7)
        separate = FundRaising.objects.create(
            city=self.city,
            title="Separate project",
            description="Another description",
            total_amount=5000,
            each_don_xp=2,
        )
        third = Donor.objects.create(user=self.user, fundraising=separate, amount=50, xp=2)
        self.assertEqual(first.place, 1)
        self.assertEqual(second.place, 2)
        self.assertEqual(third.place, 1)

    def test_fundraising_serializers_include_nested_city_and_images(self):
        FundImage.objects.create(Fund=self.fundraising, image=image_file())
        list_data = FundRaisingSerializer(self.fundraising).data
        detail_data = FundRaisingDetailSerializer(self.fundraising).data
        self.assertEqual(list_data["title"], "Community project")
        self.assertEqual(list_data["city"]["name"], "Tehran")
        self.assertEqual(len(list_data["images"]), 1)
        self.assertIn("is_available", list_data)
        self.assertNotIn("id", detail_data)
        self.assertNotIn("is_available", detail_data)

    def test_donate_serializer_requires_amount(self):
        serializer = DonateSerializer(data={})
        self.assertFalse(serializer.is_valid())
        self.assertIn("amount", serializer.errors)

    def test_cached_list_computes_once_then_uses_cached_value(self):
        compute = Mock(return_value=[{"id": 1}])
        first = cached_list("fundraising", "fundraising:1:ver", {"page": ["1"]}, compute)
        second = cached_list("fundraising", "fundraising:1:ver", {"page": ["1"]}, compute)
        self.assertEqual(first, [{"id": 1}])
        self.assertEqual(second, [{"id": 1}])
        compute.assert_called_once_with()

    def test_bump_version_initializes_missing_key_and_increments_existing_key(self):
        bump_version("fundraising:missing:ver")
        self.assertEqual(cache.get("fundraising:missing:ver"), 2)
        cache.set("fundraising:existing:ver", 4)
        bump_version("fundraising:existing:ver")
        self.assertEqual(cache.get("fundraising:existing:ver"), 5)

    def test_donor_signals_bump_cache_version_on_create_and_delete(self):
        key = f"fundraising:{self.fundraising.id}:donors:ver"
        cache.set(key, 4)
        donor = Donor.objects.create(user=self.user, fundraising=self.fundraising, amount=100, xp=7)
        self.assertEqual(cache.get(key), 5)
        donor.delete()
        self.assertEqual(cache.get(key), 6)

    @patch("Funds.services.donation.send_notification")
    @patch("Funds.services.donation.bump_version", wraps=bump_version)
    def test_donation_updates_fundraising_and_cross_app_side_effects(self, bump, send_notification):
        key = f"fundraising:{self.fundraising.id}:donors:ver"
        cache.set(key, 4)
        donor = donate_fundraising(
            user=self.user,
            fundraising_id=self.fundraising.id,
            amount="250",
        )
        self.assertEqual(donor.amount, Decimal("250"))
        self.assertEqual(donor.xp, 7)
        self.assertEqual(donor.place, 1)
        self.fundraising.refresh_from_db()
        self.assertEqual(self.fundraising.current_donation, Decimal("250"))
        self.assertTrue(Transaction.objects.filter(
            user=self.user,
            fundraising=self.fundraising,
            amount=250,
            transaction_type=Transaction.TransactionType.Withdraw,
        ).exists())
        transaction = Transaction.objects.get(
            user=self.user,
            fundraising=self.fundraising,
            amount=250,
            transaction_type=Transaction.TransactionType.Withdraw,
        )
        self.assertEqual(transaction.transaction_status, Transaction.TransactionStatus.COMPLETE)
        self.assertEqual(transaction.payment_gateway, Transaction.PaymentGateWay.app)
        self.assertEqual(transaction.balance_after, Decimal("1000"))
        self.assertTrue(XPTracker.objects.filter(
            user=self.user,
            xp=7,
            reason=XPTracker.Reason.donation,
        ).exists())
        self.assertEqual(cache.get(key), 6)
        bump.assert_called_once_with(f"fundraising:{self.fundraising.id}:donors:ver")
        send_notification.assert_called_once_with(user=self.user, message_type="donation_success")

    def test_donation_missing_fundraising_is_atomic(self):
        with self.assertRaises(Http404):
            donate_fundraising(user=self.user, fundraising_id=999999, amount=100)
        self.assertFalse(Donor.objects.exists())
        self.assertFalse(Transaction.objects.filter(user=self.user).exists())
        self.assertFalse(XPTracker.objects.filter(user=self.user).exists())

    def test_donation_invalid_decimal_does_not_create_rows(self):
        with self.assertRaises(InvalidOperation):
            donate_fundraising(user=self.user, fundraising_id=self.fundraising.id, amount="not-a-number")
        self.fundraising.refresh_from_db()
        self.assertEqual(self.fundraising.current_donation, Decimal("0"))
        self.assertFalse(Donor.objects.exists())
        self.assertFalse(Transaction.objects.filter(user=self.user).exists())
        self.assertFalse(XPTracker.objects.filter(user=self.user).exists())


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "funds-http-tests",
        }
    }
)
class FundsHttpTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = create_user("funds-http@example.com")
        self.other_user = create_user("funds-http-other@example.com")
        self.city = create_city("Shiraz")
        self.fundraising = FundRaising.objects.create(
            city=self.city,
            title="HTTP fundraising",
            description="HTTP description",
            total_amount=9000,
            each_don_xp=5,
        )

    def test_fundraising_list_and_detail_are_public(self):
        list_response = self.client.get("/api/v1/funds/fundraisings/")
        detail_response = self.client.get(f"/api/v1/funds/fundraisings/{self.fundraising.id}/")
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(list_response.json()["data"]["results"][0]["title"], "HTTP fundraising")
        self.assertEqual(detail_response.json()["data"]["title"], "HTTP fundraising")

    def test_donation_history_and_analytics_require_authentication(self):
        self.assertEqual(self.client.get("/api/v1/funds/donation/").status_code, 401)
        self.assertEqual(
            self.client.get("/api/v1/funds/donation/fundraising/1/donors/").status_code,
            401,
        )
        self.assertEqual(
            self.client.get(f"/api/v1/funds/donation/user/{self.user.id}/donations/").status_code,
            401,
        )
        self.assertEqual(self.client.get("/api/v1/funds/analytics/").status_code, 401)

    @patch("Funds.services.donation.send_notification")
    def test_authenticated_donation_and_user_scoped_history(self, send_notification):
        Donor.objects.create(user=self.other_user, fundraising=self.fundraising, amount=80, xp=5)
        response = self.client.post(
            f"/api/v1/funds/donation/fundraising/{self.fundraising.id}/donate/",
            {"amount": "125"},
            content_type="application/json",
            **auth_headers(self.user),
        )
        self.assertEqual(response.status_code, 201)
        history = self.client.get("/api/v1/funds/donation/", **auth_headers(self.user))
        self.assertEqual(history.status_code, 200)
        history_results = history.json()["data"]["results"]
        self.assertEqual(len(history_results), 1)
        self.assertEqual(history_results[0]["amount"], "125")
        self.assertEqual(history_results[0]["user"]["username"], self.user.username)
        send_notification.assert_called_once()

    def test_donation_validation_and_missing_target_fail_without_mutation(self):
        invalid = self.client.post(
            f"/api/v1/funds/donation/fundraising/{self.fundraising.id}/donate/",
            {"amount": "bad"},
            content_type="application/json",
            **auth_headers(self.user),
        )
        missing = self.client.post(
            "/api/v1/funds/donation/fundraising/999999/donate/",
            {"amount": "100"},
            content_type="application/json",
            **auth_headers(self.user),
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(missing.status_code, 404)
        self.assertFalse(Donor.objects.exists())

    def test_fundraising_donors_user_donations_and_analytics(self):
        donor = Donor.objects.create(user=self.user, fundraising=self.fundraising, amount=100, xp=5)
        other_donor = Donor.objects.create(user=self.other_user, fundraising=self.fundraising, amount=200, xp=5)
        donors = self.client.get(
            f"/api/v1/funds/donation/fundraising/{self.fundraising.id}/donors/",
            **auth_headers(self.user),
        )
        user_donations = self.client.get(
            f"/api/v1/funds/donation/user/{self.user.id}/donations/",
            **auth_headers(self.user),
        )
        analytics = self.client.get("/api/v1/funds/analytics/", **auth_headers(self.user))
        other_analytics = self.client.get(
            f"/api/v1/funds/analytics/{self.other_user.id}/",
            **auth_headers(self.user),
        )
        self.assertEqual(donors.status_code, 200)
        self.assertEqual(user_donations.status_code, 200)
        self.assertEqual(analytics.status_code, 200)
        self.assertEqual(other_analytics.status_code, 200)
        donor_results = donors.json()["data"]["results"]
        donation_results = user_donations.json()["data"]["results"]
        self.assertEqual({item["user"]["id"] for item in donor_results}, {self.user.id, self.other_user.id})
        self.assertEqual(len(donation_results), 1)
        self.assertEqual(analytics.json()["data"], {"count": 1, "total_amount": 100})
        self.assertEqual(other_analytics.json()["data"], {"count": 1, "total_amount": 200})
        self.assertEqual(donor.place, 1)
        self.assertEqual(other_donor.place, 2)

    def test_empty_analytics_returns_zero_values(self):
        response = self.client.get("/api/v1/funds/analytics/", **auth_headers(self.user))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"], {"count": 0, "total_amount": 0})
