from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from Users.models.users_models import XPTracker
from Users.models.transactions_models import Transaction
from Funds.models.funds_models import Donor

@receiver(post_save, sender=Donor)
def create_transaction_and_xp(sender, instance, created, **kwargs):
    if not created:
        return

    with transaction.atomic():
        user = instance.user

        is_gateway = Transaction.objects.filter(
            user=user,
            fundraising=instance.fundraising,
            transaction_status=Transaction.TransactionStatus.COMPLETE,
            payment_gateway=Transaction.PaymentGateWay.Zarrinpal,
        ).exists()

        if not is_gateway:
            Transaction.objects.create(
                user=user,
                fundraising=instance.fundraising,
                transaction_type=Transaction.TransactionType.Withdraw,
                transaction_status=Transaction.TransactionStatus.COMPLETE,
                payment_gateway=Transaction.PaymentGateWay.app,
                amount=instance.amount,
                balance_after=user.balance,
                description=f"donation for {instance.fundraising.title}",
            )

        XPTracker.objects.create(
            user=user,
            xp=instance.xp,
            reason=XPTracker.Reason.donation,
        )