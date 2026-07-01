import random

from celery import shared_task
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from Notification.models.notification_models import UserFCMToken, UserNotification
from Notification.tasks import send_firebase_task
from Users.models import CustomUser

from .models import Lottery, LotteryRewards


@shared_task
def run_active_lottery():
    with transaction.atomic():
        lottery = (
            Lottery.objects
            .select_for_update()
            .filter(is_active=True)
            .order_by("-lottery_datetime", "-id")
            .first()
        )

        if not lottery:
            return {"status": "no_active_lottery"}

        if timezone.now() < lottery.lottery_datetime:
            return {"status": "lottery_time_not_reached"}

        rewards = list(
            LotteryRewards.objects
            .select_for_update()
            .filter(lottery=lottery)
            .order_by("place", "id")
        )

        if not rewards:
            lottery.is_active = False
            lottery.save(update_fields=["is_active"])
            return {"status": "no_rewards"}

        users = list(
            CustomUser.objects
            .filter(is_active=True, month_score__gt=0)
            .values_list("id", "month_score")
        )

        if not users:
            lottery.is_active = False
            lottery.save(update_fields=["is_active"])
            return {"status": "no_eligible_users"}

        pool_ids = [user_id for user_id, score in users]
        pool_weights = [score for user_id, score in users]

        winners_count = min(len(rewards), len(pool_ids))

        winners = []
        for _ in range(winners_count):
            winner_id = random.choices(pool_ids, weights=pool_weights, k=1)[0]
            winners.append(winner_id)

            index = pool_ids.index(winner_id)
            pool_ids.pop(index)
            pool_weights.pop(index)

        notifications_payloads = []
        assigned_rewards = []

        for reward, user_id in zip(rewards, winners):
            LotteryRewards.objects.filter(id=reward.id).update(user_id=user_id)

            reward.user_id = user_id
            assigned_rewards.append(reward)

            CustomUser.objects.filter(id=user_id).update(
                balance=F("balance") + reward.amount
            )

            title = "برنده قرعه‌کشی"
            description = (
                f"تبریک! شما رتبه {reward.place} را برنده شدید "
                f"و مبلغ {int(reward.amount)} به کیف پول شما اضافه شد."
            )

            UserNotification.objects.create(
                user_id=user_id,
                title=title,
                description=description,
            )

            tokens = list(
                UserFCMToken.objects
                .filter(user_id=user_id)
                .values_list("token", flat=True)
            )

            for token in tokens:
                notifications_payloads.append({
                    "fcm": token,
                    "title": title,
                    "message": description,
                    "type": "lottery_win",
                    "lottery_id": lottery.id,
                    "place": reward.place,
                    "amount": str(reward.amount),
                })

        lottery.is_active = False
        lottery.save(update_fields=["is_active"])

        def send_notifications_after_commit():
            for payload in notifications_payloads:
                send_firebase_task.delay(payload)

        transaction.on_commit(send_notifications_after_commit)

        return {
            "status": "done",
            "lottery_id": lottery.id,
            "winners": winners,
            "assigned_rewards": [
                {
                    "reward_id": reward.id,
                    "place": reward.place,
                    "amount": str(reward.amount),
                    "user_id": reward.user_id,
                }
                for reward in assigned_rewards
            ],
        }