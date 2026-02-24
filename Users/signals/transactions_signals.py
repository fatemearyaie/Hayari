from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.db import transaction as db_transaction
from django.db.models import F
from Users.models.transactions_models import Transaction
from Users.models.users_models import CustomUser

@receiver(pre_save, sender=Transaction)
def apply_balance_on_complete(sender, instance, **kwargs):
    if not instance.pk:
        return

    old = Transaction.objects.filter(pk=instance.pk).values(
        "transaction_status", "transaction_type", "amount", "user_id"
    ).first()
    if not old:
        return

    was_complete = old["transaction_status"] == Transaction.TransactionStatus.COMPLETE
    will_complete = instance.transaction_status == Transaction.TransactionStatus.COMPLETE

    if was_complete or not will_complete:
        return

    amount = int(instance.amount)
    user_id = instance.user_id

    with db_transaction.atomic():
        if instance.transaction_type == Transaction.TransactionType.Deposit:
            CustomUser.objects.filter(id=user_id).update(balance=F("balance") + amount)

        elif instance.transaction_type == Transaction.TransactionType.Withdraw:
            updated = CustomUser.objects.filter(id=user_id, balance__gte=amount).update(
                balance=F("balance") - amount
            )
            if updated == 0:
                instance.transaction_status = Transaction.TransactionStatus.COMPLETE
