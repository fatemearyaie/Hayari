from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from django.db.models import F
from Users.models.transactions_models import Transaction


@receiver(post_save, sender=Transaction)
def update_user_balance(sender, instance, created, **kwargs):
    if created:
        user = instance.user
        if instance.transaction_status == Transaction.TransactionStatus.COMPLETE:
            with transaction.atomic():
                if instance.transaction_type == Transaction.TransactionType.Deposit:
                    user.balance = F('balance') + instance.amount
                elif instance.transaction_type == Transaction.TransactionType.Withdraw:
                    if user.balance >= instance.amount:
                        user.balance = F('balance') - instance.amount
                    else:
                        print("Insufficient balance for withdrawal")
                        instance.transaction_status = Transaction.TransactionStatus.CANCEL
                        instance.save()

                user.save(update_fields=['balance'])
