from decimal import Decimal

import requests
from django.db.models import F
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.reverse import reverse

from Funds.models import FundRaising, Donor
from Funds.services.donation import donate_fundraising
from Hayari.settings.base import MERCHANT
from Users.models.users_models import CustomUser
from Users.models.transactions_models import Transaction
from Users.serializers.transactions_serializers import TransactionSerializer
from django.db import transaction as db_transaction


ZP_API_REQUEST = "https://sandbox.zarinpal.com/pg/v4/payment/request.json"
ZP_API_STARTPAY = "https://sandbox.zarinpal.com/pg/StartPay/"
ZP_API_VERIFY = "https://sandbox.zarinpal.com/pg/v4/payment/verify.json"
CallbackURL = 'http://127.0.0.1:8000/api/v1/users/zarinpal/verify/'

def status_check(transaction, status, request, authority):
    if status != "OK":
        transaction.transaction_status = Transaction.TransactionStatus.CANCEL
        transaction.save(update_fields=["transaction_status"])
        return render(request, "error_payment.html")

    payload = {
        "merchant_id": MERCHANT,
        "authority": authority,
        "amount": int(transaction.amount),
    }

    resp = requests.post(ZP_API_VERIFY, json=payload).json()
    code = resp["data"]["code"]

    if code not in (100,):
        transaction.transaction_status = Transaction.TransactionStatus.CANCEL
        transaction.save(update_fields=["transaction_status"])
        return render(request, "error_payment.html")


    return None


class TransactionView(viewsets.ReadOnlyModelViewSet):
    throttle_scope = 'custom'
    permission_classes = [IsAuthenticated]
    serializer_class = TransactionSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['transaction_status', 'transaction_type']
    ordering_fields = ['created_at', 'amount']

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

        if not fundraising_id:
            user = CustomUser.objects.get(pk=user.pk)
            tx = Transaction.objects.create(
                user=user,
                amount=amount,
                transaction_status=Transaction.TransactionStatus.PENDING,
                transaction_type=Transaction.TransactionType.Deposit,
                description=f'پرداخت بابت افزایش موجودی'
            )

            payment_url = request.build_absolute_uri(
                reverse('zarinpal-request', kwargs={'pk': tx.id}, request=request)
            )
            return Response({
                "payment_url": payment_url,
            })


        fundraising = get_object_or_404(FundRaising, pk=fundraising_id)
        with db_transaction.atomic():
            user = CustomUser.objects.select_for_update().get(pk=user.pk)
            wallet_balance = user.balance or Decimal(0)

            if amount <= wallet_balance:
                user.balance = F("balance") - amount
                user.save(update_fields=["balance"])
                user.refresh_from_db(fields=["balance"])

                tx = Transaction.objects.create(
                    user=user,
                    fundraising=fundraising,
                    amount=amount,
                    wallet_used=wallet_balance,
                    balance_after=user.balance,
                    transaction_status=Transaction.TransactionStatus.COMPLETE,
                    description=f'پرداخت بابت حمایت'
                )



                donate_fundraising(
                    user=user,
                    fundraising_id=fundraising.id,
                    amount=amount
                )

                return Response({
                    "from_wallet": True,
                    "pay_from_wallet": float(amount),
                    "pay_from_gateway": 0,
                })

            pay_from_gateway = amount - wallet_balance

            tx = Transaction.objects.create(
                user=user,
                fundraising=fundraising,
                amount=pay_from_gateway,
                wallet_used=wallet_balance,
                transaction_status=Transaction.TransactionStatus.PENDING,
                description=f'پرداخت بابت حمایت'
            )

        payment_url = request.build_absolute_uri(
            reverse('zarinpal-request', kwargs={'pk': tx.id}, request=request)
        )

        return Response({
            "from_wallet": False,
            "pay_from_wallet": float(wallet_balance),
            "pay_from_gateway": float(pay_from_gateway),
            "payment_url": payment_url,
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
        transaction.save(update_fields=["authority"])

        return redirect(ZP_API_STARTPAY + transaction.authority)

    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def verify(self, request):
        tx_id = request.GET.get("transaction_id")
        authority = request.GET.get("Authority")
        status = request.GET.get("Status")

        if not tx_id:
            return Response({"detail": "transaction_id is missing"}, status=400)

        transaction = get_object_or_404(Transaction, id=tx_id)

        # without fundraising
        if not transaction.fundraising:
            if transaction.transaction_status == Transaction.TransactionStatus.COMPLETE:
                return render(request, "success_payment.html")

            resp = status_check(transaction, status, request, authority)

            if resp is not None:
                return resp
            with db_transaction.atomic():
                tx = Transaction.objects.select_for_update().select_related("user").get(pk=transaction.pk)
                if tx.transaction_status == Transaction.TransactionStatus.COMPLETE:
                    return render(request, "success_payment.html")

                user = CustomUser.objects.select_for_update().get(pk=tx.user_id)

                tx.balance_after = user.balance
                tx.transaction_status = Transaction.TransactionStatus.COMPLETE
                tx.save(update_fields=["balance_after", "transaction_status"])

            return render(request, "success_payment.html")


        # donation flow
        if transaction.transaction_status == Transaction.TransactionStatus.COMPLETE:
            donor = Donor.objects.filter(
                user=transaction.user,
                fundraising=transaction.fundraising,
                amount=transaction.wallet_used + transaction.amount
            ).first()
            return render(request, "success_payment.html", {"donor": donor})

        resp = status_check(transaction, status, request, authority)
        if resp is not None:
            return resp

        with db_transaction.atomic():
            user = CustomUser.objects.select_for_update().get(pk=transaction.user.pk)

            if transaction.wallet_used > 0:
                user.balance = F("balance") - transaction.wallet_used
                user.save(update_fields=["balance"])

            transaction.balance_after = user.balance
            transaction.transaction_status = Transaction.TransactionStatus.COMPLETE
            transaction.save(update_fields=["transaction_status"])

            donor = Donor.objects.create(
                user=user,
                fundraising=transaction.fundraising,
                amount=transaction.wallet_used + transaction.amount,
                xp=transaction.fundraising.each_don_xp
            )

            donate_fundraising(
                user=user,
                fundraising_id=transaction.fundraising.id,
                amount=donor.amount
            )

        return render(request, "success_payment.html", {"donor": donor})


