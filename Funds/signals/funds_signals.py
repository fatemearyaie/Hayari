from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from Funds.models.funds_models import Donor
from Users.models.users_models import XPTracker
from Users.models.transactions_models import Transaction


@receiver(post_save, sender=Donor)
def create_transaction_and_xp(sender, instance, created, **kwargs):
    if not created:
        return

    with transaction.atomic():
        Transaction.objects.create(
            user=instance.user,
            transaction_type=Transaction.TransactionType.Withdraw,
            transaction_status=Transaction.TransactionStatus.COMPLETE,
            payment_gateway=Transaction.PaymentGateWay.app,
            amount=instance.amount,
            balance_after=instance.user.balance - instance.amount,
        )

        XPTracker.objects.create(
            user=instance.user,
            xp=instance.xp,
            reason=XPTracker.Reason.donation,
        )
