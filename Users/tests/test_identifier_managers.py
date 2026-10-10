"""Normalization and custom user creation (no external service calls)."""

from django.test import TestCase

from Users.models.users_models import CustomUser
from Users.utils.identifier import username_identifier


class UsernameIdentifierTests(TestCase):
    def test_phone_removes_spaces_dashes_and_plus(self):
        self.assertEqual(
            username_identifier(" +98 912-345 6789 "),
            {"email": None, "phone": "989123456789"},
        )

    def test_email_is_trimmed_and_lowercased(self):
        self.assertEqual(
            username_identifier("  FAtEmE@Example.COM  "),
            {"email": "fateme@example.com", "phone": None},
        )

    def test_empty_string_returns_no_identifiers(self):
        self.assertEqual(username_identifier(""), {"email": None, "phone": None})

    def test_none_returns_no_identifiers(self):
        self.assertEqual(username_identifier(None), {"email": None, "phone": None})

    def test_non_email_value_is_treated_as_phone(self):
        # This is the CURRENT behavior, not a proof that the number is valid.
        self.assertEqual(username_identifier("abc"), {"email": None, "phone": "abc"})


class CustomUserManagerTests(TestCase):
    def test_create_user_normalizes_phone_and_sets_username(self):
        user = CustomUser.objects.create_user(phone=" 0912-345 6789 ")
        self.assertEqual(user.phone, "09123456789")
        self.assertEqual(user.username, "09123456789")
        self.assertFalse(user.has_usable_password())

    def test_create_user_normalizes_email_and_sets_username(self):
        user = CustomUser.objects.create_user(email="  Fateme@EXAMPLE.COM  ")
        self.assertEqual(user.email, "fateme@example.com")
        self.assertEqual(user.username, "fateme@example.com")

    def test_create_user_with_password_can_authenticate_by_password(self):
        user = CustomUser.objects.create_user(email="auth@example.com", password="s3cr3t-pass")
        self.assertTrue(user.check_password("s3cr3t-pass"))
        self.assertFalse(user.check_password("incorrect"))

    def test_create_user_without_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            CustomUser.objects.create_user()

    def test_create_superuser_needs_password(self):
        with self.assertRaises(ValueError):
            CustomUser.objects.create_superuser(email="admin@example.com")

    def test_create_superuser_sets_staff_and_superuser_flags(self):
        user = CustomUser.objects.create_superuser(
            email="admin@example.com", password="secret-pass"
        )
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_active)

    def test_create_superuser_can_derive_email_from_username(self):
        user = CustomUser.objects.create_superuser(
            username="ADMIN@EXAMPLE.COM", password="secret-pass"
        )
        self.assertEqual(user.email, "admin@example.com")
        self.assertEqual(user.username, "admin@example.com")

    def test_moderation_flags_follow_model_status(self):
        user = CustomUser.objects.create_user(phone="09121110000")
        self.assertFalse(user.is_disabled())
        self.assertFalse(user.is_read_only())
        user.moderation_status = CustomUser.ModerationStatus.READ_ONLY
        self.assertTrue(user.is_read_only())
        user.moderation_status = CustomUser.ModerationStatus.DISABLED
        self.assertTrue(user.is_disabled())
        self.assertFalse(user.is_read_only())
