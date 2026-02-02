from decimal import Decimal

import requests
from django.db.models import F
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets ,filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from Funds.models import FundRaising, Donor
from Hayari.settings.base import MERCHANT
from Users.models.users_models import CustomUser
from Users.models.transactions_models import Transaction
from Users.serializers.transactions_serializers import TransactionSerializer
from django.db import transaction as db_transaction
from Funds.services.donation import donate_fundraising


ZP_API_REQUEST = "https://sandbox.zarinpal.com/pg/v4/payment/request.json"
ZP_API_STARTPAY = "https://sandbox.zarinpal.com/pg/StartPay/"
ZP_API_VERIFY = "https://sandbox.zarinpal.com/pg/v4/payment/verify.json"
CallbackURL = 'http://localhost:8000/api/v1/users/zarinpal/verify/'

class TransactionView(viewsets.ReadOnlyModelViewSet):
    throttle_scope = 'custom'
    permission_classes = [IsAuthenticated]
    serializer_class = TransactionSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['transaction_status','transaction_type']
    ordering_fields = [ 'created_at','amount']

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)


class PaymentViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'])
    def start(self, request):
        user = request.user
        fundraising_id = request.data.get("fundraising_id")
        amount = Decimal(request.data.get("amount", 0))

        if amount <= 0:
            return Response({"error": "amount > 0"})

        fundraising = get_object_or_404(FundRaising, pk=fundraising_id)

        with db_transaction.atomic():
            user = CustomUser.objects.select_for_update().get(pk=user.pk)
            wallet_balance = user.balance or Decimal(0)

            pay_from_wallet = min(wallet_balance, amount)
            pay_from_gateway = amount - pay_from_wallet

            # اگر کل مبلغ از ولت بود → همینجا verify داخلی
            if pay_from_gateway == 0:
                user.balance -= amount
                user.save()

                Donor.objects.create(
                    user=user,
                    fundraising=fundraising,
                    amount=amount,
                    xp=fundraising.each_don_xp,
                )

                Transaction.objects.create(
                    user=user,
                    fundraising=fundraising,
                    amount=amount,
                    transaction_status=Transaction.TransactionStatus.COMPLETE,
                    from_wallet=True,
                )

                return Response({
                    "from_wallet": True,
                    "pay_from_wallet": float(amount),
                    "pay_from_gateway": 0,
                })

            # اگر ترکیبی یا فقط زرین پال
            tx = Transaction.objects.create(
                user=user,
                fundraising=fundraising,
                amount=pay_from_gateway,
                transaction_status=Transaction.TransactionStatus.PENDING,
                from_wallet=False,
            )

        url = request.build_absolute_uri(f"/api/zarinpal/{tx.id}/request/")
        return Response({
            "from_wallet": False,
            "pay_from_wallet": float(pay_from_wallet),
            "pay_from_gateway": float(pay_from_gateway),
            "payment_url": url,
        })


    @action(detail=True, methods=['get'], permission_classes=[AllowAny])
    def request(self, request, pk=None):
        transaction = get_object_or_404(Transaction, id=pk)

        payload = {
            "merchant_id": MERCHANT,
            "amount": int(transaction.amount),
            "callback_url": f"{CallbackURL}?transaction_id={transaction.id}",
            "description": "donation",
        }

        resp = requests.post(ZP_API_REQUEST, json=payload).json()
        if resp["data"]["code"] != 100:
            return HttpResponse(str(resp), status=400)

        transaction.authority = resp["data"]["authority"]
        transaction.save()

        return redirect(ZP_API_STARTPAY + transaction.authority)

    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def verify(self, request):
        tx_id = request.GET.get("transaction_id")
        authority = request.GET.get("Authority")
        status = request.GET.get("Status")

        transaction = get_object_or_404(Transaction, id=tx_id)

        if status != "OK":
            transaction.transaction_status = Transaction.TransactionStatus.CANCEL
            transaction.save()
            return render(request, "error_payment.html")

        payload = {
            "merchant_id": MERCHANT,
            "authority": authority,
            "amount": int(transaction.amount),
        }

        resp = requests.post(ZP_API_VERIFY, json=payload).json()
        code = resp["data"]["code"]

        if code not in [100, 101]:
            transaction.transaction_status = Transaction.TransactionStatus.CANCEL
            transaction.save()
            return render(request, "error_payment.html")

        with db_transaction.atomic():
            transaction.transaction_status = Transaction.TransactionStatus.COMPLETE
            transaction.save()

            donor = Donor.objects.create(
                user=transaction.user,
                fundraising=transaction.fundraising,
                amount=transaction.amount,
                xp=transaction.fundraising.each_don_xp
            )

        return render(request, "success_payment.html", {"donor": donor})



