"""DRF serializer contracts: validation, database writes, and field visibility."""

from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from Users.models.banner_models import HomeBanner
from Users.models.transactions_models import Transaction
from Users.models.users_models import City, Country, CustomUser, OTP
from Users.serializers.banner_serializers import HomeBannerSerializer
from Users.serializers.transactions_serializers import TransactionSerializer
from Users.serializers.users_serializers import (
    CitySerializer,
    GoogleAuthSerializer,
    OTPGeneratorSerializer,
    OTPVerifySerializer,
    OtherUserProfileSerializer,
    RegisterSerializer,
    UserProfileSerializer,
)


class OTPGeneratorSerializerTests(TestCase):
    def test_phone_is_normalized(self):
        serializer = OTPGeneratorSerializer(data={"username": "+98 912-345 6789"})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["phone"], "989123456789")
        self.assertIsNone(serializer.validated_data["email"])

    def test_email_is_normalized(self):
        serializer = OTPGeneratorSerializer(data={"username": "  F@example.COM  "})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["email"], "f@example.com")
        self.assertIsNone(serializer.validated_data["phone"])

    def test_empty_username_is_rejected(self):
        serializer = OTPGeneratorSerializer(data={"username": ""})
        self.assertFalse(serializer.is_valid())
        self.assertIn("username", serializer.errors)

    def test_missing_username_is_rejected(self):
        serializer = OTPGeneratorSerializer(data={})
        self.assertFalse(serializer.is_valid())
        self.assertIn("username", serializer.errors)

    def test_overlong_username_is_rejected(self):
        serializer = OTPGeneratorSerializer(data={"username": "x" * 51})
        self.assertFalse(serializer.is_valid())
        self.assertIn("username", serializer.errors)

    def test_save_creates_otp_with_phone_and_unused_state(self):
        serializer = OTPGeneratorSerializer(data={"username": "09123456789"})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        otp = serializer.save()
        saved = OTP.objects.get(pk=otp.pk)
        self.assertEqual(OTP.objects.count(), 1)
        self.assertEqual(saved.phone, "09123456789")
        self.assertIsNone(saved.email)
        self.assertFalse(saved.is_used)
        self.assertEqual(len(saved.otp), 6)

    def test_save_creates_otp_with_email(self):
        serializer = OTPGeneratorSerializer(data={"username": "USER@EXAMPLE.COM"})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        otp = serializer.save()
        self.assertEqual(otp.email, "user@example.com")
        self.assertIsNone(otp.phone)


class OTPVerifySerializerTests(TestCase):
    def test_valid_otp_creates_user_and_marks_code_used(self):
        otp = OTP.objects.create(phone="09125550101", otp="123456")
        serializer = OTPVerifySerializer(data={"username": otp.phone, "otp": "123456"})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        result = serializer.save()
        otp.refresh_from_db()
        self.assertTrue(otp.is_used)
        self.assertEqual(result["username"], otp.phone)
        self.assertTrue(result["created"])
        self.assertTrue(result["access_token"])
        self.assertTrue(result["refresh_token"])
        self.assertTrue(CustomUser.objects.filter(username=otp.phone).exists())

    def test_valid_otp_reuses_existing_user(self):
        user = CustomUser.objects.create_user(email="reuse@example.com")
        OTP.objects.create(email="reuse@example.com", otp="123456")
        serializer = OTPVerifySerializer(
            data={"username": "REUSE@EXAMPLE.COM", "otp": "123456"}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        result = serializer.save()
        self.assertFalse(result["created"])
        self.assertEqual(result["username"], user.username)
        self.assertEqual(CustomUser.objects.count(), 1)

    def test_wrong_otp_is_rejected_and_record_remains_unused(self):
        otp = OTP.objects.create(phone="09125550102", otp="123456")
        serializer = OTPVerifySerializer(data={"username": otp.phone, "otp": "654321"})
        self.assertFalse(serializer.is_valid())
        self.assertIn("اخطار", serializer.errors)
        otp.refresh_from_db()
        self.assertFalse(otp.is_used)

    def test_expired_otp_is_rejected(self):
        otp = OTP.objects.create(phone="09125550103", otp="123456")
        OTP.objects.filter(pk=otp.pk).update(created_at=timezone.now() - timedelta(minutes=6))
        serializer = OTPVerifySerializer(data={"username": otp.phone, "otp": "123456"})
        self.assertFalse(serializer.is_valid())
        self.assertIn("اخطار", serializer.errors)

    def test_otp_field_must_be_present(self):
        serializer = OTPVerifySerializer(data={"username": "09125550104"})
        self.assertFalse(serializer.is_valid())
        self.assertIn("otp", serializer.errors)

    def test_otp_cannot_exceed_six_characters(self):
        serializer = OTPVerifySerializer(
            data={"username": "09125550104", "otp": "1234567"}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("otp", serializer.errors)


class OtherSerializersTests(TestCase):
    def test_register_saves_normalized_email_and_unusable_password(self):
        serializer = RegisterSerializer(data={"email": "First@Example.COM"})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        user = serializer.save()
        self.assertEqual(user.email, "first@example.com")
        self.assertEqual(user.username, "first@example.com")
        self.assertFalse(user.has_usable_password())

    def test_google_auth_requires_a_complete_authentication_method(self):
        for data in ({}, {"code": "abc"}, {"id_token": ""}):
            with self.subTest(data=data):
                serializer = GoogleAuthSerializer(data=data)
                self.assertFalse(serializer.is_valid())

    def test_google_auth_accepts_direct_id_token(self):
        serializer = GoogleAuthSerializer(data={"id_token": "sample-token"})
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_google_auth_accepts_code_pkce_with_redirect_uri(self):
        serializer = GoogleAuthSerializer(data={
            "code": "auth-code", "code_verifier": "verifier",
            "redirect_uri": "https://example.com/callback",
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_profile_score_and_balance_cannot_be_updated_by_serializer(self):
        user = CustomUser.objects.create_user(phone="09125550105")
        serializer = UserProfileSerializer(user, data={
            "name": "New name", "balance": 900000,
            "total_score": 100, "month_score": 100,
        }, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        user.refresh_from_db()
        self.assertEqual(user.name, "New name")
        self.assertEqual(user.balance, 0)
        self.assertEqual(user.total_score, 0)
        self.assertEqual(user.month_score, 0)

    def test_other_profile_does_not_expose_phone_or_balance(self):
        user = CustomUser.objects.create_user(phone="09125550106", name="Public")
        result = OtherUserProfileSerializer(user).data
        self.assertIn("name", result)
        self.assertNotIn("phone", result)
        self.assertNotIn("email", result)
        self.assertNotIn("balance", result)

    def test_city_serializer_returns_only_id_and_name(self):
        country = Country.objects.create(name="Country")
        city = City.objects.create(name="City", country=country)
        self.assertEqual(set(CitySerializer(city).data.keys()), {"id", "name"})

    def test_home_banner_serializer_contains_public_fields(self):
        banner = HomeBanner.objects.create(
            banner="banners/home/test.jpg", message="Welcome", url="https://example.com"
        )
        self.assertEqual(
            set(HomeBannerSerializer(banner).data.keys()), {"banner", "message", "url"}
        )

    def test_transaction_serializer_does_not_expose_user(self):
        user = CustomUser.objects.create_user(phone="09125550107")
        tx = Transaction.objects.create(user=user, amount=500)
        result = TransactionSerializer(tx).data
        self.assertNotIn("user", result)
        self.assertIn("transaction_status", result)
        self.assertIn("amount", result)
