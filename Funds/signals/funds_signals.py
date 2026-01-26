from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta

from Funds.models.funds_models import Donor
from Users.models.users_models import XPTracker
from Users.models.transactions_models import Transaction


@receiver(post_save, sender=Donor)
def create_transaction_and_xp(sender, instance, created, **kwargs):
    if not created:
        return

    with transaction.atomic():
        user = instance.user

        # ✅ تشخیص donate از درگاه (برای اینکه بالانس کم نشه)
        recent_from = timezone.now() - timedelta(minutes=10)

        is_gateway_donation = Transaction.objects.filter(
            user=user,
            transaction_status=Transaction.TransactionStatus.COMPLETE,
            transaction_type=Transaction.TransactionType.Deposit,
            amount=instance.amount,
            description__contains="donate:",
            created_at__gte=recent_from,  # اگر created_at داری
        ).exists()

        if not is_gateway_donation:
            # ✅ donate از کیف پول => کسر موجودی + ثبت Withdraw
            user.balance -= instance.amount
            user.save(update_fields=["balance"])

            Transaction.objects.create(
                user=user,
                fundraising=instance.fundraising,  # ✅ این خط کلیدی بود
                transaction_type=Transaction.TransactionType.Withdraw,
                transaction_status=Transaction.TransactionStatus.COMPLETE,
                payment_gateway=Transaction.PaymentGateWay.app,
                amount=instance.amount,
                balance_after=user.balance,  # ✅ درست
            )

        # ✅ XP همیشه ثبت میشه
        XPTracker.objects.create(
            user=user,
            xp=instance.xp,
            reason=XPTracker.Reason.donation,
        )
