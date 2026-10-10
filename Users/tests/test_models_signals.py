"""ORM models, state transitions, and pre_save/post_save cache invalidation."""

from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from Users.models.banner_models import Banner
from Users.models.transactions_models import Transaction
from Users.models.users_models import City, Country, CustomUser, OTP, XPTracker


class OTPModelTests(TestCase):
    def test_default_code_has_six_digits_and_is_unused(self):
        otp = OTP.objects.create(email="otp@example.com")
        self.assertEqual(len(otp.otp), 6)
        self.assertTrue(otp.otp.isdigit())
        self.assertFalse(otp.is_used)

    def test_five_minute_expiration(self):
        otp = OTP.objects.create(email="expiry@example.com")
        self.assertFalse(otp.is_expired())
        OTP.objects.filter(pk=otp.pk).update(created_at=timezone.now() - timedelta(minutes=6))
        otp.refresh_from_db()
        self.assertTrue(otp.is_expired())


class XPTrackerSignalTests(TestCase):
    def test_new_xp_record_updates_user_totals_and_snapshot(self):
        user = CustomUser.objects.create_user(phone="09124440001")
        tracker = XPTracker.objects.create(user=user, xp=25)
        user.refresh_from_db()
        tracker.refresh_from_db()
        self.assertEqual(user.total_score, 25)
        self.assertEqual(user.month_score, 25)
        self.assertEqual(tracker.total_xp_after, 25)
        self.assertEqual(tracker.month_xp_after, 25)

    def test_editing_xp_record_does_not_count_xp_a_second_time(self):
        user = CustomUser.objects.create_user(phone="09124440002")
        tracker = XPTracker.objects.create(user=user, xp=5)
        tracker.reason = XPTracker.Reason.donation
        tracker.save(update_fields=["reason"])
        user.refresh_from_db()
        self.assertEqual(user.total_score, 5)


class TransactionSignalTests(TestCase):
    def test_deposit_credits_wallet_when_it_becomes_complete(self):
        user = CustomUser.objects.create_user(phone="09124440003")
        tx = Transaction.objects.create(
            user=user, amount=150, transaction_type=Transaction.TransactionType.Deposit
        )
        user.refresh_from_db()
        self.assertEqual(user.balance, 0)
        tx.transaction_status = Transaction.TransactionStatus.COMPLETE
        tx.save(update_fields=["transaction_status"])
        user.refresh_from_db()
        self.assertEqual(user.balance, 150)

    def test_duplicate_complete_save_does_not_credit_wallet_twice(self):
        user = CustomUser.objects.create_user(phone="09124440004")
        tx = Transaction.objects.create(
            user=user, amount=70, transaction_type=Transaction.TransactionType.Deposit
        )
        tx.transaction_status = Transaction.TransactionStatus.COMPLETE
        tx.save(update_fields=["transaction_status"])
        tx.save(update_fields=["transaction_status"])
        user.refresh_from_db()
        self.assertEqual(user.balance, 70)

    def test_withdrawal_reduces_wallet_when_funds_exist(self):
        user = CustomUser.objects.create_user(phone="09124440005")
        user.balance = 100
        user.save(update_fields=["balance"])
        tx = Transaction.objects.create(
            user=user, amount=40, transaction_type=Transaction.TransactionType.Withdraw
        )
        tx.transaction_status = Transaction.TransactionStatus.COMPLETE
        tx.save(update_fields=["transaction_status"])
        user.refresh_from_db()
        self.assertEqual(user.balance, 60)

    def test_canceled_transaction_does_not_change_balance(self):
        user = CustomUser.objects.create_user(phone="09124440006")
        tx = Transaction.objects.create(
            user=user, amount=40, transaction_type=Transaction.TransactionType.Deposit
        )
        tx.transaction_status = Transaction.TransactionStatus.CANCEL
        tx.save(update_fields=["transaction_status"])
        user.refresh_from_db()
        self.assertEqual(user.balance, 0)


class CityCacheInvalidationSignalTests(TestCase):
    def setUp(self):
        self.country = Country.objects.create(name="Country")

    @patch("Users.signals.cache_signals.cache.delete")
    def test_creating_available_city_invalidates_cache(self, delete):
        City.objects.create(name="Visible", country=self.country, is_available=True)
        delete.assert_called_with("city:all")

    @patch("Users.signals.cache_signals.cache.delete")
    def test_creating_unavailable_city_does_not_invalidate_cache(self, delete):
        City.objects.create(name="Hidden", country=self.country, is_available=False)
        delete.assert_not_called()

    @patch("Users.signals.cache_signals.cache.delete")
    def test_changing_city_availability_invalidates_cache(self, delete):
        city = City.objects.create(name="Changing", country=self.country, is_available=False)
        delete.reset_mock()
        city.is_available = True
        city.save(update_fields=["is_available"])
        delete.assert_called_with("city:all")

    @patch("Users.signals.cache_signals.cache.delete")
    def test_deleting_city_invalidates_cache(self, delete):
        city = City.objects.create(name="Deleted", country=self.country, is_available=True)
        delete.reset_mock()
        city.delete()
        delete.assert_called_with("city:all")


class BannerCacheInvalidationSignalTests(TestCase):
    def make_banner(self, active=True):
        return Banner.objects.create(
            title="Banner", image="banners/sample.png",
            url="https://example.com", is_active=active,
        )

    @patch("Users.signals.cache_signals.cache.delete")
    def test_creating_active_banner_invalidates_cache(self, delete):
        self.make_banner(active=True)
        delete.assert_called_with("banner:active")

    @patch("Users.signals.cache_signals.cache.delete")
    def test_creating_inactive_banner_does_not_invalidate_cache(self, delete):
        self.make_banner(active=False)
        delete.assert_not_called()

    @patch("Users.signals.cache_signals.cache.delete")
    def test_changing_banner_active_flag_invalidates_cache(self, delete):
        banner = self.make_banner(active=False)
        delete.reset_mock()
        banner.is_active = True
        banner.save(update_fields=["is_active"])
        delete.assert_called_with("banner:active")

    @patch("Users.signals.cache_signals.cache.delete")
    def test_deleting_banner_invalidates_cache(self, delete):
        banner = self.make_banner(active=True)
        delete.reset_mock()
        banner.delete()
        delete.assert_called_with("banner:active")


class DatabaseConstraintTests(TestCase):
    def test_user_requires_phone_or_email_at_database_level(self):
        from django.db import IntegrityError, transaction as db_transaction

        with self.assertRaises(IntegrityError):
            with db_transaction.atomic():
                CustomUser.objects.create(username="no-contact")

    def test_otp_requires_phone_or_email_at_database_level(self):
        from django.db import IntegrityError, transaction as db_transaction

        with self.assertRaises(IntegrityError):
            with db_transaction.atomic():
                OTP.objects.create(phone=None, email=None)

    def test_city_name_must_be_unique_within_same_country(self):
        from django.db import IntegrityError, transaction as db_transaction

        country = Country.objects.create(name="Country")
        City.objects.create(country=country, name="Main")
        with self.assertRaises(IntegrityError):
            with db_transaction.atomic():
                City.objects.create(country=country, name="Main")

    def test_same_city_name_is_valid_in_different_countries(self):
        first = Country.objects.create(name="First")
        second = Country.objects.create(name="Second")
        City.objects.create(country=first, name="Main")
        City.objects.create(country=second, name="Main")
        self.assertEqual(City.objects.filter(name="Main").count(), 2)
