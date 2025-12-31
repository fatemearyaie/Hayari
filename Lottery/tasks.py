# tasks.py
from celery import shared_task
from django.db import transaction
from django.db.models import F
from django.utils import timezone
import random
from Notification.models.notification_models import UserFCMToken
from .models import Lottery, LotteryRewards
from Users.models import CustomUser
from Notification.tasks import send_firebase_task

@shared_task
def run_active_lottery():
    with transaction.atomic():
        # 1) only allow one active lottery at a time.
        # Lock the active lottery row to prevent concurrent execution
        lottery = (
            Lottery.objects
            .select_for_update()
            .filter(is_active=True)
            .order_by("-lottery_datetime", "-id")
            .first()
        )

        if not lottery:
            return

        # 2) If the draw time has not arrived yet do nothing
        if timezone.now() < lottery.lottery_datetime:
            return

        # 3) Fetch predefined rewards created by the admin
        # Lock reward rows to avoid race conditions
        rewards = list(
            LotteryRewards.objects
            .select_for_update()
            .filter(lottery=lottery)
            .order_by("place", "id")
        )
        if not rewards:
            # No rewards defined > deactivate the lottery
            lottery.is_active = False
            lottery.save(update_fields=["is_active"])
            return

        # 4) Fetch eligible users with their monthly scores
        users = list(
            CustomUser.objects
            .filter(is_active=True, month_score__gt=0)
            .values_list("id", "month_score")
        )
        if not users:
            # No eligible users > deactivate the lottery
            lottery.is_active = False
            lottery.save(update_fields=["is_active"])
            return

        # Separate user IDs and their weights
        pool_ids = [u[0] for u in users]
        pool_w   = [u[1] for u in users]

        # 5) Number of winners equals number of rewards,
        # but cannot exceed the number of eligible users
        k = min(len(rewards), len(pool_ids))

        winners = []
        for _ in range(k):
            # Select one winner using weighted random selection
            chosen = random.choices(pool_ids, weights=pool_w, k=1)[0]
            winners.append(chosen)

            # Remove the selected user so they cannot win again
            i = pool_ids.index(chosen)
            pool_ids.pop(i)
            pool_w.pop(i)

        # 6) Assign winners to rewards (place 1 > first winner)
        for r, uid in zip(rewards, winners):
            r.user_id = uid
        LotteryRewards.objects.bulk_update(rewards[:k], ["user"])

        # 7) increase each winner's balance based on rewards
        for r in rewards[:k]:
            CustomUser.objects.filter(id=r.user_id).update(
                balance=F("balance") + r.amount
            )
        # 8) send notification to winners
        for r in rewards[:k]:
            tokens = list(
                UserFCMToken.objects
                .filter(user_id=r.user_id)
                .values_list("token", flat=True)
            )

            for t in tokens:
                send_firebase_task.delay({
                    "fcm": t,
                    "title": "Lottery Winner!",
                    "message": f"You won place #{r.place} and received {int(r.amount)}.",
                    "type": "lottery_win",
                    "lottery_id": lottery.id,
                    "place": r.place,
                    "amount": str(r.amount),
                })
        # 9) Deactivate the lottery after the draw is completed
        lottery.is_active = False
        lottery.save(update_fields=["is_active"])
