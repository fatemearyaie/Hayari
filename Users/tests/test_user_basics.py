
from django.test import TestCase, TransactionTestCase
from Users.utils.identifier import username_identifier
from Users.serializers.users_serializers import OTPGeneratorSerializer
from Users.models.users_models import CustomUser, OTP

class UsernameIdentifierTests(TestCase):
    def test_normalizes_phone_with_spaces_and_hyphens(self):
        result = username_identifier(" 0912-345 6789 ")
        self.assertEqual(result, {"email": None,"phone":"09123456789"})

    def test_normalizes_email_with_spaces_and_uppercase(self):
        result = username_identifier(" fateme@GMAIL.COM  ")
        self.assertEqual(result, {"email":"fateme@gmail.com", "phone":None})

    def test_returns_none_for_empty_username(self):
        result = username_identifier("")
        self.assertEqual(result, {"email":None, "phone": None})


    def test_removes_plus_sign_from_phone(self):
        result = username_identifier("+989123456789")
        self.assertEqual(result,{"email": None,"phone": "989123456789"})


class OTPGeneratorSerializerTests(TestCase):

    def test_normalizes_phone_in_serializer(self):
        serializer = OTPGeneratorSerializer(data={"username": "+98 912-345 6789"})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["phone"],"989123456789")
        self.assertIsNone(serializer.validated_data["email"])


    def test_normalizes_email_in_serializer(self):
        serializer = OTPGeneratorSerializer(data={"username": "  Fateme@GMAIL.COM  "})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["email"],"fateme@gmail.com")
        self.assertIsNone(serializer.validated_data["phone"])


    def test_creates_otp_in_database(self):
        serializer = OTPGeneratorSerializer(data={"username": "09123456789"})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        otp = serializer.save()
        self.assertEqual(OTP.objects.count(), 1)
        saved_otp = OTP.objects.get(pk=otp.pk)

        self.assertEqual(saved_otp.phone, "09123456789")
        self.assertIsNone(saved_otp.email)
        self.assertFalse(saved_otp.is_used)


