import requests
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets ,filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from Hayari.settings.base import MERCHANT
from Users.models.users_models import CustomUser
from Users.models.transactions_models import Transaction
from Users.serializers.transactions_serializers import TransactionSerializer
from django.db import transaction as db_transaction

ZP_API_REQUEST = "https://sandbox.zarinpal.com/pg/v4/payment/request.json"
ZP_API_STARTPAY = "https://sandbox.zarinpal.com/pg/StartPay/"
ZP_API_VERIFY = "https://sandbox.zarinpal.com/pg/v4/payment/verify.json"
CallbackURL = 'http://localhost:8000/api/v1/users/zarinpal/verify/'

class TransactionView(viewsets.ModelViewSet):
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

    @action(detail=False,methods=['post'])
    def start(self, request):
        user = CustomUser.objects.get(id=request.user.id)
        amount = request.data.get('amount')
        if not amount:
            return Response({'amount':'amount is neccessary!'})
        transaction = Transaction.objects.create(
            user = user,
            amount = amount,
            transaction_status = Transaction.TransactionStatus.PENDING,
        )
        internal_url = request.build_absolute_uri(
            f"/api/v1/users/zarinpal/{transaction.id}/request/"
        )
        return Response({
            "transaction_id": transaction.id,
            "amount": transaction.amount,
            "payment_url": internal_url,
        })

    @action(detail=True, methods=['get'], permission_classes=[AllowAny])
    def request(self, request, pk=None):
        transaction = get_object_or_404(Transaction, id=pk)

        if transaction.authority:
            return redirect(f"{ZP_API_STARTPAY}{transaction.authority}")

        callback_url = f"{CallbackURL}?transaction_id={transaction.id}"

        payload = {
            "merchant_id": MERCHANT,
            "amount": int(transaction.amount),
            "callback_url": callback_url,
            "description": transaction.description or "payment",
        }

        try:
            resp = requests.post(ZP_API_REQUEST, json=payload, timeout=10)
            resp_json = resp.json()
        except requests.RequestException:
            return HttpResponse("payment gateway request failed", status=502)
        except ValueError:
            return HttpResponse("invalid gateway response", status=502)

        errors = resp_json.get("errors")
        data = resp_json.get("data")

        if errors:
            return HttpResponse(f"zarinpal error: {errors}", status=400)

        if not data or data.get("code") != 100:
            return HttpResponse(f"zarinpal response: {resp_json}", status=400)

        transaction.authority = data["authority"]
        transaction.save()

        return redirect(f"{ZP_API_STARTPAY}{transaction.authority}")

    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def verify(self, request):
        authority = request.GET.get('authority') or request.GET.get('Authority')
        status = request.GET.get('status') or request.GET.get('Status')
        tx_id = request.GET.get('transaction_id')

        if not tx_id or not authority:
            return HttpResponse('Invalid CallBack Parameter!')

        transaction = get_object_or_404(Transaction, id=tx_id)

        if not transaction.authority:
            transaction.authority = authority
            transaction.save()

        if status is None or status.lower() != 'ok':
            transaction.transaction_status = Transaction.TransactionStatus.CANCEL
            transaction.save()
            context = {
                "transaction": transaction,
                'error': 'payment canceled!'
            }
            return render(request, 'error_payment.html', context)

        payload = {
            "merchant_id": MERCHANT,
            "authority": authority,
            "amount": int(transaction.amount),
        }

        try:
            resp = requests.post(ZP_API_VERIFY, json=payload, timeout=10)
        except requests.RequestException:
            transaction.transaction_status = Transaction.TransactionStatus.CANCEL
            transaction.save()
            context = {
                "transaction": transaction,
                "error": "Network error"
            }
            return render(request, 'error_payment.html', context)

        if resp.status_code != 200:
            transaction.transaction_status = Transaction.TransactionStatus.CANCEL
            transaction.save()
            context = {
                "transaction": transaction,
                "error": "Gateway error"
            }
            return render(request, 'error_payment.html', context)

        resp_json = resp.json()
        data = resp_json.get("data", {})
        code = data.get('code')
        ref_id = data.get('ref_id') or data.get('refId')

        if code in (100,101):
            try:
                with db_transaction.atomic():
                    transaction.transaction_status = Transaction.TransactionStatus.COMPLETE
                    transaction.transaction_type = Transaction.TransactionType.Deposit
                    transaction.save()

                context = {
                    "tracking_code": ref_id,
                    "transaction": transaction,
                }
                return render(request, 'success_payment.html', context)

            except Exception as e:
                context = {
                    "transaction": transaction,
                    "error": f"Internal database error: {str(e)}"
                }
                return render(request, 'error_payment.html', context)

        else:
            transaction.transaction_status = Transaction.TransactionStatus.CANCEL
            transaction.save()
            context = {
                "transaction": transaction,
                "error": f"Payment failed with code {code}"
            }
            return render(request, 'error_payment.html', context)

