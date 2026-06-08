import uuid
from django.db import models

from Funds.models import FundRaising
from Users.models.users_models import CustomUser


class Transaction(models.Model):
    class TransactionStatus(models.TextChoices):
        PENDING = 'pending', 'pending'
        COMPLETE = 'complete', 'complete'
        CANCEL = 'cancel', 'cancel'
    class TransactionType(models.TextChoices):
        Withdraw = 'withdraw','withdraw'
        Deposit = 'deposit','deposit'
    class PaymentGateWay(models.TextChoices):
        Zarrinpal = 'zarrinpal','zarrinpal'
        PayPal = 'paypal', 'paypal'
        app = 'app', 'app'
    class Currency(models.TextChoices):
        Dollar = 'dollar', 'dollar'
        IRR = 'IRR', 'IRR'
    transaction_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='user_transaction')
    transaction_type = models.CharField(choices=TransactionType, default=TransactionType.Withdraw)
    transaction_status = models.CharField(choices=TransactionStatus, default=TransactionStatus.PENDING)
    payment_gateway = models.CharField(choices=PaymentGateWay, default=PaymentGateWay.Zarrinpal)
    currency = models.CharField(choices=Currency, default=Currency.IRR)

    description = models.TextField(null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=0)
    balance_after = models.DecimalField(max_digits=18, decimal_places=0, default=0)
    tracking_code = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    authority = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    from_wallet = models.BooleanField(default=True)
    wallet_used = models.DecimalField(max_digits=18, decimal_places=0, default=0)

    fundraising = models.ForeignKey(FundRaising, on_delete=models.SET_NULL, null=True, blank=True)




    class Meta:
        verbose_name = 'Transaction'
        verbose_name_plural = 'Transactions'

        indexes = [
            models.Index(fields=['transaction_id']),
            models.Index(fields=['transaction_type']),
            models.Index(fields=['transaction_status']),
            models.Index(fields=['payment_gateway']),
            models.Index(fields=['currency']),
            models.Index(fields=['amount']),
            models.Index(fields=['tracking_code']),
            models.Index(fields=['balance_after']),
        ]

    def __str__(self):
        return self.transaction_type