"""Transactions, wallet payment, Zarinpal callbacks, and banner endpoints."""

from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, TransactionTestCase
from rest_framework.test import APIClient

from Funds.models import FundRaising
from Users.models.banner_models import HomeBanner
from Users.models.transactions_models import Transaction
from Users.models.users_models import City, Country, CustomUser


class PaymentBase:
    def make_fundraising(self):
        country = Country.objects.create(name="Country")
        city = City.objects.create(name="City", country=country)
        return FundRaising.objects.create(
            city=city, title="Fund", description="Example",
            total_amount=100000, each_don_xp=5,
        )


class TransactionAndPaymentAPITests(PaymentBase, TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = CustomUser.objects.create_user(phone="09126660000")

    def test_transaction_list_requires_authentication(self):
        response = self.client.get("/api/v1/users/transactions/")
        self.assertIn(response.status_code, (401, 403))

    def test_transaction_list_only_contains_own_records(self):
        other = CustomUser.objects.create_user(phone="09126660001")
        mine = Transaction.objects.create(user=self.user, amount=100)
        Transaction.objects.create(user=other, amount=200)
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/v1/users/transactions/")
        self.assertEqual(response.status_code, 200)
        data = response.data["results"] if isinstance(response.data, dict) else response.data
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["transaction_id"], str(mine.transaction_id))

    def test_payment_start_rejects_unauthenticated_user(self):
        response = self.client.post(
            "/api/v1/users/zarinpal/start/", {"amount": 100}, format="json"
        )
        self.assertIn(response.status_code, (401, 403))

    def test_payment_start_zero_amount_does_not_create_transaction(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/v1/users/zarinpal/start/", {"amount": 0}, format="json"
        )
        # The existing implementation returns HTTP 200 with an error body.
        self.assertEqual(response.status_code, 200)
        self.assertIn("error", response.data)
        self.assertFalse(Transaction.objects.exists())

    def test_wallet_topup_creates_pending_deposit_transaction(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/v1/users/zarinpal/start/", {"amount": "250"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("payment_url", response.data)
        tx = Transaction.objects.get()
        self.assertEqual(tx.amount, 250)
        self.assertEqual(tx.transaction_type, Transaction.TransactionType.Deposit)
        self.assertEqual(tx.transaction_status, Transaction.TransactionStatus.PENDING)

    @patch("Users.views.transactions_views.donate_fundraising")
    def test_donation_paid_from_wallet(self, donate):
        fundraising = self.make_fundraising()
        CustomUser.objects.filter(pk=self.user.pk).update(balance=200)
        self.user.refresh_from_db()
        self.client.force_authenticate(user=self.user)
        response = self.client.post("/api/v1/users/zarinpal/start/", {
            "amount": "200", "fundraising_id": fundraising.pk,
        }, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["from_wallet"])
        self.assertEqual(response.data["pay_from_gateway"], 0)
        self.user.refresh_from_db()
        self.assertEqual(self.user.balance, 0)
        tx = Transaction.objects.get()
        self.assertEqual(tx.transaction_status, Transaction.TransactionStatus.COMPLETE)
        donate.assert_called_once_with(
            user=self.user, fundraising_id=fundraising.pk, amount=Decimal("200")
        )

    def test_donation_partial_wallet_creates_gateway_payment(self):
        fundraising = self.make_fundraising()
        CustomUser.objects.filter(pk=self.user.pk).update(balance=30)
        self.user.refresh_from_db()
        self.client.force_authenticate(user=self.user)
        response = self.client.post("/api/v1/users/zarinpal/start/", {
            "amount": "100", "fundraising_id": fundraising.pk,
        }, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["from_wallet"])
        self.assertEqual(response.data["pay_from_wallet"], 30.0)
        self.assertEqual(response.data["pay_from_gateway"], 70.0)
        tx = Transaction.objects.get()
        self.assertEqual(tx.amount, 70)
        self.assertEqual(tx.wallet_used, 30)
        self.assertEqual(tx.transaction_status, Transaction.TransactionStatus.PENDING)

    @patch("Users.views.transactions_views.requests.post")
    def test_gateway_request_redirects_and_saves_authority(self, post):
        tx = Transaction.objects.create(user=self.user, amount=500)
        post.return_value.json.return_value = {
            "data": {"code": 100, "authority": "test-authority"}
        }
        response = self.client.get(f"/api/v1/users/zarinpal/{tx.pk}/request/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("test-authority", response["Location"])
        self.assertEqual(post.call_count, 1)
        tx.refresh_from_db()
        self.assertEqual(tx.authority, "test-authority")

    @patch("Users.views.transactions_views.requests.post")
    def test_gateway_request_rejects_failure_response(self, post):
        tx = Transaction.objects.create(user=self.user, amount=500)
        post.return_value.json.return_value = {"data": {"code": -1}}
        response = self.client.get(f"/api/v1/users/zarinpal/{tx.pk}/request/")
        self.assertEqual(response.status_code, 400)
        tx.refresh_from_db()
        self.assertIsNone(tx.authority)

    @patch("Users.views.transactions_views.requests.post")
    def test_gateway_verify_canceled_payment_marks_transaction_canceled(self, post):
        tx = Transaction.objects.create(
            user=self.user, amount=500,
            transaction_type=Transaction.TransactionType.Deposit,
        )
        response = self.client.get(
            "/api/v1/users/zarinpal/verify/",
            {"transaction_id": tx.pk, "Authority": "abc", "Status": "NOK"},
        )
        self.assertEqual(response.status_code, 200)  # HTML error page in current code
        tx.refresh_from_db()
        self.assertEqual(tx.transaction_status, Transaction.TransactionStatus.CANCEL)
        post.assert_not_called()

    @patch("Users.views.transactions_views.requests.post")
    def test_gateway_verify_topup_credits_wallet_only_once(self, post):
        tx = Transaction.objects.create(
            user=self.user, amount=500,
            transaction_type=Transaction.TransactionType.Deposit,
        )
        post.return_value.json.return_value = {"data": {"code": 100}}
        params = {"transaction_id": tx.pk, "Authority": "abc", "Status": "OK"}
        first = self.client.get("/api/v1/users/zarinpal/verify/", params)
        second = self.client.get("/api/v1/users/zarinpal/verify/", params)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.balance, 500)
        tx.refresh_from_db()
        self.assertEqual(tx.transaction_status, Transaction.TransactionStatus.COMPLETE)
        post.assert_called_once()

    def test_verify_without_transaction_id_returns_400(self):
        response = self.client.get("/api/v1/users/zarinpal/verify/")
        self.assertEqual(response.status_code, 400)

    def test_home_banner_api_lists_available_home_banners(self):
        HomeBanner.objects.create(
            banner="banners/home/test.jpg", message="Announcement",
            url="https://example.com",
        )
        response = self.client.get("/api/v1/users/home/banner/")
        self.assertEqual(response.status_code, 200)
        data = response.data["results"] if isinstance(response.data, dict) else response.data
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["message"], "Announcement")


class TransactionCommitTests(TransactionTestCase):
    """Use TransactionTestCase where we want DB commits rather than TestCase's outer atomic."""

    def test_deposit_balance_persists_across_transaction_boundaries(self):
        user = CustomUser.objects.create_user(phone="09126669999")
        tx = Transaction.objects.create(
            user=user, amount=25,
            transaction_type=Transaction.TransactionType.Deposit,
        )
        from django.db import transaction as db_transaction

        with db_transaction.atomic():
            tx.transaction_status = Transaction.TransactionStatus.COMPLETE
            tx.save(update_fields=["transaction_status"])
        user.refresh_from_db()
        self.assertEqual(user.balance, 25)
