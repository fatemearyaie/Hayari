
from django.test import TestCase, TransactionTestCase
from Users.utils.identifier import username_identifier

class UsernameIdentifierTests(TestCase):
    def test_normalizes_phone_with_spaces_and_hyphens(self):
        result = username_identifier(" 0912-345 6789 ")
        self.assertEqual(result, {"email": None,"phone":"09123456789"})