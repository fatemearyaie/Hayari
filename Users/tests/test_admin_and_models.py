"""Lightweight checks for Users admin display helpers and remaining models."""

from django.contrib import admin
from django.test import TestCase

from Users.admin import CustomUserAdmin, HomeBannerAdmin, transactionAdmin
from Users.models.banner_models import Banner, HomeBanner, LoginEntry, Version
from Users.models.transactions_models import Transaction
from Users.models.users_models import City, Country, CustomUser


class AdditionalModelTests(TestCase):
    def test_banner_string_is_title(self):
        banner = Banner.objects.create(
            title="Campaign", image="banners/campaign.jpg", url="https://example.com",
        )
        self.assertEqual(str(banner), "Campaign")

    def test_version_defaults_to_first_version_and_non_forced(self):
        version = Version.objects.create()
        self.assertEqual(version.version_number, 1)
        self.assertFalse(version.is_force)
        self.assertEqual(version.force_min_version, 1)

    def test_city_country_names_are_string_representations(self):
        country = Country.objects.create(name="North")
        city = City.objects.create(name="Main", country=country)
        self.assertEqual(str(country), "North")
        self.assertEqual(str(city), "Main")

    def test_login_entry_links_a_specific_user(self):
        user = CustomUser.objects.create_user(phone="09128880001")
        entry = LoginEntry.objects.create(user=user)
        self.assertEqual(entry.user_id, user.pk)


class AdminFormattingTests(TestCase):
    def test_user_admin_formats_balance_for_display(self):
        user = CustomUser.objects.create_user(phone="09128880002")
        user.balance = 1234567
        model_admin = CustomUserAdmin(CustomUser, admin.site)
        self.assertEqual(model_admin.formatted_balance(user), "1,234,567")

    def test_transaction_admin_formats_amount_for_display(self):
        user = CustomUser.objects.create_user(phone="09128880003")
        tx = Transaction.objects.create(user=user, amount=123456)
        model_admin = transactionAdmin(Transaction, admin.site)
        self.assertEqual(model_admin.formatted_amount(tx), "123,456")

    def test_home_banner_admin_truncates_long_message(self):
        banner = HomeBanner(message="x" * 60, banner="banners/home/b.jpg")
        model_admin = HomeBannerAdmin(HomeBanner, admin.site)
        self.assertEqual(model_admin.short_message(banner), "x" * 50 + "...")

    def test_home_banner_admin_keeps_short_message(self):
        banner = HomeBanner(message="Hello", banner="banners/home/b.jpg")
        model_admin = HomeBannerAdmin(HomeBanner, admin.site)
        self.assertEqual(model_admin.short_message(banner), "Hello")
